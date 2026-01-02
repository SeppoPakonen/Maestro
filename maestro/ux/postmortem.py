"""
UX postmortem: Convert UX eval findings into issues and WorkGraph.

This module provides tools for turning blindfold UX evaluation results into
actionable work items (issues) and optionally a WorkGraph for fixes.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


def load_eval_artifacts(eval_dir: Path) -> Dict[str, Any]:
    """
    Load all artifacts from a UX eval directory.

    Args:
        eval_dir: Path to the UX eval directory

    Returns:
        Dict with keys: telemetry, attempts, surface, report_text

    Raises:
        FileNotFoundError: If required artifacts are missing
        json.JSONDecodeError: If JSON is invalid
    """
    artifacts = {}

    # Load telemetry.json
    telemetry_file = eval_dir / "telemetry.json"
    if not telemetry_file.exists():
        raise FileNotFoundError(f"Missing telemetry.json: {telemetry_file}")

    with open(telemetry_file, 'r') as f:
        artifacts['telemetry'] = json.load(f)

    # Load attempts.jsonl
    attempts_file = eval_dir / "attempts.jsonl"
    if not attempts_file.exists():
        raise FileNotFoundError(f"Missing attempts.jsonl: {attempts_file}")

    attempts = []
    with open(attempts_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                attempts.append(json.loads(line))
    artifacts['attempts'] = attempts

    # Load surface.json
    surface_file = eval_dir / "surface.json"
    if not surface_file.exists():
        raise FileNotFoundError(f"Missing surface.json: {surface_file}")

    with open(surface_file, 'r') as f:
        artifacts['surface'] = json.load(f)

    # Load report.md (optional, best-effort)
    eval_id = eval_dir.name
    report_file = eval_dir / f"{eval_id}.md"
    if report_file.exists():
        with open(report_file, 'r') as f:
            artifacts['report_text'] = f.read()
    else:
        artifacts['report_text'] = ""

    return artifacts


def build_ux_log(
    attempts: List[Dict[str, Any]],
    surface: Dict[str, Any],
    report_text: str,
    goal: str
) -> str:
    """
    Build a synthetic log from UX eval attempts.

    This log is shaped to be valuable to the existing log scanner:
    - Includes "tool:" tokens for commands
    - Includes "error:" lines for failures
    - Includes timeout and unknown command markers
    - Includes bounded help excerpts

    Args:
        attempts: List of attempt records from attempts.jsonl
        surface: Discovered surface from surface.json
        report_text: Report markdown text
        goal: Original UX eval goal

    Returns:
        Synthetic log string (deterministic)
    """
    lines = []

    # Header
    lines.append("="*70)
    lines.append("UX EVALUATION SYNTHETIC LOG")
    lines.append("="*70)
    lines.append("")
    lines.append(f"Goal: {goal}")
    lines.append(f"Total Attempts: {len(attempts)}")
    lines.append("")

    # Summarize surface discovery
    lines.append("--- Surface Discovery ---")
    discovered_count = len(surface.get('surface', {}))
    lines.append(f"Discovered {discovered_count} commands via help text crawl")
    lines.append("")

    # Process each attempt
    for i, attempt in enumerate(attempts):
        attempt_index = attempt.get('attempt_index', i)
        command_argv = attempt.get('command_argv', [])
        exit_code = attempt.get('exit_code', 0)
        duration_ms = attempt.get('duration_ms', 0)
        stdout_excerpt = attempt.get('stdout_excerpt', '')
        stderr_excerpt = attempt.get('stderr_excerpt', '')
        timed_out = attempt.get('timed_out', False)
        timestamp = attempt.get('timestamp', '')

        lines.append(f"--- Attempt {attempt_index + 1}: {' '.join(command_argv)} ---")
        lines.append(f"Timestamp: {timestamp}")
        lines.append(f"Duration: {duration_ms}ms")

        # Tool marker (for log scanner)
        tool_name = ' '.join(command_argv[1:]) if len(command_argv) > 1 else 'maestro'
        lines.append(f"tool: {tool_name}")

        # Status
        if timed_out:
            lines.append("status: TIMEOUT")
            lines.append("error: Command timed out after 30 seconds")
        elif exit_code == 127:
            lines.append("status: UNKNOWN_COMMAND")
            lines.append(f"error: Unknown command or subcommand: {tool_name}")
        elif exit_code != 0:
            lines.append(f"status: FAILED (exit {exit_code})")
            if stderr_excerpt:
                lines.append(f"error: {stderr_excerpt[:200]}")
        else:
            lines.append("status: SUCCESS")

        # Output excerpts (bounded)
        if stdout_excerpt and stdout_excerpt != "[DRY RUN]":
            lines.append("stdout (excerpt):")
            for line in stdout_excerpt[:500].split('\n')[:10]:
                lines.append(f"  {line}")

        if stderr_excerpt and stderr_excerpt not in ["[TIMEOUT]", ""]:
            lines.append("stderr (excerpt):")
            for line in stderr_excerpt[:500].split('\n')[:10]:
                lines.append(f"  {line}")

        lines.append("")

    # Failure summary
    failed_attempts = [a for a in attempts if a.get('exit_code', 0) != 0 or a.get('timed_out', False)]
    timeout_attempts = [a for a in attempts if a.get('timed_out', False)]
    unknown_attempts = [a for a in attempts if a.get('exit_code', 0) == 127]

    lines.append("--- Failure Summary ---")
    lines.append(f"Total Failures: {len(failed_attempts)}")
    lines.append(f"Timeouts: {len(timeout_attempts)}")
    lines.append(f"Unknown Commands: {len(unknown_attempts)}")
    lines.append(f"Other Failures: {len(failed_attempts) - len(timeout_attempts) - len(unknown_attempts)}")
    lines.append("")

    # UX friction signals (for issue categorization)
    lines.append("--- UX Friction Signals ---")

    if len(unknown_attempts) > 0:
        lines.append(f"signal: high_unknown_command_rate ({len(unknown_attempts)}/{len(attempts)})")
        lines.append("  Suggests: Poor subcommand discovery in help text")

    if len(timeout_attempts) > 0:
        lines.append(f"signal: command_timeouts ({len(timeout_attempts)}/{len(attempts)})")
        lines.append("  Suggests: Performance issues or async handling problems")

    help_to_attempt_ratio = surface.get('help_call_count', 0) / max(len(attempts), 1)
    if help_to_attempt_ratio > 3:
        lines.append(f"signal: high_help_to_attempt_ratio ({help_to_attempt_ratio:.1f})")
        lines.append("  Suggests: Unclear help text requiring multiple lookups")

    if len([a for a in attempts if a.get('exit_code', 0) == 0]) == 0:
        lines.append("signal: zero_successful_attempts")
        lines.append("  Suggests: Missing examples or poor onboarding")

    lines.append("")

    # Report excerpt (bounded)
    if report_text:
        lines.append("--- Report Excerpt ---")
        report_lines = report_text.split('\n')[:50]
        for line in report_lines:
            lines.append(line)
        if len(report_text.split('\n')) > 50:
            lines.append("... (report truncated)")
        lines.append("")

    lines.append("="*70)
    lines.append("END SYNTHETIC LOG")
    lines.append("="*70)

    return '\n'.join(lines)


class UXPostmortem:
    """
    Runs UX postmortem: converts eval findings into issues and optionally WorkGraph.
    """

    def __init__(
        self,
        eval_id: str,
        eval_dir: Path,
        verbose: bool = False,
        very_verbose: bool = False
    ):
        """
        Initialize UX postmortem runner.

        Args:
            eval_id: UX eval ID
            eval_dir: Path to UX eval directory
            verbose: Show detailed output
            very_verbose: Show all pipeline commands and outputs
        """
        self.eval_id = eval_id
        self.eval_dir = eval_dir
        self.verbose = verbose
        self.very_verbose = very_verbose
        self.postmortem_dir = eval_dir / "ux_postmortem"

    def run(
        self,
        execute: bool = False,
        create_issues: bool = False,
        decompose: bool = False,
        profile: str = 'default'
    ) -> Dict[str, Any]:
        """
        Run UX postmortem pipeline.

        Args:
            execute: Actually run pipeline (default: preview only)
            create_issues: Create issues from findings
            decompose: Create WorkGraph for fixes
            profile: WorkGraph profile (investor/purpose/default)

        Returns:
            Result dict with summary
        """
        result = {
            'eval_id': self.eval_id,
            'mode': 'execute' if execute else 'preview',
            'create_issues': create_issues,
            'decompose': decompose,
            'profile': profile,
            'log_file': None,
            'scan_id': None,
            'issues_created': [],
            'workgraph_id': None
        }

        # Step 1: Load artifacts
        if self.verbose:
            print(f"Step 1: Loading UX eval artifacts from {self.eval_dir}...")

        try:
            artifacts = load_eval_artifacts(self.eval_dir)
        except Exception as e:
            print(f"Error loading artifacts: {e}", file=sys.stderr)
            raise

        telemetry = artifacts['telemetry']
        attempts = artifacts['attempts']
        surface = artifacts['surface']
        report_text = artifacts['report_text']
        goal = telemetry.get('goal', '')

        if self.verbose:
            print(f"  Loaded {len(attempts)} attempts")
            print(f"  Discovered {len(surface.get('surface', {}))} commands")
            print()

        # Step 2: Build synthetic log
        if self.verbose:
            print("Step 2: Building synthetic log from attempts...")

        ux_log = build_ux_log(attempts, surface, report_text, goal)

        if self.very_verbose:
            print("--- Synthetic Log Preview (first 1000 chars) ---")
            print(ux_log[:1000])
            if len(ux_log) > 1000:
                print(f"... ({len(ux_log) - 1000} chars truncated)")
            print()

        # Step 3: Save or preview
        if execute:
            # Create postmortem directory
            self.postmortem_dir.mkdir(parents=True, exist_ok=True)

            # Write ux_log.txt
            log_file = self.postmortem_dir / "ux_log.txt"
            with open(log_file, 'w') as f:
                f.write(ux_log)

            result['log_file'] = str(log_file)

            if self.verbose:
                print(f"  Saved synthetic log: {log_file}")
                print()

            # Step 4: Run log scan (if execute)
            if self.verbose:
                print("Step 3: Running log scan on synthetic log...")

            scan_id = self._run_log_scan(log_file)
            result['scan_id'] = scan_id

            if self.verbose:
                print(f"  Scan ID: {scan_id}")
                print()

            # Initialize variables for later use
            issues_created = []
            workgraph_id = None

            # Step 5: Create issues (if requested)
            if create_issues and scan_id:
                if self.verbose:
                    print("Step 4: Creating issues from scan findings...")

                issues_created = self._create_issues_from_scan(scan_id)
                result['issues_created'] = issues_created

                if self.verbose:
                    print(f"  Created {len(issues_created)} issue(s)")
                    print()

            # Step 6: Decompose into WorkGraph (if requested)
            if decompose and create_issues and scan_id:
                if self.verbose:
                    print(f"Step 5: Decomposing into WorkGraph (profile: {profile})...")

                workgraph_id = self._decompose_workgraph(goal, profile)
                result['workgraph_id'] = workgraph_id

                if self.verbose:
                    print(f"  WorkGraph ID: {workgraph_id}")
                    print()

            # Save postmortem metadata
            postmortem_meta = {
                'eval_id': self.eval_id,
                'timestamp': datetime.now().isoformat(),
                'mode': 'execute',
                'log_file': str(log_file),
                'scan_id': scan_id,
                'issues_created': issues_created if create_issues else [],
                'workgraph_id': workgraph_id if decompose else None,
                'profile': profile if decompose else None
            }

            postmortem_meta_file = self.postmortem_dir / "postmortem.json"
            with open(postmortem_meta_file, 'w') as f:
                json.dump(postmortem_meta, f, indent=2)

            # Emit machine-readable markers
            print(f"MAESTRO_UX_EVAL_ID={self.eval_id}")
            if scan_id:
                print(f"MAESTRO_UX_POSTMORTEM_SCAN_ID={scan_id}")
            if issues_created:
                print(f"MAESTRO_UX_POSTMORTEM_ISSUES={len(issues_created)}")
            if workgraph_id:
                print(f"MAESTRO_UX_POSTMORTEM_WORKGRAPH_ID={workgraph_id}")

            # Human-readable summary
            if not self.very_verbose:
                print()
                print("="*60)
                print("UX POSTMORTEM COMPLETE")
                print("="*60)
                print()
                print(f"Eval ID: {self.eval_id}")
                print(f"Log File: {log_file}")
                if scan_id:
                    print(f"Scan ID: {scan_id}")
                if issues_created:
                    print(f"Issues Created: {len(issues_created)}")
                    for issue_id in issues_created[:5]:
                        print(f"  - {issue_id}")
                    if len(issues_created) > 5:
                        print(f"  ... and {len(issues_created) - 5} more")
                if workgraph_id:
                    print(f"WorkGraph: {workgraph_id}")
                    print()
                    print(f"Next: Run 'maestro plan enact {workgraph_id}' to materialize")
                print()

        else:
            # Preview mode: show what would be done
            print()
            print("="*60)
            print("UX POSTMORTEM PREVIEW (DRY RUN)")
            print("="*60)
            print()
            print(f"Eval ID: {self.eval_id}")
            print(f"Goal: {goal[:60]}{'...' if len(goal) > 60 else ''}")
            print()
            print("Would execute:")
            print()

            log_file = self.postmortem_dir / "ux_log.txt"
            print(f"  1. Save synthetic log to: {log_file}")
            print(f"     Log size: ~{len(ux_log)} bytes")
            print()

            print(f"  2. Run: maestro log scan --source {log_file} --kind run")
            print()

            if create_issues:
                print(f"  3. Run: maestro issues add --from-log <SCAN_ID>")
                print()

            if decompose:
                print(f"  4. Run: maestro plan decompose --domain issues --profile {profile} -e")
                print(f"     Input: \"Improve CLI discoverability for goal: {goal[:40]}...\"")
                print()

            print("To execute, run with --execute flag:")
            print(f"  maestro ux postmortem {self.eval_id} --execute --issues --decompose")
            print()

        return result

    def _run_log_scan(self, log_file: Path) -> Optional[str]:
        """
        Run log scan on synthetic log.

        Returns:
            Scan ID or None if failed
        """
        cmd = ['maestro', 'log', 'scan', '--source', str(log_file), '--kind', 'run']

        if self.very_verbose:
            print(f"  Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if self.very_verbose:
                print(f"  Exit code: {result.returncode}")
                if result.stdout:
                    print(f"  Stdout: {result.stdout[:500]}")
                if result.stderr:
                    print(f"  Stderr: {result.stderr[:500]}")

            # Parse scan ID from output (format: "Scan created: SCAN-...")
            for line in result.stdout.split('\n'):
                if 'Scan created:' in line or 'scan_id' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if part.startswith('SCAN-') or part.startswith('scan-'):
                            return part.strip()

            return None

        except subprocess.TimeoutExpired:
            print("  Warning: Log scan timed out", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  Warning: Log scan failed: {e}", file=sys.stderr)
            return None

    def _create_issues_from_scan(self, scan_id: str) -> List[str]:
        """
        Create issues from log scan findings.

        Returns:
            List of created issue IDs
        """
        cmd = ['maestro', 'issues', 'add', '--from-log', scan_id]

        if self.very_verbose:
            print(f"  Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if self.very_verbose:
                print(f"  Exit code: {result.returncode}")
                if result.stdout:
                    print(f"  Stdout: {result.stdout[:500]}")
                if result.stderr:
                    print(f"  Stderr: {result.stderr[:500]}")

            # Parse issue IDs from output
            issue_ids = []
            for line in result.stdout.split('\n'):
                if 'Created ISSUE-' in line or 'issue_id' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if part.startswith('ISSUE-') or part.startswith('issue-'):
                            issue_ids.append(part.strip())

            # Save to issues_created.json
            if issue_ids:
                issues_file = self.postmortem_dir / "issues_created.json"
                with open(issues_file, 'w') as f:
                    json.dump({'issue_ids': issue_ids}, f, indent=2)

            return issue_ids

        except subprocess.TimeoutExpired:
            print("  Warning: Issues creation timed out", file=sys.stderr)
            return []
        except Exception as e:
            print(f"  Warning: Issues creation failed: {e}", file=sys.stderr)
            return []

    def _decompose_workgraph(self, goal: str, profile: str) -> Optional[str]:
        """
        Decompose into WorkGraph.

        Returns:
            WorkGraph ID or None if failed
        """
        # Build input for decompose
        decompose_input = f"Improve CLI discoverability for goal: {goal}\n\nFocus on fixing help text, subcommand discovery, and onboarding."

        cmd = ['maestro', 'plan', 'decompose', '--domain', 'issues', '--profile', profile, '-e']

        if self.very_verbose:
            print(f"  Running: {' '.join(cmd)}")
            print(f"  Input (first 200 chars): {decompose_input[:200]}...")

        try:
            result = subprocess.run(
                cmd,
                input=decompose_input,
                capture_output=True,
                text=True,
                timeout=120
            )

            if self.very_verbose:
                print(f"  Exit code: {result.returncode}")
                if result.stdout:
                    print(f"  Stdout: {result.stdout[:500]}")
                if result.stderr:
                    print(f"  Stderr: {result.stderr[:500]}")

            # Parse WorkGraph ID from output
            for line in result.stdout.split('\n'):
                if 'Created WorkGraph:' in line or 'workgraph_id' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if part.startswith('wg-'):
                            wg_id = part.strip()
                            # Save to workgraph_id.txt
                            wg_file = self.postmortem_dir / "workgraph_id.txt"
                            with open(wg_file, 'w') as f:
                                f.write(wg_id)
                            return wg_id

            return None

        except subprocess.TimeoutExpired:
            print("  Warning: WorkGraph decompose timed out", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  Warning: WorkGraph decompose failed: {e}", file=sys.stderr)
            return None
