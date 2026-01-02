"""
UX report generator for evaluation results.

Generates human-readable markdown reports with failure categorization
and suggested improvements.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from .help_surface import HelpNode
from .telemetry import AttemptRecord


class UXReportGenerator:
    """
    Generates UX evaluation reports.

    Produces markdown reports with:
    - Goal and discovered surface summary
    - Attempts timeline
    - Failure categorization
    - Suggested doc/CLI improvements (ranked)
    - Next best command to try
    """

    def __init__(
        self,
        eval_id: str,
        goal: str,
        help_surface: Dict[tuple, HelpNode],
        attempts: List[AttemptRecord],
        telemetry_summary: dict,
        verbose: bool = False
    ):
        """
        Initialize report generator.

        Args:
            eval_id: Evaluation ID
            goal: Goal string
            help_surface: Discovered command surface
            attempts: List of attempt records
            telemetry_summary: Telemetry summary dict
            verbose: Whether to print progress
        """
        self.eval_id = eval_id
        self.goal = goal
        self.help_surface = help_surface
        self.attempts = attempts
        self.telemetry_summary = telemetry_summary
        self.verbose = verbose

    def generate_report(self, output_path: Path) -> None:
        """
        Generate markdown report.

        Args:
            output_path: Path to write report markdown file
        """
        lines = []

        # Header
        lines.append(f"# UX Evaluation Report: {self.eval_id}")
        lines.append(f"")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"")

        # Goal
        lines.append(f"## Goal")
        lines.append(f"")
        lines.append(f"> {self.goal}")
        lines.append(f"")

        # Discovered Surface Summary
        lines.append(f"## Discovered Surface Summary")
        lines.append(f"")
        lines.append(f"- **Total Commands:** {len(self.help_surface)}")
        lines.append(f"- **Help Calls:** {self.telemetry_summary['help_call_count']}")
        lines.append(f"- **Total Help Bytes:** {sum(len(node.help_text) for node in self.help_surface.values())}")
        lines.append(f"")

        # Top-level commands
        top_level_cmds = [
            ' '.join(node.command_path)
            for node in self.help_surface.values()
            if len(node.command_path) == 2  # maestro + subcommand
        ]
        if top_level_cmds:
            lines.append(f"**Top-level commands discovered:** {', '.join(sorted(top_level_cmds)[:10])}")
            if len(top_level_cmds) > 10:
                lines.append(f" ... and {len(top_level_cmds) - 10} more")
            lines.append(f"")

        # Attempts Timeline
        lines.append(f"## Attempts Timeline")
        lines.append(f"")
        lines.append(f"- **Total Attempts:** {len(self.attempts)}")
        lines.append(f"- **Successful:** {self.telemetry_summary['successful_attempts']}")
        lines.append(f"- **Failed:** {self.telemetry_summary['failed_attempts']}")
        lines.append(f"- **Timeouts:** {self.telemetry_summary['timeout_count']}")
        lines.append(f"- **Unknown Commands:** {self.telemetry_summary['unknown_command_count']}")
        lines.append(f"")

        if self.attempts:
            lines.append(f"### First {min(5, len(self.attempts))} Attempts")
            lines.append(f"")

            for attempt in self.attempts[:5]:
                cmd_str = ' '.join(attempt.command_argv)
                status_emoji = "✅" if attempt.exit_code == 0 else "❌"
                status_text = "SUCCESS" if attempt.exit_code == 0 else f"FAILED (exit {attempt.exit_code})"

                if attempt.timed_out:
                    status_text = "TIMEOUT"
                    status_emoji = "⏱️"

                lines.append(f"{attempt.attempt_index + 1}. {status_emoji} `{cmd_str}` - {status_text} ({attempt.duration_ms}ms)")

                # Show stderr excerpt if failed
                if attempt.exit_code != 0 and attempt.stderr_excerpt:
                    excerpt = attempt.stderr_excerpt[:200]
                    if len(attempt.stderr_excerpt) > 200:
                        excerpt += "..."
                    lines.append(f"   ```")
                    lines.append(f"   {excerpt}")
                    lines.append(f"   ```")

            lines.append(f"")

        # Failure Categorization
        lines.extend(self._generate_failure_categorization())

        # Suggested Improvements
        lines.extend(self._generate_suggested_improvements())

        # Next Best Command
        lines.extend(self._generate_next_command())

        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        if self.verbose:
            print(f"Generated UX report: {output_path}")

    def _generate_failure_categorization(self) -> List[str]:
        """Generate failure categorization section."""
        lines = []
        lines.append(f"## Failure Categorization")
        lines.append(f"")

        # Categorize failures
        timeout_failures = [a for a in self.attempts if a.timed_out]
        unknown_cmd_failures = [a for a in self.attempts if a.exit_code == 127]
        help_ambiguity_failures = [
            a for a in self.attempts
            if a.exit_code != 0
            and not a.timed_out
            and a.exit_code != 127
            and ('unrecognized' in a.stderr_excerpt.lower() or 'invalid' in a.stderr_excerpt.lower())
        ]
        other_failures = [
            a for a in self.attempts
            if a.exit_code != 0
            and a not in timeout_failures
            and a not in unknown_cmd_failures
            and a not in help_ambiguity_failures
        ]

        if timeout_failures:
            lines.append(f"### Timeouts ({len(timeout_failures)})")
            lines.append(f"")
            lines.append(f"Commands that exceeded timeout budget:")
            for attempt in timeout_failures[:3]:  # Show first 3
                cmd_str = ' '.join(attempt.command_argv)
                lines.append(f"- `{cmd_str}`")
            if len(timeout_failures) > 3:
                lines.append(f"- ... and {len(timeout_failures) - 3} more")
            lines.append(f"")

        if unknown_cmd_failures:
            lines.append(f"### Unknown Commands ({len(unknown_cmd_failures)})")
            lines.append(f"")
            lines.append(f"Commands not found or not recognized:")
            for attempt in unknown_cmd_failures[:3]:
                cmd_str = ' '.join(attempt.command_argv)
                lines.append(f"- `{cmd_str}`")
            if len(unknown_cmd_failures) > 3:
                lines.append(f"- ... and {len(unknown_cmd_failures) - 3} more")
            lines.append(f"")

        if help_ambiguity_failures:
            lines.append(f"### Help Ambiguity / Unclear Errors ({len(help_ambiguity_failures)})")
            lines.append(f"")
            lines.append(f"Commands failed due to unclear help or error messages:")
            for attempt in help_ambiguity_failures[:3]:
                cmd_str = ' '.join(attempt.command_argv)
                excerpt = attempt.stderr_excerpt[:100]
                lines.append(f"- `{cmd_str}`: {excerpt}")
            if len(help_ambiguity_failures) > 3:
                lines.append(f"- ... and {len(help_ambiguity_failures) - 3} more")
            lines.append(f"")

        if other_failures:
            lines.append(f"### Other Failures ({len(other_failures)})")
            lines.append(f"")
            for attempt in other_failures[:3]:
                cmd_str = ' '.join(attempt.command_argv)
                lines.append(f"- `{cmd_str}` (exit {attempt.exit_code})")
            if len(other_failures) > 3:
                lines.append(f"- ... and {len(other_failures) - 3} more")
            lines.append(f"")

        if not (timeout_failures or unknown_cmd_failures or help_ambiguity_failures or other_failures):
            lines.append(f"No failures detected.")
            lines.append(f"")

        return lines

    def _generate_suggested_improvements(self) -> List[str]:
        """Generate suggested improvements section."""
        lines = []
        lines.append(f"## Suggested Improvements (Ranked)")
        lines.append(f"")

        improvements = []

        # Heuristic 1: If many unknown commands, suggest better help structure
        if self.telemetry_summary['unknown_command_count'] > 2:
            improvements.append({
                'priority': 'HIGH',
                'category': 'Help Structure',
                'suggestion': 'Improve subcommand discovery in help text (found {count} unknown commands)'.format(
                    count=self.telemetry_summary['unknown_command_count']
                )
            })

        # Heuristic 2: If many timeouts, suggest performance or async issues
        if self.telemetry_summary['timeout_count'] > 1:
            improvements.append({
                'priority': 'MEDIUM',
                'category': 'Performance',
                'suggestion': 'Investigate command timeouts ({count} commands exceeded timeout)'.format(
                    count=self.telemetry_summary['timeout_count']
                )
            })

        # Heuristic 3: If help calls are high relative to attempts, suggest better discoverability
        if len(self.attempts) > 0 and self.telemetry_summary['help_call_count'] > len(self.attempts) * 2:
            improvements.append({
                'priority': 'MEDIUM',
                'category': 'Discoverability',
                'suggestion': 'Reduce need for repeated help calls (help/attempt ratio: {ratio:.1f})'.format(
                    ratio=self.telemetry_summary['help_call_count'] / max(1, len(self.attempts))
                )
            })

        # Heuristic 4: If no successful attempts, suggest better examples or onboarding
        if len(self.attempts) > 0 and self.telemetry_summary['successful_attempts'] == 0:
            improvements.append({
                'priority': 'HIGH',
                'category': 'Onboarding',
                'suggestion': 'Add examples or quickstart guide (no successful attempts for goal)'
            })

        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        improvements.sort(key=lambda x: priority_order.get(x['priority'], 3))

        if improvements:
            for imp in improvements:
                lines.append(f"### [{imp['priority']}] {imp['category']}")
                lines.append(f"")
                lines.append(f"{imp['suggestion']}")
                lines.append(f"")
        else:
            lines.append(f"No major improvements identified. UX appears discoverable for this goal.")
            lines.append(f"")

        return lines

    def _generate_next_command(self) -> List[str]:
        """Generate next best command section."""
        lines = []
        lines.append(f"## Next Best Command")
        lines.append(f"")

        # Find first successful command, or first failed command if none succeeded
        successful = [a for a in self.attempts if a.exit_code == 0]

        if successful:
            next_cmd = successful[0]
            lines.append(f"The first successful command was:")
            lines.append(f"")
            lines.append(f"```bash")
            lines.append(f"{' '.join(next_cmd.command_argv)}")
            lines.append(f"```")
            lines.append(f"")
            lines.append(f"Consider this as the canonical path for similar goals.")
        elif self.attempts:
            lines.append(f"No successful attempts found. The first attempt was:")
            lines.append(f"")
            lines.append(f"```bash")
            lines.append(f"{' '.join(self.attempts[0].command_argv)}")
            lines.append(f"```")
            lines.append(f"")
            lines.append(f"Review the error and help text to identify the correct command.")
        else:
            lines.append(f"No attempts were made.")

        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*This report was generated by `maestro ux eval` blindfold evaluator.*")
        lines.append(f"")

        return lines
