#!/usr/bin/env python3
"""
CLI Surface Audit Tool

This tool audits the actual CLI command surface (from code parser structure)
against the canonical runbook-extracted command list.

Generates: docs/workflows/v3/reports/cli_surface_audit.md
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Set, Dict, List, Tuple
import importlib.util


def load_maestro_parser():
    """Load the Maestro CLI parser by importing the module."""
    # Add project root to sys.path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    try:
        from maestro.modules.cli_parser import create_main_parser
        return create_main_parser()
    except ImportError as e:
        print(f"ERROR: Failed to import Maestro CLI parser: {e}")
        sys.exit(1)


def extract_commands_from_parser(parser: argparse.ArgumentParser) -> Set[str]:
    """
    Extract all CLI commands and subcommands from the argparse parser.
    Returns normalized commands in the format: "maestro <command> <subcommand> ..."
    """
    commands = set()

    # Get subparsers from the main parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # Iterate through all registered subcommands
            for name, subparser in action.choices.items():
                # Add the main command
                commands.add(f"maestro {name}")

                # Check if this subparser has its own subparsers
                for subaction in subparser._actions:
                    if isinstance(subaction, argparse._SubParsersAction):
                        for subname, _ in subaction.choices.items():
                            commands.add(f"maestro {name} {subname}")

    return commands


def load_allowed_commands(allowed_file: Path) -> Set[str]:
    """Load allowed commands from the canonical runbook-extracted list."""
    if not allowed_file.exists():
        print(f"ERROR: Allowed commands file not found: {allowed_file}")
        sys.exit(1)

    commands = set()
    with open(allowed_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                commands.add(line)

    return commands


def normalize_command_pattern(command: str) -> str:
    """
    Normalize command to a comparable pattern.
    Extracts the first 2-3 tokens (maestro + command + optional subcommand).
    """
    tokens = command.split()
    if len(tokens) >= 3:
        return ' '.join(tokens[:3])
    elif len(tokens) >= 2:
        return ' '.join(tokens[:2])
    return command


def categorize_commands(
    code_commands: Set[str],
    allowed_commands: Set[str]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Categorize commands into three groups:
    1. In both code and runbooks (✅)
    2. In code but NOT in runbooks (⚠️)
    3. In runbooks but NOT in code (❌)
    """
    # Normalize both sets for comparison
    code_patterns = {normalize_command_pattern(cmd) for cmd in code_commands}
    allowed_patterns = {normalize_command_pattern(cmd) for cmd in allowed_commands}

    in_both = sorted(code_patterns & allowed_patterns)
    in_code_only = sorted(code_patterns - allowed_patterns)
    in_runbooks_only = sorted(allowed_patterns - code_patterns)

    return in_both, in_code_only, in_runbooks_only


def generate_report(
    in_both: List[str],
    in_code_only: List[str],
    in_runbooks_only: List[str],
    output_file: Path
):
    """Generate the markdown audit report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(output_file, 'w') as f:
        f.write("# CLI Surface Audit Report\n\n")
        f.write(f"**Generated:** {timestamp}\n\n")
        f.write("**Purpose:** Compare actual CLI command surface (from code parser) ")
        f.write("against canonical runbook-extracted command list.\n\n")
        f.write("**Policy:** [Test Command Truth Policy](test_command_truth_policy.md)\n\n")
        f.write("**Canonical Commands:** `allowed_commands.normalized.txt`\n\n")
        f.write("---\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- ✅ In both code and runbooks: {len(in_both)} commands\n")
        f.write(f"- ⚠️  In code but NOT in runbooks: {len(in_code_only)} commands\n")
        f.write(f"- ❌ In runbooks but NOT in code: {len(in_runbooks_only)} commands\n\n")
        f.write("---\n\n")

        # In both
        f.write("## ✅ In Both Code and Runbooks\n\n")
        f.write("These commands are properly aligned between implementation and documentation.\n\n")
        if in_both:
            f.write("```\n")
            for cmd in in_both:
                f.write(f"{cmd}\n")
            f.write("```\n\n")
        else:
            f.write("_None found._\n\n")

        f.write("---\n\n")

        # In code only (WARNING)
        f.write("## ⚠️ In Code But NOT in Runbooks\n\n")
        f.write("**These commands exist in the code but are NOT documented in runbooks.**\n\n")
        f.write("**Possible reasons:**\n")
        f.write("1. Legacy commands that should be deprecated/removed\n")
        f.write("2. New commands that need runbook documentation\n")
        f.write("3. Aliases or internal commands not meant for users\n\n")
        f.write("**Action Required:**\n")
        f.write("- Review each command\n")
        f.write("- If legacy (e.g., `session`, `understand`, `resume`, `rules`), ")
        f.write("consider deprecation\n")
        f.write("- If new and valid, add to runbooks and re-extract allowed commands\n")
        f.write("- If internal/alias, document why it's not in runbooks\n\n")

        if in_code_only:
            f.write("```\n")
            for cmd in in_code_only:
                f.write(f"{cmd}\n")
            f.write("```\n\n")
        else:
            f.write("_None found._\n\n")

        f.write("---\n\n")

        # In runbooks only (ERROR)
        f.write("## ❌ In Runbooks But NOT in Code\n\n")
        f.write("**These commands are documented in runbooks but don't exist in code.**\n\n")
        f.write("**This indicates:**\n")
        f.write("1. Commands removed from code but not from documentation\n")
        f.write("2. Commands not yet implemented\n")
        f.write("3. Potential typos in runbook documentation\n\n")
        f.write("**Action Required:**\n")
        f.write("- If removed, update runbooks to remove these commands\n")
        f.write("- If planned, implement them or mark as TODO in runbooks\n")
        f.write("- If typos, fix runbook documentation\n\n")

        if in_runbooks_only:
            f.write("```\n")
            for cmd in in_runbooks_only:
                f.write(f"{cmd}\n")
            f.write("```\n\n")
        else:
            f.write("_None found._\n\n")

        f.write("---\n\n")

        # Next steps
        f.write("## Next Steps\n\n")
        f.write("1. Review \"In code but NOT in runbooks\" section\n")
        f.write("2. Document deprecation status for legacy commands ")
        f.write("(see `docs/workflows/v3/cli/DEPRECATION.md`)\n")
        f.write("3. Update runbooks or code to align the command surface\n")
        f.write("4. Re-run this audit after changes\n\n")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    allowed_file = project_root / "docs/workflows/v3/reports/allowed_commands.normalized.txt"
    output_file = project_root / "docs/workflows/v3/reports/cli_surface_audit.md"

    print("=== CLI Surface Audit ===")
    print(f"Canonical commands: {allowed_file}")
    print(f"Output report: {output_file}")
    print()

    # Load the parser and extract commands
    print("Loading Maestro CLI parser...")
    parser = load_maestro_parser()
    code_commands = extract_commands_from_parser(parser)
    print(f"Extracted {len(code_commands)} commands from code parser")

    # Load allowed commands
    print("Loading allowed commands from runbooks...")
    allowed_commands = load_allowed_commands(allowed_file)
    print(f"Loaded {len(allowed_commands)} allowed commands")
    print()

    # Categorize commands
    print("Categorizing commands...")
    in_both, in_code_only, in_runbooks_only = categorize_commands(
        code_commands, allowed_commands
    )

    print(f"✅ In both: {len(in_both)}")
    print(f"⚠️  In code only: {len(in_code_only)}")
    print(f"❌ In runbooks only: {len(in_runbooks_only)}")
    print()

    # Generate report
    print("Generating report...")
    generate_report(in_both, in_code_only, in_runbooks_only, output_file)

    print()
    print("✅ Audit complete!")
    print(f"Report: {output_file}")
    print()

    # Print warnings if there are discrepancies
    if in_code_only:
        print("⚠️  WARNING: Commands exist in code but not in runbooks:")
        for cmd in in_code_only[:10]:  # Show first 10
            print(f"   - {cmd}")
        if len(in_code_only) > 10:
            print(f"   ... and {len(in_code_only) - 10} more")
        print()

    if in_runbooks_only:
        print("❌ ERROR: Commands in runbooks but not in code:")
        for cmd in in_runbooks_only[:10]:  # Show first 10
            print(f"   - {cmd}")
        if len(in_runbooks_only) > 10:
            print(f"   ... and {len(in_runbooks_only) - 10} more")
        print()


if __name__ == "__main__":
    main()
