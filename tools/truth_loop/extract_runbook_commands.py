#!/usr/bin/env python3
"""
Runbook command extractor for truth loop.

This module scans runbook example files and extracts actual maestro command usage.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add maestro to path
MAESTRO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MAESTRO_ROOT))

from tools.truth_loop.normalize import normalize_command


# Patterns to identify command lines in runbooks
COMMAND_PATTERNS = [
    # Direct execution patterns
    r"^\s*maestro\s+",  # Direct maestro call
    r"^\s*m\s+",  # Short alias
    r"^\s*\./maestro\.py\s+",  # Direct script call
    r"^\s*python3?\s+-?m?\s+maestro\s+",  # Python invocation

    # Wrapped execution patterns
    r"^\s*MAESTRO_BIN=\S+\s+maestro\s+",  # MAESTRO_BIN wrapper
    r"^\s*env\s+\w+=\S+\s+maestro\s+",  # env wrapper

    # Run function pattern (common in examples)
    r"^\s*run\s+maestro\s+",  # run maestro ...
    r"^\s*run\s+m\s+",  # run m ...

    # Variable expansion pattern
    r"^\s*\$\{?MAESTRO_BIN\}?\s+",  # ${MAESTRO_BIN} or $MAESTRO_BIN
]

# Patterns to IGNORE (these are not actual command executions)
IGNORE_PATTERNS = [
    r"^\s*#",  # Comments
    r"^\s*echo\s+[\"']maestro",  # Echo statements (documentation)
    r"^\s*echo\s+maestro",  # Echo without quotes
    r"^\s*printf\s+",  # Printf statements
    r"^\s*\|\s*maestro",  # Piped commands (maestro as receiver)
    r"maestro\s+directory",  # False positive: "maestro directory"
    r"maestro\s+files",  # False positive: "maestro files"
    r"maestro\s+package",  # False positive: "maestro package"
    r"maestro\s+import",  # False positive: "maestro import"
]


def should_ignore_line(line: str) -> bool:
    """
    Check if a line should be ignored during extraction.

    Args:
        line: Line to check

    Returns:
        True if line should be ignored
    """
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def is_command_line(line: str) -> bool:
    """
    Check if a line is a maestro command execution.

    Args:
        line: Line to check

    Returns:
        True if line is a command execution
    """
    if should_ignore_line(line):
        return False

    for pattern in COMMAND_PATTERNS:
        if re.search(pattern, line):
            return True

    return False


def extract_command_from_line(line: str) -> str:
    """
    Extract the command portion from a line.

    Args:
        line: Full line from runbook

    Returns:
        Extracted command string (or empty if not a command)
    """
    if not is_command_line(line):
        return ""

    # Strip leading/trailing whitespace
    line = line.strip()

    # Remove trailing comments
    if "#" in line:
        # Be careful not to remove # from quoted strings
        # For simplicity, just remove everything after unquoted #
        parts = line.split("#")
        if len(parts) > 1:
            # Check if # is in quotes
            in_quotes = False
            for i, char in enumerate(line):
                if char in ("'", '"'):
                    in_quotes = not in_quotes
                elif char == "#" and not in_quotes:
                    line = line[:i]
                    break

    line = line.strip()

    # Remove trailing backslash continuation
    if line.endswith("\\"):
        line = line[:-1].strip()

    return line


def scan_runbook_file(file_path: Path) -> List[str]:
    """
    Scan a single runbook file and extract commands.

    Args:
        file_path: Path to runbook file

    Returns:
        List of raw command lines
    """
    commands = []

    try:
        with open(file_path, "r") as f:
            for line_no, line in enumerate(f, 1):
                cmd = extract_command_from_line(line)
                if cmd:
                    commands.append(cmd)

    except Exception as e:
        print(f"Warning: Failed to read {file_path}: {e}", file=sys.stderr)

    return commands


def scan_runbook_directories() -> Tuple[List[str], Dict[str, int]]:
    """
    Scan all runbook directories and extract commands.

    Returns:
        Tuple of (raw commands list, file counts dict)
    """
    runbooks_base = MAESTRO_ROOT / "docs" / "workflows" / "v3" / "runbooks" / "examples"

    # Scan directories
    scan_dirs = [
        runbooks_base / "input_from_v2_proposed",
        runbooks_base / "proposed",
    ]

    all_commands = []
    file_counts = {}

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            print(f"Warning: Directory not found: {scan_dir}", file=sys.stderr)
            continue

        # Find all .sh files
        sh_files = list(scan_dir.glob("**/*.sh"))
        print(f"Scanning {len(sh_files)} files in {scan_dir.relative_to(MAESTRO_ROOT)}...")

        dir_count = 0
        for sh_file in sorted(sh_files):
            commands = scan_runbook_file(sh_file)
            all_commands.extend(commands)
            dir_count += len(commands)

        file_counts[str(scan_dir.relative_to(MAESTRO_ROOT))] = dir_count

    return all_commands, file_counts


def save_outputs(
    raw_commands: List[str],
    normalized_commands: List[str],
    frequency: Counter,
) -> None:
    """
    Save extracted runbook commands to files.

    Args:
        raw_commands: List of raw command strings
        normalized_commands: List of normalized command strings
        frequency: Counter of command frequencies
    """
    reports_dir = MAESTRO_ROOT / "docs" / "workflows" / "v3" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Save raw commands
    raw_path = reports_dir / "runbook_commands.raw.txt"
    with open(raw_path, "w") as f:
        for cmd in raw_commands:
            f.write(f"{cmd}\n")

    # Save normalized commands (sorted, unique)
    normalized_path = reports_dir / "runbook_commands.normalized.txt"
    unique_normalized = sorted(set(normalized_commands))
    with open(normalized_path, "w") as f:
        for cmd in unique_normalized:
            f.write(f"{cmd}\n")

    # Save frequency CSV
    freq_path = reports_dir / "runbook_commands.freq.csv"
    with open(freq_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["command", "count"])
        for cmd, count in frequency.most_common():
            writer.writerow([cmd, count])

    print(f"\nSaved outputs:")
    print(f"  - {raw_path} ({len(raw_commands)} commands)")
    print(f"  - {normalized_path} ({len(unique_normalized)} unique)")
    print(f"  - {freq_path} (frequency analysis)")


def main():
    """Main entry point."""
    print("Extracting runbook commands...")
    print("=" * 80)

    # Scan runbook directories
    raw_commands, file_counts = scan_runbook_directories()

    print(f"\nExtracted {len(raw_commands)} command references:")
    for dir_name, count in file_counts.items():
        print(f"  - {dir_name}: {count} commands")

    # Normalize commands
    print("\nNormalizing commands...")
    normalized_commands = []
    frequency = Counter()

    for raw_cmd in raw_commands:
        try:
            normalized, tokens, signature = normalize_command(raw_cmd)
            normalized_commands.append(normalized)
            frequency[normalized] += 1
        except Exception as e:
            print(f"Warning: Failed to normalize '{raw_cmd}': {e}", file=sys.stderr)

    # Save outputs
    save_outputs(raw_commands, normalized_commands, frequency)

    # Print top commands
    print(f"\nTop 10 most frequent commands:")
    for cmd, count in frequency.most_common(10):
        print(f"  {count:3d}x  {cmd}")

    print("\nRunbook command extraction complete!")


if __name__ == "__main__":
    main()
