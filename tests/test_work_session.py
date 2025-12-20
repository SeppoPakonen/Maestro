"""
Tests for the work session infrastructure.
"""
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import pytest

from maestro.work_session import (
    WorkSession,
    SessionStatus,
    SessionType,
    create_session,
    load_session,
    save_session,
    list_sessions,
    get_session_hierarchy,
    interrupt_session,
    resume_session,
    complete_session,
    pause_session_for_user_input,
)


class TestWorkSession:
    """Test suite for work session functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.sessions_dir = self.temp_dir / "docs" / "sessions"
        self.sessions_dir.mkdir(parents=True)
        
    def teardown_method(self):
        """Clean up after each test method."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_work_session_dataclass_creation(self):
        """Test WorkSession dataclass creation with all fields."""
        session = WorkSession(
            session_id="test-id-123",
            session_type=SessionType.WORK_TRACK.value,
            parent_session_id="parent-id-456",
            status=SessionStatus.RUNNING.value,
            created="2023-01-01T00:00:00",
            modified="2023-01-01T00:00:00",
            related_entity={"track_id": "track1", "phase_id": "phase1"},
            breadcrumbs_dir="/path/to/breadcrumbs",
            metadata={"key": "value"}
        )
        
        assert session.session_id == "test-id-123"
        assert session.session_type == SessionType.WORK_TRACK.value
        assert session.parent_session_id == "parent-id-456"
        assert session.status == SessionStatus.RUNNING.value
        assert session.created == "2023-01-01T00:00:00"
        assert session.modified == "2023-01-01T00:00:00"
        assert session.related_entity == {"track_id": "track1", "phase_id": "phase1"}
        assert session.breadcrumbs_dir == "/path/to/breadcrumbs"
        assert session.metadata == {"key": "value"}
    
    def test_work_session_defaults(self):
        """Test WorkSession dataclass with default values."""
        session = WorkSession(
            session_id="test-id-123",
            session_type=SessionType.WORK_TRACK.value
        )
        
        assert session.session_id == "test-id-123"
        assert session.session_type == SessionType.WORK_TRACK.value
        assert session.parent_session_id is None
        assert session.status == SessionStatus.RUNNING.value
        assert session.related_entity == {}
        assert session.metadata == {}
        # Verify timestamps are in ISO format
        assert datetime.fromisoformat(session.created.replace('Z', '+00:00'))
        assert datetime.fromisoformat(session.modified.replace('Z', '+00:00'))
    
    def test_create_session(self):
        """Test session creation and directory structure."""
        session = create_session(
            session_type=SessionType.WORK_PHASE.value,
            base_path=self.sessions_dir
        )
        
        # Verify session object properties
        assert session.session_type == SessionType.WORK_PHASE.value
        assert session.status == SessionStatus.RUNNING.value
        assert session.parent_session_id is None
        
        # Verify directory structure was created
        session_dir = self.sessions_dir / session.session_id
        assert session_dir.exists()
        assert session_dir.is_dir()
        
        # Verify breadcrumbs directory was created
        breadcrumbs_dir = session_dir / "breadcrumbs"
        assert breadcrumbs_dir.exists()
        assert breadcrumbs_dir.is_dir()
        
        # Verify session.json was created
        session_json = session_dir / "session.json"
        assert session_json.exists()
        
        # Verify content of session.json
        with open(session_json, 'r') as f:
            data = json.load(f)
            assert data["session_id"] == session.session_id
            assert data["session_type"] == SessionType.WORK_PHASE.value
            assert data["status"] == SessionStatus.RUNNING.value
    
    def test_create_nested_session(self):
        """Test creation of nested sessions (child sessions)."""
        # Create parent session
        parent_session = create_session(
            session_type=SessionType.WORK_TRACK.value,
            base_path=self.sessions_dir
        )
        
        # Create child session
        child_session = create_session(
            session_type=SessionType.WORK_PHASE.value,
            parent_session_id=parent_session.session_id,
            base_path=self.sessions_dir
        )
        
        # Verify child session properties
        assert child_session.parent_session_id == parent_session.session_id
        assert child_session.session_type == SessionType.WORK_PHASE.value
        
        # Verify nested directory structure
        child_dir = self.sessions_dir / parent_session.session_id / child_session.session_id
        assert child_dir.exists()
        assert child_dir.is_dir()
        
        # Verify breadcrumbs directory exists
        breadcrumbs_dir = child_dir / "breadcrumbs"
        assert breadcrumbs_dir.exists()
        
        # Verify session.json exists
        session_json = child_dir / "session.json"
        assert session_json.exists()
    
    def test_save_and_load_session(self):
        """Test saving and loading session functionality."""
        # Create and save a session
        original_session = create_session(
            session_type=SessionType.DISCUSSION.value,
            related_entity={"issue_id": "issue123"},
            metadata={"test": True},
            base_path=self.sessions_dir
        )
        
        # Load the session back
        session_json_path = self.sessions_dir / original_session.session_id / "session.json"
        loaded_session = load_session(session_json_path)
        
        # Verify the sessions match
        assert loaded_session.session_id == original_session.session_id
        assert loaded_session.session_type == original_session.session_type
        assert loaded_session.status == original_session.status
        assert loaded_session.related_entity == original_session.related_entity
        assert loaded_session.metadata == original_session.metadata
        
        # Verify that loading updates the modification time
        assert datetime.fromisoformat(loaded_session.created.replace('Z', '+00:00'))
    
    def test_save_session_atomic_write(self):
        """Test atomic write functionality for session saving."""
        session = create_session(
            session_type=SessionType.ANALYZE.value,
            base_path=self.sessions_dir
        )
        
        # Modify session and save
        session.status = SessionStatus.COMPLETED.value
        session.metadata["test"] = "atomic_write"
        
        session_json_path = self.sessions_dir / session.session_id / "session.json"
        save_session(session, session_json_path)
        
        # Load again to verify changes were saved
        reloaded_session = load_session(session_json_path)
        assert reloaded_session.status == SessionStatus.COMPLETED.value
        assert reloaded_session.metadata["test"] == "atomic_write"
    
    def test_list_sessions(self):
        """Test listing sessions functionality."""
        # Create multiple sessions
        session1 = create_session(
            session_type=SessionType.WORK_TRACK.value,
            base_path=self.sessions_dir
        )
        
        session2 = create_session(
            session_type=SessionType.WORK_PHASE.value,
            base_path=self.sessions_dir
        )
        
        session3 = create_session(
            session_type=SessionType.WORK_ISSUE.value,
            status=SessionStatus.COMPLETED.value,
            base_path=self.sessions_dir
        )
        
        # List all sessions
        all_sessions = list_sessions(base_path=self.sessions_dir)
        assert len(all_sessions) == 3
        
        # Verify all session IDs are in the list
        session_ids = [s.session_id for s in all_sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids
        
        # Test filtering by type
        track_sessions = list_sessions(
            base_path=self.sessions_dir,
            session_type=SessionType.WORK_TRACK.value
        )
        assert len(track_sessions) == 1
        assert track_sessions[0].session_id == session1.session_id
        
        # Test filtering by status
        completed_sessions = list_sessions(
            base_path=self.sessions_dir,
            status=SessionStatus.COMPLETED.value
        )
        assert len(completed_sessions) == 1
        assert completed_sessions[0].session_id == session3.session_id
    
    def test_session_lifecycle(self):
        """Test the complete session lifecycle."""
        session = create_session(
            session_type=SessionType.FIX.value,
            base_path=self.sessions_dir
        )
        
        # Verify initial state
        assert session.status == SessionStatus.RUNNING.value
        
        # Interrupt the session
        interrupted_session = interrupt_session(session, reason="Test interruption")
        assert interrupted_session.status == SessionStatus.INTERRUPTED.value
        assert interrupted_session.metadata["interruption_reason"] == "Test interruption"
        
        # Resume the session
        resumed_session = resume_session(interrupted_session)
        assert resumed_session.status == SessionStatus.RUNNING.value
        
        # Complete the session
        completed_session = complete_session(resumed_session)
        assert completed_session.status == SessionStatus.COMPLETED.value
        assert "completion_time" in completed_session.metadata
    
    def test_session_hierarchy(self):
        """Test session hierarchy functionality."""
        # Create parent session
        parent_session = create_session(
            session_type=SessionType.WORK_TRACK.value,
            base_path=self.sessions_dir
        )
        
        # Create child session
        child_session = create_session(
            session_type=SessionType.WORK_PHASE.value,
            parent_session_id=parent_session.session_id,
            base_path=self.sessions_dir
        )
        
        # Create another child session
        child_session2 = create_session(
            session_type=SessionType.WORK_ISSUE.value,
            parent_session_id=parent_session.session_id,
            base_path=self.sessions_dir
        )
        
        # Create a grandchild session
        grandchild_session = create_session(
            session_type=SessionType.DISCUSSION.value,
            parent_session_id=child_session.session_id,
            base_path=self.sessions_dir
        )
        
        # Test hierarchy
        hierarchy = get_session_hierarchy(base_path=self.sessions_dir)
        root_sessions = hierarchy.get("root", [])
        
        # Should have one root session (parent_session)
        assert len(root_sessions) == 1
        root_session_data = root_sessions[0]
        assert root_session_data["session"].session_id == parent_session.session_id
        
        # Root session should have 2 children (child_session and child_session2)
        children = root_session_data["children"]
        assert len(children) == 2
        
        # Check that the children are the two direct children we created
        child_ids = [c["session"].session_id for c in children]
        assert child_session.session_id in child_ids
        assert child_session2.session_id in child_ids
        
        # Check that grandchild is nested under child_session
        for child in children:
            if child["session"].session_id == child_session.session_id:
                grandchild_nodes = child["children"]
                assert len(grandchild_nodes) == 1
                assert grandchild_nodes[0]["session"].session_id == grandchild_session.session_id
                break
        else:
            assert False, "Child session not found in hierarchy"
    
    def test_pause_session_for_user_input_stub(self):
        """Test that the pause_session_for_user_input stub raises NotImplementedError."""
        session = WorkSession(
            session_id="test-id",
            session_type=SessionType.DISCUSSION.value
        )
        
        with pytest.raises(NotImplementedError):
            pause_session_for_user_input(session, "Test question")