from __future__ import annotations

import argparse
import os
from typing import List

from maestro.issues.issue_store import list_issues, load_issue, rollback_issue_state, update_issue_state
from maestro.issues.model import ISSUE_TYPES, ISSUE_STATES


def add_issues_parser(subparsers) -> argparse.ArgumentParser:
    issues_parser = subparsers.add_parser("issues", help="Issue tracking commands")
    issues_subparsers = issues_parser.add_subparsers(dest="issues_subcommand", help="Issues subcommands")

    list_parser = issues_subparsers.add_parser("list", aliases=["ls"], help="List issues")
    list_parser.add_argument("--type", help="Filter by issue type")

    show_parser = issues_subparsers.add_parser("show", help="Show issue details")
    show_parser.add_argument("issue_id", help="Issue ID to show")

    state_parser = issues_subparsers.add_parser("state", help="Update issue state")
    state_parser.add_argument("issue_id", help="Issue ID to update")
    state_parser.add_argument("state", help="New state")

    rollback_parser = issues_subparsers.add_parser("rollback", help="Rollback issue state")
    rollback_parser.add_argument("issue_id", help="Issue ID to rollback")

    for issue_type in sorted(ISSUE_TYPES):
        type_parser = issues_subparsers.add_parser(issue_type, help=f"List {issue_type} issues")
        type_parser.set_defaults(issue_type=issue_type)

    return issues_parser


def handle_issues_command(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root() or os.getcwd()
    subcommand = getattr(args, "issues_subcommand", None)
    if subcommand in (None, "list"):
        issue_type = getattr(args, "type", None)
        if subcommand is None and hasattr(args, "issue_type"):
            issue_type = args.issue_type
        return _handle_list(repo_root, issue_type)
    if subcommand == "show":
        return _handle_show(repo_root, args.issue_id)
    if subcommand == "state":
        return _handle_state(repo_root, args.issue_id, args.state)
    if subcommand == "rollback":
        return _handle_rollback(repo_root, args.issue_id)
    if hasattr(args, "issue_type"):
        return _handle_list(repo_root, args.issue_type)
    print(f"Unknown issues subcommand: {subcommand}")
    return 1


def _handle_list(repo_root: str, issue_type: str | None) -> int:
    if issue_type and issue_type not in ISSUE_TYPES:
        print(f"Unknown issue type: {issue_type}")
        return 1
    issues = list_issues(repo_root, issue_type=issue_type)
    if not issues:
        print("No issues found.")
        return 0
    for issue in issues:
        location = f"{issue.file}:{issue.line}:{issue.column}".rstrip(":0")
        print(f"- {issue.issue_id} [{issue.issue_type}] {issue.state} {issue.title}")
        if location:
            print(f"  {location}")
    return 0


def _handle_show(repo_root: str, issue_id: str) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)
    print(f"ID: {record.issue_id}")
    print(f"Type: {record.issue_type}")
    print(f"State: {record.state}")
    print(f"Priority: {record.priority}")
    print(f"Title: {record.title}")
    print(f"Description: {record.description}")
    location = f"{record.file}:{record.line}:{record.column}".rstrip(":0")
    print(f"Location: {location or 'N/A'}")
    print(f"Created: {record.created_at}")
    print(f"Modified: {record.modified_at}")
    if record.tool:
        print(f"Tool: {record.tool}")
    if record.rule:
        print(f"Rule: {record.rule}")
    return 0


def _handle_state(repo_root: str, issue_id: str, state: str) -> int:
    if state not in ISSUE_STATES:
        print(f"Invalid state '{state}'. Valid: {', '.join(ISSUE_STATES)}")
        return 1
    try:
        updated = update_issue_state(repo_root, issue_id, state)
    except ValueError as exc:
        print(str(exc))
        return 1
    if not updated:
        print(f"Issue not found: {issue_id}")
        return 1
    print(f"Issue {issue_id} -> {state}")
    return 0


def _handle_rollback(repo_root: str, issue_id: str) -> int:
    rolled_back = rollback_issue_state(repo_root, issue_id)
    if not rolled_back:
        print(f"No rollback available for {issue_id}")
        return 1
    print(f"Rolled back {issue_id}")
    return 0


def _find_issue_path(repo_root: str, issue_id: str) -> str | None:
    issues_dir = os.path.join(repo_root, "docs", "issues")
    candidate = os.path.join(issues_dir, f"{issue_id}.md")
    if os.path.exists(candidate):
        return candidate
    if not os.path.isdir(issues_dir):
        return None
    for name in os.listdir(issues_dir):
        if name.startswith(issue_id) and name.endswith(".md"):
            return os.path.join(issues_dir, name)
    return None


def _find_repo_root() -> str | None:
    current_dir = os.getcwd()
    while current_dir != "/":
        if os.path.exists(os.path.join(current_dir, ".maestro")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None
