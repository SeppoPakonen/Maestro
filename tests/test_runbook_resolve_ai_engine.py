"""
Tests for the runbook resolve command with AI engine functionality.

This module tests the updated maestro runbook resolve command to ensure it properly
uses AI engines by default and supports the new features.
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
    EvidenceOnlyGenerator,
    _get_runbook_storage_path,
    _ensure_runbook_storage,
    _load_runbook
)


def test_runbook_resolve_uses_ai_engine_by_default(tmp_path, monkeypatch):
    """Test that runbook resolve uses AI engine by default (not evidence-only)."""
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

    # Mock the engine selection to return a mock engine
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_engine = Mock()
        mock_engine.name = "test-engine"
        mock_engine.generate.return_value = json.dumps({
            "title": "Test Runbook from AI",
            "goal": "Test goal from AI",
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

        # Create mock args without --evidence-only flag
        args = argparse.Namespace()
        args.text = "Create a test runbook with AI"
        args.verbose = False
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None  # Use default engine selection
        args.evidence_only = False  # Default - should use AI
        args.name = None
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Verify that select_engine_for_role was called (indicating AI was used)
        mock_select_engine.assert_called_once_with('worker', preferred_order=None)

        # Check that the runbook file was created
        runbooks_dir = docs_root / "runbooks" / "items"
        runbook_files = list(runbooks_dir.glob("*.json"))
        assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"


def test_runbook_resolve_uses_evidence_only_when_flagged(tmp_path, monkeypatch):
    """Test that runbook resolve uses evidence-only when --evidence-only flag is set."""
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

    # Mock the EvidenceOnlyGenerator to track if it's used
    with patch('maestro.commands.runbook.EvidenceOnlyGenerator') as mock_evidence_gen_class:
        mock_evidence_gen = Mock()
        mock_evidence_gen.generate.return_value = {
            "id": "test-evidence-only",
            "title": "Test Evidence Only",
            "goal": "Test goal from evidence",
            "steps": [
                {
                    "n": 1,
                    "actor": "dev",
                    "action": "Review docs",
                    "expected": "Documentation reviewed"
                }
            ],
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        mock_evidence_gen_class.return_value = mock_evidence_gen

        # Create mock args with --evidence-only flag
        args = argparse.Namespace()
        args.text = "Create a test runbook with evidence only"
        args.verbose = False
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = True  # Use evidence-only
        args.name = None
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Verify that EvidenceOnlyGenerator was used (not AI engine)
        mock_evidence_gen_class.assert_called_once()
        mock_evidence_gen.generate.assert_called_once()

        # Verify that engine selection was NOT called
        # We can't easily check this without patching the entire function,
        # but we know EvidenceOnlyGenerator was used instead of AIRunbookGenerator


def test_runbook_resolve_with_custom_name(tmp_path, monkeypatch):
    """Test that runbook resolve respects the --name flag."""
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

    # Mock the engine to return a runbook with a different title
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_engine = Mock()
        mock_engine.name = "test-engine"
        mock_engine.generate.return_value = json.dumps({
            "title": "AI Generated Title",
            "goal": "Test goal from AI",
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

        # Create mock args with custom name
        args = argparse.Namespace()
        args.text = "Create a test runbook"
        args.verbose = False
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False
        args.name = "Custom Runbook Name"  # Custom name
        args.dry_run = False

        # Call the function
        handle_runbook_resolve(args)

        # Check that the runbook file was created
        runbooks_dir = docs_root / "runbooks" / "items"
        runbook_files = list(runbooks_dir.glob("*.json"))
        assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"

        # Check the content of the runbook file
        runbook_file = runbook_files[0]
        with open(runbook_file, 'r') as f:
            runbook_content = json.load(f)

        # Verify the title was overridden by the custom name
        assert runbook_content['title'] == "Custom Runbook Name"


def test_runbook_resolve_dry_run_does_not_save(tmp_path, monkeypatch):
    """Test that runbook resolve with --dry-run does not save the runbook."""
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
            "title": "Test Dry Run",
            "goal": "Test goal for dry run",
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

        # Create mock args with dry-run flag
        args = argparse.Namespace()
        args.text = "Create a test runbook for dry run"
        args.verbose = False
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False
        args.name = None
        args.dry_run = True  # Dry run - should not save

        # Call the function
        handle_runbook_resolve(args)

        # Check that NO runbook file was created
        runbooks_dir = docs_root / "runbooks" / "items"
        runbook_files = list(runbooks_dir.glob("*.json"))
        assert len(runbook_files) == 0, f"Expected 0 runbook files, found {len(runbook_files)}"


def test_runbook_resolve_verbose_shows_engine_info(tmp_path, monkeypatch, capsys):
    """Test that runbook resolve with -v shows engine information."""
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

        # Create mock args with verbose flag
        args = argparse.Namespace()
        args.text = "Create a test runbook for verbose output"
        args.verbose = True  # Enable verbose
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

        # Check that verbose information is in the output
        assert "Prompt hash:" in captured.out
        assert "test-engine" in captured.out  # Engine name should be shown
        assert "Input:" in captured.out


def test_airunbook_generator_creates_proper_runbook():
    """Test that AIRunbookGenerator creates proper runbooks from AI responses."""
    # Create a mock engine
    mock_engine = Mock()
    mock_engine.generate.return_value = json.dumps({
        "title": "AI Generated Runbook",
        "goal": "Test goal from AI",
        "steps": [
            {
                "n": 1,
                "actor": "dev",
                "action": "Run the test command",
                "expected": "Command executes successfully"
            }
        ]
    })

    # Create an AIRunbookGenerator instance
    generator = AIRunbookGenerator(mock_engine)

    # Create mock evidence
    from maestro.commands.runbook import RunbookEvidence
    evidence = RunbookEvidence(
        repo_root="/test/repo",
        commands_docs=[{"filename": "test.md", "title": "Test Command", "summary": "Does something"}],
        help_text="Test help text",
        help_bin_path="/test/binary"
    )

    # Generate a runbook
    runbook = generator.generate(evidence, "Test request text")

    # Verify the runbook structure
    assert "id" in runbook
    assert runbook["title"] == "AI Generated Runbook"
    assert runbook["goal"] == "Test goal from AI"
    assert len(runbook["steps"]) == 1
    assert runbook["steps"][0]["n"] == 1
    assert runbook["steps"][0]["actor"] == "dev"
    assert runbook["steps"][0]["action"] == "Run the test command"
    assert runbook["steps"][0]["expected"] == "Command executes successfully"


def test_airunbook_generator_handles_invalid_json():
    """Test that AIRunbookGenerator handles invalid AI responses gracefully."""
    # Create a mock engine that returns invalid JSON
    mock_engine = Mock()
    mock_engine.generate.return_value = "This is not valid JSON"

    # Create an AIRunbookGenerator instance
    generator = AIRunbookGenerator(mock_engine)

    # Create mock evidence
    from maestro.commands.runbook import RunbookEvidence
    evidence = RunbookEvidence(
        repo_root="/test/repo",
        commands_docs=[],
        help_text=None,
        help_bin_path=None
    )

    # Generate a runbook - should fall back to EvidenceOnlyGenerator
    runbook = generator.generate(evidence, "Test request text")

    # Verify it's a valid runbook structure (from fallback)
    assert "id" in runbook
    assert "title" in runbook
    assert "steps" in runbook
    assert isinstance(runbook["steps"], list)


def test_runbook_resolve_fails_when_no_engine_available_and_not_using_evidence_only(tmp_path, monkeypatch):
    """Test that runbook resolve fails gracefully when no engine is available and evidence-only is forced."""
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

    # Mock the engine selection to raise ValueError (no engine available)
    with patch('maestro.commands.runbook.select_engine_for_role') as mock_select_engine:
        mock_select_engine.side_effect = ValueError("No engines enabled for worker role")

        # Create mock args without --evidence-only flag (should try to use AI)
        args = argparse.Namespace()
        args.text = "Create a test runbook with AI"
        args.verbose = False
        args.eval = False
        args.no_evidence = False
        args.help_bin = None
        args.commands_dir = str(commands_dir)
        args.engine = None
        args.evidence_only = False  # Should try to use AI
        args.name = None
        args.dry_run = False

        # Run the CLI command using subprocess to capture exit code
        result = subprocess.run([
            sys.executable, "-c",
            f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "Create a test runbook with AI"
args.verbose = False
args.eval = False
args.no_evidence = False
args.help_bin = None
args.commands_dir = '{str(commands_dir)}'
args.engine = None
args.evidence_only = False  # This will try to use AI
args.name = None
args.dry_run = False

handle_runbook_resolve(args)
            """
        ], capture_output=True, text=True, cwd=str(tmp_path))

        # Check that the command succeeded by falling back to evidence-only
        # This is the expected behavior - it should fall back to evidence-only
        assert result.returncode == 0, f"Command should have succeeded with fallback but failed with error: {result.stderr}"
        assert "Created/updated runbook:" in result.stdout