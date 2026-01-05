#!/usr/bin/env python3
"""
Real Qwen Blindfold Meta-Feedback Loop Runner.

This is a meta-evaluation tool that runs qwen in an iterative loop,
testing Maestro CLI discoverability from help text alone.

Architecture:
- Goal-only prompt (no command hints)
- Step-by-step execution (qwen emits one command at a time)
- Stuck detection (repeated commands, help loops, no progress)
- Artifact export compatible with maestro ux postmortem

Usage:
    python tools/ux_qwen_loop/run.py \\
        --maestro-bin "./maestro.py" \\
        --repo-root ~/Dev/MyRepo \\
        --goal "Create a runbook for building this repo" \\
        --execute
"""

import argparse
import json
import os
import subprocess
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add tools directory to path for local imports
TOOLS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(TOOLS_DIR))


class QwenLoopRunner:
    """Runs qwen in an iterative blindfold UX evaluation loop."""

    # Safety: allowlisted commands (safe mode)
    SAFE_COMMANDS = {
        'pwd', 'ls', 'cat', 'tree', 'find', 'rg', 'grep',
        'head', 'tail', 'wc', 'echo', 'which', 'env'
    }

    # Output bounds
    MAX_OUTPUT_CHARS = 2000
    MAX_PROMPT_DISPLAY_CHARS = 2000

    def __init__(
        self,
        maestro_bin: str,
        repo_root: str,
        goal: str,
        qwen_bin: str = "qwen",
        max_steps: int = 30,
        timeout_help_s: int = 8,
        timeout_cmd_s: int = 60,
        execute: bool = False,
        postmortem: bool = False,
        profile: str = "investor",
        allow_any_command: bool = False,
        verbose: int = 0
    ):
        self.maestro_bin = maestro_bin
        self.repo_root = Path(repo_root).resolve()
        self.goal = goal
        self.qwen_bin = qwen_bin
        self.max_steps = max_steps
        self.timeout_help_s = timeout_help_s
        self.timeout_cmd_s = timeout_cmd_s
        self.execute = execute
        self.postmortem = postmortem
        self.profile = profile
        self.allow_any_command = allow_any_command
        self.verbose = verbose

        # Generate EVAL_ID: ux_qwen_YYYYMMDD_HHMMSS_<shortsha>
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        hash_input = f"{goal}{repo_root}".encode('utf-8')
        short_sha = hashlib.sha256(hash_input).hexdigest()[:8]
        self.eval_id = f"ux_qwen_{timestamp}_{short_sha}"

        # Session state
        self.step_count = 0
        self.attempts = []  # List of step events for attempts.jsonl
        self.telemetry = {
            'eval_id': self.eval_id,
            'goal': goal,
            'repo_root': str(self.repo_root),
            'maestro_bin': maestro_bin,
            'max_steps': max_steps,
            'execute': execute,
            'start_time': now.isoformat(),
            'end_time': None,
            'total_steps': 0,
            'help_calls': 0,
            'run_calls': 0,
            'successes': 0,
            'failures': 0,
            'timeouts': 0,
            'stuck_reason': None
        }

        self.surface_seed = ""  # Top-level help output
        self.last_prompt = ""
        self.last_qwen_output = ""

        # Import stuck detector
        from ux_qwen_loop.stuck import StuckDetector
        self.stuck_detector = StuckDetector(
            max_repeated=2,
            help_loop_threshold=0.7,
            help_loop_window=10,
            no_progress_steps=8
        )

    def build_initial_prompt(self) -> str:
        """Build the initial goal-only prompt for qwen."""
        prompt = f"""You are evaluating the UX of a CLI tool called Maestro by attempting to accomplish a goal using ONLY the help text and command outputs.

**Your Goal**: {self.goal}

**Constraints**:
- You can only see stdout/stderr from commands you run.
- You must start by running: {self.maestro_bin} --help
- You do not have access to source code, documentation, or the internet.
- You must discover the right commands solely from help text.

**Output Format** (stream-json):
For each step, output a single JSON object with:
- "next_command": the exact shell command to run next (string)
- "note": optional commentary about why you're running this command (string)
- "done": set to true when you've accomplished the goal or are stuck (boolean)

**Examples**:
{{"next_command": "{self.maestro_bin} --help", "note": "Starting with top-level help"}}
{{"next_command": "{self.maestro_bin} runbook --help", "note": "Exploring runbook subcommand"}}
{{"next_command": "{self.maestro_bin} runbook list", "note": "Checking existing runbooks"}}
{{"done": true, "note": "Goal accomplished: created runbook RUN-123"}}

**Current Step**: This is your first step. Run the top-level help command to start discovering.
"""
        return prompt

    def build_step_prompt(self, last_command: str, last_result: Dict[str, Any]) -> str:
        """Build the prompt for the next step, given the last command result."""
        stdout = last_result.get('stdout', '')
        stderr = last_result.get('stderr', '')
        exit_code = last_result.get('exit_code', 0)
        timeout = last_result.get('timeout', False)

        # Bound output
        stdout = self._bound_output(stdout)
        stderr = self._bound_output(stderr)

        prompt = f"""**Last Command**: {last_command}
**Exit Code**: {exit_code}
**Timeout**: {timeout}

**Stdout**:
```
{stdout}
```

**Stderr**:
```
{stderr}
```

What is your next command? Output a JSON object with "next_command" and optional "note", or set "done": true if you've accomplished the goal or are stuck.
"""
        return prompt

    def _bound_output(self, text: str) -> str:
        """Bound output to MAX_OUTPUT_CHARS."""
        if len(text) > self.MAX_OUTPUT_CHARS:
            return text[:self.MAX_OUTPUT_CHARS] + "\n[TRUNCATED]"
        return text

    def call_qwen(self, prompt: str) -> Dict[str, Any]:
        """Call qwen CLI and parse stream-json output."""
        self.last_prompt = prompt

        if self.verbose >= 2:
            print("\n=== QWEN PROMPT (first 2000 chars) ===")
            print(prompt[:self.MAX_PROMPT_DISPLAY_CHARS])
            if len(prompt) > self.MAX_PROMPT_DISPLAY_CHARS:
                print(f"... [TRUNCATED {len(prompt) - self.MAX_PROMPT_DISPLAY_CHARS} chars]")
            print()

        # Call qwen: echo "$PROMPT" | qwen -y -o stream-json -
        try:
            proc = subprocess.Popen(
                [self.qwen_bin, '-y', '-o', 'stream-json', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_root),
                text=True
            )

            stdout, stderr = proc.communicate(input=prompt, timeout=60)
            self.last_qwen_output = stdout

            if self.verbose >= 2:
                print("\n=== QWEN OUTPUT (first 2000 chars) ===")
                print(stdout[:self.MAX_PROMPT_DISPLAY_CHARS])
                if len(stdout) > self.MAX_PROMPT_DISPLAY_CHARS:
                    print(f"... [TRUNCATED {len(stdout) - self.MAX_PROMPT_DISPLAY_CHARS} chars]")
                print()

            if proc.returncode != 0:
                return {
                    'error': f"Qwen failed with exit code {proc.returncode}",
                    'stderr': stderr
                }

            # Parse stream-json output
            return self._parse_qwen_output(stdout)

        except subprocess.TimeoutExpired:
            return {'error': 'Qwen timeout (60s)'}
        except FileNotFoundError:
            return {'error': f'Qwen binary not found: {self.qwen_bin}'}
        except Exception as e:
            return {'error': f'Qwen execution failed: {e}'}

    def _parse_qwen_output(self, output: str) -> Dict[str, Any]:
        """Parse qwen stream-json output.

        Accepts:
        1. Single JSON object: {"next_command": "...", "note": "...", "done": false}
        2. Stream of JSON objects (NDJSON) - take the last valid one
        3. Fallback: line starting with "CMD:" extracts command

        Returns dict with keys: next_command (str), note (str), done (bool), error (str)
        """
        lines = [line.strip() for line in output.strip().split('\n') if line.strip()]

        last_valid = None

        for line in lines:
            try:
                obj = json.loads(line)
                # Valid if has next_command or done
                if 'next_command' in obj or obj.get('done'):
                    last_valid = obj
            except json.JSONDecodeError:
                # Try fallback CMD: pattern
                if line.startswith('CMD:'):
                    cmd = line[4:].strip()
                    last_valid = {'next_command': cmd, 'note': 'Extracted from CMD: prefix'}

        if last_valid:
            return {
                'next_command': last_valid.get('next_command', ''),
                'note': last_valid.get('note', ''),
                'done': last_valid.get('done', False),
                'error': None
            }

        # No valid parse
        return {
            'error': 'Failed to parse qwen output (no valid JSON with next_command or done)',
            'raw_output': output[:500]
        }

    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a command and return structured result.

        Returns: {
            'command': str,
            'exit_code': int,
            'stdout': str,
            'stderr': str,
            'duration': float,
            'timeout': bool,
            'rejected': bool,
            'rejection_reason': str or None
        }
        """
        # Safety check
        if not self.allow_any_command:
            if not self._is_safe_command(command):
                return {
                    'command': command,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': f'Command rejected by safety policy: {command}',
                    'duration': 0.0,
                    'timeout': False,
                    'rejected': True,
                    'rejection_reason': 'not in allowlist (maestro + safe shell commands)'
                }

        # Determine timeout
        is_help = '--help' in command or '-h' in command
        timeout = self.timeout_help_s if is_help else self.timeout_cmd_s

        start_time = time.time()

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )

            duration = time.time() - start_time

            return {
                'command': command,
                'exit_code': proc.returncode,
                'stdout': proc.stdout or '',
                'stderr': proc.stderr or '',
                'duration': duration,
                'timeout': False,
                'rejected': False,
                'rejection_reason': None
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'command': command,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout}s',
                'duration': duration,
                'timeout': True,
                'rejected': False,
                'rejection_reason': None
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                'command': command,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Execution error: {e}',
                'duration': duration,
                'timeout': False,
                'rejected': False,
                'rejection_reason': None
            }

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe (maestro or allowlisted shell command)."""
        tokens = command.strip().split()
        if not tokens:
            return False

        # Extract command name (handle env vars like MAESTRO_DOCS_ROOT=... maestro ...)
        cmd_name = None
        script_name = None
        for i, token in enumerate(tokens):
            if '=' not in token and not token.startswith('-'):
                if cmd_name is None:
                    cmd_name = token
                elif script_name is None and i == 1:
                    # If second non-flag token, might be script name (e.g., python script.py)
                    script_name = token
                    break
                else:
                    break

        if not cmd_name:
            return False

        # Resolve to basename
        cmd_base = Path(cmd_name).name

        # Check if it's maestro
        if 'maestro' in cmd_base.lower():
            return True

        # Check if script name contains maestro (e.g., python stub_maestro.py)
        if script_name and 'maestro' in Path(script_name).name.lower():
            return True

        # Check if in safe list
        if cmd_base in self.SAFE_COMMANDS:
            return True

        return False

    def run_loop(self) -> None:
        """Run the main qwen loop."""
        # Step 0: Get surface seed (top-level help)
        if self.verbose:
            print(f"Getting surface seed: {self.maestro_bin} --help")

        help_result = self.execute_command(f"{self.maestro_bin} --help")
        self.surface_seed = help_result['stdout']

        if self.verbose:
            print(f"Surface seed captured ({len(self.surface_seed)} chars)")

        # Step 1: Initial prompt
        prompt = self.build_initial_prompt()
        qwen_response = self.call_qwen(prompt)

        if qwen_response.get('error'):
            print(f"Error calling qwen: {qwen_response['error']}", file=sys.stderr)
            self.telemetry['stuck_reason'] = f"qwen_error: {qwen_response['error']}"
            return

        # Main loop
        while self.step_count < self.max_steps:
            self.step_count += 1

            # Check for done signal
            if qwen_response.get('done'):
                if self.verbose:
                    print(f"[Step {self.step_count}] Qwen signaled done")
                self.telemetry['stuck_reason'] = 'done_by_qwen'
                break

            # Get next command
            next_cmd = qwen_response.get('next_command', '').strip()
            note = qwen_response.get('note', '')

            if not next_cmd:
                if self.verbose:
                    print(f"[Step {self.step_count}] No command from qwen, stopping")
                self.telemetry['stuck_reason'] = 'no_command_from_qwen'
                break

            if self.verbose:
                print(f"\n[Step {self.step_count}] Command: {next_cmd}")
                if note:
                    print(f"  Note: {note}")

            # Execute command
            result = self.execute_command(next_cmd)

            # Update telemetry
            is_help = '--help' in next_cmd or '-h' in next_cmd
            if is_help:
                self.telemetry['help_calls'] += 1
            else:
                self.telemetry['run_calls'] += 1

            if result['exit_code'] == 0 and not result['rejected']:
                self.telemetry['successes'] += 1
            else:
                self.telemetry['failures'] += 1

            if result['timeout']:
                self.telemetry['timeouts'] += 1

            # Record step
            step_event = {
                'step': self.step_count,
                'command': next_cmd,
                'note': note,
                'exit_code': result['exit_code'],
                'stdout': self._bound_output(result['stdout']),
                'stderr': self._bound_output(result['stderr']),
                'duration': result['duration'],
                'timeout': result['timeout'],
                'rejected': result['rejected'],
                'rejection_reason': result['rejection_reason']
            }
            self.attempts.append(step_event)

            # Check stuck detector
            stuck_reason = self.stuck_detector.update(step_event)
            if stuck_reason:
                if self.verbose:
                    print(f"[Step {self.step_count}] Stuck detected: {stuck_reason}")
                self.telemetry['stuck_reason'] = stuck_reason
                break

            # Build next prompt
            prompt = self.build_step_prompt(next_cmd, result)
            qwen_response = self.call_qwen(prompt)

            if qwen_response.get('error'):
                if self.verbose:
                    print(f"[Step {self.step_count}] Qwen error: {qwen_response['error']}")
                self.telemetry['stuck_reason'] = f"qwen_error: {qwen_response['error']}"
                break

        # Finalize telemetry
        self.telemetry['total_steps'] = self.step_count
        self.telemetry['end_time'] = datetime.now().isoformat()

        if self.step_count >= self.max_steps and not self.telemetry.get('stuck_reason'):
            self.telemetry['stuck_reason'] = 'max_steps_reached'

    def export_artifacts(self) -> Path:
        """Export artifacts to docs/maestro/ux_eval/<EVAL_ID>/."""
        from ux_qwen_loop.export import export_artifacts

        output_dir = export_artifacts(
            eval_id=self.eval_id,
            attempts=self.attempts,
            telemetry=self.telemetry,
            surface_seed=self.surface_seed,
            stuck_summary=self.stuck_detector.summary(),
            goal=self.goal,
            repo_root=str(self.repo_root),
            maestro_bin=self.maestro_bin
        )

        return output_dir

    def run_postmortem(self, output_dir: Path) -> Optional[str]:
        """Optionally run maestro ux postmortem and return WorkGraph ID if found."""
        if not self.postmortem:
            return None

        if self.verbose:
            print(f"\nRunning postmortem on {self.eval_id}...")

        cmd_parts = [
            self.maestro_bin,
            'ux', 'postmortem', self.eval_id,
            '--issues', '--decompose',
            '--profile', self.profile
        ]

        if self.execute:
            cmd_parts.append('--execute')

        cmd = ' '.join(cmd_parts)

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                text=True
            )

            if self.verbose:
                print(f"Postmortem exit code: {proc.returncode}")

            if proc.returncode == 0:
                # Try to extract WorkGraph ID from output
                for line in proc.stdout.split('\n'):
                    if 'wg-' in line:
                        # Simple extraction: find first wg-YYYYMMDD-XXXXXXXX
                        import re
                        match = re.search(r'wg-\d{8}-[a-f0-9]{8}', line)
                        if match:
                            return match.group(0)
                return None
            else:
                if self.verbose:
                    print(f"Postmortem failed:\n{proc.stderr}")
                return None

        except Exception as e:
            if self.verbose:
                print(f"Postmortem error: {e}")
            return None

    def print_summary(self, output_dir: Path, wg_id: Optional[str] = None) -> None:
        """Print final summary."""
        print("\n" + "="*60)
        print("Qwen Blindfold UX Evaluation Complete")
        print("="*60)
        print(f"Eval ID: {self.eval_id}")
        print(f"Goal: {self.goal}")
        print(f"Steps: {self.telemetry['total_steps']} / {self.max_steps}")
        print(f"Help calls: {self.telemetry['help_calls']}")
        print(f"Run calls: {self.telemetry['run_calls']}")
        print(f"Successes: {self.telemetry['successes']}")
        print(f"Failures: {self.telemetry['failures']}")
        print(f"Timeouts: {self.telemetry['timeouts']}")
        print(f"Stuck reason: {self.telemetry['stuck_reason']}")
        print(f"\nArtifacts: {output_dir}")

        if wg_id:
            print(f"\nWorkGraph created: {wg_id}")
            print("\nNext steps:")
            print(f"  maestro plan enact {wg_id} --profile {self.profile}")
            print(f"  maestro plan sprint {wg_id} --top 5 --profile {self.profile}")
        elif self.postmortem:
            print("\nPostmortem did not create a WorkGraph.")
            print("Check the artifacts for stuck diagnosis and UX fix recommendations.")


def main():
    parser = argparse.ArgumentParser(
        description="Real Qwen Blindfold Meta-Feedback Loop Runner"
    )

    parser.add_argument(
        '--maestro-bin',
        required=True,
        help='Path or command to run maestro (e.g., "./maestro.py" or "python -m maestro")'
    )
    parser.add_argument(
        '--repo-root',
        required=True,
        help='Repository root directory (cwd for commands)'
    )
    parser.add_argument(
        '--goal',
        required=True,
        help='Single-sentence goal for qwen to accomplish'
    )
    parser.add_argument(
        '--qwen-bin',
        default='qwen',
        help='Qwen binary name or path (default: qwen)'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=30,
        help='Maximum number of steps (default: 30)'
    )
    parser.add_argument(
        '--timeout-help-s',
        type=int,
        default=8,
        help='Timeout for help commands in seconds (default: 8)'
    )
    parser.add_argument(
        '--timeout-cmd-s',
        type=int,
        default=60,
        help='Timeout for other commands in seconds (default: 60)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Allow write operations (default: safe mode blocks writes)'
    )
    parser.add_argument(
        '--postmortem',
        action='store_true',
        help='Run maestro ux postmortem after evaluation'
    )
    parser.add_argument(
        '--profile',
        default='investor',
        help='Profile for postmortem (default: investor)'
    )
    parser.add_argument(
        '--allow-any-command',
        action='store_true',
        help='DANGER: Allow any command, not just maestro + safe shell commands'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Verbose output (-v: progress, -vv: include prompts and qwen output)'
    )

    args = parser.parse_args()

    # Validate inputs
    repo_root = Path(args.repo_root)
    if not repo_root.exists():
        print(f"Error: repo-root does not exist: {repo_root}", file=sys.stderr)
        sys.exit(1)

    # Create runner
    runner = QwenLoopRunner(
        maestro_bin=args.maestro_bin,
        repo_root=str(repo_root),
        goal=args.goal,
        qwen_bin=args.qwen_bin,
        max_steps=args.max_steps,
        timeout_help_s=args.timeout_help_s,
        timeout_cmd_s=args.timeout_cmd_s,
        execute=args.execute,
        postmortem=args.postmortem,
        profile=args.profile,
        allow_any_command=args.allow_any_command,
        verbose=args.verbose
    )

    # Run loop
    runner.run_loop()

    # Export artifacts
    output_dir = runner.export_artifacts()

    # Optional postmortem
    wg_id = runner.run_postmortem(output_dir)

    # Print summary
    runner.print_summary(output_dir, wg_id)


if __name__ == '__main__':
    main()
