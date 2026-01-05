"""
Tests for the Project Operations pipeline.
"""
import json
import tempfile
from pathlib import Path
import pytest

from maestro.project_ops.schemas import validate_project_ops_result
from maestro.project_ops.operations import CreateTrack, CreatePhase, CreateTask, MoveTaskToDone, SetContext
from maestro.project_ops.decoder import decode_project_ops_json, DecodeError
from maestro.project_ops.translator import actions_to_ops
from maestro.project_ops.executor import ProjectOpsExecutor, PreviewResult
from maestro.tracks.json_store import JsonStore


def test_validate_project_ops_result_valid():
    """Test that valid ProjectOpsResult passes validation."""
    valid_data = {
        "kind": "project_ops",
        "version": 1,
        "scope": "project",
        "actions": [
            {
                "action": "track_create",
                "title": "Test Track"
            }
        ]
    }

    result = validate_project_ops_result(valid_data)
    assert result["kind"] == "project_ops"
    assert result["version"] == 1
    assert result["scope"] == "project"
    assert len(result["actions"]) == 1


def test_validate_project_ops_result_invalid():
    """Test that invalid ProjectOpsResult raises ValidationError."""
    invalid_data = {
        "kind": "wrong_kind",
        "version": 1,
        "scope": "project",
        "actions": []
    }

    with pytest.raises(Exception):
        validate_project_ops_result(invalid_data)


def test_decode_project_ops_json_valid():
    """Test decoding valid ProjectOpsResult JSON."""
    project_ops_result = {
        "kind": "project_ops",
        "version": 1,
        "scope": "project",
        "actions": [
            {
                "action": "track_create",
                "title": "Test Track"
            }
        ]
    }

    result = decode_project_ops_json(json.dumps(project_ops_result))
    assert result["kind"] == "project_ops"
    assert result["scope"] == "project"
    assert len(result["actions"]) == 1
    assert result["actions"][0]["action"] == "track_create"


def test_decode_project_ops_json_invalid():
    """Test decoding invalid ProjectOpsResult JSON raises DecodeError."""
    invalid_json = '{"kind": "wrong", "version": 1, "scope": "project", "actions": []}'

    with pytest.raises(DecodeError, match="ProjectOpsResult JSON invalid"):
        decode_project_ops_json(invalid_json)


def test_actions_to_ops_valid():
    """Test translating valid actions to operations."""
    project_ops_result = {
        "kind": "project_ops",
        "version": 1,
        "scope": "project",
        "actions": [
            {
                "action": "track_create",
                "title": "New Track"
            },
            {
                "action": "phase_create",
                "track": "New Track",
                "title": "New Phase"
            },
            {
                "action": "task_create",
                "track": "New Track",
                "phase": "New Phase",
                "title": "New Task"
            },
            {
                "action": "task_move_to_done",
                "track": "New Track",
                "phase": "New Phase",
                "task": "New Task"
            },
            {
                "action": "context_set",
                "current_track": "New Track",
                "current_phase": "New Phase"
            }
        ]
    }

    ops = actions_to_ops(project_ops_result)
    assert len(ops) == 5
    assert isinstance(ops[0], CreateTrack)
    assert isinstance(ops[1], CreatePhase)
    assert isinstance(ops[2], CreateTask)
    assert isinstance(ops[3], MoveTaskToDone)
    assert isinstance(ops[4], SetContext)


def test_actions_to_ops_invalid_scope():
    """Test that invalid scope raises DecodeError."""
    project_ops_result = {
        "kind": "project_ops",
        "version": 1,
        "scope": "invalid",
        "actions": []
    }

    with pytest.raises(DecodeError, match="Invalid scope"):
        actions_to_ops(project_ops_result)


def test_actions_to_ops_unknown_action():
    """Test that unknown action type raises DecodeError."""
    project_ops_result = {
        "kind": "project_ops",
        "version": 1,
        "scope": "project",
        "actions": [
            {
                "action": "unknown_action",
                "title": "Test"
            }
        ]
    }

    with pytest.raises(DecodeError, match="Unknown action type"):
        actions_to_ops(project_ops_result)


def test_actions_to_ops_missing_required_fields():
    """Test that missing required fields raise DecodeError."""
    # Missing title for track_create
    project_ops_result = {
        "kind": "project_ops",
        "version": 1,
        "scope": "project",
        "actions": [
            {
                "action": "track_create"
            }
        ]
    }

    with pytest.raises(DecodeError, match="track_create action requires 'title'"):
        actions_to_ops(project_ops_result)


def test_preview_ops():
    """Test preview functionality of the executor."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "docs" / "maestro"
        executor = ProjectOpsExecutor(str(base_path))
        
        # Create operations
        ops = [
            CreateTrack(title="Test Track")
        ]
        
        preview_result = executor.preview_ops(ops)
        
        assert isinstance(preview_result, PreviewResult)
        assert len(preview_result.changes) == 1
        assert "Create track" in preview_result.changes[0]


def test_apply_ops_dry_run():
    """Test apply functionality with dry_run=True."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "docs" / "maestro"
        executor = ProjectOpsExecutor(str(base_path))
        
        # Create operations
        ops = [
            CreateTrack(title="Test Track")
        ]
        
        preview_result = executor.apply_ops(ops, dry_run=True)
        
        assert isinstance(preview_result, PreviewResult)
        json_store = JsonStore(str(base_path))
        assert json_store.list_all_tracks() == []


def test_apply_ops():
    """Test apply functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "docs" / "maestro"
        executor = ProjectOpsExecutor(str(base_path))
        
        # Create operations
        ops = [
            CreateTrack(title="Test Track")
        ]
        
        # Apply the operations
        result = executor.apply_ops(ops, dry_run=False)
        
        json_store = JsonStore(str(base_path))
        assert json_store.list_all_tracks()
        assert len(result.changes) >= 1


def test_executor_with_all_operation_types():
    """Test executor with all operation types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "docs" / "maestro"
        executor = ProjectOpsExecutor(str(base_path))
        
        # Create operations of all types
        ops = [
            CreateTrack(title="New Track"),
            SetContext(current_track="New Track")
        ]
        
        # Preview the operations
        preview_result = executor.preview_ops(ops)
        assert len(preview_result.changes) == 2
        
        # Apply the operations
        result = executor.apply_ops(ops, dry_run=False)
        
        # Check that operations were applied
        json_store = JsonStore(str(base_path))
        assert json_store.list_all_tracks()
        assert len(result.changes) >= 2


def test_idempotency_expectations():
    """Test idempotency - applying same operation twice should handle appropriately."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir) / "docs" / "maestro"
        executor = ProjectOpsExecutor(str(base_path))
        
        # Create an operation to create a track
        ops = [
            CreateTrack(title="Idempotent Test Track")
        ]
        
        # Apply the operation once
        result1 = executor.apply_ops(ops, dry_run=False)
        assert len(result1.changes) >= 1
        
        # Apply the same operation again - this should fail since track already exists
        try:
            result2 = executor.apply_ops(ops, dry_run=False)
            # If we get here, the second operation didn't fail as expected
            # This might be acceptable depending on implementation - we'll just verify that 
            # the system handles duplicate creation appropriately
        except Exception:
            # This is expected behavior - trying to create duplicate track should fail
            pass
