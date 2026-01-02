"""Error logging module for recording invalid commands."""

import json
import os
from datetime import datetime, timezone
import sys


def write_error_record(state_dir: str, cookie: str, argv: list[str], cwd: str,
                       stdin_text: str, version: str, redaction_rules=None) -> str:
    """
    Write an error record to disk in JSON format.

    Args:
        state_dir: Base state directory
        cookie: Error cookie ID
        argv: Command line arguments (excluding program name)
        cwd: Current working directory
        stdin_text: Text from stdin
        version: Blindfold version
        redaction_rules: List of (pattern, replace) tuples for redaction

    Returns:
        str: Full path to the created JSON file
    """
    from .redaction import redact_text

    # Create errors directory if it doesn't exist
    errors_dir = os.path.join(state_dir, "errors")
    os.makedirs(errors_dir, exist_ok=True)

    # Prepare stdin snippet (first 8192 chars)
    max_snippet_len = 8192
    if len(stdin_text) > max_snippet_len:
        stdin_snippet = stdin_text[:max_snippet_len]
        stdin_truncated = True
    else:
        stdin_snippet = stdin_text
        stdin_truncated = False

    # Apply redaction to stdin snippet if rules are provided
    if redaction_rules:
        stdin_snippet = redact_text(stdin_snippet, redaction_rules)

    # Create error record
    error_record = {
        "cookie": cookie,
        "argv": argv,
        "cwd": cwd,
        "stdin_snippet": stdin_snippet,
        "stdin_truncated": stdin_truncated,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "blindfold_version": version,
        "python_version": sys.version
    }

    # Write to JSON file
    error_file_path = os.path.join(errors_dir, f"{cookie}.json")
    with open(error_file_path, "w", encoding="utf-8") as f:
        json.dump(error_record, f, ensure_ascii=False, indent=2)

    return error_file_path