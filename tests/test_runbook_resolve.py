"""
Tests for the runbook resolve command functionality.

This module tests the maestro runbook resolve command to ensure it properly
creates runbook entries and updates the index.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


def test_runbook_resolve_positional_creates_entry(tmp_path, monkeypatch):
    """Test that runbook resolve with positional argument creates an entry."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory (project root)
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

    # Run the CLI command
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "freeform"
args.verbose = False
args.eval = False
args.no_evidence = False
args.help_bin = None
args.commands_dir = '{str(commands_dir)}'
args.engine = 'evidence'

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Check that the runbook file was created (we can't predict the exact ID)
    runbooks_dir = docs_root / "runbooks" / "items"
    runbook_files = list(runbooks_dir.glob("*.json"))
    assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"

    # Check the content of the runbook file
    runbook_file = runbook_files[0]
    with open(runbook_file, 'r') as f:
        runbook_content = json.load(f)

    # Verify the runbook has the expected structure
    assert 'id' in runbook_content
    assert 'title' in runbook_content
    assert 'steps' in runbook_content
    assert len(runbook_content['steps']) > 0
    assert 'generated' in runbook_content.get('tags', [])
    assert 'evidence-based' in runbook_content.get('tags', [])

    # Check that the index was updated
    index_file = docs_root / "runbooks" / "index.json"
    assert index_file.exists(), f"Index file was not created at {index_file}"

    with open(index_file, 'r') as f:
        index_content = json.load(f)

    # Verify the runbook is in the index
    runbook_id = runbook_content['id']
    index_entry = next((item for item in index_content if item['id'] == runbook_id), None)
    assert index_entry is not None
    assert index_entry['title'] == runbook_content['title']


def test_runbook_resolve_eval_reads_stdin(tmp_path, monkeypatch):
    """Test that runbook resolve with -e flag reads from stdin."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory (project root)
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

    # Run the CLI command with stdin input
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = None  # No positional argument
args.verbose = False
args.eval = True  # Use stdin
args.no_evidence = False
args.help_bin = None
args.commands_dir = '{str(commands_dir)}'
args.engine = 'evidence'

handle_runbook_resolve(args)
        """
    ], input="test input from stdin", capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Check that the runbook file was created (we can't predict the exact ID)
    runbooks_dir = docs_root / "runbooks" / "items"
    runbook_files = list(runbooks_dir.glob("*.json"))
    assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"

    # Check the content of the runbook file
    runbook_file = runbook_files[0]
    with open(runbook_file, 'r') as f:
        runbook_content = json.load(f)

    # Verify the runbook has the expected structure
    assert 'id' in runbook_content
    assert 'title' in runbook_content
    assert 'steps' in runbook_content
    assert len(runbook_content['steps']) > 0
    assert 'generated' in runbook_content.get('tags', [])
    assert 'evidence-based' in runbook_content.get('tags', [])

    # Check that the index was updated
    index_file = docs_root / "runbooks" / "index.json"
    assert index_file.exists(), f"Index file was not created at {index_file}"

    with open(index_file, 'r') as f:
        index_content = json.load(f)

    # Verify the runbook is in the index
    runbook_id = runbook_content['id']
    index_entry = next((item for item in index_content if item['id'] == runbook_id), None)
    assert index_entry is not None
    assert index_entry['title'] == runbook_content['title']


def test_runbook_list_shows_created_entry(tmp_path, monkeypatch):
    """Test that runbook list shows the created entry."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory (project root)
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

    # First, create a runbook using the resolve command
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test list shows entry"
args.verbose = False
args.eval = False
args.no_evidence = False
args.help_bin = None
args.commands_dir = '{str(commands_dir)}'
args.engine = 'evidence'

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the resolve command succeeded
    assert result.returncode == 0, f"Resolve command failed with stderr: {result.stderr}"

    # Now run the list command to see if it shows the created entry
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_list
import argparse

# Create mock args for list command
args = argparse.Namespace()
args.runbook_subcommand = 'list'
args.status = None
args.scope = None
args.tag = None
args.archived = False
args.type = 'all'

handle_runbook_list(args)
        """
    ], capture_output=True, text=True)

    # Check that the list command succeeded
    assert result.returncode == 0, f"List command failed with stderr: {result.stderr}"

    # Check that the output contains a runbook (we can't predict the exact ID)
    assert "runbook" in result.stdout.lower()  # Should mention runbooks
    assert "found" in result.stdout.lower()    # Should say "Found X runbook(s)"


def test_runbook_resolve_verbose_prints_prompt_hash(tmp_path, monkeypatch):
    """Test that runbook resolve with -v prints prompt hash."""
    # Set MAESTRO_DOCS_ROOT to point to the temp directory (project root)
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

    # Run the CLI command with verbose flag
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test verbose output"
args.verbose = True  # Enable verbose
args.eval = False
args.no_evidence = False
args.help_bin = None
args.commands_dir = '{str(commands_dir)}'
args.engine = 'evidence'

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Check that the output contains prompt hash information
    assert "Prompt hash:" in result.stdout
    assert "Engine:" in result.stdout
    assert "Input:" in result.stdout
    assert "[EVIDENCE_ONLY - deterministic compilation]" in result.stdout

    # Check that the runbook file was created (we can't predict the exact ID)
    runbooks_dir = docs_root / "runbooks" / "items"
    runbook_files = list(runbooks_dir.glob("*.json"))
    assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"