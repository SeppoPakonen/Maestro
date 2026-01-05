"""
Tests for the new runbook resolve command functionality with evidence collection.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


def test_runbook_resolve_with_evidence_collection(tmp_path, monkeypatch):
    """Test that runbook resolve with evidence collection works properly."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))

    # Create a commands directory with a sample file
    commands_dir = tmp_path / "docs" / "commands"
    commands_dir.mkdir(parents=True)
    
    # Create a sample command documentation file
    sample_doc = commands_dir / "sample_command.md"
    sample_doc.write_text("# Sample Command\n\nThis command does something useful.\n")

    # Run the CLI command with evidence collection
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent)}')

from maestro.commands.runbook import handle_runbook_resolve, collect_repo_evidence
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test runbook with evidence collection"
args.verbose = True
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
    assert "Created/updated runbook:" in result.stdout
    assert "[EVIDENCE_ONLY - deterministic compilation]" in result.stdout

    # Find the runbook file that was created (we can't predict the exact ID)
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
    assert 'evidence-based' in runbook_content.get('tags', [])

    # Verify that the steps include evidence-based content
    steps = runbook_content['steps']
    assert len(steps) >= 2  # At least verify help + command doc step
    
    # Check that the first step is about verifying help
    first_step = steps[0]
    assert 'Verify CLI help is available' in first_step['action']
    
    # Check that there's a step for the command doc we created
    command_steps = [step for step in steps if 'sample_command.md' in step['action']]
    assert len(command_steps) >= 1

    # Check that the index was updated
    index_file = docs_root / "runbooks" / "index.json"
    assert index_file.exists(), f"Index file was not created at {index_file}"

    with open(index_file, 'r') as f:
        index_content = json.load(f)

    # Verify the runbook is in the index
    runbook_id = runbook_content['id']
    index_entry = next((item for item in index_content if item['id'] == runbook_id), None)
    assert index_entry is not None


def test_runbook_resolve_no_evidence_flag(tmp_path, monkeypatch):
    """Test that runbook resolve works with --no-evidence flag."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))

    # Run the CLI command with no evidence flag
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test runbook without evidence"
args.verbose = False
args.eval = False
args.no_evidence = True  # No evidence collection
args.help_bin = None
args.commands_dir = None
args.engine = 'evidence'

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
    assert "Created/updated runbook:" in result.stdout

    # Find the runbook file that was created
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
    assert len(runbook_content['steps']) >= 1

    # Verify that the runbook was created with basic steps
    steps = runbook_content['steps']
    assert len(steps) >= 1
    assert steps[0]['action'] == 'Implement steps based on requirements'


def test_runbook_resolve_with_test_fake_engine(tmp_path, monkeypatch):
    """Test that FAKE_ENGINE banner appears only when MAESTRO_TEST_FAKE_ENGINE is set."""
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    docs_root = tmp_path / "docs" / "maestro"
    monkeypatch.setenv('MAESTRO_DOCS_ROOT', str(docs_root))
    monkeypatch.setenv('MAESTRO_TEST_FAKE_ENGINE', '1')  # Enable test fake engine

    # Run the CLI command with verbose output
    result = subprocess.run([
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, '{str(Path(__file__).parent)}')

from maestro.commands.runbook import handle_runbook_resolve
import argparse

# Create mock args
args = argparse.Namespace()
args.text = "test fake engine banner"
args.verbose = True  # Enable verbose to see engine info
args.eval = False
args.no_evidence = True
args.help_bin = None
args.commands_dir = None
args.engine = 'auto'  # Auto should use fake engine when env var is set

handle_runbook_resolve(args)
        """
    ], capture_output=True, text=True, cwd=str(tmp_path))

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
    assert "Created/updated runbook:" in result.stdout
    # Should show FAKE_ENGINE banner because env var is set
    assert "[FAKE_ENGINE - for testing purposes]" in result.stdout

    # Find the runbook file that was created
    runbooks_dir = docs_root / "runbooks" / "items"
    runbook_files = list(runbooks_dir.glob("*.json"))
    assert len(runbook_files) == 1, f"Expected 1 runbook file, found {len(runbook_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])