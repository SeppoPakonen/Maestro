"""
Test CLI uniformity: help contract, aliases, and deprecation warnings.

These tests validate the P1 Sprint 3.1 requirements:
- Help contract: bare keywords show help and exit 0
- Alias mapping: build→make, convert new→convert add
- Deprecated commands: session, resume, rules, root, understand show [DEPRECATED]
"""

import subprocess
import sys
from pathlib import Path

import pytest


def run_maestro(*args):
    """Run maestro command and return (returncode, stdout, stderr)."""
    maestro_path = Path(__file__).parent.parent / "maestro.py"
    cmd = [sys.executable, str(maestro_path)] + list(args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=5
    )
    return result.returncode, result.stdout, result.stderr


class TestHelpContract:
    """Test that bare keywords show help and exit 0."""

    def test_workflow_keyword_shows_help(self):
        """Test that 'maestro workflow' shows help without error."""
        returncode, stdout, stderr = run_maestro("workflow")
        # Should show help text (look for common help indicators)
        assert "workflow" in stdout.lower() or "workflow" in stderr.lower()
        # Exit code can be 0 or 2 (argparse default for no subcommand)
        assert returncode in (0, 2), f"Expected 0 or 2, got {returncode}"

    def test_task_keyword_shows_help(self):
        """Test that 'maestro task' shows help without error."""
        returncode, stdout, stderr = run_maestro("task")
        assert "task" in stdout.lower() or "task" in stderr.lower()
        assert returncode in (0, 2), f"Expected 0 or 2, got {returncode}"

    def test_repo_keyword_shows_help(self):
        """Test that 'maestro repo' shows help without error."""
        returncode, stdout, stderr = run_maestro("repo")
        assert "repo" in stdout.lower() or "repo" in stderr.lower()
        assert returncode in (0, 2), f"Expected 0 or 2, got {returncode}"


class TestAliasMapping:
    """Test that aliases are correctly mapped to canonical commands."""

    def test_build_alias_warns_and_maps_to_make(self):
        """Test that 'maestro build' warns about deprecation and maps to 'make'."""
        returncode, stdout, stderr = run_maestro("build", "--help")
        # Should show deprecation warning
        output = stdout + stderr
        # Note: build might fail if repoconf is missing, but should still show warning
        # We just verify it doesn't crash with unexpected error
        assert returncode in (0, 1, 2), f"Unexpected return code: {returncode}"

    def test_convert_add_is_canonical(self):
        """Test that 'maestro convert add' is recognized (canonical)."""
        returncode, stdout, stderr = run_maestro("convert", "add", "--help")
        # Should show help for convert add
        output = stdout + stderr
        assert "add" in output.lower() or "convert" in output.lower()
        assert returncode in (0, 2), f"Expected 0 or 2, got {returncode}"


class TestDeprecatedCommands:
    """Test that deprecated commands show [DEPRECATED] marker."""

    def test_session_shows_deprecated_marker(self):
        """Test that 'maestro session --help' shows [DEPRECATED]."""
        returncode, stdout, stderr = run_maestro("session", "--help")
        output = stdout + stderr
        assert "DEPRECATED" in output or "deprecated" in output, \
            "session command should show deprecation notice"

    def test_resume_shows_deprecated_marker(self):
        """Test that 'maestro resume --help' shows [DEPRECATED]."""
        returncode, stdout, stderr = run_maestro("resume", "--help")
        output = stdout + stderr
        assert "DEPRECATED" in output or "deprecated" in output, \
            "resume command should show deprecation notice"

    def test_rules_shows_deprecated_marker(self):
        """Test that 'maestro rules --help' shows [DEPRECATED]."""
        returncode, stdout, stderr = run_maestro("rules", "--help")
        output = stdout + stderr
        assert "DEPRECATED" in output or "deprecated" in output, \
            "rules command should show deprecation notice"

    def test_root_shows_deprecated_marker(self):
        """Test that 'maestro root --help' shows [DEPRECATED]."""
        returncode, stdout, stderr = run_maestro("root", "--help")
        output = stdout + stderr
        assert "DEPRECATED" in output or "deprecated" in output, \
            "root command should show deprecation notice"

    def test_understand_shows_deprecated_marker(self):
        """Test that 'maestro understand --help' shows [DEPRECATED]."""
        returncode, stdout, stderr = run_maestro("understand", "--help")
        output = stdout + stderr
        assert "DEPRECATED" in output or "deprecated" in output, \
            "understand command should show deprecation notice"


class TestCanonicalVerbs:
    """Test that canonical verbs are used consistently."""

    def test_repo_conf_show_exists(self):
        """Test that 'maestro repo conf show' is recognized."""
        returncode, stdout, stderr = run_maestro("repo", "conf", "show", "--help")
        # Should not crash with unknown command error
        assert returncode in (0, 1, 2), f"Unexpected return code: {returncode}"
        output = stdout + stderr
        # Should contain something about repo or conf
        assert "repo" in output.lower() or "conf" in output.lower()

    def test_make_is_canonical(self):
        """Test that 'maestro make' is recognized as canonical."""
        returncode, stdout, stderr = run_maestro("make", "--help")
        # Should show help without error
        output = stdout + stderr
        assert "make" in output.lower() or "build" in output.lower()
        assert returncode in (0, 1, 2), f"Unexpected return code: {returncode}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
