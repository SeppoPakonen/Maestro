"""
Ops run executor - deterministic runbook execution.

Executes ops plans (YAML-based action lists) that call Maestro subcommands.
"""

import json
import os
import subprocess
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from maestro.config.paths import get_docs_root

try:
    import yaml
except Exception:
    yaml = None


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_index: int
    command: str
    started_at: str
    exit_code: int
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL output."""
        result = {
            "step_index": self.step_index,
            "command": self.command,
            "started_at": self.started_at,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class RunResult:
    """Result of executing an entire ops run."""
    run_id: str
    plan_name: str
    plan_path: str
    started_at: str
    completed_at: str
    dry_run: bool
    exit_code: int
    step_results: List[StepResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_meta_dict(self) -> Dict[str, Any]:
        """Convert to meta.json format."""
        result = {
            "run_id": self.run_id,
            "plan_name": self.plan_name,
            "plan_path": self.plan_path,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dry_run": self.dry_run,
            "exit_code": self.exit_code,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary.json format."""
        successful = sum(1 for r in self.step_results if r.exit_code == 0)
        failed = len(self.step_results) - successful
        total_duration = sum(r.duration_ms for r in self.step_results)

        return {
            "total_steps": len(self.step_results),
            "successful_steps": successful,
            "failed_steps": failed,
            "total_duration_ms": total_duration,
            "exit_code": self.exit_code,
        }


def generate_run_id(plan_name: str) -> str:
    """Generate a deterministic run ID.

    Format: <timestamp>_ops_run_<hash>
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Simple hash from plan name
    import hashlib
    name_hash = hashlib.md5(plan_name.encode()).hexdigest()[:4]
    return f"{timestamp}_ops_run_{name_hash}"


def load_ops_plan(plan_path: Path) -> Dict[str, Any]:
    """Load and validate ops plan YAML.

    Args:
        plan_path: Path to plan YAML file

    Returns:
        Parsed plan dict

    Raises:
        ValueError: If plan is invalid
    """
    if not plan_path.exists():
        raise ValueError(f"Plan file not found: {plan_path}")

    if yaml is None:
        raise ValueError("YAML support not available. Install pyyaml to use ops run.")

    try:
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

    # Validate structure
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a YAML object")

    if plan.get("kind") != "ops_run":
        raise ValueError(f"Invalid kind: {plan.get('kind')} (expected: ops_run)")

    if "name" not in plan:
        raise ValueError("Plan must have a 'name' field")

    if "steps" not in plan or not isinstance(plan["steps"], list):
        raise ValueError("Plan must have a 'steps' list")

    if "allow_legacy" in plan and not isinstance(plan["allow_legacy"], bool):
        raise ValueError("Plan 'allow_legacy' must be a boolean if provided")

    # Validate steps
    for i, step in enumerate(plan["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} must be an object")

        # Support both old format (maestro: "string") and new format (kind: maestro, args: [...])
        if "kind" in step:
            # New structured format
            if step["kind"] != "maestro":
                raise ValueError(f"Step {i}: only 'maestro' kind is supported, got '{step['kind']}'")

            if "args" not in step:
                raise ValueError(f"Step {i}: structured format requires 'args' field")

            if not isinstance(step["args"], list):
                raise ValueError(f"Step {i}: 'args' must be a list")

            # Optional fields validation
            if "timeout_s" in step and not isinstance(step["timeout_s"], (int, float)):
                raise ValueError(f"Step {i}: 'timeout_s' must be a number")

            if "cwd" in step and not isinstance(step["cwd"], str):
                raise ValueError(f"Step {i}: 'cwd' must be a string")

            if "allow_write" in step and not isinstance(step["allow_write"], bool):
                raise ValueError(f"Step {i}: 'allow_write' must be a boolean")

        elif "maestro" in step:
            # Old simple format (backward compatibility)
            if not isinstance(step["maestro"], str):
                raise ValueError(f"Step {i}: 'maestro' value must be a string")
        else:
            raise ValueError(f"Step {i}: must have either 'maestro' or 'kind' field")

    return plan


def resolve_placeholders(
    command: str,
    placeholders: Dict[str, Optional[str]],
    allow_unresolved: bool = False
) -> str:
    """Replace known placeholders in a command string."""
    unresolved = [key for key, value in placeholders.items() if key in command and not value]
    if unresolved and not allow_unresolved:
        raise ValueError(f"Missing placeholder values: {', '.join(unresolved)}")

    resolved = command
    for key, value in placeholders.items():
        if value:
            resolved = resolved.replace(key, value)
    return resolved


def extract_scan_id(output: str) -> Optional[str]:
    """Extract log scan ID from command output."""
    for line in output.splitlines():
        match = re.match(r"Scan created:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
    return None


def extract_workgraph_id(output: str) -> Optional[str]:
    """Extract WorkGraph ID from command output.

    Looks for patterns like:
    - "WorkGraph created: wg-20260101-a3f5b8c2"
    - "WorkGraph ID: wg-20260101-a3f5b8c2"
    - "WorkGraph materialized: wg-20260101-a3f5b8c2"
    - "created WorkGraph instead ... WorkGraph ID: wg-..."
    """
    for line in output.splitlines():
        # Try "WorkGraph created: <id>" pattern
        match = re.search(r"WorkGraph created:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
        # Try "WorkGraph ID: <id>" pattern
        match = re.search(r"WorkGraph ID:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
        # Try "WorkGraph materialized: <id>" pattern
        match = re.search(r"WorkGraph materialized:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
    return None


def extract_workgraph_run_id(output: str) -> Optional[str]:
    """Extract WorkGraph run ID from command output.

    Looks for patterns like:
    - "Run completed: wr-20260101-120000-a3f5b8c2"
    - "Run ID: wr-20260101-120000-a3f5b8c2"
    """
    for line in output.splitlines():
        # Try "Run completed: <id>" pattern
        match = re.search(r"Run completed:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
        # Try "Run ID: <id>" pattern (for future compatibility)
        match = re.search(r"Run ID:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
    return None


def execute_step(
    command: str,
    dry_run: bool = False,
    docs_root: Optional[Path] = None,
    allow_legacy: bool = False,
    timeout: int = 300,
    cwd: Optional[str] = None
) -> StepResult:
    """Execute a single maestro command step.

    Args:
        command: Maestro command to execute (without 'maestro' prefix)
        dry_run: If True, don't actually execute
        docs_root: Override docs root for testing
        allow_legacy: If True, allow legacy commands
        timeout: Command timeout in seconds (default 300)
        cwd: Working directory for command execution

    Returns:
        StepResult with execution details
    """
    started_at = datetime.now().isoformat()
    start_time = datetime.now()

    if dry_run:
        # Dry-run mode: don't execute, just log
        duration_ms = 0
        return StepResult(
            step_index=0,  # Will be set by caller
            command=command,
            started_at=started_at,
            exit_code=0,
            duration_ms=duration_ms,
            stdout="[DRY RUN]",
            stderr="",
            metadata={}
        )

    # Determine maestro entrypoint
    maestro_bin = os.environ.get("MAESTRO_BIN")
    if maestro_bin:
        # Use explicitly set binary
        cmd_parts = [maestro_bin] + command.split()
    elif Path("./maestro.py").exists():
        # Use local maestro.py
        cmd_parts = [sys.executable, "./maestro.py"] + command.split()
    else:
        # Use python -m maestro
        cmd_parts = [sys.executable, "-m", "maestro"] + command.split()

    # Set up environment
    env = os.environ.copy()
    if docs_root:
        env["MAESTRO_DOCS_ROOT"] = str(docs_root)
    env["MAESTRO_ENABLE_LEGACY"] = "1" if allow_legacy else "0"

    # Execute
    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            cwd=cwd  # Use specified working directory if provided
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        exit_code = 124  # Standard timeout exit code
        stdout = ""
        stderr = f"Step timed out after {timeout} seconds"
    except Exception as e:
        exit_code = 1
        stdout = ""
        stderr = f"Failed to execute: {e}"

    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    # Extract metadata from output (scan IDs, workgraph IDs, run IDs)
    metadata = {}
    if stdout:
        scan_id = extract_scan_id(stdout)
        if scan_id:
            metadata["scan_id"] = scan_id

        wg_id = extract_workgraph_id(stdout)
        if wg_id:
            metadata["workgraph_id"] = wg_id

        wg_run_id = extract_workgraph_run_id(stdout)
        if wg_run_id:
            metadata["workgraph_run_id"] = wg_run_id

    return StepResult(
        step_index=0,  # Will be set by caller
        command=command,
        started_at=started_at,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr,
        metadata=metadata
    )


def create_run_record(result: RunResult, docs_root: Optional[Path] = None) -> Path:
    """Create run record directory and files.

    Args:
        result: RunResult to write
        docs_root: Override docs root for testing

    Returns:
        Path to run record directory
    """
    if not docs_root:
        docs_root = get_docs_root()

    # Create run directory
    run_dir = docs_root / "docs" / "maestro" / "ops" / "runs" / result.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write meta.json
    with open(run_dir / "meta.json", 'w', encoding='utf-8') as f:
        json.dump(result.to_meta_dict(), f, indent=2)

    # Write steps.jsonl
    with open(run_dir / "steps.jsonl", 'w', encoding='utf-8') as f:
        for step in result.step_results:
            f.write(json.dumps(step.to_dict()) + "\n")

    # Write stdout.txt
    with open(run_dir / "stdout.txt", 'w', encoding='utf-8') as f:
        for step in result.step_results:
            if step.stdout:
                f.write(f"=== Step {step.step_index}: {step.command} ===\n")
                f.write(step.stdout)
                f.write("\n\n")

    # Write stderr.txt
    with open(run_dir / "stderr.txt", 'w', encoding='utf-8') as f:
        for step in result.step_results:
            if step.stderr:
                f.write(f"=== Step {step.step_index}: {step.command} ===\n")
                f.write(step.stderr)
                f.write("\n\n")

    # Write summary.json
    with open(run_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(result.to_summary_dict(), f, indent=2)

    return run_dir


def update_run_index(result: RunResult, docs_root: Optional[Path] = None) -> None:
    """Update ops run index.

    Args:
        result: RunResult to add to index
        docs_root: Override docs root for testing
    """
    if not docs_root:
        docs_root = get_docs_root()

    index_path = docs_root / "docs" / "maestro" / "ops" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing index
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {"runs": []}

    # Add new run
    index["runs"].append({
        "run_id": result.run_id,
        "plan_name": result.plan_name,
        "started_at": result.started_at,
        "exit_code": result.exit_code,
    })

    # Write back
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)


def run_ops_plan(
    plan_path: Path,
    dry_run: bool = False,
    continue_on_error: bool = False,
    docs_root: Optional[Path] = None,
    execute_writes: bool = False
) -> RunResult:
    """Execute an ops plan.

    Args:
        plan_path: Path to ops plan YAML
        dry_run: If True, show what would be executed without running
        continue_on_error: If True, continue executing steps even if one fails
        docs_root: Override docs root for testing
        execute_writes: If True, allow write steps to execute (default: False)

    Returns:
        RunResult with execution details
    """
    # Load plan
    plan = load_ops_plan(plan_path)

    # Generate run ID
    run_id = generate_run_id(plan["name"])
    allow_legacy = bool(plan.get("allow_legacy", False))

    placeholders: Dict[str, Optional[str]] = {
        "<LAST_RUN_ID>": run_id,
        "<LAST_SCAN_ID>": None,
        "<LAST_WORKGRAPH_ID>": None,
        "<LAST_WORKGRAPH_RUN_ID>": None,
    }

    # Initialize result
    started_at = datetime.now().isoformat()
    result = RunResult(
        run_id=run_id,
        plan_name=plan["name"],
        plan_path=str(plan_path.resolve()),
        started_at=started_at,
        completed_at="",
        dry_run=dry_run,
        exit_code=0,
        step_results=[]
    )

    # Execute steps
    for i, step in enumerate(plan["steps"]):
        # Extract command from step (support both old and new formats)
        if "kind" in step:
            # New structured format
            # Convert args list to command string
            raw_command = " ".join(step["args"])
            timeout = int(step.get("timeout_s", 300))
            cwd = step.get("cwd")
            allow_write = step.get("allow_write", False)
        else:
            # Old simple format
            raw_command = step["maestro"]
            timeout = 300
            cwd = None
            allow_write = False

        # Resolve placeholders in command
        command = resolve_placeholders(
            raw_command,
            placeholders,
            allow_unresolved=dry_run
        )

        # Check if this is a write step that should be skipped
        step_dry_run = dry_run
        if allow_write and not execute_writes and not dry_run:
            # This is a write step but --execute was not passed
            # Force dry-run mode for this step
            step_dry_run = True

        # Execute step
        step_result = execute_step(
            command,
            dry_run=step_dry_run,
            docs_root=docs_root,
            allow_legacy=allow_legacy,
            timeout=timeout,
            cwd=cwd
        )
        step_result.step_index = i
        result.step_results.append(step_result)

        # Update placeholders from step metadata
        if step_result.exit_code == 0 and step_result.metadata:
            if "scan_id" in step_result.metadata:
                placeholders["<LAST_SCAN_ID>"] = step_result.metadata["scan_id"]
            if "workgraph_id" in step_result.metadata:
                placeholders["<LAST_WORKGRAPH_ID>"] = step_result.metadata["workgraph_id"]
            if "workgraph_run_id" in step_result.metadata:
                placeholders["<LAST_WORKGRAPH_RUN_ID>"] = step_result.metadata["workgraph_run_id"]

        # Aggregate metadata into run result
        if step_result.metadata:
            for key, value in step_result.metadata.items():
                # Store with step index prefix to avoid conflicts
                result.metadata[f"step_{i}_{key}"] = value
                # Also store as last known value (for easy access)
                result.metadata[f"last_{key}"] = value

        # Check for failure
        if step_result.exit_code != 0:
            if not continue_on_error:
                # Stop on first failure
                result.exit_code = 2
                break
            else:
                # Note failure but continue
                result.exit_code = 1

    # Complete
    result.completed_at = datetime.now().isoformat()

    # Create run record
    create_run_record(result, docs_root)

    # Update index
    update_run_index(result, docs_root)

    return result


def list_ops_runs(docs_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all ops runs.

    Args:
        docs_root: Override docs root for testing

    Returns:
        List of run summaries
    """
    if not docs_root:
        docs_root = get_docs_root()

    index_path = docs_root / "docs" / "maestro" / "ops" / "index.json"

    if not index_path.exists():
        return []

    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    return index.get("runs", [])


def show_ops_run(run_id: str, docs_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Show details of a specific ops run.

    Args:
        run_id: Run ID to show
        docs_root: Override docs root for testing

    Returns:
        Run details dict or None if not found
    """
    if not docs_root:
        docs_root = get_docs_root()

    run_dir = docs_root / "docs" / "maestro" / "ops" / "runs" / run_id

    if not run_dir.exists():
        return None

    # Load all run data
    with open(run_dir / "meta.json", 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(run_dir / "summary.json", 'r', encoding='utf-8') as f:
        summary = json.load(f)

    # Load steps
    steps = []
    with open(run_dir / "steps.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            steps.append(json.loads(line))

    return {
        "meta": meta,
        "summary": summary,
        "steps": steps,
    }
