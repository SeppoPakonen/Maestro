"""Tests for the discuss router functionality."""

import json
from unittest.mock import Mock, patch, MagicMock
import pytest
from pathlib import Path

from maestro.ai import (
    PatchOperation,
    PatchOperationType,
    ContractType,
    TrackContract,
    PhaseContract,
    TaskContract,
    GlobalContract
)
from maestro.commands.discuss import (
    handle_discuss_command,
    handle_track_discuss,
    handle_phase_discuss,
    handle_task_discuss,
    apply_patch_operations,
    save_discussion_artifacts,
    update_artifact_status
)


def test_track_contract_operations():
    """Test that TrackContract allows correct operations."""
    # Verify allowed operations
    allowed_ops = [
        PatchOperationType.ADD_TRACK,
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ]
    
    for op in allowed_ops:
        assert op in TrackContract.allowed_operations


def test_phase_contract_operations():
    """Test that PhaseContract allows correct operations."""
    # Verify allowed operations
    allowed_ops = [
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ]
    
    for op in allowed_ops:
        assert op in PhaseContract.allowed_operations


def test_task_contract_operations():
    """Test that TaskContract allows correct operations."""
    # Verify allowed operations
    allowed_ops = [
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ]
    
    for op in allowed_ops:
        assert op in TaskContract.allowed_operations


def test_global_contract_operations():
    """Test that GlobalContract allows all operations."""
    # Verify allowed operations
    allowed_ops = [
        PatchOperationType.ADD_TRACK,
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ]
    
    for op in allowed_ops:
        assert op in GlobalContract.allowed_operations


def test_save_discussion_artifacts():
    """Test saving discussion artifacts."""
    from datetime import datetime
    
    # Create mock patch operations
    patch_ops = [
        PatchOperation(
            op_type=PatchOperationType.ADD_TASK,
            data={'task_name': 'Test task', 'phase_id': 'test-phase', 'task_id': 'test.1'}
        )
    ]
    
    # Call the function
    session_id = save_discussion_artifacts(
        initial_prompt='Test prompt',
        patch_operations=patch_ops,
        engine_name='test-engine',
        model_name='test-model',
        contract_type=ContractType.TASK
    )
    
    # Verify session ID format
    assert session_id.startswith('discuss_task_')
    
    # Check that files were created
    artifacts_dir = Path('docs/maestro/ai/artifacts')
    results_file = artifacts_dir / f'{session_id}_results.json'
    
    assert results_file.exists()
    
    # Check content of results file
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    assert data['session_id'] == session_id
    assert data['engine'] == 'test-engine'
    assert data['model'] == 'test-model'
    assert data['contract_type'] == 'task'
    assert data['initial_prompt'] == 'Test prompt'
    assert data['status'] == 'pending'
    assert len(data['patch_operations']) == 1
    assert data['patch_operations'][0]['op_type'] == 'add_task'
    assert 'transcript' in data
    
    # Clean up
    results_file.unlink()
    if artifacts_dir.exists() and not any(artifacts_dir.iterdir()):
        artifacts_dir.rmdir()


def test_update_artifact_status():
    """Test updating artifact status."""
    from datetime import datetime
    
    # Create a mock results file
    artifacts_dir = Path('docs/maestro/ai/artifacts')
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = 'test_session_123456'
    results_file = artifacts_dir / f'{session_id}_results.json'
    
    # Create initial data
    initial_data = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    with open(results_file, 'w') as f:
        json.dump(initial_data, f)
    
    # Update status
    update_artifact_status(session_id, 'applied', [{'op_type': 'add_task', 'data': {'name': 'test'}}])
    
    # Verify update
    with open(results_file, 'r') as f:
        updated_data = json.load(f)
    
    assert updated_data['status'] == 'applied'
    assert 'applied_at' in updated_data
    assert updated_data['applied_operations'] == [{'op_type': 'add_task', 'data': {'name': 'test'}}]
    
    # Clean up
    results_file.unlink()
    if artifacts_dir.exists() and not any(artifacts_dir.iterdir()):
        artifacts_dir.rmdir()


@patch('maestro.commands.discuss.run_discussion_with_router')
def test_handle_track_discuss_with_operations(mock_router):
    """Test track discuss with patch operations returned."""
    # Mock return value
    mock_ops = [
        PatchOperation(
            op_type=PatchOperationType.ADD_TASK,
            data={'task_name': 'Test task', 'phase_id': 'test-phase', 'task_id': 'test.1'}
        )
    ]
    mock_router.return_value = (mock_ops, None)
    
    # Mock args
    args = Mock()
    args.prompt = 'Test prompt'
    args.engine = 'test-engine'
    args.model = 'test-model'
    args.dry_run = True  # Skip user input
    
    # Call function
    with patch('builtins.input', return_value='n'):  # Say no to applying changes
        with patch('maestro.commands.discuss.choose_mode') as mock_choose:
            mock_choose.return_value = Mock(value='terminal')
            result = handle_track_discuss('test-track', args)
    
    # Verify router was called with correct contract
    mock_router.assert_called_once()
    assert result == 0


@patch('maestro.commands.discuss.run_discussion_with_router')
def test_handle_phase_discuss_with_operations(mock_router):
    """Test phase discuss with patch operations returned."""
    # Mock return value
    mock_ops = [
        PatchOperation(
            op_type=PatchOperationType.ADD_TASK,
            data={'task_name': 'Test task', 'phase_id': 'test-phase', 'task_id': 'test.1'}
        )
    ]
    mock_router.return_value = (mock_ops, None)
    
    # Mock args
    args = Mock()
    args.prompt = 'Test prompt'
    args.engine = 'test-engine'
    args.model = 'test-model'
    args.dry_run = True  # Skip user input
    
    # Call function
    with patch('builtins.input', return_value='n'):  # Say no to applying changes
        with patch('maestro.commands.discuss.choose_mode') as mock_choose:
            mock_choose.return_value = Mock(value='terminal')
            result = handle_phase_discuss('test-phase', args)
    
    # Verify router was called with correct contract
    mock_router.assert_called_once()
    assert result == 0


@patch('maestro.commands.discuss.run_discussion_with_router')
def test_handle_task_discuss_with_operations(mock_router):
    """Test task discuss with patch operations returned."""
    # Mock return value
    mock_ops = [
        PatchOperation(
            op_type=PatchOperationType.EDIT_TASK_FIELDS,
            data={'task_id': 'test.1', 'fields': {'status': 'done'}}
        )
    ]
    mock_router.return_value = (mock_ops, None)
    
    # Mock args
    args = Mock()
    args.prompt = 'Test prompt'
    args.engine = 'test-engine'
    args.model = 'test-model'
    args.dry_run = True  # Skip user input
    
    # Call function
    with patch('builtins.input', return_value='n'):  # Say no to applying changes
        with patch('maestro.commands.discuss.choose_mode') as mock_choose:
            mock_choose.return_value = Mock(value='terminal')
            result = handle_task_discuss('test.1', args)
    
    # Verify router was called with correct contract
    mock_router.assert_called_once()
    assert result == 0


@patch('maestro.commands.discuss.run_discussion_with_router')
def test_handle_discuss_command_with_track_context(mock_router):
    """Test general discuss command with track context."""
    # Mock return value
    mock_ops = [
        PatchOperation(
            op_type=PatchOperationType.ADD_PHASE,
            data={'phase_name': 'Test phase', 'track_id': 'test-track', 'phase_id': 'test-phase'}
        )
    ]
    mock_router.return_value = (mock_ops, None)
    
    # Mock args with track context
    args = Mock()
    args.track_id = 'test-track'
    args.phase_id = None
    args.task_id = None
    args.prompt = 'Test prompt'
    args.engine = 'test-engine'
    args.model = 'test-model'
    args.dry_run = True  # Skip user input
    
    # Call function
    with patch('builtins.input', return_value='n'):  # Say no to applying changes
        with patch('maestro.commands.discuss.choose_mode') as mock_choose:
            mock_choose.return_value = Mock(value='terminal')
            result = handle_discuss_command(args)
    
    # Verify router was called with correct contract
    mock_router.assert_called_once()
    # The first argument should be the initial prompt
    assert mock_router.call_args[1]['contract_type'] == ContractType.TRACK
    assert result == 0


@patch('maestro.commands.discuss.run_discussion_with_router')
def test_handle_discuss_command_invalid_json(mock_router, tmp_path, monkeypatch):
    """Ensure invalid JSON stops apply and returns non-zero."""
    mock_router.return_value = ([], "Invalid JSON payload")

    args = Mock()
    args.track_id = None
    args.phase_id = None
    args.task_id = None
    args.prompt = 'Test prompt'
    args.engine = 'test-engine'
    args.model = 'test-model'
    args.dry_run = True

    monkeypatch.chdir(tmp_path)

    with patch('maestro.commands.discuss.choose_mode') as mock_choose:
        mock_choose.return_value = Mock(value='terminal')
        result = handle_discuss_command(args)

    assert result == 1


def test_apply_patch_operations_add_task():
    """Test applying ADD_TASK patch operation."""
    # Create mock patch operation
    patch_op = PatchOperation(
        op_type=PatchOperationType.ADD_TASK,
        data={
            'task_name': 'Test Task',
            'task_id': 'test.1',
            'phase_id': 'test-phase'
        }
    )
    
    # Create a temporary phase file
    phase_file = Path('docs/phases/test-phase.md')
    phase_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write minimal content to the phase file
    phase_content = f"""# Phase test-phase: Test Phase 📋 **[Planned]**

- *phase_id*: *test-phase*
- *status*: *planned*
- *completion*: 0

## Tasks

"""
    phase_file.write_text(phase_content)
    
    try:
        # Apply the patch
        apply_patch_operations([patch_op])
        
        # Verify the task was added to the file
        content = phase_file.read_text()
        assert 'Test Task' in content
        assert 'test.1' in content
    finally:
        # Clean up
        if phase_file.exists():
            phase_file.unlink()
        if phase_file.parent.exists() and not any(phase_file.parent.iterdir()):
            phase_file.parent.rmdir()


def test_apply_patch_operations_mark_done():
    """Test applying MARK_DONE patch operation."""
    # Create mock patch operation
    patch_op = PatchOperation(
        op_type=PatchOperationType.MARK_DONE,
        data={
            'item_type': 'task',
            'item_id': 'test.1'
        }
    )
    
    # This test will verify that the function doesn't crash
    # The actual implementation would need to update task status
    # which requires finding the task in a file
    apply_patch_operations([patch_op])


def test_apply_patch_operations_add_track():
    """Test applying ADD_TRACK patch operation."""
    # Create mock patch operation
    patch_op = PatchOperation(
        op_type=PatchOperationType.ADD_TRACK,
        data={
            'track_name': 'Test Track',
            'track_id': 'test-track'
        }
    )
    
    # Create a temporary todo file
    todo_file = Path('docs/todo.md')
    todo_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write minimal content to the todo file
    todo_content = """# Maestro Development TODO

**Last Updated**: 2023-01-01

---
"""
    todo_file.write_text(todo_content)
    
    try:
        # Apply the patch
        apply_patch_operations([patch_op])
        
        # Verify the track was added to the file
        content = todo_file.read_text()
        assert 'Test Track' in content
        assert 'test-track' in content
    finally:
        # Clean up
        if todo_file.exists():
            todo_file.unlink()
        if todo_file.parent.exists() and not any(todo_file.parent.iterdir()):
            todo_file.parent.rmdir()


if __name__ == '__main__':
    pytest.main([__file__])
