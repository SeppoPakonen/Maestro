#!/usr/bin/env python3
"""
CLI surface extractor for truth loop.

This module walks the argparse parser tree and extracts all reachable commands,
respecting the MAESTRO_ENABLE_LEGACY kill-switch.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add maestro to path
MAESTRO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MAESTRO_ROOT))

from maestro.modules.cli_parser import create_main_parser


def walk_parser(
    parser: argparse.ArgumentParser,
    prefix: List[str] = None,
    commands: Set[str] = None,
    command_details: List[Dict] = None,
) -> Tuple[Set[str], List[Dict]]:
    """
    Recursively walk an argparse parser and extract all command paths.

    Args:
        parser: ArgumentParser instance
        prefix: Command prefix path (e.g., ["repo", "resolve"])
        commands: Set to accumulate normalized command strings
        command_details: List to accumulate detailed command info

    Returns:
        Tuple of (commands set, command details list)
    """
    if prefix is None:
        prefix = []
    if commands is None:
        commands = set()
    if command_details is None:
        command_details = []

    # Look for subparsers
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # Found subparsers - walk each choice
            for choice_name, choice_parser in action.choices.items():
                # Skip help command and single-letter aliases in output
                if choice_name == "help" or choice_name == "h":
                    continue

                # Build command path
                command_path = prefix + [choice_name]
                command_str = " ".join(command_path)

                # Check if this is an alias (single letter or obvious alias)
                is_alias = (
                    len(choice_name) == 1
                    or choice_name in ("ls", "sh", "rm", "b", "bc", "tl", "stt")
                )

                # Only add non-alias commands to the set
                if not is_alias:
                    commands.add(command_str)

                    # Extract command details
                    detail = {
                        "command": command_str,
                        "path": command_path,
                        "help": action.choices[choice_name].description or "",
                        "aliases": [],
                    }

                    # Find aliases for this command
                    for alias_name, alias_parser in action.choices.items():
                        if alias_parser is choice_parser and alias_name != choice_name:
                            detail["aliases"].append(alias_name)

                    command_details.append(detail)

                # Recurse into subparser
                walk_parser(choice_parser, command_path, commands, command_details)

    return commands, command_details


def extract_cli_surface(enable_legacy: bool = False) -> Tuple[Set[str], List[Dict]]:
    """
    Extract the CLI surface by walking the argparse tree.

    Args:
        enable_legacy: Whether to enable legacy commands (MAESTRO_ENABLE_LEGACY=1)

    Returns:
        Tuple of (commands set, command details list)
    """
    # Set environment variable for legacy mode
    if enable_legacy:
        os.environ["MAESTRO_ENABLE_LEGACY"] = "1"
    else:
        os.environ["MAESTRO_ENABLE_LEGACY"] = "0"

    # Create parser
    parser = create_main_parser()

    # Walk parser tree
    commands, details = walk_parser(parser)

    return commands, details


def save_outputs(
    commands: Set[str],
    details: List[Dict],
    output_prefix: str,
) -> None:
    """
    Save extracted CLI surface to files.

    Args:
        commands: Set of command strings
        details: List of command detail dicts
        output_prefix: Output file prefix (e.g., "cli_surface.default")
    """
    reports_dir = MAESTRO_ROOT / "docs" / "workflows" / "v3" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Sort commands deterministically
    sorted_commands = sorted(commands)

    # Save text file (one command per line)
    txt_path = reports_dir / f"{output_prefix}.txt"
    with open(txt_path, "w") as f:
        for cmd in sorted_commands:
            f.write(f"{cmd}\n")

    # Save JSON file
    json_path = reports_dir / f"{output_prefix}.json"
    sorted_details = sorted(details, key=lambda x: x["command"])
    with open(json_path, "w") as f:
        json.dump(
            {
                "commands": sorted_commands,
                "details": sorted_details,
                "count": len(sorted_commands),
            },
            f,
            indent=2,
        )

    print(f"Saved {len(sorted_commands)} commands to:")
    print(f"  - {txt_path}")
    print(f"  - {json_path}")


def main():
    """Main entry point."""
    print("Extracting CLI surface...")
    print("=" * 80)

    # Extract default CLI surface (legacy disabled)
    print("\n1. Default mode (MAESTRO_ENABLE_LEGACY=0)")
    commands_default, details_default = extract_cli_surface(enable_legacy=False)
    save_outputs(commands_default, details_default, "cli_surface.default")

    # Extract legacy CLI surface (legacy enabled)
    print("\n2. Legacy mode (MAESTRO_ENABLE_LEGACY=1)")
    commands_legacy, details_legacy = extract_cli_surface(enable_legacy=True)
    save_outputs(commands_legacy, details_legacy, "cli_surface.legacy")

    # Report diff
    print("\n" + "=" * 80)
    legacy_only = commands_legacy - commands_default
    print(f"\nLegacy-only commands ({len(legacy_only)}):")
    for cmd in sorted(legacy_only):
        print(f"  - {cmd}")

    print("\nCLI surface extraction complete!")


if __name__ == "__main__":
    main()
