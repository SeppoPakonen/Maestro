"""Fast-path help regression tests for CLI commands."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


MAESTRO_PATH = Path(__file__).parent.parent / "maestro.py"


def _run_maestro(args, env=None, timeout=2):
    command = [sys.executable, str(MAESTRO_PATH)] + list(args)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _with_legacy_env():
    env = os.environ.copy()
    env["MAESTRO_ENABLE_LEGACY"] = "1"
    return env


def _assert_fast_help(args, *, env=None, expect_deprecated=False, expect_text=None):
    result = _run_maestro(args, env=env, timeout=2)
    output = (result.stdout + result.stderr).lower()

    if expect_deprecated:
        assert "deprecated" in output
    if expect_text:
        assert expect_text in output

    assert result.returncode in (0, 1, 2)


def test_resume_help_fast():
    _assert_fast_help(["resume", "--help"], env=_with_legacy_env(), expect_deprecated=True)


def test_rules_help_fast():
    _assert_fast_help(["rules", "--help"], env=_with_legacy_env(), expect_deprecated=True)


def test_root_help_fast():
    _assert_fast_help(["root", "--help"], env=_with_legacy_env(), expect_deprecated=True)


def test_understand_help_fast():
    _assert_fast_help(["understand", "--help"], env=_with_legacy_env(), expect_deprecated=True)


def test_make_help_fast():
    _assert_fast_help(["make", "--help"], expect_text="make")


def test_workflow_keyword_help_fast():
    _assert_fast_help(["workflow"], expect_text="workflow")
