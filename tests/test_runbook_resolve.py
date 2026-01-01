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
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))
    
    # Define a fake resolver for deterministic output
    def fake_resolver(text, verbose=False):
        return {
            "id": "rb-test-runbook-creation-12345678",
            "title": "Test runbook creation",
            "goal": "Test runbook creation",
            "steps": [
                {
                    "cmd": "echo hi",
                    "expect": "Command executes successfully",
                    "notes": "n"
                }
            ],
            "tags": ["generated"],
            "status": "proposed",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    
    # Mock the resolver by patching the function
    # We'll do this by temporarily modifying the sys.path and importing the module
    # to patch the function directly
    
    # Run the CLI command
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

# Patch the create_runbook_from_freeform function before importing
import maestro.commands.runbook
original_resolver = maestro.commands.runbook.create_runbook_from_freeform

def mock_resolver(text, verbose=False):
    return {{
        "id": "rb-test-runbook-creation-12345678",
        "title": "Test runbook creation",
        "goal": "Test runbook creation",
        "steps": [
            {{
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }}
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }}

maestro.commands.runbook.create_runbook_from_freeform = mock_resolver

# Now import and run the command
from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "freeform"
args.verbose = False
args.eval = False

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True)
    
    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
    
    # Check that the runbook file was created
    runbook_file = docs_root / "runbooks" / "items" / "rb-test-runbook-creation-12345678.json"
    assert runbook_file.exists(), f"Runbook file was not created at {runbook_file}"
    
    # Check the content of the runbook file
    with open(runbook_file, 'r') as f:
        runbook_content = json.load(f)
    
    expected_runbook = {
        "id": "rb-test-runbook-creation-12345678",
        "title": "Test runbook creation",
        "goal": "Test runbook creation",
        "steps": [
            {
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }
    
    assert runbook_content == expected_runbook
    
    # Check that the index was updated
    index_file = docs_root / "runbooks" / "index.json"
    assert index_file.exists(), f"Index file was not created at {index_file}"
    
    with open(index_file, 'r') as f:
        index_content = json.load(f)
    
    expected_index_entry = {
        "id": "rb-test-runbook-creation-12345678",
        "title": "Test runbook creation",
        "tags": ["generated"],
        "status": "proposed",
        "updated_at": "2026-01-01T00:00:00"
    }
    
    assert expected_index_entry in index_content


def test_runbook_resolve_eval_reads_stdin(tmp_path, monkeypatch):
    """Test that runbook resolve with -e flag reads from stdin."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))
    
    # Run the CLI command with stdin input
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

# Patch the create_runbook_from_freeform function
import maestro.commands.runbook
original_resolver = maestro.commands.runbook.create_runbook_from_freeform

def mock_resolver(text, verbose=False):
    # Verify that the text from stdin was passed correctly
    assert text == "test input from stdin"
    return {{
        "id": "rb-test-runbook-from-stdin-87654321",
        "title": "Test runbook from stdin",
        "goal": "Test runbook from stdin",
        "steps": [
            {{
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }}
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }}

maestro.commands.runbook.create_runbook_from_freeform = mock_resolver

# Now import and run the command
from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = None  # No positional argument
args.verbose = False
args.eval = True  # Use stdin

handle_runbook_resolve(args)
        """
    ], input="test input from stdin", capture_output=True, text=True)
    
    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
    
    # Check that the runbook file was created
    runbook_file = docs_root / "runbooks" / "items" / "rb-test-runbook-from-stdin-87654321.json"
    assert runbook_file.exists(), f"Runbook file was not created at {runbook_file}"
    
    # Check the content of the runbook file
    with open(runbook_file, 'r') as f:
        runbook_content = json.load(f)
    
    expected_runbook = {
        "id": "rb-test-runbook-from-stdin-87654321",
        "title": "Test runbook from stdin",
        "goal": "Test runbook from stdin",
        "steps": [
            {
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }
    
    assert runbook_content == expected_runbook
    
    # Check that the index was updated
    index_file = docs_root / "runbooks" / "index.json"
    assert index_file.exists(), f"Index file was not created at {index_file}"
    
    with open(index_file, 'r') as f:
        index_content = json.load(f)
    
    expected_index_entry = {
        "id": "rb-test-runbook-from-stdin-87654321",
        "title": "Test runbook from stdin",
        "tags": ["generated"],
        "status": "proposed",
        "updated_at": "2026-01-01T00:00:00"
    }
    
    assert expected_index_entry in index_content


def test_runbook_list_shows_created_entry(tmp_path, monkeypatch):
    """Test that runbook list shows the created entry."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))
    
    # First, create a runbook using the resolve command
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

# Patch the create_runbook_from_freeform function
import maestro.commands.runbook
original_resolver = maestro.commands.runbook.create_runbook_from_freeform

def mock_resolver(text, verbose=False):
    return {{
        "id": "rb-test-list-shows-entry-11223344",
        "title": "Test list shows entry",
        "goal": "Test that list command shows created entry",
        "steps": [
            {{
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }}
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }}

maestro.commands.runbook.create_runbook_from_freeform = mock_resolver

# Now import and run the command
from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test list shows entry"
args.verbose = False
args.eval = False

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True)
    
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
    
    # Check that the output contains the created runbook
    assert "rb-test-list-shows-entry-11223344" in result.stdout
    assert "Test list shows entry" in result.stdout


def test_runbook_resolve_verbose_prints_prompt_hash(tmp_path, monkeypatch):
    """Test that runbook resolve with -v prints prompt hash."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))
    
    # Run the CLI command with verbose flag
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent.parent)}')

# Patch the create_runbook_from_freeform function
import maestro.commands.runbook
original_resolver = maestro.commands.runbook.create_runbook_from_freeform

def mock_resolver(text, verbose=False):
    return {{
        "id": "rb-test-verbose-output-55667788",
        "title": "Test verbose output",
        "goal": "Test verbose output",
        "steps": [
            {{
                "cmd": "echo hi",
                "expect": "Command executes successfully",
                "notes": "n"
            }}
        ],
        "tags": ["generated"],
        "status": "proposed",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00"
    }}

maestro.commands.runbook.create_runbook_from_freeform = mock_resolver

# Now import and run the command
from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test verbose output"
args.verbose = True  # Enable verbose
args.eval = False

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True)
    
    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
    
    # Check that the output contains prompt hash information
    assert "Prompt hash:" in result.stdout
    assert "Engine:" in result.stdout
    assert "Input:" in result.stdout
    
    # Check that the runbook file was created
    runbook_file = docs_root / "runbooks" / "items" / "rb-test-verbose-output-55667788.json"
    assert runbook_file.exists(), f"Runbook file was not created at {runbook_file}"