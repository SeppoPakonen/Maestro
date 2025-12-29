#!/usr/bin/env python3
"""
Truth loop comparator - diff runbook commands vs CLI surface.

This module compares commands found in runbooks against the actual CLI surface,
identifying gaps, deprecated usage, and alignment opportunities.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add maestro to path
MAESTRO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MAESTRO_ROOT))


# Legacy command mapping from LEGACY_MAPPING.md
LEGACY_MAPPING = {
    "build": "make",
    "compile": "make",
    "understand": "repo resolve",
    "rules": "solutions",
    "resume": "work resume OR discuss resume",
    "session": "wsession",
    "root": "track OR phase OR task",
}


def load_runbook_commands(reports_dir: Path) -> Set[str]:
    """
    Load normalized runbook commands from file.

    Args:
        reports_dir: Reports directory path

    Returns:
        Set of normalized command strings
    """
    runbook_file = reports_dir / "runbook_commands.normalized.txt"

    if not runbook_file.exists():
        print(f"Error: {runbook_file} not found. Run extract_runbook_commands.py first.", file=sys.stderr)
        sys.exit(1)

    commands = set()
    with open(runbook_file, "r") as f:
        for line in f:
            line = line.strip()
            # Filter out lines with shell artifacts
            if line and not any(x in line for x in ["|", ">", "<", "${", "||", "&&"]):
                # Extract base command (first 2-3 tokens)
                tokens = line.split()
                if len(tokens) >= 2:
                    base_cmd = " ".join(tokens[:min(3, len(tokens))])
                    commands.add(base_cmd)
                elif len(tokens) == 1:
                    commands.add(tokens[0])

    return commands


def load_cli_surface(reports_dir: Path, mode: str = "default") -> Set[str]:
    """
    Load CLI surface commands from file.

    Args:
        reports_dir: Reports directory path
        mode: "default" or "legacy"

    Returns:
        Set of CLI command strings
    """
    cli_file = reports_dir / f"cli_surface.{mode}.txt"

    if not cli_file.exists():
        print(f"Error: {cli_file} not found. Run extract_cli_surface.py first.", file=sys.stderr)
        sys.exit(1)

    commands = set()
    with open(cli_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                commands.add(line)

    return commands


def categorize_commands(
    runbook_cmds: Set[str],
    cli_cmds: Set[str],
) -> Dict[str, Set[str]]:
    """
    Categorize commands into truth loop categories.

    Args:
        runbook_cmds: Commands from runbooks
        cli_cmds: Commands from CLI surface

    Returns:
        Dict of category name -> set of commands
    """
    categories = {
        "both_ok": set(),
        "runbook_only": set(),
        "cli_only": set(),
        "needs_alias": set(),
        "needs_docs": set(),
        "needs_runbook_fix": set(),
    }

    # Check each runbook command
    for rb_cmd in runbook_cmds:
        if rb_cmd in cli_cmds:
            # Perfect match - both ok
            categories["both_ok"].add(rb_cmd)
        else:
            # Not in CLI - check if it's a legacy/deprecated form
            first_word = rb_cmd.split()[0] if rb_cmd else ""
            if first_word in LEGACY_MAPPING:
                categories["needs_runbook_fix"].add(rb_cmd)
                categories["needs_alias"].add(rb_cmd)
            else:
                # Runbook uses it but CLI doesn't have it
                categories["runbook_only"].add(rb_cmd)

    # Check CLI-only commands (no runbook examples)
    for cli_cmd in cli_cmds:
        if cli_cmd not in runbook_cmds:
            # CLI has it but no runbook examples
            categories["cli_only"].add(cli_cmd)
            # These might need docs
            first_word = cli_cmd.split()[0] if cli_cmd else ""
            # Filter out some internal/utility commands
            if first_word not in ("b", "plan", "ops"):
                categories["needs_docs"].add(cli_cmd)

    return categories


def generate_markdown_report(
    categories: Dict[str, Set[str]],
    output_path: Path,
) -> None:
    """
    Generate markdown truth loop diff report.

    Args:
        categories: Categorized commands
        output_path: Output file path
    """
    with open(output_path, "w") as f:
        f.write("# Truth Loop Diff Report\n\n")
        f.write("Comparison of runbook command usage vs CLI surface.\n\n")
        f.write("**Generated:** Run `python tools/truth_loop/compare.py` to regenerate.\n\n")
        f.write("---\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- ✅ **Both OK**: {len(categories['both_ok'])} commands aligned\n")
        f.write(f"- ⚠️ **Runbook Only**: {len(categories['runbook_only'])} commands in runbooks but not CLI\n")
        f.write(f"- 📖 **CLI Only**: {len(categories['cli_only'])} commands in CLI but no runbook examples\n")
        f.write(f"- 🔄 **Needs Alias**: {len(categories['needs_alias'])} commands using legacy forms\n")
        f.write(f"- 📝 **Needs Docs**: {len(categories['needs_docs'])} commands missing runbook examples\n")
        f.write(f"- 🔧 **Needs Runbook Fix**: {len(categories['needs_runbook_fix'])} deprecated command usage\n\n")

        f.write("---\n\n")

        # Runbook-only commands
        f.write("## ⚠️ Runbook-Only Commands\n\n")
        f.write("Commands found in runbooks but not in CLI surface (default mode).\n\n")
        if categories["runbook_only"]:
            f.write("```\n")
            for cmd in sorted(categories["runbook_only"]):
                f.write(f"{cmd}\n")
            f.write("```\n\n")
        else:
            f.write("*None*\n\n")

        f.write("**Action:** Verify these commands exist in CLI or update runbooks.\n\n")
        f.write("---\n\n")

        # CLI-only commands (needs docs)
        f.write("## 📖 CLI-Only Commands (Need Examples)\n\n")
        f.write("Commands in CLI surface but missing runbook examples.\n\n")
        if categories["needs_docs"]:
            # Group by namespace
            by_namespace = defaultdict(list)
            for cmd in sorted(categories["needs_docs"]):
                namespace = cmd.split()[0] if cmd else "other"
                by_namespace[namespace].append(cmd)

            for namespace in sorted(by_namespace.keys()):
                f.write(f"### `{namespace}` namespace\n\n")
                f.write("```\n")
                for cmd in by_namespace[namespace]:
                    f.write(f"{cmd}\n")
                f.write("```\n\n")
        else:
            f.write("*None*\n\n")

        f.write("**Action:** Create runbook examples for these commands.\n\n")
        f.write("---\n\n")

        # Alias coverage
        f.write("## 🔄 Alias Coverage\n\n")
        f.write("Commands using legacy forms that need alias mapping verification.\n\n")
        if categories["needs_alias"]:
            f.write("| Runbook Command | Canonical Replacement |\n")
            f.write("|-----------------|----------------------|\n")
            for cmd in sorted(categories["needs_alias"]):
                first_word = cmd.split()[0]
                replacement = LEGACY_MAPPING.get(first_word, "?")
                f.write(f"| `{cmd}` | `{replacement}` |\n")
            f.write("\n")
        else:
            f.write("*None*\n\n")

        f.write("**Action:** Verify aliases exist and update runbooks to use canonical forms.\n\n")
        f.write("---\n\n")

        # Debt table
        f.write("## 🔧 Debt Table (Deprecated Usage)\n\n")
        f.write("Runbook commands using deprecated forms.\n\n")
        if categories["needs_runbook_fix"]:
            f.write("```\n")
            for cmd in sorted(categories["needs_runbook_fix"]):
                first_word = cmd.split()[0]
                replacement = LEGACY_MAPPING.get(first_word, "?")
                f.write(f"{cmd:<40} → {replacement}\n")
            f.write("```\n\n")
        else:
            f.write("*None*\n\n")

        f.write("**Action:** Update runbooks to use canonical command forms.\n\n")
        f.write("---\n\n")

        # Aligned commands (both ok) - summary only
        f.write("## ✅ Aligned Commands\n\n")
        f.write(f"{len(categories['both_ok'])} commands are properly aligned between runbooks and CLI.\n\n")
        f.write("</details>\n\n")


def generate_json_report(
    categories: Dict[str, Set[str]],
    output_path: Path,
) -> None:
    """
    Generate JSON truth loop diff report.

    Args:
        categories: Categorized commands
        output_path: Output file path
    """
    # Convert sets to sorted lists for JSON
    json_data = {
        key: sorted(values)
        for key, values in categories.items()
    }

    with open(output_path, "w") as f:
        json.dump(json_data, f, indent=2)


def main():
    """Main entry point."""
    print("Comparing runbook commands vs CLI surface...")
    print("=" * 80)

    reports_dir = MAESTRO_ROOT / "docs" / "workflows" / "v3" / "reports"

    # Load inputs
    print("\n1. Loading runbook commands...")
    runbook_cmds = load_runbook_commands(reports_dir)
    print(f"   Found {len(runbook_cmds)} unique commands in runbooks")

    print("\n2. Loading CLI surface (default mode)...")
    cli_cmds = load_cli_surface(reports_dir, mode="default")
    print(f"   Found {len(cli_cmds)} commands in CLI surface")

    # Categorize
    print("\n3. Categorizing commands...")
    categories = categorize_commands(runbook_cmds, cli_cmds)

    # Generate reports
    print("\n4. Generating reports...")
    md_output = reports_dir / "truth_loop_diff.md"
    json_output = reports_dir / "truth_loop_diff.json"

    generate_markdown_report(categories, md_output)
    generate_json_report(categories, json_output)

    print(f"   - {md_output}")
    print(f"   - {json_output}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  ✅ Both OK:            {len(categories['both_ok'])}")
    print(f"  ⚠️  Runbook Only:       {len(categories['runbook_only'])}")
    print(f"  📖 CLI Only:           {len(categories['cli_only'])}")
    print(f"  🔄 Needs Alias:        {len(categories['needs_alias'])}")
    print(f"  📝 Needs Docs:         {len(categories['needs_docs'])}")
    print(f"  🔧 Needs Runbook Fix:  {len(categories['needs_runbook_fix'])}")

    print("\nTruth loop comparison complete!")


if __name__ == "__main__":
    main()
