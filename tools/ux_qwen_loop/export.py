"""
Artifact export for qwen blindfold UX evaluation.

Exports session data in a format compatible with maestro ux postmortem.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def export_artifacts(
    eval_id: str,
    attempts: List[Dict[str, Any]],
    telemetry: Dict[str, Any],
    surface_seed: str,
    stuck_summary: Dict[str, Any],
    goal: str,
    repo_root: str,
    maestro_bin: str
) -> Path:
    """Export all artifacts to docs/maestro/ux_eval/<EVAL_ID>/.

    Args:
        eval_id: Unique evaluation ID
        attempts: List of step events
        telemetry: Aggregate statistics
        surface_seed: Top-level help output
        stuck_summary: Summary from stuck detector
        goal: Original goal
        repo_root: Repository root path
        maestro_bin: Maestro binary used

    Returns:
        Path to output directory
    """
    # Determine output directory
    # Try docs/maestro first, fall back to cwd if not available
    repo_path = Path(repo_root)
    candidates = [
        repo_path / "docs" / "maestro" / "ux_eval",
        repo_path / "ux_eval",
        Path.cwd() / "ux_eval"
    ]

    output_base = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            output_base = candidate
            break
        except (PermissionError, OSError):
            continue

    if output_base is None:
        # Last resort: temp directory
        output_base = Path(tempfile.gettempdir()) / "maestro_ux_eval"
        output_base.mkdir(parents=True, exist_ok=True)

    output_dir = output_base / eval_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export attempts.jsonl
    attempts_path = output_dir / "attempts.jsonl"
    with open(attempts_path, 'w', encoding='utf-8') as f:
        for attempt in attempts:
            f.write(json.dumps(attempt) + '\n')

    # Export telemetry.json
    telemetry_path = output_dir / "telemetry.json"
    with open(telemetry_path, 'w', encoding='utf-8') as f:
        json.dump(telemetry, f, indent=2)

    # Export surface.txt
    surface_path = output_dir / "surface.txt"
    with open(surface_path, 'w', encoding='utf-8') as f:
        f.write(surface_seed)

    # Generate and export report.md
    report_path = output_dir / "report.md"
    report = generate_report(
        eval_id=eval_id,
        goal=goal,
        telemetry=telemetry,
        stuck_summary=stuck_summary,
        attempts=attempts,
        maestro_bin=maestro_bin,
        repo_root=repo_root
    )
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return output_dir


def generate_report(
    eval_id: str,
    goal: str,
    telemetry: Dict[str, Any],
    stuck_summary: Dict[str, Any],
    attempts: List[Dict[str, Any]],
    maestro_bin: str,
    repo_root: str
) -> str:
    """Generate human-friendly markdown report."""

    lines = []
    lines.append("# Qwen Blindfold UX Evaluation Report")
    lines.append("")
    lines.append(f"**Eval ID**: {eval_id}")
    lines.append(f"**Goal**: {goal}")
    lines.append(f"**Repo**: {repo_root}")
    lines.append(f"**Maestro**: {maestro_bin}")
    lines.append(f"**Timestamp**: {telemetry.get('start_time', 'unknown')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total steps: {telemetry.get('total_steps', 0)} / {telemetry.get('max_steps', 0)}")
    lines.append(f"- Help calls: {telemetry.get('help_calls', 0)}")
    lines.append(f"- Run calls: {telemetry.get('run_calls', 0)}")
    lines.append(f"- Successes: {telemetry.get('successes', 0)}")
    lines.append(f"- Failures: {telemetry.get('failures', 0)}")
    lines.append(f"- Timeouts: {telemetry.get('timeouts', 0)}")
    lines.append(f"- Stuck reason: {telemetry.get('stuck_reason', 'none')}")
    lines.append("")

    # Stuck diagnosis
    stuck_reason = telemetry.get('stuck_reason')
    if stuck_reason and stuck_reason not in ['done_by_qwen', 'none']:
        lines.append("## Stuck Diagnosis")
        lines.append("")
        lines.append(f"**Reason**: {stuck_reason}")
        lines.append("")

        # Add stuck detector summary
        lines.append("**Stuck Detector Summary**:")
        lines.append("")
        lines.append(f"- Unique commands: {stuck_summary.get('unique_commands', 0)}")
        lines.append(f"- Most repeated: `{stuck_summary.get('most_repeated_command', ['none', 0])[0]}` ({stuck_summary.get('most_repeated_command', ['none', 0])[1]} times)")
        lines.append(f"- Total timeouts: {stuck_summary.get('total_timeouts', 0)}")
        lines.append(f"- Total errors: {stuck_summary.get('total_errors', 0)}")
        lines.append(f"- Unique IDs seen: {stuck_summary.get('unique_ids_seen', 0)}")
        lines.append(f"- Steps since progress: {stuck_summary.get('steps_since_last_progress', 0)}")
        lines.append(f"- Recent help ratio: {stuck_summary.get('recent_help_ratio', 0):.2%}")
        lines.append("")

    # UX Fix Recommendations (extracted from failure patterns)
    recommendations = extract_ux_recommendations(attempts, stuck_reason, stuck_summary)
    if recommendations:
        lines.append("## Recommended UX Fixes")
        lines.append("")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"### {i}. {rec['title']}")
            lines.append("")
            lines.append(f"**Priority**: {rec['priority']}")
            lines.append(f"**Evidence**: {rec['evidence']}")
            lines.append("")
            lines.append(f"**Proposed Change**: {rec['change']}")
            lines.append("")
            lines.append(f"**Expected Impact**: {rec['impact']}")
            lines.append("")

    # Step-by-step transcript (bounded)
    lines.append("## Transcript (last 20 steps)")
    lines.append("")
    last_steps = attempts[-20:] if len(attempts) > 20 else attempts
    for step in last_steps:
        lines.append(f"### Step {step.get('step', '?')}")
        lines.append("")
        lines.append(f"**Command**: `{step.get('command', '')}`")
        if step.get('note'):
            lines.append(f"**Note**: {step.get('note', '')}")
        lines.append(f"**Exit Code**: {step.get('exit_code', 0)}")
        lines.append(f"**Duration**: {step.get('duration', 0):.2f}s")
        if step.get('timeout'):
            lines.append("**Timeout**: Yes")
        if step.get('rejected'):
            lines.append(f"**Rejected**: {step.get('rejection_reason', 'unknown')}")
        lines.append("")

        stdout = step.get('stdout', '')
        stderr = step.get('stderr', '')

        if stdout:
            lines.append("**Stdout**:")
            lines.append("```")
            lines.append(stdout[:500])
            if len(stdout) > 500:
                lines.append("... [TRUNCATED]")
            lines.append("```")
            lines.append("")

        if stderr:
            lines.append("**Stderr**:")
            lines.append("```")
            lines.append(stderr[:500])
            if len(stderr) > 500:
                lines.append("... [TRUNCATED]")
            lines.append("```")
            lines.append("")

    # Artifacts
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"All artifacts saved to: `docs/maestro/ux_eval/{eval_id}/`")
    lines.append("")
    lines.append("- `attempts.jsonl` - Step-by-step transcript")
    lines.append("- `telemetry.json` - Aggregate statistics")
    lines.append("- `surface.txt` - Top-level help output")
    lines.append("- `report.md` - This report")
    lines.append("")

    return '\n'.join(lines)


def extract_ux_recommendations(
    attempts: List[Dict[str, Any]],
    stuck_reason: str,
    stuck_summary: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Extract UX fix recommendations from failure patterns."""
    recommendations = []

    # Recommendation 1: Repeated command → better error message or examples
    most_repeated = stuck_summary.get('most_repeated_command', ['none', 0])
    if most_repeated[1] >= 2:
        recommendations.append({
            'title': 'Improve feedback for repeated command',
            'priority': 'P0',
            'evidence': f'Command `{most_repeated[0]}` repeated {most_repeated[1]} times',
            'change': f'Add helpful error message or usage example for: {most_repeated[0]}',
            'impact': 'Reduce confusion when user repeats same command expecting different result'
        })

    # Recommendation 2: Help loop → better command discovery
    help_ratio = stuck_summary.get('recent_help_ratio', 0)
    if help_ratio > 0.5:
        recommendations.append({
            'title': 'Improve command discoverability',
            'priority': 'P1',
            'evidence': f'{help_ratio:.0%} of recent commands were help calls',
            'change': 'Add command suggestions or "next steps" to help text',
            'impact': 'Reduce time spent reading help pages, faster task completion'
        })

    # Recommendation 3: Timeouts → performance or missing progress indicators
    total_timeouts = stuck_summary.get('total_timeouts', 0)
    if total_timeouts > 0:
        recommendations.append({
            'title': 'Add progress indicators or reduce timeout exposure',
            'priority': 'P1',
            'evidence': f'{total_timeouts} commands timed out',
            'change': 'Add progress bars, streaming output, or async execution with status checks',
            'impact': 'Better user experience for long-running operations'
        })

    # Recommendation 4: No progress → unclear success indicators
    steps_no_progress = stuck_summary.get('steps_since_last_progress', 0)
    if steps_no_progress >= 5:
        recommendations.append({
            'title': 'Add clear success indicators',
            'priority': 'P1',
            'evidence': f'{steps_no_progress} steps without visible progress markers (IDs, files)',
            'change': 'Print clear success messages with IDs or file paths on completion',
            'impact': 'User knows immediately when operation succeeded and what was created'
        })

    # Recommendation 5: Repeated errors → input validation or better error messages
    total_errors = stuck_summary.get('total_errors', 0)
    if total_errors >= 3:
        recommendations.append({
            'title': 'Improve error messages and input validation',
            'priority': 'P2',
            'evidence': f'{total_errors} commands failed',
            'change': 'Add validation with specific error messages explaining what went wrong and how to fix',
            'impact': 'Faster error recovery, reduced frustration'
        })

    return recommendations
