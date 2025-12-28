"""
Log scanner for extracting findings from build/run output.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from .fingerprint import generate_fingerprint, extract_file_line


class Finding:
    """Represents a single finding from log analysis."""

    def __init__(
        self,
        kind: str,
        severity: str,
        message: str,
        fingerprint: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        tool: Optional[str] = None,
        raw_line: Optional[str] = None,
    ):
        self.kind = kind
        self.severity = severity
        self.message = message
        self.fingerprint = fingerprint
        self.file = file
        self.line = line
        self.tool = tool
        self.raw_line = raw_line

    def to_dict(self) -> dict:
        """Convert finding to dictionary for JSON serialization."""
        return {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
            "fingerprint": self.fingerprint,
            "file": self.file,
            "line": self.line,
            "tool": self.tool,
            "raw_line": self.raw_line,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Finding":
        """Create Finding from dictionary."""
        return cls(
            kind=data["kind"],
            severity=data["severity"],
            message=data["message"],
            fingerprint=data["fingerprint"],
            file=data.get("file"),
            line=data.get("line"),
            tool=data.get("tool"),
            raw_line=data.get("raw_line"),
        )


def extract_findings(log_text: str, kind_filter: Optional[str] = None) -> List[Finding]:
    """
    Extract findings from log text.

    Args:
        log_text: Raw log text
        kind_filter: Optional filter for finding kind (build, run, any)

    Returns:
        List of findings extracted from the log
    """
    findings = []

    # Error patterns (GCC/Clang style)
    error_patterns = [
        (r'error:', 'error', 'blocker'),
        (r'fatal error:', 'error', 'blocker'),
        (r'undefined reference', 'error', 'blocker'),
        (r'cannot find', 'error', 'blocker'),
        (r'No such file', 'error', 'blocker'),
    ]

    # Warning patterns
    warning_patterns = [
        (r'warning:', 'warning', 'warning'),
        (r'note:', 'info', 'info'),
    ]

    # Crash patterns
    crash_patterns = [
        (r'Segmentation fault', 'crash', 'critical'),
        (r'segfault', 'crash', 'critical'),
        (r'SIGSEGV', 'crash', 'critical'),
        (r'core dumped', 'crash', 'critical'),
        (r'Assertion.*failed', 'crash', 'critical'),
    ]

    all_patterns = error_patterns + warning_patterns + crash_patterns

    for line in log_text.splitlines():
        line_strip = line.strip()
        if not line_strip:
            continue

        for pattern, kind, severity in all_patterns:
            if re.search(pattern, line_strip, re.IGNORECASE):
                # Apply kind filter if specified
                if kind_filter and kind_filter != 'any':
                    if kind_filter == 'build' and kind not in ['error', 'warning']:
                        continue
                    if kind_filter == 'run' and kind != 'crash':
                        continue

                # Detect tool from common patterns
                tool = detect_tool(line_strip)

                # Extract file and line number
                file, line_num = extract_file_line(line_strip)

                # Generate fingerprint
                fingerprint = generate_fingerprint(
                    message=line_strip,
                    tool=tool,
                    file=file,
                )

                finding = Finding(
                    kind=kind,
                    severity=severity,
                    message=line_strip,
                    fingerprint=fingerprint,
                    file=file,
                    line=line_num,
                    tool=tool,
                    raw_line=line,
                )
                findings.append(finding)
                break  # Only match first pattern per line

    return findings


def detect_tool(line: str) -> Optional[str]:
    """
    Detect the tool that generated the message.

    Args:
        line: Log line

    Returns:
        Tool name or None
    """
    # Common tool patterns
    tools = [
        ('gcc', r'\bgcc\b'),
        ('g++', r'\bg\+\+\b'),
        ('clang', r'\bclang\b'),
        ('clang++', r'\bclang\+\+\b'),
        ('ld', r'\bld\b'),
        ('pytest', r'\bpytest\b'),
        ('mypy', r'\bmypy\b'),
        ('pylint', r'\bpylint\b'),
        ('rustc', r'\brustc\b'),
        ('cargo', r'\bcargo\b'),
        ('javac', r'\bjavac\b'),
        ('msbuild', r'\bmsbuild\b'),
        ('make', r'\bmake\b'),
    ]

    for tool_name, pattern in tools:
        if re.search(pattern, line, re.IGNORECASE):
            return tool_name

    return None


def create_scan(
    source_path: Optional[str],
    log_text: Optional[str],
    kind: str = 'any',
    repo_root: Optional[str] = None,
    command_context: Optional[str] = None,
) -> str:
    """
    Create a new log scan.

    Args:
        source_path: Path to log file (if reading from file)
        log_text: Log text (if reading from string)
        kind: Scan kind (build, run, any)
        repo_root: Repository root (defaults to cwd)
        command_context: Command that generated the log

    Returns:
        Scan ID

    Raises:
        ValueError: If neither source_path nor log_text provided
    """
    if not source_path and not log_text:
        raise ValueError("Either source_path or log_text must be provided")

    if not repo_root:
        repo_root = os.getcwd()

    # Read log text from file if needed
    if source_path and not log_text:
        with open(source_path, 'r', encoding='utf-8', errors='replace') as f:
            log_text = f.read()

    # Generate scan ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_id = f"{timestamp}_{kind}"

    # Create scan directory
    scan_dir = get_scan_path(scan_id, repo_root)
    os.makedirs(scan_dir, exist_ok=True)

    # Extract findings
    findings = extract_findings(log_text, kind_filter=kind)

    # Create metadata
    meta = {
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat(),
        "source_path": str(source_path) if source_path else None,
        "kind": kind,
        "cwd": os.getcwd(),
        "command_context": command_context,
        "finding_count": len(findings),
    }

    # Write files
    meta_path = os.path.join(scan_dir, "meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    raw_path = os.path.join(scan_dir, "raw.txt")
    with open(raw_path, 'w', encoding='utf-8') as f:
        f.write(log_text)

    findings_path = os.path.join(scan_dir, "findings.json")
    findings_data = [f.to_dict() for f in findings]
    with open(findings_path, 'w', encoding='utf-8') as f:
        json.dump(findings_data, f, indent=2)

    return scan_id


def list_scans(repo_root: Optional[str] = None) -> List[dict]:
    """
    List all log scans.

    Args:
        repo_root: Repository root (defaults to cwd)

    Returns:
        List of scan metadata dictionaries
    """
    if not repo_root:
        repo_root = os.getcwd()

    scans_dir = os.path.join(repo_root, "docs", "maestro", "log_scans")
    if not os.path.exists(scans_dir):
        return []

    scans = []
    for scan_id in os.listdir(scans_dir):
        scan_path = os.path.join(scans_dir, scan_id)
        if not os.path.isdir(scan_path):
            continue

        meta_path = os.path.join(scan_path, "meta.json")
        if not os.path.exists(meta_path):
            continue

        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            scans.append(meta)

    # Sort by timestamp descending
    scans.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return scans


def load_scan(scan_id: str, repo_root: Optional[str] = None) -> Optional[dict]:
    """
    Load scan details.

    Args:
        scan_id: Scan ID
        repo_root: Repository root (defaults to cwd)

    Returns:
        Scan data dictionary with meta and findings, or None if not found
    """
    if not repo_root:
        repo_root = os.getcwd()

    scan_path = get_scan_path(scan_id, repo_root)
    if not os.path.exists(scan_path):
        return None

    meta_path = os.path.join(scan_path, "meta.json")
    findings_path = os.path.join(scan_path, "findings.json")

    if not os.path.exists(meta_path) or not os.path.exists(findings_path):
        return None

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    with open(findings_path, 'r', encoding='utf-8') as f:
        findings_data = json.load(f)
        findings = [Finding.from_dict(f) for f in findings_data]

    return {
        "meta": meta,
        "findings": findings,
    }


def get_scan_path(scan_id: str, repo_root: Optional[str] = None) -> str:
    """
    Get path to scan directory.

    Args:
        scan_id: Scan ID
        repo_root: Repository root (defaults to cwd)

    Returns:
        Path to scan directory
    """
    if not repo_root:
        repo_root = os.getcwd()

    return os.path.join(repo_root, "docs", "maestro", "log_scans", scan_id)
