"""
Tests for the runbook resolve -vv/--very-verbose flag functionality.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import argparse

from maestro.commands.runbook import (
    handle_runbook_resolve,
    AIRunbookGenerator,
    _get_runbook_storage_path,
    format_ai_output_for_display
)


def test_runbook_resolve_vv_prints_prompt_and_output(tmp_path, monkeypatch, capsys):
    """Test that runbook resolve with -vv prints the prompt and AI output."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(tmp_path))

    # Create the expected directory structure
    docs_root = tmp_path / "docs" / "maestro"
    docs_root.mkdir(parents=True)

    # Create a commands directory with a sample file for evidence collection
    commands_dir = tmp_path / "docs" / "commands"
    commands_dir.mkdir(parents=True)

    # Create a sample command documentation file
    sample_doc = commands_dir / "sample_command.md"
    sample_doc.write_text("# Sample Command\n\nThis command does something useful.\n")

    # Mock the engine to return a runbook
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_engine = Mock()
        mock_engine.name = "test-engine"
        mock_engine.generate.return_value = json.dumps({
            "title": "Test Verbose Output",
            "goal": "Test goal for verbose output",
            "steps": [
                {
                    "n": 1,
                    "actor": "dev",
                    "action": "Run the test command",
                    "expected": "Command executes successfully"
                }
            ]
        })
        mock_select_engine.return_value = mock_engine

        # Create mock args with very verbose flag
        args = argparse.Namespace()
        args.text = "Create a test runbook for very verbose output"
        args.verbose = False  # Not using regular verbose
        args.very_verbose = True  # Enable very verbose
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False
        args.name = None
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Capture the output
        captured = capsys.readouterr()

        # Check that very verbose information is in the output
        assert "=== RUNBOOK RESOLVE PROMPT (sent to engine) ===" in captured.out
        assert "=== RUNBOOK RESOLVE AI OUTPUT (raw) ===" in captured.out
        assert "=== END AI OUTPUT ===" in captured.out
        assert "Create a test runbook for very verbose output" in captured.out  # Should be in the prompt
        assert "Test Verbose Output" in captured.out  # Should be in the AI output


def test_runbook_resolve_v_implies_not_vv_output(tmp_path, monkeypatch, capsys):
    """Test that regular -v does NOT print the full prompt and AI output."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(tmp_path))

    # Create the expected directory structure
    docs_root = tmp_path / "docs" / "maestro"
    docs_root.mkdir(parents=True)

    # Create a commands directory with a sample file for evidence collection
    commands_dir = tmp_path / "docs" / "commands"
    commands_dir.mkdir(parents=True)

    # Create a sample command documentation file
    sample_doc = commands_dir / "sample_command.md"
    sample_doc.write_text("# Sample Command\n\nThis command does something useful.\n")

    # Mock the engine to return a runbook
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_engine = Mock()
        mock_engine.name = "test-engine"
        mock_engine.generate.return_value = json.dumps({
            "title": "Test Verbose Output",
            "goal": "Test goal for verbose output",
            "steps": [
                {
                    "n": 1,
                    "actor": "dev",
                    "action": "Run the test command",
                    "expected": "Command executes successfully"
                }
            ]
        })
        mock_select_engine.return_value = mock_engine

        # Create mock args with regular verbose flag only
        args = argparse.Namespace()
        args.text = "Create a test runbook for regular verbose output"
        args.verbose = True  # Enable regular verbose
        args.very_verbose = False  # NOT very verbose
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False
        args.name = None
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Capture the output
        captured = capsys.readouterr()

        # Check that regular verbose info is present
        assert "Prompt hash:" in captured.out
        assert "test-engine" in captured.out  # Engine name should be shown

        # Check that very verbose information is NOT in the output
        assert "=== RUNBOOK RESOLVE PROMPT (sent to engine) ===" not in captured.out
        assert "=== RUNBOOK RESOLVE AI OUTPUT (raw) ===" not in captured.out


def test_format_ai_output_for_display_json():
    """Test that format_ai_output_for_display properly formats JSON."""
    ai_output = json.dumps({
        "title": "Test Runbook",
        "steps": [
            {"n": 1, "action": "Do something"}
        ]
    }, indent=2)
    
    formatted = format_ai_output_for_display(ai_output)
    
    # Should be pretty-printed JSON
    assert "Test Runbook" in formatted
    assert "Do something" in formatted
    assert "\n  " in formatted  # Should have indentation


def test_format_ai_output_for_display_truncation():
    """Test that format_ai_output_for_display truncates long output."""
    # Create a long output (more than 2000 lines)
    long_output = "\n".join([f"Line {i}" for i in range(2500)])  # 2500 lines
    
    formatted = format_ai_output_for_display(long_output, max_lines=2000)
    
    # Should be truncated
    assert "(... output truncated; full output exceeds 2000 lines)" in formatted
    # Should still contain some of the original content
    assert "Line 0" in formatted
    assert "Line 1999" in formatted  # Last line before truncation
    assert "Line 2000" not in formatted  # Should not contain lines beyond the limit


def test_format_ai_output_for_display_plain_text():
    """Test that format_ai_output_for_display handles plain text."""
    plain_text = "This is plain text\nWith multiple lines\nAnd some content"
    
    formatted = format_ai_output_for_display(plain_text)
    
    # Should preserve the text structure
    assert "This is plain text" in formatted
    assert "With multiple lines" in formatted
    assert "And some content" in formatted


def test_runbook_resolve_vv_implies_v_behavior(tmp_path, monkeypatch, capsys):
    """Test that -vv includes all -v behavior plus additional output."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(tmp_path))

    # Create the expected directory structure
    docs_root = tmp_path / "docs" / "maestro"
    docs_root.mkdir(parents=True)

    # Create a commands directory with a sample file for evidence collection
    commands_dir = tmp_path / "docs" / "commands"
    commands_dir.mkdir(parents=True)

    # Create a sample command documentation file
    sample_doc = commands_dir / "sample_command.md"
    sample_doc.write_text("# Sample Command\n\nThis command does something useful.\n")

    # Mock the engine to return a runbook
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_engine = Mock()
        mock_engine.name = "test-engine"
        mock_engine.generate.return_value = json.dumps({
            "title": "Test Verbose Output",
            "goal": "Test goal for verbose output",
            "steps": [
                {
                    "n": 1,
                    "actor": "dev",
                    "action": "Run the test command",
                    "expected": "Command executes successfully"
                }
            ]
        })
        mock_select_engine.return_value = mock_engine

        # Create mock args with very verbose flag (which should imply -v)
        args = argparse.Namespace()
        args.text = "Create a test runbook for very verbose output"
        args.verbose = False  # Not explicitly set, but -vv should imply it
        args.very_verbose = True  # Enable very verbose
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False
        args.name = None
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Capture the output
        captured = capsys.readouterr()

        # Check that -v behavior is included (prompt hash, engine info)
        assert "Prompt hash:" in captured.out
        assert "test-engine" in captured.out  # Engine name should be shown
        
        # Check that -vv additional output is also present
        assert "=== RUNBOOK RESOLVE PROMPT (sent to engine) ===" in captured.out
        assert "=== RUNBOOK RESOLVE AI OUTPUT (raw) ===" in captured.out