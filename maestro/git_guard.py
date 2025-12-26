"""Git branch guard for active work sessions."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from maestro.work_session import list_sessions, SessionStatus


def get_current_branch(repo_root: Optional[str] = None) -> Optional[str]:
    """Return the current git branch name or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root or None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_git_root(repo_root: Optional[str] = None) -> Optional[str]:
    """Return git root path or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_root or None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def check_branch_guard(repo_root: Optional[str] = None) -> Optional[str]:
    """Return an error message if active work session branch mismatches current branch."""
    active_sessions = [
        session for session in list_sessions()
        if session.session_type.startswith("work_")
        and session.status in (SessionStatus.RUNNING.value, SessionStatus.PAUSED.value)
    ]

    if not active_sessions:
        return None

    current_branch = get_current_branch(repo_root)
    current_root = get_git_root(repo_root)

    for session in active_sessions:
        session_branch = session.metadata.get("git_branch")
        session_root = session.metadata.get("git_root")
        if not session_branch or not session_root:
            continue
        if current_root and Path(session_root).resolve() != Path(current_root).resolve():
            continue
        if current_branch and session_branch != current_branch:
            return (
                f"Active work session '{session.session_id}' started on branch '{session_branch}', "
                f"but current branch is '{current_branch}'. Close the session or return to '{session_branch}'."
            )

    return None
