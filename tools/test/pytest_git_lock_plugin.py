"""
Pytest plugin to detect repo git index locks and report the offending test.

This plugin checks for a .git/index.lock file before and after each test.
If the lock appears, it fails the test and prints guidance so the user can
remove the stale lock safely.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest


LOCK_FILENAME = "index.lock"
_lock_detected = False
_lock_event = None


def _lock_path() -> Path:
    repo_root = os.environ.get("MAESTRO_REPO_ROOT")
    if repo_root:
        return Path(repo_root) / ".git" / LOCK_FILENAME
    return Path.cwd() / ".git" / LOCK_FILENAME


def _lock_exists() -> bool:
    try:
        return _lock_path().exists()
    except OSError:
        return False


def _record_lock_event(nodeid: str, phase: str) -> None:
    global _lock_detected, _lock_event
    if _lock_detected:
        return
    _lock_detected = True
    _lock_event = {
        "nodeid": nodeid,
        "phase": phase,
        "path": str(_lock_path()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _fail_with_lock(nodeid: str, phase: str) -> None:
    _record_lock_event(nodeid, phase)
    message = (
        f"Git index lock detected ({_lock_event['path']}) {phase} {nodeid}.\n"
        "If no git process is running, remove stale lock: rm -f .git/index.lock"
    )
    pytest.fail(message, pytrace=False)


def pytest_runtest_setup(item):
    if _lock_exists():
        _fail_with_lock(item.nodeid, "before")


def pytest_runtest_teardown(item):
    if _lock_exists():
        _fail_with_lock(item.nodeid, "after")
