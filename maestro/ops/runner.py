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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL output."""
        return {
            "step_index": self.step_index,
            "command": self.command,
            "started_at": self.started_at,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }


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

    def to_meta_dict(self) -> Dict[str, Any]:
        """Convert to meta.json format."""
        return {
            "run_id": self.run_id,
            "plan_name": self.plan_name,
            "plan_path": self.plan_path,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dry_run": self.dry_run,
            "exit_code": self.exit_code,
        }

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

        if "maestro" not in step:
            raise ValueError(f"Step {i} must have a 'maestro' key")

        if not isinstance(step["maestro"], str):
            raise ValueError(f"Step {i} 'maestro' value must be a string")

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


def execute_step(
    command: str,
    dry_run: bool = False,
    docs_root: Optional[Path] = None,
    allow_legacy: bool = False
) -> StepResult:
    """Execute a single maestro command step.

    Args:
        command: Maestro command to execute (without 'maestro' prefix)
        dry_run: If True, don't actually execute
        docs_root: Override docs root for testing
        allow_legacy: If True, allow legacy commands

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
            stderr=""
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
            timeout=300  # 5 minute timeout per step
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        exit_code = 124  # Standard timeout exit code
        stdout = ""
        stderr = "Step timed out after 300 seconds"
    except Exception as e:
        exit_code = 1
        stdout = ""
        stderr = f"Failed to execute: {e}"

    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return StepResult(
        step_index=0,  # Will be set by caller
        command=command,
        started_at=started_at,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr
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
    docs_root: Optional[Path] = None
) -> RunResult:
    """Execute an ops plan.

    Args:
        plan_path: Path to ops plan YAML
        dry_run: If True, show what would be executed without running
        continue_on_error: If True, continue executing steps even if one fails
        docs_root: Override docs root for testing

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
        raw_command = step["maestro"]
        command = resolve_placeholders(
            raw_command,
            placeholders,
            allow_unresolved=dry_run
        )

        step_result = execute_step(
            command,
            dry_run=dry_run,
            docs_root=docs_root,
            allow_legacy=allow_legacy
        )
        step_result.step_index = i
        result.step_results.append(step_result)

        if step_result.exit_code == 0:
            scan_id = extract_scan_id(step_result.stdout)
            if scan_id:
                placeholders["<LAST_SCAN_ID>"] = scan_id

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
