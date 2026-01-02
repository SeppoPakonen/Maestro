"""
Telemetry recorder for UX evaluation attempts.

Records each command attempt with exit code, duration, and bounded output.
"""

import json
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class AttemptRecord:
    """Record of a single command attempt."""
    attempt_index: int
    command_argv: List[str]
    exit_code: int
    duration_ms: int
    stdout_excerpt: str  # Bounded to 2000 chars
    stderr_excerpt: str  # Bounded to 2000 chars
    timestamp: str
    timed_out: bool = False


class TelemetryRecorder:
    """
    Records telemetry for UX evaluation attempts.

    Stores attempt records and provides summary statistics.
    """

    def __init__(
        self,
        eval_id: str,
        goal: str,
        output_dir: Path,
        verbose: bool = False
    ):
        """
        Initialize telemetry recorder.

        Args:
            eval_id: Unique evaluation ID
            goal: Goal string being evaluated
            output_dir: Directory to write telemetry files
            verbose: Whether to print progress
        """
        self.eval_id = eval_id
        self.goal = goal
        self.output_dir = output_dir
        self.verbose = verbose

        self.attempts: List[AttemptRecord] = []
        self.help_call_count: int = 0
        self.unknown_command_count: int = 0
        self.timeout_count: int = 0

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def record_attempt(
        self,
        command_argv: List[str],
        timeout: float = 30.0,
        dry_run: bool = True
    ) -> AttemptRecord:
        """
        Execute a command and record the attempt.

        Args:
            command_argv: Command to execute (e.g., ['maestro', 'plan', 'list'])
            timeout: Timeout for command execution (seconds)
            dry_run: If True, does not actually execute (returns dummy record)

        Returns:
            AttemptRecord for this attempt
        """
        attempt_index = len(self.attempts)

        if dry_run:
            # Dry run: create dummy record without executing
            record = AttemptRecord(
                attempt_index=attempt_index,
                command_argv=command_argv,
                exit_code=0,
                duration_ms=0,
                stdout_excerpt="[DRY RUN]",
                stderr_excerpt="",
                timestamp=datetime.now().isoformat(),
                timed_out=False
            )
        else:
            # Execute command and record results
            start_time = time.time()
            timed_out = False

            try:
                result = subprocess.run(
                    command_argv,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False
                )

                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr

            except subprocess.TimeoutExpired:
                exit_code = 124  # Standard timeout exit code
                stdout = ""
                stderr = "[TIMEOUT]"
                timed_out = True
                self.timeout_count += 1

            except FileNotFoundError:
                exit_code = 127  # Command not found
                stdout = ""
                stderr = f"[ERROR: Command not found: {command_argv[0]}]"
                self.unknown_command_count += 1

            except Exception as e:
                exit_code = 1
                stdout = ""
                stderr = f"[ERROR: {e}]"

            duration_ms = int((time.time() - start_time) * 1000)

            # Bound output to 2000 chars
            stdout_excerpt = stdout[:2000]
            if len(stdout) > 2000:
                stdout_excerpt += "\n... (truncated)"

            stderr_excerpt = stderr[:2000]
            if len(stderr) > 2000:
                stderr_excerpt += "\n... (truncated)"

            record = AttemptRecord(
                attempt_index=attempt_index,
                command_argv=command_argv,
                exit_code=exit_code,
                duration_ms=duration_ms,
                stdout_excerpt=stdout_excerpt,
                stderr_excerpt=stderr_excerpt,
                timestamp=datetime.now().isoformat(),
                timed_out=timed_out
            )

        self.attempts.append(record)

        if self.verbose:
            cmd_str = ' '.join(command_argv)
            status = "DRY RUN" if dry_run else f"exit {record.exit_code}"
            print(f"  Attempt {attempt_index}: {cmd_str} ({status})")

        return record

    def increment_help_calls(self, count: int = 1) -> None:
        """Increment help call counter."""
        self.help_call_count += count

    def save_telemetry(self) -> None:
        """Save telemetry data to files."""
        # Save telemetry.json (summary)
        telemetry_data = {
            'eval_id': self.eval_id,
            'goal': self.goal,
            'total_attempts': len(self.attempts),
            'help_call_count': self.help_call_count,
            'timeout_count': self.timeout_count,
            'unknown_command_count': self.unknown_command_count,
            'successful_attempts': sum(1 for a in self.attempts if a.exit_code == 0),
            'failed_attempts': sum(1 for a in self.attempts if a.exit_code != 0),
        }

        telemetry_json_path = self.output_dir / 'telemetry.json'
        with open(telemetry_json_path, 'w', encoding='utf-8') as f:
            json.dump(telemetry_data, f, indent=2)

        if self.verbose:
            print(f"Saved telemetry.json: {telemetry_json_path}")

        # Save attempts.jsonl (detailed records)
        attempts_jsonl_path = self.output_dir / 'attempts.jsonl'
        with open(attempts_jsonl_path, 'w', encoding='utf-8') as f:
            for attempt in self.attempts:
                f.write(json.dumps(asdict(attempt)) + '\n')

        if self.verbose:
            print(f"Saved attempts.jsonl: {attempts_jsonl_path}")

    def get_summary(self) -> dict:
        """Get telemetry summary dictionary."""
        return {
            'eval_id': self.eval_id,
            'goal': self.goal,
            'total_attempts': len(self.attempts),
            'help_call_count': self.help_call_count,
            'timeout_count': self.timeout_count,
            'unknown_command_count': self.unknown_command_count,
            'successful_attempts': sum(1 for a in self.attempts if a.exit_code == 0),
            'failed_attempts': sum(1 for a in self.attempts if a.exit_code != 0),
        }
