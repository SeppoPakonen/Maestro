"""
Tests for the Plan Help command behavior.
"""
import sys
from io import StringIO
from unittest.mock import patch
import pytest

from maestro.main import main


def test_plan_help_shows_subcommands():
    """Test that 'maestro plan' without subcommands shows help."""
    # Capture stdout
    captured_output = StringIO()

    # Track if SystemExit is raised
    exit_raised = False
    exit_code = None

    with patch('sys.argv', ['maestro', 'plan']), \
         patch('sys.stdout', captured_output), \
         patch('sys.stderr', captured_output):
        try:
            main()
        except SystemExit as e:
            exit_raised = True
            exit_code = e.code

    # Get the output
    output = captured_output.getvalue()

    # Check that help is shown (either via help text or usage)
    assert 'usage:' in output or 'Plan subcommands' in output
    # Check that subcommands are mentioned
    assert 'add' in output
    assert 'list' in output
    assert 'show' in output
    assert 'discuss' in output
    assert 'explore' in output

    # Verify exit code is 0 (help should exit cleanly)
    # If SystemExit was raised, verify its code
    if exit_raised:
        assert exit_code == 0


def test_plan_help_contains_all_subcommands():
    """Test that 'maestro plan --help' contains all subcommands in usage."""
    # Capture stdout
    captured_output = StringIO()
    
    with patch('sys.argv', ['maestro', 'plan', '--help']), \
         patch('sys.stdout', captured_output), \
         patch('sys.stderr', captured_output), \
         pytest.raises(SystemExit) as exc_info:
        main()
    
    # Verify exit code is 0 (help should exit cleanly)
    assert exc_info.value.code == 0
    
    # Get the output
    output = captured_output.getvalue()
    
    # Check that all expected subcommands are in the help
    assert 'add' in output
    assert 'list' in output
    assert 'show' in output
    assert 'discuss' in output
    assert 'explore' in output
    assert 'ops' in output