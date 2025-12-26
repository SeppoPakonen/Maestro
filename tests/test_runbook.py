"""
Unit tests for runbook command.
"""
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest import mock
import sys
import argparse

# Import the runbook command handlers
from maestro.commands.runbook import (
    _get_runbook_storage_path,
    _ensure_runbook_storage,
    _load_index,
    _save_index,
    _load_runbook,
    _save_runbook,
    _generate_runbook_id,
    handle_runbook_add,
    handle_runbook_list,
    handle_runbook_show,
    handle_runbook_edit,
    handle_runbook_rm,
    handle_step_add,
    handle_step_edit,
    handle_step_rm,
    handle_step_renumber,
    handle_runbook_export,
    _export_runbook_md,
    _export_runbook_puml,
)


@pytest.fixture
def temp_runbook_dir(monkeypatch):
    """Create a temporary directory for runbook testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Mock Path.cwd() to return our temp directory
    monkeypatch.setattr(Path, 'cwd', lambda: temp_path)

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir)


def test_ensure_runbook_storage(temp_runbook_dir):
    """Test that runbook storage directories are created properly."""
    _ensure_runbook_storage()

    storage_path = temp_runbook_dir / "docs" / "maestro" / "runbooks"
    assert storage_path.exists()
    assert (storage_path / "items").exists()
    assert (storage_path / "exports").exists()


def test_generate_runbook_id():
    """Test runbook ID generation."""
    with mock.patch('maestro.commands.runbook._load_index', return_value=[]):
        runbook_id = _generate_runbook_id("User Authentication Flow")
        assert runbook_id == "user-authentication-flow"

        # Test with special characters
        runbook_id = _generate_runbook_id("API v2.0 Integration!")
        assert runbook_id == "api-v20-integration"


def test_generate_runbook_id_conflict():
    """Test runbook ID generation with conflicts."""
    existing = [{'id': 'test-runbook'}]
    with mock.patch('maestro.commands.runbook._load_index', return_value=existing):
        runbook_id = _generate_runbook_id("Test Runbook")
        assert runbook_id == "test-runbook-1"


def test_runbook_add(temp_runbook_dir, capsys):
    """Test creating a runbook."""
    args = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test", "demo"],
        source_program=None,
        target_project=None
    )

    handle_runbook_add(args)

    # Check output
    captured = capsys.readouterr()
    assert "Created runbook: test-runbook" in captured.out

    # Verify files were created
    storage_path = temp_runbook_dir / "docs" / "maestro" / "runbooks"
    assert (storage_path / "index.json").exists()
    assert (storage_path / "items" / "test-runbook.json").exists()

    # Load and verify index
    index = _load_index()
    assert len(index) == 1
    assert index[0]['id'] == 'test-runbook'
    assert index[0]['title'] == 'Test Runbook'
    assert index[0]['tags'] == ["test", "demo"]

    # Load and verify runbook
    runbook = _load_runbook('test-runbook')
    assert runbook is not None
    assert runbook['title'] == 'Test Runbook'
    assert runbook['scope'] == 'product'
    assert runbook['status'] == 'proposed'
    assert runbook['tags'] == ["test", "demo"]


def test_runbook_list_empty(temp_runbook_dir, capsys):
    """Test listing runbooks when none exist."""
    args = argparse.Namespace(status=None, scope=None, tag=None)
    handle_runbook_list(args)

    captured = capsys.readouterr()
    assert "No runbooks found" in captured.out


def test_runbook_list(temp_runbook_dir, capsys):
    """Test listing runbooks."""
    # Create a runbook first
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="user",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # List runbooks
    args_list = argparse.Namespace(status=None, scope=None, tag=None)
    handle_runbook_list(args_list)

    captured = capsys.readouterr()
    assert "Found 1 runbook(s)" in captured.out
    assert "test-runbook" in captured.out
    assert "Test Runbook" in captured.out


def test_runbook_show(temp_runbook_dir, capsys):
    """Test showing a runbook."""
    # Create a runbook first
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Show the runbook
    args_show = argparse.Namespace(id="test-runbook")
    handle_runbook_show(args_show)

    captured = capsys.readouterr()
    assert "Runbook: Test Runbook" in captured.out
    assert "ID: test-runbook" in captured.out
    assert "Status: proposed" in captured.out


def test_runbook_show_not_found(temp_runbook_dir, capsys):
    """Test showing a non-existent runbook."""
    args_show = argparse.Namespace(id="nonexistent")
    handle_runbook_show(args_show)

    captured = capsys.readouterr()
    assert "Error: Runbook 'nonexistent' not found" in captured.out


def test_runbook_edit(temp_runbook_dir, capsys):
    """Test editing a runbook."""
    # Create a runbook first
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Edit the runbook
    args_edit = argparse.Namespace(
        id="test-runbook",
        title="Updated Runbook",
        status="approved",
        scope="user",
        tag=["updated"]
    )
    handle_runbook_edit(args_edit)

    captured = capsys.readouterr()
    assert "Updated runbook: test-runbook" in captured.out

    # Verify changes
    runbook = _load_runbook('test-runbook')
    assert runbook['title'] == 'Updated Runbook'
    assert runbook['status'] == 'approved'
    assert runbook['scope'] == 'user'
    assert 'updated' in runbook['tags']


def test_runbook_rm_with_force(temp_runbook_dir, capsys):
    """Test removing a runbook with --force flag."""
    # Create a runbook first
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Remove with force
    args_rm = argparse.Namespace(id="test-runbook", force=True)
    handle_runbook_rm(args_rm)

    captured = capsys.readouterr()
    assert "Deleted runbook: test-runbook" in captured.out

    # Verify deletion
    runbook = _load_runbook('test-runbook')
    assert runbook is None

    index = _load_index()
    assert len(index) == 0


def test_step_add(temp_runbook_dir, capsys):
    """Test adding a step to a runbook."""
    # Create a runbook first
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Add a step
    args_step = argparse.Namespace(
        id="test-runbook",
        actor="user",
        action="Navigate to login page",
        expected="Login form is displayed",
        details="User clicks on login button",
        variants=["via mobile app", "via web browser"]
    )
    handle_step_add(args_step)

    captured = capsys.readouterr()
    assert "Added step 1 to runbook test-runbook" in captured.out

    # Verify step
    runbook = _load_runbook('test-runbook')
    assert len(runbook['steps']) == 1
    step = runbook['steps'][0]
    assert step['n'] == 1
    assert step['actor'] == 'user'
    assert step['action'] == 'Navigate to login page'
    assert step['expected'] == 'Login form is displayed'
    assert step['details'] == 'User clicks on login button'
    assert step['variants'] == ['via mobile app', 'via web browser']


def test_step_edit(temp_runbook_dir, capsys):
    """Test editing a step in a runbook."""
    # Create runbook and add step
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    args_step_add = argparse.Namespace(
        id="test-runbook",
        actor="user",
        action="Navigate to login page",
        expected="Login form is displayed",
        details=None,
        variants=None
    )
    handle_step_add(args_step_add)

    # Edit the step
    args_step_edit = argparse.Namespace(
        id="test-runbook",
        n=1,
        actor="system",
        action="Display login form",
        expected="Form is visible",
        details="Render login UI"
    )
    handle_step_edit(args_step_edit)

    captured = capsys.readouterr()
    assert "Updated step 1 in runbook test-runbook" in captured.out

    # Verify changes
    runbook = _load_runbook('test-runbook')
    step = runbook['steps'][0]
    assert step['actor'] == 'system'
    assert step['action'] == 'Display login form'
    assert step['expected'] == 'Form is visible'


def test_step_rm(temp_runbook_dir, capsys):
    """Test removing a step from a runbook."""
    # Create runbook and add steps
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    for i in range(3):
        args_step = argparse.Namespace(
            id="test-runbook",
            actor="user",
            action=f"Action {i+1}",
            expected=f"Expected {i+1}",
            details=None,
            variants=None
        )
        handle_step_add(args_step)

    # Remove middle step
    args_step_rm = argparse.Namespace(id="test-runbook", n=2)
    handle_step_rm(args_step_rm)

    captured = capsys.readouterr()
    assert "Removed step 2 from runbook test-runbook" in captured.out

    # Verify renumbering
    runbook = _load_runbook('test-runbook')
    assert len(runbook['steps']) == 2
    assert runbook['steps'][0]['n'] == 1
    assert runbook['steps'][0]['action'] == 'Action 1'
    assert runbook['steps'][1]['n'] == 2
    assert runbook['steps'][1]['action'] == 'Action 3'


def test_step_renumber(temp_runbook_dir, capsys):
    """Test renumbering steps in a runbook."""
    # Create runbook and add steps
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    for i in range(3):
        args_step = argparse.Namespace(
            id="test-runbook",
            actor="user",
            action=f"Action {i+1}",
            expected=f"Expected {i+1}",
            details=None,
            variants=None
        )
        handle_step_add(args_step)

    # Manually break numbering (simulate)
    runbook = _load_runbook('test-runbook')
    runbook['steps'][0]['n'] = 5
    runbook['steps'][1]['n'] = 10
    runbook['steps'][2]['n'] = 15
    _save_runbook(runbook)

    # Renumber
    args_renumber = argparse.Namespace(id="test-runbook")
    handle_step_renumber(args_renumber)

    captured = capsys.readouterr()
    assert "Renumbered 3 steps in runbook test-runbook" in captured.out

    # Verify renumbering
    runbook = _load_runbook('test-runbook')
    assert runbook['steps'][0]['n'] == 1
    assert runbook['steps'][1]['n'] == 2
    assert runbook['steps'][2]['n'] == 3


def test_export_markdown(temp_runbook_dir):
    """Test exporting a runbook to Markdown."""
    # Create a complete runbook
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    args_step = argparse.Namespace(
        id="test-runbook",
        actor="user",
        action="Navigate to login page",
        expected="Login form is displayed",
        details="User clicks on login button",
        variants=["via mobile app"]
    )
    handle_step_add(args_step)

    # Load runbook and export
    runbook = _load_runbook('test-runbook')
    md_content = _export_runbook_md(runbook)

    assert "# Runbook: Test Runbook" in md_content
    assert "**ID:** test-runbook" in md_content
    assert "## Steps" in md_content
    assert "### Step 1: Navigate to login page" in md_content
    assert "**Actor:** user" in md_content
    assert "**Expected:** Login form is displayed" in md_content


def test_export_puml(temp_runbook_dir):
    """Test exporting a runbook to PlantUML."""
    # Create a complete runbook
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    args_step = argparse.Namespace(
        id="test-runbook",
        actor="user",
        action="Navigate to login page",
        expected="Login form is displayed",
        details=None,
        variants=None
    )
    handle_step_add(args_step)

    # Load runbook and export
    runbook = _load_runbook('test-runbook')
    puml_content = _export_runbook_puml(runbook)

    assert "@startuml" in puml_content
    assert "title Runbook: Test Runbook" in puml_content
    assert ":Navigate to login page|user;" in puml_content
    assert "note right: Login form is displayed" in puml_content
    assert "@enduml" in puml_content


def test_export_command_md(temp_runbook_dir, capsys):
    """Test the export command with Markdown format."""
    # Create runbook
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Export
    args_export = argparse.Namespace(
        id="test-runbook",
        format="md",
        out=None
    )
    handle_runbook_export(args_export)

    captured = capsys.readouterr()
    assert "Exported runbook test-runbook" in captured.out

    # Verify file exists
    export_path = temp_runbook_dir / "docs" / "maestro" / "runbooks" / "exports" / "test-runbook.md"
    assert export_path.exists()


def test_export_command_puml(temp_runbook_dir, capsys):
    """Test the export command with PlantUML format."""
    # Create runbook
    args_add = argparse.Namespace(
        title="Test Runbook",
        scope="product",
        tag=["test"],
        source_program=None,
        target_project=None
    )
    handle_runbook_add(args_add)

    # Export
    args_export = argparse.Namespace(
        id="test-runbook",
        format="puml",
        out=None
    )
    handle_runbook_export(args_export)

    captured = capsys.readouterr()
    assert "Exported runbook test-runbook" in captured.out

    # Verify file exists
    export_path = temp_runbook_dir / "docs" / "maestro" / "runbooks" / "exports" / "test-runbook.puml"
    assert export_path.exists()


def test_context_fields(temp_runbook_dir):
    """Test that context fields are saved correctly."""
    args_add = argparse.Namespace(
        title="Reverse Engineering Runbook",
        scope="reverse_engineering",
        tag=["re"],
        source_program="Legacy App v1.2",
        target_project="New Modern App"
    )
    handle_runbook_add(args_add)

    runbook = _load_runbook('reverse-engineering-runbook')
    assert runbook['context']['source_program'] == "Legacy App v1.2"
    assert runbook['context']['target_project'] == "New Modern App"
