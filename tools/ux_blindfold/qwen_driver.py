#!/usr/bin/env python3
"""
Qwen-driven blindfold UX audit harness for Maestro.

This harness uses the REAL qwen CLI to evaluate Maestro's discoverability
from help text alone. Qwen only sees --help outputs and command results,
never the argparse internals.

Protocol:
- Qwen emits NDJSON (stream-json) with action objects
- Actions: help, run, note, done
- Harness enforces budgets and write-safety rules
- Artifacts written to docs/workflows/v3/reports/ux_blindfold/

Usage:
    python tools/ux_blindfold/qwen_driver.py --goal "Create a runbook" [OPTIONS]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib


class QwenBlindfolDriver:
    """Drives a qwen-powered blindfold UX audit session."""

    # Write-blocking verbs and flags
    WRITEY_VERBS = {
        'add', 'enact', 'run', 'resolve', 'prune', 'archive',
        'restore', 'delete', 'remove', 'link', 'commit'
    }
    WRITEY_FLAGS = {'--execute', '--write', '--apply'}

    # Budgets
    MAX_HELP_CALLS = 10
    MAX_OUTPUT_CHARS = 4000
    MAX_TOTAL_TRANSCRIPT_CHARS = 120_000
    HELP_TIMEOUT_S = 5
    RUN_TIMEOUT_S = 20

    def __init__(
        self,
        goal: str,
        maestro_bin: str = "maestro",
        docs_root: Optional[str] = None,
        repo: str = ".",
        max_steps: int = 12,
        execute: bool = False,
        qwen_bin: str = "qwen"
    ):
        self.goal = goal
        self.maestro_bin = maestro_bin
        self.docs_root = docs_root
        self.repo = Path(repo).resolve()
        self.max_steps = max_steps
        self.execute = execute
        self.qwen_bin = qwen_bin

        # State
        self.help_call_count = 0
        self.run_call_count = 0
        self.blocked_write_count = 0
        self.transcript: List[Dict[str, Any]] = []
        self.telemetry: Dict[str, Any] = {
            'goal': goal,
            'repo': str(self.repo),
            'maestro_bin': maestro_bin,
            'qwen_bin': qwen_bin,
            'execute_mode': execute,
            'max_steps': max_steps,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'help_calls': 0,
            'run_attempts': 0,
            'successes': 0,
            'failures': 0,
            'blocked_writes': 0,
            'timeouts': 0,
            'unknown_commands': 0,
            'total_transcript_chars': 0
        }
        self.surface_seed: Optional[str] = None
        self.qwen_prompt: Optional[str] = None

        # Set up output directory
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        short_sha = hashlib.sha256(goal.encode()).hexdigest()[:8]
        self.output_dir = self.repo / "docs" / "workflows" / "v3" / "reports" / "ux_blindfold" / f"{timestamp}_{short_sha}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_prompt(self) -> str:
        """Build the system prompt for qwen."""
        prompt = f"""You are evaluating the UX discoverability of the Maestro CLI tool.

GOAL: {self.goal}

RULES:
1. You can ONLY discover Maestro commands via --help text and command outputs
2. You MUST emit JSON objects (one per line, NDJSON format) with these actions:
   - {{"action":"help","argv":["maestro","--help"]}}        # request help page
   - {{"action":"run","argv":["maestro","track","list"]}}   # run a command
   - {{"action":"note","text":"exploring track commands"}}  # optional commentary
   - {{"action":"done","result":{{...}}}}                    # final summary

3. SAFETY: Write operations are {"BLOCKED" if not self.execute else "ALLOWED BUT SANDBOXED"}
   {"- Commands with verbs like add/enact/run/resolve/commit will be BLOCKED" if not self.execute else ""}
   - If blocked, you'll see: {{"error":"blocked_write_attempt","argv":[...]}}

4. BUDGETS:
   - Maximum help calls: {self.MAX_HELP_CALLS}
   - Maximum steps: {self.max_steps}
   - Command output truncated to {self.MAX_OUTPUT_CHARS} chars

5. PROTOCOL:
   - All argv must be JSON lists (e.g., ["maestro", "track", "list"])
   - Help requests must end with "--help" or "-h"
   - Single-shot planning: emit your ENTIRE action sequence at once
   - Stop early by emitting {{"action":"done","result":{{...}}}}

6. FINAL RESULT FORMAT:
   When done, emit:
   {{
     "action": "done",
     "result": {{
       "success": true/false,
       "goal_achieved": "description of what was achieved",
       "friction_points": [
         {{"issue": "unclear help text", "evidence": "step 3", "severity": "high"}},
         ...
       ],
       "improvement_suggestions": [
         {{
           "priority": "P0",
           "area": "help text",
           "proposed_change": "...",
           "expected_impact": "...",
           "evidence": "transcript line 5"
         }},
         ...
       ]
     }}
   }}

INITIAL HELP SURFACE:
I will provide the top-level Maestro help output below. Start your action sequence now.
"""
        return prompt

    def get_surface_seed(self) -> str:
        """Get the initial top-level help output."""
        if self.surface_seed:
            return self.surface_seed

        result = self._execute_command(
            [self.maestro_bin, "--help"],
            timeout=self.HELP_TIMEOUT_S
        )
        self.surface_seed = result['stdout']
        return self.surface_seed

    def _execute_command(
        self,
        argv: List[str],
        timeout: int,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute a command and return structured result."""
        start_time = time.time()

        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        # Set MAESTRO_DOCS_ROOT if specified
        if self.docs_root:
            exec_env['MAESTRO_DOCS_ROOT'] = self.docs_root
        elif self.execute:
            # Force sandboxed docs root in execute mode
            exec_env['MAESTRO_DOCS_ROOT'] = str(self.repo / "docs" / "maestro")

        try:
            proc = subprocess.run(
                argv,
                cwd=str(self.repo),
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = time.time() - start_time

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            # Truncate deterministically
            if len(stdout) > self.MAX_OUTPUT_CHARS:
                stdout = stdout[:self.MAX_OUTPUT_CHARS] + "\n[TRUNCATED]"
            if len(stderr) > self.MAX_OUTPUT_CHARS:
                stderr = stderr[:self.MAX_OUTPUT_CHARS] + "\n[TRUNCATED]"

            return {
                'argv': argv,
                'returncode': proc.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'duration': duration,
                'timeout': False
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.telemetry['timeouts'] += 1
            return {
                'argv': argv,
                'returncode': -1,
                'stdout': "",
                'stderr': f"Command timed out after {timeout}s",
                'duration': duration,
                'timeout': True
            }
        except FileNotFoundError:
            return {
                'argv': argv,
                'returncode': -1,
                'stdout': "",
                'stderr': f"Command not found: {argv[0]}",
                'duration': 0,
                'timeout': False
            }

    def _is_writey_command(self, argv: List[str]) -> bool:
        """Check if command looks like it writes."""
        if not argv:
            return False

        # Check for writey verbs in argv
        for arg in argv:
            if arg.lower() in self.WRITEY_VERBS:
                return True
            if arg in self.WRITEY_FLAGS:
                return True

        return False

    def handle_help_action(self, argv: List[str]) -> Dict[str, Any]:
        """Handle a help request action."""
        # Enforce help call budget
        if self.help_call_count >= self.MAX_HELP_CALLS:
            return {
                'event': 'help_budget_exceeded',
                'argv': argv,
                'message': f'Help budget exceeded ({self.MAX_HELP_CALLS} max)'
            }

        # Validate help request ends with --help or -h
        if not (argv and (argv[-1] == '--help' or argv[-1] == '-h')):
            return {
                'event': 'help_invalid',
                'argv': argv,
                'message': 'Help request must end with --help or -h'
            }

        self.help_call_count += 1
        self.telemetry['help_calls'] += 1

        result = self._execute_command(argv, timeout=self.HELP_TIMEOUT_S)

        event = {
            'event': 'help_result',
            'argv': argv,
            'returncode': result['returncode'],
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'duration': result['duration']
        }

        self.transcript.append(event)
        return event

    def handle_run_action(self, argv: List[str]) -> Dict[str, Any]:
        """Handle a run command action."""
        # Check write safety
        if not self.execute and self._is_writey_command(argv):
            self.blocked_write_count += 1
            self.telemetry['blocked_writes'] += 1

            event = {
                'event': 'blocked_write_attempt',
                'argv': argv,
                'error': 'blocked_write_attempt',
                'message': 'Write commands blocked in safe mode. Use --execute to allow.'
            }
            self.transcript.append(event)
            return event

        # Execute command
        self.run_call_count += 1
        self.telemetry['run_attempts'] += 1

        # Use RUN_TIMEOUT from env if set
        timeout = int(os.getenv('MAESTRO_UX_QWEN_RUN_TIMEOUT', self.RUN_TIMEOUT_S))

        result = self._execute_command(argv, timeout=timeout)

        # Track success/failure
        if result['returncode'] == 0:
            self.telemetry['successes'] += 1
        else:
            self.telemetry['failures'] += 1

            # Track failure reasons
            if 'not found' in result['stderr'].lower() or 'unknown' in result['stderr'].lower():
                self.telemetry['unknown_commands'] += 1

        event = {
            'event': 'run_result',
            'argv': argv,
            'returncode': result['returncode'],
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'duration': result['duration'],
            'timeout': result['timeout']
        }

        self.transcript.append(event)
        return event

    def handle_note_action(self, text: str) -> Dict[str, Any]:
        """Handle a note action."""
        event = {
            'event': 'qwen_note',
            'text': text
        }
        self.transcript.append(event)
        return event

    def handle_done_action(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the done action."""
        event = {
            'event': 'qwen_done',
            'result': result
        }
        self.transcript.append(event)
        return event

    def run_qwen(self) -> List[Dict[str, Any]]:
        """Run qwen and parse stream-json output."""
        # Build full prompt with seed help
        seed = self.get_surface_seed()
        prompt = self.build_prompt()
        full_prompt = f"{prompt}\n\n{seed}\n\nBegin your action sequence now:"

        self.qwen_prompt = full_prompt

        # Save prompt to artifact
        prompt_file = self.output_dir / "qwen_prompt.txt"
        prompt_file.write_text(full_prompt, encoding='utf-8')

        # Save seed to artifact
        seed_file = self.output_dir / "surface_seed.txt"
        seed_file.write_text(seed, encoding='utf-8')

        # Execute qwen
        try:
            proc = subprocess.Popen(
                [self.qwen_bin, '-y', '-o', 'stream-json', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = proc.communicate(input=full_prompt, timeout=120)

            if proc.returncode != 0:
                raise RuntimeError(f"qwen exited with code {proc.returncode}: {stderr}")

        except FileNotFoundError:
            raise RuntimeError(f"qwen binary not found: {self.qwen_bin}")
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError("qwen timed out after 120s")

        # Parse stream-json output
        actions = []
        for line in stdout.strip().split('\n'):
            if not line.strip():
                continue

            try:
                obj = json.loads(line)
                if 'action' in obj:
                    actions.append(obj)
                else:
                    # Record garbage
                    self.transcript.append({
                        'event': 'qwen_garbage',
                        'line': line[:200]  # Truncate
                    })
            except json.JSONDecodeError:
                # Record garbage
                self.transcript.append({
                    'event': 'qwen_garbage',
                    'line': line[:200]
                })

        return actions

    def execute_actions(self, actions: List[Dict[str, Any]]) -> None:
        """Execute the action sequence from qwen."""
        for i, action_obj in enumerate(actions):
            # Check max steps
            if i >= self.max_steps:
                self.transcript.append({
                    'event': 'max_steps_reached',
                    'message': f'Stopped at {self.max_steps} steps'
                })
                break

            # Check transcript size budget
            transcript_chars = sum(len(json.dumps(e)) for e in self.transcript)
            if transcript_chars > self.MAX_TOTAL_TRANSCRIPT_CHARS:
                self.transcript.append({
                    'event': 'transcript_budget_exceeded',
                    'message': f'Transcript exceeded {self.MAX_TOTAL_TRANSCRIPT_CHARS} chars'
                })
                break

            action = action_obj.get('action')

            if action == 'help':
                argv = action_obj.get('argv', [])
                self.handle_help_action(argv)

            elif action == 'run':
                argv = action_obj.get('argv', [])
                self.handle_run_action(argv)

            elif action == 'note':
                text = action_obj.get('text', '')
                self.handle_note_action(text)

            elif action == 'done':
                result = action_obj.get('result', {})
                self.handle_done_action(result)
                break  # Stop on done

            else:
                # Unknown action
                self.transcript.append({
                    'event': 'unknown_action',
                    'action': action,
                    'raw': action_obj
                })

    def generate_report(self) -> str:
        """Generate human-friendly markdown report."""
        # Extract qwen's final suggestions
        done_event = None
        for event in reversed(self.transcript):
            if event.get('event') == 'qwen_done':
                done_event = event
                break

        suggestions = []
        friction_points = []

        if done_event and 'result' in done_event:
            result = done_event['result']
            suggestions = result.get('improvement_suggestions', [])
            friction_points = result.get('friction_points', [])

        # Build report
        report_lines = [
            "# Maestro UX Blindfold Audit Report",
            "",
            f"**Goal**: {self.goal}",
            f"**Repo**: {self.repo}",
            f"**Maestro Binary**: {self.maestro_bin}",
            f"**Qwen Binary**: {self.qwen_bin}",
            f"**Execute Mode**: {'Yes' if self.execute else 'No (safe)'}",
            f"**Timestamp**: {self.telemetry['start_time']}",
            "",
            "## Summary",
            "",
            f"- Help calls: {self.telemetry['help_calls']} / {self.MAX_HELP_CALLS}",
            f"- Run attempts: {self.telemetry['run_attempts']}",
            f"- Successes: {self.telemetry['successes']}",
            f"- Failures: {self.telemetry['failures']}",
            f"- Blocked writes: {self.telemetry['blocked_writes']}",
            f"- Timeouts: {self.telemetry['timeouts']}",
            f"- Unknown commands: {self.telemetry['unknown_commands']}",
            "",
            "## Failure Breakdown",
            ""
        ]

        # Calculate failure reasons
        failure_reasons = {}
        for event in self.transcript:
            if event.get('event') == 'run_result' and event.get('returncode') != 0:
                stderr = event.get('stderr', '').lower()
                if 'timeout' in stderr:
                    failure_reasons['timeout'] = failure_reasons.get('timeout', 0) + 1
                elif 'not found' in stderr or 'unknown' in stderr:
                    failure_reasons['unknown_command'] = failure_reasons.get('unknown_command', 0) + 1
                else:
                    failure_reasons['other'] = failure_reasons.get('other', 0) + 1
            elif event.get('event') == 'blocked_write_attempt':
                failure_reasons['blocked_write'] = failure_reasons.get('blocked_write', 0) + 1

        for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1]):
            report_lines.append(f"- {reason}: {count}")

        if not failure_reasons:
            report_lines.append("- No failures")

        # Add friction points
        report_lines.extend([
            "",
            "## Friction Points (from qwen)",
            ""
        ])

        if friction_points:
            for fp in friction_points:
                issue = fp.get('issue', 'unknown')
                evidence = fp.get('evidence', 'N/A')
                severity = fp.get('severity', 'medium')
                report_lines.append(f"- **[{severity.upper()}]** {issue} (evidence: {evidence})")
        else:
            report_lines.append("- No friction points reported")

        # Add improvement suggestions
        report_lines.extend([
            "",
            "## Improvement Suggestions (prioritized)",
            ""
        ])

        if suggestions:
            for i, sug in enumerate(suggestions[:10], 1):  # Top 10
                priority = sug.get('priority', 'P2')
                area = sug.get('area', 'unknown')
                change = sug.get('proposed_change', 'N/A')
                impact = sug.get('expected_impact', 'N/A')
                evidence = sug.get('evidence', 'N/A')

                report_lines.extend([
                    f"### {i}. [{priority}] {area}",
                    "",
                    f"**Proposed Change**: {change}",
                    "",
                    f"**Expected Impact**: {impact}",
                    "",
                    f"**Evidence**: {evidence}",
                    ""
                ])
        else:
            report_lines.append("- No suggestions reported")

        # Add artifacts location
        report_lines.extend([
            "",
            "## Artifacts",
            "",
            f"All artifacts saved to: `{self.output_dir}`",
            "",
            "- `transcript.jsonl` - Full event log",
            "- `telemetry.json` - Aggregate statistics",
            "- `qwen_prompt.txt` - Exact prompt sent to qwen",
            "- `surface_seed.txt` - Initial help output",
            "- `report.md` - This report",
            ""
        ])

        return "\n".join(report_lines)

    def save_artifacts(self) -> None:
        """Save all artifacts to output directory."""
        # Update telemetry
        self.telemetry['end_time'] = datetime.now(timezone.utc).isoformat()
        self.telemetry['total_transcript_chars'] = sum(
            len(json.dumps(e)) for e in self.transcript
        )

        # Save transcript
        transcript_file = self.output_dir / "transcript.jsonl"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            for event in self.transcript:
                f.write(json.dumps(event) + '\n')

        # Save telemetry
        telemetry_file = self.output_dir / "telemetry.json"
        telemetry_file.write_text(
            json.dumps(self.telemetry, indent=2),
            encoding='utf-8'
        )

        # Save report
        report = self.generate_report()
        report_file = self.output_dir / "report.md"
        report_file.write_text(report, encoding='utf-8')

    def run(self) -> int:
        """Run the full blindfold audit session."""
        print(f"Starting qwen-driven blindfold UX audit...")
        print(f"Goal: {self.goal}")
        print(f"Repo: {self.repo}")
        print(f"Execute mode: {'Yes' if self.execute else 'No (safe)'}")
        print()

        try:
            # Run qwen and get action sequence
            print("Running qwen...")
            actions = self.run_qwen()
            print(f"Qwen generated {len(actions)} actions")

            # Execute action sequence
            print("Executing actions...")
            self.execute_actions(actions)

            # Save artifacts
            print("Saving artifacts...")
            self.save_artifacts()

            # Print summary
            print()
            print("=" * 60)
            print("AUDIT COMPLETE")
            print("=" * 60)
            print(f"Report: {self.output_dir / 'report.md'}")
            print()
            print(f"Steps executed: {len(self.transcript)}")
            print(f"Successes: {self.telemetry['successes']}")
            print(f"Failures: {self.telemetry['failures']}")
            print(f"Blocked writes: {self.telemetry['blocked_writes']}")
            print()

            # Extract top 3 suggestions
            done_event = None
            for event in reversed(self.transcript):
                if event.get('event') == 'qwen_done':
                    done_event = event
                    break

            if done_event and 'result' in done_event:
                suggestions = done_event['result'].get('improvement_suggestions', [])
                if suggestions:
                    print("Top 3 Recommendations:")
                    for i, sug in enumerate(suggestions[:3], 1):
                        priority = sug.get('priority', 'P2')
                        area = sug.get('area', 'unknown')
                        change = sug.get('proposed_change', 'N/A')[:80]
                        print(f"  {i}. [{priority}] {area}: {change}")

            return 0

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

            # Try to save partial artifacts
            try:
                self.save_artifacts()
                print(f"Partial artifacts saved to: {self.output_dir}")
            except:
                pass

            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Qwen-driven blindfold UX audit harness for Maestro'
    )
    parser.add_argument(
        '--goal',
        required=True,
        help='Goal string for the audit (e.g., "Create a runbook")'
    )
    parser.add_argument(
        '--maestro-bin',
        default='maestro',
        help='Maestro binary command (default: maestro)'
    )
    parser.add_argument(
        '--docs-root',
        help='Override MAESTRO_DOCS_ROOT (optional)'
    )
    parser.add_argument(
        '--repo',
        default='.',
        help='Repository path (default: current directory)'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=12,
        help='Maximum action steps (default: 12)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Enable execute mode (allows writes, sandboxed to MAESTRO_DOCS_ROOT)'
    )
    parser.add_argument(
        '--qwen-bin',
        default='qwen',
        help='Qwen binary command (default: qwen)'
    )

    args = parser.parse_args()

    driver = QwenBlindfolDriver(
        goal=args.goal,
        maestro_bin=args.maestro_bin,
        docs_root=args.docs_root,
        repo=args.repo,
        max_steps=args.max_steps,
        execute=args.execute,
        qwen_bin=args.qwen_bin
    )

    sys.exit(driver.run())


if __name__ == '__main__':
    main()
