#!/usr/bin/env python3
"""
Command suggestion tool - suggest next commands based on adjacency heuristics.

This tool provides "doctor-like" suggestions for next commands based on common
command sequences and prerequisite gates.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add maestro to path
MAESTRO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MAESTRO_ROOT))


# Command adjacency heuristics (common command sequences)
ADJACENCY_MAP = {
    "init": [
        ("repo resolve", "Scan repository structure"),
        ("select toolchain detect", "Detect available toolchains"),
        ("platform caps detect", "Detect platform capabilities"),
        ("runbook list", "View available runbooks"),
        ("workflow list", "View available workflows"),
    ],
    "repo resolve": [
        ("repo conf show", "Review repository configuration"),
        ("make", "Build the project"),
        ("select toolchain set", "Select build toolchain"),
        ("track add", "Create work tracking hierarchy"),
        ("runbook add", "Document build process"),
    ],
    "repo conf": [
        ("make", "Execute build with selected config"),
        ("tu build", "Build translation unit index"),
        ("select toolchain show", "Review selected toolchain"),
    ],
    "make": [
        ("log scan", "Scan build logs for issues"),
        ("issues add", "Add build error as issue"),
        ("tu query", "Query code structure"),
        ("repo show", "Review build outputs"),
    ],
    "log scan": [
        ("issues add", "Ingest scan findings as issues"),
        ("log show", "Review scan details"),
        ("work start", "Start work on fixing issues"),
    ],
    "issues add": [
        ("task add", "Create task to fix issue"),
        ("issues link", "Link issue to existing task"),
        ("work issue", "Start work on specific issue"),
        ("solutions match", "Find matching solutions"),
    ],
    "task add": [
        ("work task", "Start work on task"),
        ("task link", "Link task to phase or issue"),
        ("discuss task", "Discuss task with AI"),
        ("runbook add", "Document task approach"),
    ],
    "work task": [
        ("wsession breadcrumb add", "Add breadcrumb to work session"),
        ("discuss", "Get AI assistance"),
        ("make", "Build and test changes"),
        ("task set status", "Update task status"),
    ],
    "discuss": [
        ("wsession breadcrumb add", "Record discussion outcomes"),
        ("task add", "Create tasks from discussion"),
        ("make", "Execute discussed changes"),
        ("discuss resume", "Resume interrupted session"),
    ],
    "runbook add": [
        ("runbook step-add", "Add steps to runbook"),
        ("runbook show", "Review runbook content"),
        ("workflow init", "Create workflow from runbook"),
        ("runbook export", "Export runbook to markdown"),
    ],
    "workflow init": [
        ("workflow node add", "Add nodes to workflow"),
        ("workflow edge add", "Connect workflow nodes"),
        ("workflow validate", "Validate workflow structure"),
        ("workflow render", "Render workflow diagram"),
    ],
    "select toolchain": [
        ("platform caps detect", "Detect platform capabilities"),
        ("repo resolve", "Re-scan with toolchain context"),
        ("make", "Build with selected toolchain"),
        ("select toolchain export", "Export toolchain profile"),
    ],
    "platform caps": [
        ("platform caps prefer", "Set preferred capabilities"),
        ("platform caps require", "Set required capabilities"),
        ("select toolchain set", "Select matching toolchain"),
        ("repo conf show", "Review resolved configuration"),
    ],
    "convert add": [
        ("convert plan", "View conversion plan"),
        ("convert run", "Execute conversion"),
        ("discuss convert", "Discuss conversion approach"),
    ],
    "convert plan": [
        ("convert plan approve", "Approve conversion plan"),
        ("convert plan reject", "Reject and regenerate plan"),
        ("convert show", "Review plan details"),
    ],
}


# Prerequisite gates for common commands
PREREQUISITE_GATES = {
    "make": ["REPO_TRUTH_EXISTS", "TOOLCHAIN_SELECTED"],
    "tu build": ["REPO_TRUTH_EXISTS", "MAKE_SUCCESS"],
    "work start": ["REPO_TRUTH_EXISTS", "!BLOCKED_BY_BUILD_ERRORS"],
    "repo conf show": ["REPO_TRUTH_EXISTS"],
    "log scan": ["BUILD_OUTPUT_EXISTS"],
    "issues add": ["LOG_SCAN_COMPLETE OR MANUAL_TRIAGE"],
    "discuss": ["REPO_TRUTH_EXISTS"],
}


def get_command_prefix(command: str) -> str:
    """
    Extract command prefix for adjacency lookup.

    Args:
        command: Full command (e.g., "repo resolve lite")

    Returns:
        Command prefix (e.g., "repo resolve")
    """
    tokens = command.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:2])
    elif len(tokens) == 1:
        return tokens[0]
    return ""


def suggest_next_commands(command: str, top_n: int = 5) -> List[Tuple[str, str]]:
    """
    Suggest next commands based on adjacency heuristics.

    Args:
        command: Current command
        top_n: Number of suggestions to return

    Returns:
        List of (command, rationale) tuples
    """
    prefix = get_command_prefix(command)

    # Look up adjacency map
    if prefix in ADJACENCY_MAP:
        suggestions = ADJACENCY_MAP[prefix][:top_n]
    else:
        # No specific adjacency map - return general suggestions
        suggestions = [
            ("discuss", "Get AI assistance with next steps"),
            ("make", "Build and test changes"),
            ("log scan", "Scan for issues"),
            ("work start", "Start work session"),
        ][:top_n]

    return suggestions


def check_prerequisites(command: str) -> List[str]:
    """
    Check prerequisites (gates) for a command.

    Args:
        command: Command to check

    Returns:
        List of prerequisite gate names
    """
    prefix = get_command_prefix(command)
    return PREREQUISITE_GATES.get(prefix, [])


def analyze_runbook_file(file_path: Path) -> Dict:
    """
    Analyze a runbook file and suggest next commands.

    Args:
        file_path: Path to runbook file

    Returns:
        Dict with analysis results
    """
    # TODO: Parse runbook file and extract last command
    # For now, return placeholder
    return {
        "last_command": None,
        "total_commands": 0,
        "suggestions": [],
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Suggest next commands based on context",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Current command (e.g., 'repo resolve')",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Analyze runbook file and suggest next commands",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of suggestions to show (default: 5)",
    )

    args = parser.parse_args()

    if args.file:
        # Analyze runbook file
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        result = analyze_runbook_file(args.file)
        print(f"Runbook analysis: {args.file}")
        print(f"Total commands: {result['total_commands']}")
        if result['last_command']:
            print(f"Last command: {result['last_command']}")
            print("\nSuggested next commands:")
            for cmd, reason in result['suggestions']:
                print(f"  - {cmd:<30} # {reason}")
        else:
            print("No commands found in runbook")

    elif args.command:
        # Suggest next commands after specific command
        print(f"After: maestro {args.command}\n")

        # Check prerequisites
        prereqs = check_prerequisites(args.command)
        if prereqs:
            print("Prerequisites:")
            for gate in prereqs:
                if gate.startswith("!"):
                    print(f"  ⚠️  Must NOT have: {gate[1:]}")
                else:
                    print(f"  ✓  Must have: {gate}")
            print()

        # Get suggestions
        suggestions = suggest_next_commands(args.command, top_n=args.top)
        print(f"Top {len(suggestions)} suggested next commands:")
        for i, (cmd, reason) in enumerate(suggestions, 1):
            print(f"  {i}. maestro {cmd:<30} # {reason}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
