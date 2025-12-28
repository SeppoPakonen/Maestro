"""
JSON-based issue storage for observability pipeline.

This module handles the new JSON-based issue storage under docs/maestro/issues/
for issues created from log scans.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class IssueRecord:
    """Represents an issue in JSON format."""

    def __init__(
        self,
        issue_id: str,
        fingerprint: str,
        severity: str,
        status: str,
        message: str,
        first_seen: str,
        last_seen: str,
        occurrences: List[Dict[str, str]],
        linked_tasks: Optional[List[str]] = None,
        tool: Optional[str] = None,
        file: Optional[str] = None,
        line: Optional[int] = None,
        kind: Optional[str] = None,
    ):
        self.issue_id = issue_id
        self.fingerprint = fingerprint
        self.severity = severity
        self.status = status
        self.message = message
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.occurrences = occurrences
        self.linked_tasks = linked_tasks or []
        self.tool = tool
        self.file = file
        self.line = line
        self.kind = kind

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_id": self.issue_id,
            "fingerprint": self.fingerprint,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "occurrences": self.occurrences,
            "linked_tasks": self.linked_tasks,
            "tool": self.tool,
            "file": self.file,
            "line": self.line,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IssueRecord":
        """Create from dictionary."""
        return cls(
            issue_id=data["issue_id"],
            fingerprint=data["fingerprint"],
            severity=data["severity"],
            status=data["status"],
            message=data["message"],
            first_seen=data["first_seen"],
            last_seen=data["last_seen"],
            occurrences=data["occurrences"],
            linked_tasks=data.get("linked_tasks", []),
            tool=data.get("tool"),
            file=data.get("file"),
            line=data.get("line"),
            kind=data.get("kind"),
        )


def get_issues_dir(repo_root: Optional[str] = None) -> str:
    """Get the issues directory path."""
    if not repo_root:
        repo_root = os.getcwd()
    return os.path.join(repo_root, "docs", "maestro", "issues")


def get_issue_path(issue_id: str, repo_root: Optional[str] = None) -> str:
    """Get the path to an issue file."""
    issues_dir = get_issues_dir(repo_root)
    return os.path.join(issues_dir, f"{issue_id}.json")


def load_fingerprint_index(repo_root: Optional[str] = None) -> Dict[str, str]:
    """
    Load the fingerprint index.

    Returns:
        Dict mapping fingerprint -> issue_id
    """
    issues_dir = get_issues_dir(repo_root)
    index_path = os.path.join(issues_dir, "fingerprint_index.json")

    if not os.path.exists(index_path):
        return {}

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_fingerprint_index(index: Dict[str, str], repo_root: Optional[str] = None):
    """Save the fingerprint index."""
    issues_dir = get_issues_dir(repo_root)
    os.makedirs(issues_dir, exist_ok=True)

    index_path = os.path.join(issues_dir, "fingerprint_index.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)


def get_next_issue_id(repo_root: Optional[str] = None) -> str:
    """Get the next available issue ID."""
    issues_dir = get_issues_dir(repo_root)

    if not os.path.exists(issues_dir):
        return "ISSUE-001"

    # Find highest existing issue number
    max_num = 0
    for filename in os.listdir(issues_dir):
        if filename.startswith("ISSUE-") and filename.endswith(".json"):
            try:
                num_str = filename[6:-5]  # Extract number between ISSUE- and .json
                num = int(num_str)
                max_num = max(max_num, num)
            except ValueError:
                continue

    return f"ISSUE-{max_num + 1:03d}"


def create_or_update_issue(
    fingerprint: str,
    severity: str,
    message: str,
    scan_id: str,
    timestamp: str,
    tool: Optional[str] = None,
    file: Optional[str] = None,
    line: Optional[int] = None,
    kind: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Create new issue or update existing issue by fingerprint.

    Args:
        fingerprint: Issue fingerprint
        severity: Issue severity
        message: Error message
        scan_id: Scan ID where this finding occurred
        timestamp: Timestamp of occurrence
        tool: Tool that generated the finding
        file: File where error occurred
        line: Line number
        kind: Finding kind (error, warning, crash)
        repo_root: Repository root

    Returns:
        Tuple of (issue_id, is_new)
    """
    index = load_fingerprint_index(repo_root)

    # Check if issue exists by fingerprint
    if fingerprint in index:
        issue_id = index[fingerprint]
        issue_path = get_issue_path(issue_id, repo_root)

        # Load existing issue
        with open(issue_path, 'r', encoding='utf-8') as f:
            issue_data = json.load(f)

        issue = IssueRecord.from_dict(issue_data)

        # Update occurrence
        occurrence = {
            "scan_id": scan_id,
            "timestamp": timestamp,
        }
        issue.occurrences.append(occurrence)
        issue.last_seen = timestamp

        # If issue was resolved/ignored, reopen it
        if issue.status in ['resolved', 'ignored']:
            issue.status = 'open'

        # Save updated issue
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue.to_dict(), f, indent=2)

        return issue_id, False
    else:
        # Create new issue
        issue_id = get_next_issue_id(repo_root)

        occurrence = {
            "scan_id": scan_id,
            "timestamp": timestamp,
        }

        issue = IssueRecord(
            issue_id=issue_id,
            fingerprint=fingerprint,
            severity=severity,
            status='open',
            message=message,
            first_seen=timestamp,
            last_seen=timestamp,
            occurrences=[occurrence],
            tool=tool,
            file=file,
            line=line,
            kind=kind,
        )

        # Save issue
        issues_dir = get_issues_dir(repo_root)
        os.makedirs(issues_dir, exist_ok=True)

        issue_path = get_issue_path(issue_id, repo_root)
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue.to_dict(), f, indent=2)

        # Update index
        index[fingerprint] = issue_id
        save_fingerprint_index(index, repo_root)

        return issue_id, True


def list_issues_json(
    repo_root: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> List[IssueRecord]:
    """
    List issues from JSON storage.

    Args:
        repo_root: Repository root
        severity: Filter by severity
        status: Filter by status

    Returns:
        List of IssueRecord objects
    """
    issues_dir = get_issues_dir(repo_root)

    if not os.path.exists(issues_dir):
        return []

    issues = []
    for filename in os.listdir(issues_dir):
        if not filename.startswith("ISSUE-") or not filename.endswith(".json"):
            continue

        issue_path = os.path.join(issues_dir, filename)
        with open(issue_path, 'r', encoding='utf-8') as f:
            issue_data = json.load(f)

        issue = IssueRecord.from_dict(issue_data)

        # Apply filters
        if severity and issue.severity != severity:
            continue
        if status and issue.status != status:
            continue

        issues.append(issue)

    # Sort by severity priority then last_seen
    severity_order = {'blocker': 0, 'critical': 1, 'warning': 2, 'info': 3}
    issues.sort(key=lambda x: (
        severity_order.get(x.severity, 999),
        x.last_seen
    ), reverse=True)

    return issues


def load_issue_json(issue_id: str, repo_root: Optional[str] = None) -> Optional[IssueRecord]:
    """Load issue from JSON storage."""
    issue_path = get_issue_path(issue_id, repo_root)

    if not os.path.exists(issue_path):
        return None

    with open(issue_path, 'r', encoding='utf-8') as f:
        issue_data = json.load(f)

    return IssueRecord.from_dict(issue_data)


def update_issue_json(issue: IssueRecord, repo_root: Optional[str] = None):
    """Update issue in JSON storage."""
    issue_path = get_issue_path(issue.issue_id, repo_root)

    with open(issue_path, 'w', encoding='utf-8') as f:
        json.dump(issue.to_dict(), f, indent=2)


def link_issue_to_task(issue_id: str, task_id: str, repo_root: Optional[str] = None) -> bool:
    """
    Link issue to task.

    Args:
        issue_id: Issue ID
        task_id: Task ID
        repo_root: Repository root

    Returns:
        True if successful, False if issue not found
    """
    issue = load_issue_json(issue_id, repo_root)
    if not issue:
        return False

    if task_id not in issue.linked_tasks:
        issue.linked_tasks.append(task_id)
        update_issue_json(issue, repo_root)

    return True


def resolve_issue(issue_id: str, reason: Optional[str] = None, repo_root: Optional[str] = None) -> bool:
    """Resolve an issue."""
    issue = load_issue_json(issue_id, repo_root)
    if not issue:
        return False

    issue.status = 'resolved'
    update_issue_json(issue, repo_root)
    return True


def ignore_issue(issue_id: str, reason: Optional[str] = None, repo_root: Optional[str] = None) -> bool:
    """Ignore an issue."""
    issue = load_issue_json(issue_id, repo_root)
    if not issue:
        return False

    issue.status = 'ignored'
    update_issue_json(issue, repo_root)
    return True
