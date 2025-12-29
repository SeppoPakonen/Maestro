#!/usr/bin/env python3
"""
Command normalization for truth loop.

This module provides canonical normalization of Maestro commands from various forms
(shell scripts, CLI surface, etc.) into a standard format for comparison.
"""

from typing import List, Tuple, Optional
import re


# Alias mapping for canonical verbs
CANONICAL_VERB_ALIASES = {
    # Build alias
    "build": "make",
    "compile": "make",
    "b": "make",

    # List aliases
    "ls": "list",
    "l": "list",

    # Show aliases
    "sh": "show",
    "s": "show",

    # Remove aliases
    "rm": "remove",
    "delete": "remove",
    "del": "remove",

    # Add aliases
    "a": "add",
    "new": "add",  # convert new → convert add
    "create": "add",

    # Edit aliases
    "e": "edit",
    "update": "edit",

    # Legacy command aliases
    "session": "wsession",
    "understand": "repo resolve",  # Note: multi-word replacement
    "resume": None,  # Context-dependent: "discuss resume" or "work resume"
    "rules": "solutions",
    "root": None,  # Context-dependent: track/phase/task
}


# Command wrappers to strip
COMMAND_WRAPPERS = [
    r"^\s*run\s+",  # run function (common in runbook examples)
    r"^\s*MAESTRO_BIN=\S+\s+",  # MAESTRO_BIN=... wrapper
    r"^\s*env\s+\w+=\S+\s+",  # env VAR=... wrapper
    r"^\s*\./maestro\.py\s+",  # ./maestro.py
    r"^\s*python3?\s+-?m?\s+maestro\s+",  # python -m maestro or python maestro
    r"^\s*maestro\s+",  # maestro
    r"^\s*m\s+",  # m (short alias)
]


# Special normalization rules for specific commands
SPECIAL_NORMALIZATIONS = {
    # Old flag-based patterns → new keyword-based patterns
    r"repo\s+resolve\s+--level\s+deep": "repo refresh all",
    r"repo\s+resolve\s+--level\s+lite": "repo resolve lite",
    r"discuss\s+--resume\s+(\S+)": r"discuss resume \1",
    r"discuss\s+--context\s+(\S+)": r"discuss \1",
}


def strip_wrappers(command_line: str) -> str:
    """
    Strip command wrappers from a command line.

    Args:
        command_line: Raw command line (e.g., "MAESTRO_BIN=maestro maestro repo resolve")

    Returns:
        Command line with wrappers stripped (e.g., "repo resolve")
    """
    result = command_line
    for pattern in COMMAND_WRAPPERS:
        result = re.sub(pattern, "", result)
    return result.strip()


def apply_special_normalizations(command: str) -> str:
    """
    Apply special normalization rules for specific command patterns.

    Args:
        command: Command string after wrapper stripping

    Returns:
        Normalized command
    """
    result = command
    for pattern, replacement in SPECIAL_NORMALIZATIONS.items():
        result = re.sub(pattern, replacement, result)
    return result


def normalize_verbs(tokens: List[str]) -> List[str]:
    """
    Normalize verbs using canonical verb aliases.

    Args:
        tokens: Command tokens (e.g., ["repo", "ls"])

    Returns:
        Tokens with verbs normalized (e.g., ["repo", "list"])
    """
    result = []
    for i, token in enumerate(tokens):
        # Check if token is in alias map
        if token in CANONICAL_VERB_ALIASES:
            replacement = CANONICAL_VERB_ALIASES[token]
            if replacement is None:
                # Context-dependent alias, keep as-is for now
                result.append(token)
            elif " " in replacement:
                # Multi-word replacement (e.g., "understand" → "repo resolve")
                result.extend(replacement.split())
            else:
                result.append(replacement)
        else:
            result.append(token)

    return result


def extract_signature(tokens: List[str]) -> str:
    """
    Extract a signature from tokens by replacing flag values with placeholders.

    Args:
        tokens: Command tokens

    Returns:
        Signature string (e.g., "repo resolve --reason <ARG>")
    """
    signature_tokens = []
    skip_next = False

    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue

        if token.startswith("--"):
            # Long flag
            if "=" in token:
                # --flag=value → --flag <ARG>
                flag_name = token.split("=")[0]
                signature_tokens.append(f"{flag_name} <ARG>")
            else:
                # --flag value → --flag <ARG>
                signature_tokens.append(token)
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    signature_tokens.append("<ARG>")
                    skip_next = True
        elif token.startswith("-") and not token.startswith("--"):
            # Short flag
            signature_tokens.append(token)
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                signature_tokens.append("<ARG>")
                skip_next = True
        else:
            # Regular token
            signature_tokens.append(token)

    return " ".join(signature_tokens)


def normalize_command(command_line: str) -> Tuple[str, List[str], str]:
    """
    Normalize a command line into canonical form.

    Args:
        command_line: Raw command line from runbook or other source

    Returns:
        Tuple of:
        - normalized: Normalized command string (e.g., "repo list")
        - tokens: Full token list with flags (e.g., ["repo", "list", "--archived"])
        - signature: Signature with flag values abstracted (e.g., "repo list --archived")
    """
    # Strip wrappers
    stripped = strip_wrappers(command_line)

    # Apply special normalizations
    normalized_str = apply_special_normalizations(stripped)

    # Tokenize
    tokens = normalized_str.split()

    # Normalize verbs
    tokens = normalize_verbs(tokens)

    # Extract base command (no flags)
    base_tokens = [t for t in tokens if not t.startswith("-")]
    normalized = " ".join(base_tokens)

    # Extract signature (flags with placeholders)
    signature = extract_signature(tokens)

    return normalized, tokens, signature


def get_report_categories() -> List[str]:
    """
    Get the list of report categories for truth loop analysis.

    Returns:
        List of category names
    """
    return [
        "both_ok",           # In both runbooks and CLI surface
        "runbook_only",      # In runbooks but not in CLI surface
        "cli_only",          # In CLI surface but not in runbooks
        "needs_alias",       # Used in runbooks via alias mapping
        "needs_docs",        # CLI exists but no runbook examples
        "needs_runbook_fix", # Runbooks reference TODO_CMD or deprecated forms
    ]


# Test cases for normalization
if __name__ == "__main__":
    test_cases = [
        "MAESTRO_BIN=maestro maestro repo resolve",
        "./maestro.py repo resolve --level deep",
        "python -m maestro discuss --resume SESSION-123",
        "maestro build default",
        "m repo ls",
        "maestro runbook archive RB-001 --reason 'test'",
        "maestro convert new pipeline-name",
        "env FOO=bar maestro task sh TASK-01",
    ]

    print("Normalization test cases:")
    print("=" * 80)
    for test in test_cases:
        normalized, tokens, signature = normalize_command(test)
        print(f"\nInput:      {test}")
        print(f"Normalized: {normalized}")
        print(f"Tokens:     {tokens}")
        print(f"Signature:  {signature}")
