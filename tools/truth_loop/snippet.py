#!/usr/bin/env python3
"""
Runbook snippet emitter - generate runbook-ready code blocks.

This tool generates shell script snippets for runbook examples.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add maestro to path
MAESTRO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MAESTRO_ROOT))


# Command metadata for snippet generation
COMMAND_METADATA = {
    "init": {
        "expect": "Repo truth created under docs/maestro/",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": ["REPO_TRUTH_FORMAT_IS_JSON"],
    },
    "repo resolve": {
        "expect": "Repository structure scanned and indexed",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "REPO_INDEX"],
        "gates": ["REPO_RESOLVE_IDEMPOTENCY"],
    },
    "repo refresh": {
        "expect": "Repository index refreshed with latest changes",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "REPO_INDEX"],
        "gates": [],
    },
    "make": {
        "expect": "Build executed successfully",
        "stores": ["BUILD_OUTPUT"],
        "gates": ["MAKE_TARGET_VALID", "TOOLCHAIN_SELECTED"],
    },
    "runbook list": {
        "expect": "List of runbooks displayed",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "runbook show": {
        "expect": "Runbook content displayed",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "runbook archive": {
        "expect": "Runbook moved to archived/ directory",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "ARCHIVE_INDEX"],
        "gates": ["ARCHIVE_IDEMPOTENCY"],
    },
    "runbook restore": {
        "expect": "Runbook restored from archive",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "ARCHIVE_INDEX"],
        "gates": ["RESTORE_PATH_OCCUPIED"],
    },
    "workflow list": {
        "expect": "List of workflows displayed",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "workflow show": {
        "expect": "Workflow content displayed",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "workflow archive": {
        "expect": "Workflow moved to archived/ directory",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "ARCHIVE_INDEX"],
        "gates": ["ARCHIVE_IDEMPOTENCY"],
    },
    "workflow restore": {
        "expect": "Workflow restored from archive",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO", "ARCHIVE_INDEX"],
        "gates": ["RESTORE_PATH_OCCUPIED"],
    },
    "discuss": {
        "expect": "AI discussion session started",
        "stores": ["AI_SESSION_DOCS_MAESTRO"],
        "gates": [],
    },
    "work start": {
        "expect": "Work session started",
        "stores": ["WORK_SESSION_DOCS_MAESTRO"],
        "gates": ["BLOCKED_BY_BUILD_ERRORS"],
    },
    "task add": {
        "expect": "Task created",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "issues add": {
        "expect": "Issue created",
        "stores": ["REPO_TRUTH_DOCS_MAESTRO"],
        "gates": [],
    },
    "log scan": {
        "expect": "Log scanned and findings extracted",
        "stores": ["LOG_SCAN_DOCS_MAESTRO"],
        "gates": ["LOG_SCAN_DETERMINISM"],
    },
}


def get_command_metadata(command: str) -> Dict[str, any]:
    """
    Get metadata for a command.

    Args:
        command: Command string (e.g., "repo resolve")

    Returns:
        Dict with expect, stores, gates, notes
    """
    # Try exact match first
    if command in COMMAND_METADATA:
        return COMMAND_METADATA[command]

    # Try prefix match (e.g., "repo resolve lite" matches "repo resolve")
    for cmd_key in COMMAND_METADATA:
        if command.startswith(cmd_key):
            return COMMAND_METADATA[cmd_key]

    # No metadata found - return defaults
    return {
        "expect": "TODO: Add expected output description",
        "stores": ["TODO_STORE"],
        "gates": [],
    }


def generate_snippet(command: str, include_example: bool = True) -> str:
    """
    Generate a runbook snippet for a command.

    Args:
        command: Command string (e.g., "repo resolve")
        include_example: Whether to include example arguments

    Returns:
        Runbook snippet as string
    """
    metadata = get_command_metadata(command)

    # Build the command line
    cmd_line = f"run maestro {command}"

    # Build snippet
    lines = [
        f"{cmd_line}",
        f"# EXPECT: {metadata['expect']}",
    ]

    # Add stores
    if metadata["stores"]:
        stores_str = ", ".join(metadata["stores"])
        lines.append(f"# STORES: {stores_str}")
    else:
        lines.append("# STORES: none")

    # Add gates
    if metadata["gates"]:
        gates_str = ", ".join(metadata["gates"])
        lines.append(f"# GATES: {gates_str}")
    else:
        lines.append("# GATES: none")

    # Add notes if metadata has TODO markers
    if "TODO" in str(metadata):
        lines.append("# NOTES: Metadata incomplete - verify expected outputs and gates")

    return "\n".join(lines)


def load_cli_only_commands(reports_dir: Path) -> List[str]:
    """
    Load commands that are in CLI but missing runbook examples.

    Args:
        reports_dir: Reports directory path

    Returns:
        List of CLI-only command strings
    """
    diff_file = reports_dir / "truth_loop_diff.json"

    if not diff_file.exists():
        print(f"Error: {diff_file} not found. Run compare.py first.", file=sys.stderr)
        sys.exit(1)

    with open(diff_file, "r") as f:
        data = json.load(f)

    return data.get("needs_docs", [])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate runbook snippets for commands",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to generate snippet for (e.g., 'repo resolve')",
    )
    parser.add_argument(
        "--all-missing-examples",
        action="store_true",
        help="Generate snippets for all commands missing examples",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit number of snippets when using --all-missing-examples (default: 20)",
    )

    args = parser.parse_args()

    if args.all_missing_examples:
        # Generate snippets for all missing commands
        reports_dir = MAESTRO_ROOT / "docs" / "workflows" / "v3" / "reports"
        cli_only = load_cli_only_commands(reports_dir)

        print("# Runbook Snippets for Missing Examples\n")
        print(f"# Generated {min(len(cli_only), args.limit)} of {len(cli_only)} snippets\n")
        print("#!/usr/bin/env bash")
        print("set -euo pipefail\n")
        print("run(){ echo \"+ $*\"; }\n")

        for i, cmd in enumerate(cli_only[:args.limit]):
            if i > 0:
                print()
            snippet = generate_snippet(cmd)
            print(snippet)

    elif args.command:
        # Generate snippet for specific command
        snippet = generate_snippet(args.command)
        print(snippet)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
