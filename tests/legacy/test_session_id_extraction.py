"""Unit tests for session ID extraction from engine output."""

import json
from maestro.ai.session_manager import extract_session_id
from maestro.ai.types import AiEngineName


class TestSessionIdExtraction:
    """Test session ID extraction from engine-specific outputs."""

    def test_extract_qwen_session_id(self):
        """Test extracting session ID from Qwen output."""
        # Create sample parsed events that match the expected format
        events = [
            {"type": "message", "content": "Hello", "session_id": "qwen-session-123"},
            {"type": "status", "status": "completed", "session_id": "qwen-session-123"}
        ]
        
        session_id = extract_session_id("qwen", events)
        assert session_id == "qwen-session-123"

    def test_extract_gemini_session_id(self):
        """Test extracting session ID from Gemini output."""
        # Create sample parsed events that match the expected format
        events = [
            {"type": "message", "content": "Hello", "sessionId": "gemini-session-456"},
            {"type": "status", "status": "completed", "sessionId": "gemini-session-456"}
        ]
        
        session_id = extract_session_id("gemini", events)
        assert session_id == "gemini-session-456"

    def test_extract_claude_session_id(self):
        """Test extracting session ID from Claude output."""
        # Create sample parsed events that match the expected format
        events = [
            {"type": "message", "content": "Hello", "id": "claude-session-789"},
            {"type": "status", "status": "completed", "id": "claude-session-789"}
        ]
        
        session_id = extract_session_id("claude", events)
        assert session_id == "claude-session-789"

    def test_extract_codex_session_id(self):
        """Test extracting session ID from Codex output."""
        # Create sample parsed events that match the expected format
        events = [
            {
                "type": "message", 
                "content": "Hello", 
                "session": {"id": "codex-session-abc"}
            },
            {
                "type": "status", 
                "status": "completed", 
                "session": {"id": "codex-session-abc"}
            }
        ]
        
        session_id = extract_session_id("codex", events)
        assert session_id == "codex-session-abc"

    def test_extract_session_id_missing_id(self):
        """Test that extraction returns None when no session ID is present."""
        events = [
            {"type": "message", "content": "Hello"},
            {"type": "status", "status": "completed"}
        ]
        
        session_id = extract_session_id("qwen", events)
        assert session_id is None

    def test_extract_session_id_malformed_data(self):
        """Test that extraction handles malformed data gracefully."""
        events = [
            "not a dict",
            {"type": "message", "content": "Hello"},
            123,
            {"session_id": ""},  # Empty session ID
            {"session_id": None}  # None session ID
        ]
        
        session_id = extract_session_id("qwen", events)
        assert session_id is None

    def test_extract_session_id_nested_metadata(self):
        """Test extracting session ID from nested metadata structure."""
        events = [
            {
                "type": "message",
                "content": "Hello",
                "metadata": {
                    "session_id": "nested-session-xyz"
                }
            }
        ]
        
        session_id = extract_session_id("qwen", events)
        assert session_id == "nested-session-xyz"

    def test_extract_session_id_different_engine_types(self):
        """Test extraction with different engine name literals."""
        events = [{"session_id": "test-session"}]
        
        for engine in ["qwen", "gemini", "codex", "claude"]:
            session_id = extract_session_id(engine, events)
            assert session_id == "test-session"

    def test_extract_session_id_empty_events(self):
        """Test that extraction returns None for empty events list."""
        session_id = extract_session_id("qwen", [])
        assert session_id is None

    def test_extract_session_id_none_events(self):
        """Test that extraction returns None for None events."""
        session_id = extract_session_id("qwen", None)
        assert session_id is None