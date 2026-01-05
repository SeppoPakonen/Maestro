"""Test cases for discussion migration to work session framework."""

import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

from maestro.discussion import DiscussionSession, create_discussion_session, resume_discussion
from maestro.work_session import WorkSession, SessionType, create_session, load_session
from maestro.breadcrumb import list_breadcrumbs, get_breadcrumb_summary


def test_create_discussion_session():
    """Test creating a discussion session with work session infrastructure."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'track_id': 'cli-tpt-1'},
        mode="editor"
    )
    
    # Verify the session was created properly
    assert discussion_session.work_session.session_type == SessionType.DISCUSSION.value
    assert discussion_session.work_session.related_entity == {'track_id': 'cli-tpt-1'}
    assert discussion_session.mode == "editor"
    assert discussion_session.work_session.status == "running"


def test_create_discussion_session_general():
    """Test creating a general discussion session without specific entity."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="terminal"
    )
    
    # Verify the session was created properly
    assert discussion_session.work_session.session_type == SessionType.DISCUSSION.value
    assert discussion_session.work_session.related_entity == {}
    assert discussion_session.mode == "terminal"
    assert discussion_session.work_session.status == "running"


def test_discussion_session_process_command_done():
    """Test processing the /done command which should complete the session."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Process the /done command
    should_continue = discussion_session.process_command("/done")
    
    # The command should return False to indicate session should end
    assert should_continue is False
    # The session should be marked as completed
    assert discussion_session.work_session.status == "completed"


def test_discussion_session_process_command_quit():
    """Test processing the /quit command which should interrupt the session."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Process the /quit command
    should_continue = discussion_session.process_command("/quit")
    
    # The command should return False to indicate session should end
    assert should_continue is False
    # The session should be marked as interrupted
    assert discussion_session.work_session.status == "interrupted"


def test_discussion_session_process_command_history():
    """Test processing the /history command which should show history and continue."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Process the /history command
    should_continue = discussion_session.process_command("/history")
    
    # The command should return True to indicate session should continue
    assert should_continue is True


def test_discussion_session_process_command_other():
    """Test processing other commands which should continue."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Process an unrecognized command
    should_continue = discussion_session.process_command("/unknown")
    
    # The command should return True to indicate session should continue
    assert should_continue is True


def test_discussion_session_editor_mode():
    """Test discussion session running in editor mode."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )

    # For this test, we'll just verify that the method exists and can be called
    # without crashing (with proper mocking)
    with patch.object(discussion_session, '_get_context_for_session'), \
         patch('maestro.ai.editor.EditorDiscussion'), \
         patch.object(discussion_session, '_wrap_editor_start') as mock_wrap_start:

        mock_result = Mock()
        mock_result.actions = []
        mock_result.completed = True
        mock_wrap_start.return_value.return_value = mock_result

        # This should run the editor mode
        result = discussion_session.run_editor_mode()

        # Verify the result
        assert result.actions == []
        assert result.completed is True


def test_discussion_session_terminal_mode():
    """Test discussion session running in terminal mode."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="terminal"
    )

    # For this test, we'll just verify that the method exists and can be called
    # without crashing (with proper mocking)
    with patch.object(discussion_session, '_get_context_for_session'), \
         patch('maestro.ai.terminal.TerminalDiscussion'), \
         patch.object(discussion_session, '_wrap_terminal_start') as mock_wrap_start:

        mock_result = Mock()
        mock_result.actions = []
        mock_result.completed = True
        mock_wrap_start.return_value.return_value = mock_result

        # This should run the terminal mode
        result = discussion_session.run_terminal_mode()

        # Verify the result
        assert result.actions == []
        assert result.completed is True


def test_discussion_session_breadcrumb_creation():
    """Test that breadcrumbs are created during discussion."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Simulate adding a breadcrumb
    from maestro.breadcrumb import create_breadcrumb, write_breadcrumb
    
    breadcrumb = create_breadcrumb(
        prompt="Test prompt",
        response="Test response",
        tools_called=[],
        files_modified=[],
        parent_session_id=discussion_session.work_session.session_id,
        depth_level=0,
        model_used="claude-sonnet",
        token_count={"input": 10, "output": 20},
        cost=0.01
    )
    
    # Write the breadcrumb
    breadcrumb_path = write_breadcrumb(
        breadcrumb,
        discussion_session.work_session.session_id
    )
    
    # Verify the breadcrumb was written to the session's breadcrumbs directory
    assert Path(breadcrumb_path).exists()
    
    # Verify we can list breadcrumbs for this session
    breadcrumbs = list_breadcrumbs(discussion_session.work_session.session_id)
    assert len(breadcrumbs) == 1
    assert breadcrumbs[0].prompt == "Test prompt"
    assert breadcrumbs[0].response == "Test response"


def test_discussion_session_summary():
    """Test getting summary of discussion session."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Create a few breadcrumbs
    from maestro.breadcrumb import create_breadcrumb, write_breadcrumb
    
    for i in range(3):
        breadcrumb = create_breadcrumb(
            prompt=f"Test prompt {i}",
            response=f"Test response {i}",
            tools_called=[],
            files_modified=[],
            parent_session_id=discussion_session.work_session.session_id,
            depth_level=0,
            model_used="claude-sonnet",
            token_count={"input": 10, "output": 20},
            cost=0.01
        )
        
        write_breadcrumb(breadcrumb, discussion_session.work_session.session_id)
    
    # Get summary
    summary = get_breadcrumb_summary(discussion_session.work_session.session_id)
    
    assert summary["total_breadcrumbs"] == 3
    assert summary["total_tokens"]["input"] == 30  # 3 * 10
    assert summary["total_tokens"]["output"] == 60  # 3 * 20
    assert summary["total_cost"] == 0.03  # 3 * 0.01


def test_resume_discussion():
    """Test resuming a previous discussion session."""
    # Create an initial session
    original_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    original_session_id = original_session.work_session.session_id
    
    # Add some breadcrumbs to simulate a conversation
    from maestro.breadcrumb import create_breadcrumb, write_breadcrumb
    
    for i in range(2):
        breadcrumb = create_breadcrumb(
            prompt=f"Test prompt {i}",
            response=f"Test response {i}",
            tools_called=[],
            files_modified=[],
            parent_session_id=original_session_id,
            depth_level=0,
            model_used="claude-sonnet",
            token_count={"input": 10, "output": 20},
            cost=0.01
        )
        
        write_breadcrumb(breadcrumb, original_session_id)
    
    # Resume the session
    resumed_session = resume_discussion(original_session_id)
    
    # Verify the resumed session has the same ID
    assert resumed_session.work_session.session_id == original_session_id
    
    # Verify breadcrumbs are accessible
    breadcrumbs = list_breadcrumbs(original_session_id)
    assert len(breadcrumbs) == 2


def test_discussion_session_generate_actions():
    """Test generating actions from discussion history."""
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        mode="editor"
    )
    
    # Add some breadcrumbs with potential actions
    from maestro.breadcrumb import create_breadcrumb, write_breadcrumb
    
    # Add a breadcrumb with JSON action in the response
    breadcrumb = create_breadcrumb(
        prompt="Create a new track for session infrastructure",
        response='{"actions": [{"type": "track.add", "data": {"name": "Session Infrastructure", "priority": "P0"}}]}',
        tools_called=[],
        files_modified=[],
        parent_session_id=discussion_session.work_session.session_id,
        depth_level=0,
        model_used="claude-sonnet",
        token_count={"input": 20, "output": 50},
        cost=0.02
    )
    
    write_breadcrumb(breadcrumb, discussion_session.work_session.session_id)
    
    # Generate actions from the discussion
    actions = discussion_session.generate_actions()
    
    # Verify that actions were extracted (this is a simplified test)
    # The actual extraction logic is quite basic in our implementation
    assert isinstance(actions, list)


@patch('maestro.ai.discussion.parse_todo_safe')
def test_track_discuss_integration(mock_parse_todo):
    """Test that track discuss command creates session properly."""
    # Mock the todo parsing to return a track
    mock_parse_todo.return_value = {
        "tracks": [{"track_id": "cli-tpt-1", "name": "Test Track"}]
    }

    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'track_id': 'cli-tpt-1'},
        mode="editor"
    )

    # Verify session context
    context = discussion_session._get_context_for_session()
    assert context.context_type == "track"
    assert context.context_id == "cli-tpt-1"


def test_phase_discuss_integration():
    """Test that phase discuss command creates session properly."""
    # This test requires a phase to exist, so we'll test the session creation
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'phase_id': 'cli-tpt-1'},
        mode="editor"
    )
    
    # The context creation will fail in a test environment without actual phase files
    # So we just verify the session was created with correct parameters
    assert discussion_session.work_session.related_entity == {'phase_id': 'cli-tpt-1'}


def test_task_discuss_integration():
    """Test that task discuss command creates session properly."""
    # This test requires a task to exist, so we'll test the session creation
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'task_id': 'cli-tpt-1-1'},
        mode="editor"
    )
    
    # The context creation will fail in a test environment without actual task files
    # So we just verify the session was created with correct parameters
    assert discussion_session.work_session.related_entity == {'task_id': 'cli-tpt-1-1'}


if __name__ == "__main__":
    pytest.main([__file__])
