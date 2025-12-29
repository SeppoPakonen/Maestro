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
import sys
from pathlib import Path
from typing import Set


# Global state for collecting passed test nodeids
_passed_nodeids: Set[str] = set()


def pytest_configure(config):
    """Register plugin markers and setup."""
    config.addinivalue_line(
        "markers",
        "checkpoint: internal marker for checkpoint/resume plugin"
    )


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
        with open(resume_path, "r") as f:
            passed_set = {line.strip() for line in f if line.strip()}
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
    if report.when == "call" and report.outcome == "passed":
        _passed_nodeids.add(report.nodeid)


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
        with open(checkpoint_path, "w") as f:
            for nodeid in sorted(_passed_nodeids):
                f.write(f"{nodeid}\n")

        # Print confirmation (will be visible in runner output)
        if _passed_nodeids:
            print(f"\nCheckpoint written: {checkpoint_file} ({len(_passed_nodeids)} passed tests)")
    except Exception as e:
        print(f"WARNING: Failed to write checkpoint file: {e}", file=sys.stderr)
