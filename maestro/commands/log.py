"""
Log command handlers for Maestro CLI.
"""

import argparse
import os
import sys
from pathlib import Path

from maestro.log import create_scan, list_scans, load_scan


def add_log_parser(subparsers) -> argparse.ArgumentParser:
    """Add log command parser."""
    log_parser = subparsers.add_parser(
        'log',
        help='Log scanning and observability commands'
    )
    log_subparsers = log_parser.add_subparsers(
        dest='log_subcommand',
        help='Log subcommands'
    )

    # log scan
    scan_parser = log_subparsers.add_parser(
        'scan',
        help='Scan build/run output or log files for errors and warnings'
    )
    scan_parser.add_argument(
        '--source',
        help='Path to log file to scan'
    )
    scan_parser.add_argument(
        '--last-run',
        action='store_true',
        help='Use last captured run output (if exists)'
    )
    scan_parser.add_argument(
        '--kind',
        choices=['build', 'run', 'any'],
        default='any',
        help='Type of scan (build errors, runtime crashes, or any)'
    )
    scan_parser.add_argument(
        '--stdin',
        action='store_true',
        help='Read log from stdin'
    )

    # log list
    list_parser = log_subparsers.add_parser(
        'list',
        aliases=['ls'],
        help='List all log scans'
    )

    # log show
    show_parser = log_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show scan details and findings'
    )
    show_parser.add_argument(
        'scan_id',
        help='Scan ID to show'
    )

    return log_parser


def handle_log_command(args: argparse.Namespace) -> int:
    """Handle log commands."""
    subcommand = getattr(args, 'log_subcommand', None)

    if subcommand in (None, 'list', 'ls'):
        return handle_log_list(args)
    elif subcommand == 'scan':
        return handle_log_scan(args)
    elif subcommand in ('show', 'sh'):
        return handle_log_show(args)
    else:
        print(f"Unknown log subcommand: {subcommand}")
        return 1


def handle_log_scan(args: argparse.Namespace) -> int:
    """Handle log scan command."""
    repo_root = find_repo_root() or os.getcwd()

    # Determine log source
    log_text = None
    source_path = None

    if args.stdin:
        # Read from stdin
        log_text = sys.stdin.read()
    elif args.last_run:
        # Look for last run output
        last_run_path = os.path.join(repo_root, "docs", "maestro", "last_run.txt")
        if not os.path.exists(last_run_path):
            print("Error: No last run output found")
            print(f"Expected: {last_run_path}")
            return 1
        source_path = last_run_path
    elif args.source:
        # Use specified file
        source_path = args.source
        if not os.path.exists(source_path):
            print(f"Error: Log file not found: {source_path}")
            return 1
    else:
        # Try to read from stdin if available
        if not sys.stdin.isatty():
            log_text = sys.stdin.read()
        else:
            print("Error: No log source specified")
            print("Use --source <PATH>, --last-run, --stdin, or pipe log to stdin")
            return 1

    # Create scan
    try:
        scan_id = create_scan(
            source_path=source_path,
            log_text=log_text,
            kind=args.kind,
            repo_root=repo_root,
        )
    except Exception as exc:
        print(f"Error creating scan: {exc}")
        return 1

    # Load scan to show summary
    scan_data = load_scan(scan_id, repo_root)
    if not scan_data:
        print(f"Error: Failed to load scan {scan_id}")
        return 1

    meta = scan_data['meta']
    findings = scan_data['findings']

    # Count findings by severity
    severity_counts = {}
    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    print(f"Scan created: {scan_id}")
    print(f"Source: {source_path or 'stdin'}")
    print(f"Findings: {len(findings)} total")

    if severity_counts:
        print("Breakdown:")
        for severity in ['blocker', 'critical', 'warning', 'info']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")

    if len(findings) > 0:
        print(f"\nNext: maestro issues add --from-log {scan_id}")

    return 0


def handle_log_list(args: argparse.Namespace) -> int:
    """Handle log list command."""
    repo_root = find_repo_root() or os.getcwd()
    scans = list_scans(repo_root)

    if not scans:
        print("No log scans found.")
        return 0

    print(f"Log scans ({len(scans)} total):\n")
    for scan in scans:
        scan_id = scan.get('scan_id', 'unknown')
        timestamp = scan.get('timestamp', 'unknown')
        kind = scan.get('kind', 'any')
        finding_count = scan.get('finding_count', 0)
        source = scan.get('source_path') or 'stdin'

        # Shorten source path for display
        if source != 'stdin':
            source = Path(source).name

        print(f"  {scan_id}")
        print(f"    {timestamp} | {kind} | {finding_count} findings | {source}")

    return 0


def handle_log_show(args: argparse.Namespace) -> int:
    """Handle log show command."""
    repo_root = find_repo_root() or os.getcwd()
    scan_data = load_scan(args.scan_id, repo_root)

    if not scan_data:
        print(f"Scan not found: {args.scan_id}")
        return 1

    meta = scan_data['meta']
    findings = scan_data['findings']

    print(f"Scan ID: {meta.get('scan_id')}")
    print(f"Timestamp: {meta.get('timestamp')}")
    print(f"Kind: {meta.get('kind')}")
    print(f"Source: {meta.get('source_path') or 'stdin'}")
    print(f"CWD: {meta.get('cwd')}")
    if meta.get('command_context'):
        print(f"Command: {meta.get('command_context')}")
    print(f"\nFindings ({len(findings)} total):\n")

    # Group by severity
    by_severity = {}
    for finding in findings:
        severity = finding.severity
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(finding)

    # Show in severity order
    for severity in ['blocker', 'critical', 'warning', 'info']:
        if severity not in by_severity:
            continue

        print(f"  [{severity.upper()}]")
        for finding in by_severity[severity]:
            location = ""
            if finding.file:
                location = f"{finding.file}"
                if finding.line:
                    location += f":{finding.line}"
            if location:
                print(f"    {location}")
            print(f"    {finding.message}")
            if finding.tool:
                print(f"    (tool: {finding.tool}, fingerprint: {finding.fingerprint[:16]}...)")
            else:
                print(f"    (fingerprint: {finding.fingerprint[:16]}...)")
            print()

    return 0


def find_repo_root() -> str | None:
    """Find repository root by looking for .maestro or docs/maestro."""
    current_dir = os.getcwd()
    while current_dir != "/":
        # Check for new-style docs/maestro
        if os.path.exists(os.path.join(current_dir, "docs", "maestro")):
            return current_dir
        # Check for old-style .maestro
        if os.path.exists(os.path.join(current_dir, ".maestro")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None
