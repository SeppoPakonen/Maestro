#!/usr/bin/env python3
"""
Create ledger candidates report from extracted command IR
"""

import yaml
import sys
from pathlib import Path
from collections import defaultdict

def extract_ledger_hints_from_cmd(cmd_file):
    """Extract ledger hints from a command IR file."""
    try:
        with open(cmd_file) as f:
            data = yaml.safe_load(f)

        hints = data.get('ledger_hints', [])
        storage_backend = data.get('storage_backend', 'unknown')
        cmd_id = data.get('id', cmd_file.stem)

        return {
            'cmd_id': cmd_id,
            'layer': data.get('layer', 'unknown'),
            'storage_backend': storage_backend,
            'hints': hints,
            'file': str(cmd_file)
        }
    except Exception as e:
        print(f"ERROR reading {cmd_file}: {e}", file=sys.stderr)
        return None

def main():
    # Paths
    cmd_dir = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir' / 'cmd'
    report_dir = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'reports'
    report_file = report_dir / 'ledger_candidates.md'

    # Create report directory
    report_dir.mkdir(parents=True, exist_ok=True)

    # Find all command code layer files
    code_files = sorted(cmd_dir.glob('CMD-*.code.yaml'))

    print(f"Scanning {len(code_files)} command code layer files...")

    # Collect all hints
    all_candidates = []
    markdown_storage_commands = []
    datamarkdown_mentions = []

    for code_file in code_files:
        result = extract_ledger_hints_from_cmd(code_file)
        if not result:
            continue

        # Collect explicit hints from ledger_hints field
        for hint in result['hints']:
            all_candidates.append({
                'cmd_id': result['cmd_id'],
                'type': 'explicit',
                'description': hint,
                'file': result['file']
            })

        # Detect markdown storage backend (violation of REPO_TRUTH_FORMAT_IS_JSON)
        if result['storage_backend'] in ['markdown', 'mixed']:
            markdown_storage_commands.append(result)
            all_candidates.append({
                'cmd_id': result['cmd_id'],
                'type': 'storage_backend_violation',
                'description': f"Command uses {result['storage_backend']} storage backend (violates REPO_TRUTH_FORMAT_IS_JSON)",
                'file': result['file'],
                'invariant': 'REPO_TRUTH_FORMAT_IS_JSON',
                'fix': 'Replace markdown persistence with JSON; update docs/tests'
            })

    # Create markdown report
    report_content = [
        "# Ledger Candidates — Spec→Code Contradictions",
        "",
        "This report lists contradictions detected between v2 specification and observed v1 code behavior.",
        "Generated automatically from command IR extraction.",
        "",
        f"**Total candidates:** {len(all_candidates)}",
        "",
        "---",
        ""
    ]

    # Section 1: Storage Backend Violations
    if markdown_storage_commands:
        report_content.extend([
            "## 1. Storage Backend Violations (REPO_TRUTH_FORMAT_IS_JSON)",
            "",
            f"**Count:** {len(markdown_storage_commands)}",
            "",
            "Commands using markdown or mixed storage backend instead of JSON:",
            ""
        ])

        for cmd in markdown_storage_commands:
            report_content.extend([
                f"### {cmd['cmd_id']}",
                "",
                f"- **Storage backend:** {cmd['storage_backend']}",
                f"- **File:** `{cmd['file']}`",
                f"- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON",
                f"- **Fix required:** Replace markdown persistence with JSON in command implementation",
                ""
            ])

    # Section 2: Explicit Ledger Hints
    explicit_hints = [c for c in all_candidates if c['type'] == 'explicit']
    if explicit_hints:
        report_content.extend([
            "---",
            "",
            "## 2. Explicit Ledger Hints from Code Layer",
            "",
            f"**Count:** {len(explicit_hints)}",
            "",
            "Hints explicitly flagged during extraction:",
            ""
        ])

        # Group by command
        hints_by_cmd = defaultdict(list)
        for hint in explicit_hints:
            hints_by_cmd[hint['cmd_id']].append(hint)

        for cmd_id, hints in sorted(hints_by_cmd.items()):
            report_content.extend([
                f"### {cmd_id}",
                "",
                f"**File:** `{hints[0]['file']}`",
                ""
            ])

            for hint in hints:
                report_content.append(f"- {hint['description']}")

            report_content.append("")

    # Section 3: Summary by Command
    report_content.extend([
        "---",
        "",
        "## 3. Summary by Command",
        "",
        "| Command | Issues | Storage Backend | File |",
        "|---------|--------|-----------------|------|"
    ])

    cmd_summary = defaultdict(lambda: {'count': 0, 'storage': 'unknown', 'file': ''})
    for candidate in all_candidates:
        cmd_id = candidate['cmd_id']
        cmd_summary[cmd_id]['count'] += 1
        if cmd_summary[cmd_id]['file'] == '':
            cmd_summary[cmd_id]['file'] = candidate.get('file', '')

    # Add storage backend info
    for code_file in code_files:
        result = extract_ledger_hints_from_cmd(code_file)
        if result:
            cmd_summary[result['cmd_id']]['storage'] = result['storage_backend']

    for cmd_id, info in sorted(cmd_summary.items()):
        storage = info['storage']
        count = info['count']
        file_short = Path(info['file']).name if info['file'] else '—'
        report_content.append(f"| {cmd_id} | {count} | {storage} | {file_short} |")

    report_content.extend([
        "",
        "---",
        "",
        "## Next Steps",
        "",
        "1. Review each candidate and determine if it represents a true contradiction",
        "2. For confirmed contradictions, create implementation tasks to fix code",
        "3. Update v1 documentation to reflect v2 spec decisions",
        "4. Add tests to prevent regression",
        ""
    ])

    # Write report
    with open(report_file, 'w') as f:
        f.write('\n'.join(report_content))

    print(f"\n✓ Ledger candidates report created: {report_file}")
    print(f"  Total candidates: {len(all_candidates)}")
    print(f"  Storage violations: {len(markdown_storage_commands)}")
    print(f"  Explicit hints: {len(explicit_hints)}")

if __name__ == '__main__':
    main()
