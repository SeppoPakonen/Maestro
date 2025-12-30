"""
Pytest plugin for checkpoint/resume functionality.

Provides two main features:
1. Checkpoint writing: Records all PASSED test nodeids to a file after each run
2. Resume mode: Skips tests that were previously PASSED (based on checkpoint file)

Usage:
    # Enable checkpoint writing (runner sets MAESTRO_TEST_CHECKPOINT env var)
    MAESTRO_TEST_CHECKPOINT=/tmp/checkpoint.txt pytest

    # Enable resume mode (runner sets MAESTRO_TEST_RESUME_FROM env var)
    MAESTRO_TEST_RESUME_FROM=/tmp/checkpoint.txt pytest
"""
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Set


# Global state for collecting passed test nodeids
_passed_nodeids: Set[str] = set()
_failed_count = 0
_started_at = None
_pytest_args_str = ""
CHECKPOINT_DELIM = "--- PASSED NODEIDS ---"


def _load_checkpoint_nodeids(path: Path) -> Set[str]:
    lines = path.read_text().splitlines()
    if CHECKPOINT_DELIM in lines:
        index = lines.index(CHECKPOINT_DELIM)
        return {line.strip() for line in lines[index + 1 :] if line.strip()}
    return {
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }


def pytest_configure(config):
    """Register plugin markers and setup."""
    global _pytest_args_str
    args = getattr(config, "invocation_params", None)
    if args is not None and hasattr(args, "args"):
        _pytest_args_str = " ".join(shlex.quote(arg) for arg in args.args)
    config.addinivalue_line(
        "markers",
        "checkpoint: internal marker for checkpoint/resume plugin"
    )


def pytest_sessionstart(session):
    """Capture test start time for checkpoint metadata."""
    global _started_at
    _started_at = datetime.now(timezone.utc)


def pytest_collection_modifyitems(session, config, items):
    """
    Hook called after test collection.
    If resume mode is enabled, filter out previously passed tests.
    """
    resume_file = os.environ.get("MAESTRO_TEST_RESUME_FROM")
    if not resume_file:
        return

    resume_path = Path(resume_file)
    if not resume_path.exists():
        print(f"ERROR: Resume checkpoint file not found: {resume_file}", file=sys.stderr)
        sys.exit(1)

    # Load previously passed test nodeids
    try:
        passed_set = _load_checkpoint_nodeids(resume_path)
    except Exception as e:
        print(f"ERROR: Failed to read resume checkpoint: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter out previously passed tests
    original_count = len(items)
    items[:] = [item for item in items if item.nodeid not in passed_set]
    skipped_count = original_count - len(items)

    if skipped_count > 0:
        print(f"Resume: skipping {skipped_count} previously passed tests from {resume_file}")


def pytest_runtest_logreport(report):
    """
    Hook called for each test phase (setup/call/teardown).
    Collect nodeids of tests that passed.
    """
    # Only record on 'call' phase and if outcome is 'passed'
    global _failed_count
    if report.when == "call":
        if report.outcome == "passed":
            _passed_nodeids.add(report.nodeid)
        elif report.outcome == "failed":
            _failed_count += 1


def pytest_sessionfinish(session, exitstatus):
    """
    Hook called after entire test session finishes.
    Write checkpoint file with all passed test nodeids.
    """
    checkpoint_file = os.environ.get("MAESTRO_TEST_CHECKPOINT")
    if not checkpoint_file:
        return

    checkpoint_path = Path(checkpoint_file)

    # Ensure parent directory exists
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        started_at = _started_at or datetime.now(timezone.utc)
        finished_at = datetime.now(timezone.utc)
        passed_count = len(_passed_nodeids)
        with open(checkpoint_path, "w") as f:
            f.write("# Maestro pytest checkpoint\n")
            f.write(f"# started_at: {started_at.isoformat()}\n")
            f.write(f"# finished_at: {finished_at.isoformat()}\n")
            f.write(f"# pytest_args: {_pytest_args_str}\n")
            f.write(f"# passed_tests_count: {passed_count}\n")
            f.write(f"# failed_tests_count: {_failed_count}\n")
            f.write(f"{CHECKPOINT_DELIM}\n")
            for nodeid in sorted(_passed_nodeids):
                f.write(f"{nodeid}\n")

        # Print confirmation (will be visible in runner output)
        if _passed_nodeids:
            print(f"\nCheckpoint written: {checkpoint_file} ({len(_passed_nodeids)} passed tests)")
    except Exception as e:
        print(f"WARNING: Failed to write checkpoint file: {e}", file=sys.stderr)
