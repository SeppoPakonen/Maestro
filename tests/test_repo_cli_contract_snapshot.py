"""
Parser snapshot tests for repo commands.

These tests ensure the CLI contract remains stable after refactoring.
"""

import subprocess
import sys


def test_repo_help_shows_subcommands():
    """Verify repo --help shows expected subcommands."""
    result = subprocess.run(
        [sys.executable, "-m", "maestro", "repo", "--help"],
        capture_output=True,
        text=True,
        cwd="/home/sblo/Dev/Maestro"
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"

    # Check for key subcommands
    expected_subcommands = [
        "resolve",
        "show",
        "pkg",
        "asm",
        "conf",
        "refresh",
        "hier",
        "conventions",
        "profile",
        "evidence",
        "rules",
        "hub",
    ]

    for subcmd in expected_subcommands:
        assert subcmd in result.stdout, f"Expected '{subcmd}' in help output"


def test_repo_profile_help_shows_subcommands():
    """Verify repo profile --help shows init and show."""
    result = subprocess.run(
        [sys.executable, "-m", "maestro", "repo", "profile", "--help"],
        capture_output=True,
        text=True,
        cwd="/home/sblo/Dev/Maestro"
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert "show" in result.stdout, "Expected 'show' subcommand in profile help"
    assert "init" in result.stdout, "Expected 'init' subcommand in profile help"


def test_repo_evidence_help_shows_subcommands():
    """Verify repo evidence --help shows pack, list, show."""
    result = subprocess.run(
        [sys.executable, "-m", "maestro", "repo", "evidence", "--help"],
        capture_output=True,
        text=True,
        cwd="/home/sblo/Dev/Maestro"
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert "pack" in result.stdout, "Expected 'pack' subcommand in evidence help"
    assert "list" in result.stdout, "Expected 'list' subcommand in evidence help"
    assert "show" in result.stdout, "Expected 'show' subcommand in evidence help"


def test_repo_asm_alias_works():
    """Verify 'asm' alias works for assembly command."""
    result = subprocess.run(
        [sys.executable, "-m", "maestro", "repo", "asm", "--help"],
        capture_output=True,
        text=True,
        cwd="/home/sblo/Dev/Maestro"
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert "assembly" in result.stdout.lower(), "Expected assembly-related help"


def test_repo_resolve_alias_works():
    """Verify 'res' alias works for resolve command."""
    result = subprocess.run(
        [sys.executable, "-m", "maestro", "repo", "res", "--help"],
        capture_output=True,
        text=True,
        cwd="/home/sblo/Dev/Maestro"
    )

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert "scan" in result.stdout.lower(), "Expected resolve/scan help"


if __name__ == "__main__":
    # Run tests manually
    print("Running CLI contract snapshot tests...")
    test_repo_help_shows_subcommands()
    print("✓ repo --help test passed")

    test_repo_profile_help_shows_subcommands()
    print("✓ repo profile --help test passed")

    test_repo_evidence_help_shows_subcommands()
    print("✓ repo evidence --help test passed")

    test_repo_asm_alias_works()
    print("✓ repo asm alias test passed")

    test_repo_resolve_alias_works()
    print("✓ repo resolve alias test passed")

    print("\nAll tests passed!")
