"""
Fingerprint generation for log findings.

Provides stable, deterministic fingerprints for error messages to enable
deduplication across scans.
"""

import hashlib
import re
from pathlib import Path
from typing import Optional


def normalize_message(message: str, remove_line_numbers: bool = False) -> str:
    """
    Normalize error message for fingerprinting.

    Args:
        message: Raw error message
        remove_line_numbers: If True, collapse line-specific numbers

    Returns:
        Normalized message with stable components
    """
    normalized = message

    # Remove timestamps (common patterns)
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)
    normalized = re.sub(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)

    # Remove PIDs and thread IDs
    normalized = re.sub(r'\bPID\s*[:=]?\s*\d+\b', 'PID:<PID>', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bTID\s*[:=]?\s*\d+\b', 'TID:<TID>', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\[pid\s*\d+\]', '[pid <PID>]', normalized, flags=re.IGNORECASE)

    # Convert absolute paths to relative (common repo patterns)
    # Match paths like /home/user/project/src/foo.cpp or C:\Users\user\project\src\foo.cpp
    normalized = re.sub(
        r'(?:^|[\s\'"])([/\\](?:home|Users|root|opt|var|c:|C:)[^\s:]+[/\\])',
        r'<REPO>/',
        normalized
    )

    # Simplify common path separators
    normalized = normalized.replace('\\\\', '/')
    normalized = normalized.replace('\\', '/')

    # Remove line-specific numbers if requested (for very noisy error messages)
    if remove_line_numbers:
        # Preserve file:line references but normalize the line number
        normalized = re.sub(r':\d+:', ':<LINE>:', normalized)
        normalized = re.sub(r'line\s+\d+', 'line <LINE>', normalized, flags=re.IGNORECASE)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()

    return normalized


def generate_fingerprint(
    message: str,
    tool: Optional[str] = None,
    file: Optional[str] = None,
    remove_line_numbers: bool = False
) -> str:
    """
    Generate stable fingerprint for a finding.

    Args:
        message: Error message
        tool: Tool that generated the finding (gcc, clang, pytest, etc.)
        file: File path where error occurred
        remove_line_numbers: If True, normalize line numbers for very noisy messages

    Returns:
        SHA256 fingerprint hex string
    """
    # Normalize the message
    norm_message = normalize_message(message, remove_line_numbers)

    # Build fingerprint components
    components = [norm_message]

    if tool:
        components.append(f"tool:{tool.lower().strip()}")

    if file:
        # Use only the basename to avoid path sensitivity
        file_basename = Path(file).name
        components.append(f"file:{file_basename}")

    # Join components and hash
    fingerprint_text = " | ".join(components)
    fingerprint = hashlib.sha256(fingerprint_text.encode('utf-8')).hexdigest()

    return fingerprint


def extract_file_line(message: str) -> tuple[Optional[str], Optional[int]]:
    """
    Extract file path and line number from error message.

    Args:
        message: Error message that may contain file:line references

    Returns:
        Tuple of (file_path, line_number) or (None, None) if not found
    """
    # Common patterns: file.cpp:42, file.py:100:5, /path/to/file.c:42:1
    patterns = [
        r'([^\s:]+\.(?:cpp|c|h|hpp|py|js|ts|go|rs|java)):(\d+)',
        r'([^\s:]+):(\d+):\d+',
        r'"([^"]+)"\s*,\s*line\s+(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            file_path = match.group(1)
            line_number = int(match.group(2))
            return file_path, line_number

    return None, None
