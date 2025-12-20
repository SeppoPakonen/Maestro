"""Tests for the breadcrumb system in maestro."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from maestro.breadcrumb import (
    Breadcrumb,
    create_breadcrumb,
    write_breadcrumb,
    load_breadcrumb,
    list_breadcrumbs,
    reconstruct_session_timeline,
    get_breadcrumb_summary,
    capture_tool_call,
    track_file_modification,
    estimate_tokens,
    calculate_cost,
    parse_ai_dialog,
    auto_breadcrumb_wrapper,
    dataclass_to_dict,
    dict_to_breadcrumb
)


class TestBreadcrumb:
    """Test the Breadcrumb dataclass and related functions."""

    def test_breadcrumb_creation(self):
        """Test creating a Breadcrumb object."""
        breadcrumb = Breadcrumb(
            timestamp="20251220_143025_123456",
            breadcrumb_id="test-id-123",
            prompt="Test prompt",
            response="Test response",
            tools_called=[],
            files_modified=[],
            parent_session_id="parent-123",
            depth_level=1,
            model_used="claude-3-5-sonnet",
            token_count={"input": 10, "output": 20},
            cost=0.01,
            error=None
        )

        assert breadcrumb.timestamp == "20251220_143025_123456"
        assert breadcrumb.breadcrumb_id == "test-id-123"
        assert breadcrumb.prompt == "Test prompt"
        assert breadcrumb.response == "Test response"
        assert breadcrumb.depth_level == 1
        assert breadcrumb.model_used == "claude-3-5-sonnet"
        assert breadcrumb.token_count == {"input": 10, "output": 20}
        assert breadcrumb.cost == 0.01

    def test_create_breadcrumb(self):
        """Test the create_breadcrumb function."""
        breadcrumb = create_breadcrumb(
            prompt="Test prompt",
            response="Test response",
            tools_called=[],
            files_modified=[],
            parent_session_id="parent-123",
            depth_level=1,
            model_used="claude-3-5-sonnet",
            token_count={"input": 10, "output": 20},
            cost=0.01
        )

        # Check that timestamp and ID are generated
        assert breadcrumb.timestamp is not None
        assert breadcrumb.breadcrumb_id is not None
        assert breadcrumb.prompt == "Test prompt"
        assert breadcrumb.response == "Test response"
        assert breadcrumb.depth_level == 1
        assert breadcrumb.model_used == "claude-3-5-sonnet"
        assert breadcrumb.token_count == {"input": 10, "output": 20}
        assert breadcrumb.cost == 0.01

    def test_write_and_load_breadcrumb(self):
        """Test writing and loading a breadcrumb."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test breadcrumb
            breadcrumb = create_breadcrumb(
                prompt="Test prompt",
                response="Test response",
                tools_called=[],
                files_modified=[],
                parent_session_id=None,
                depth_level=0,
                model_used="claude-3-5-sonnet",
                token_count={"input": 10, "output": 20},
                cost=0.01
            )

            # Write the breadcrumb
            session_id = "test-session-123"
            session_path = os.path.join(temp_dir, "docs", "sessions", session_id)
            os.makedirs(session_path, exist_ok=True)
            
            filepath = write_breadcrumb(
                breadcrumb, 
                session_id, 
                sessions_dir=os.path.join(temp_dir, "docs", "sessions")
            )

            # Verify file exists
            assert os.path.exists(filepath)

            # Load and verify content
            loaded_breadcrumb = load_breadcrumb(filepath)
            assert loaded_breadcrumb.breadcrumb_id == breadcrumb.breadcrumb_id
            assert loaded_breadcrumb.prompt == breadcrumb.prompt
            assert loaded_breadcrumb.response == breadcrumb.response
            assert loaded_breadcrumb.depth_level == breadcrumb.depth_level
            assert loaded_breadcrumb.model_used == breadcrumb.model_used
            assert loaded_breadcrumb.token_count == breadcrumb.token_count
            assert loaded_breadcrumb.cost == breadcrumb.cost

    def test_list_breadcrumbs(self):
        """Test listing breadcrumbs for a session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sessions_dir = os.path.join(temp_dir, "docs", "sessions")
            session_id = "test-session-123"
            
            # Create breadcrumbs in different depth levels
            for depth in [0, 1, 2]:
                depth_path = Path(sessions_dir) / session_id / "breadcrumbs" / str(depth)
                depth_path.mkdir(parents=True, exist_ok=True)
                
                # Create a breadcrumb file for each depth
                breadcrumb = create_breadcrumb(
                    prompt=f"Test prompt for depth {depth}",
                    response=f"Test response for depth {depth}",
                    tools_called=[],
                    files_modified=[],
                    parent_session_id=None,
                    depth_level=depth,
                    model_used="claude-3-5-sonnet",
                    token_count={"input": 10, "output": 20},
                    cost=0.01
                )
                
                # Write breadcrumb with a specific timestamp
                breadcrumb.timestamp = f"20251220_14302{depth}_12345{depth}"
                
                breadcrumb_file = depth_path / f"{breadcrumb.timestamp}.json"
                with open(breadcrumb_file, 'w') as f:
                    json.dump(dataclass_to_dict(breadcrumb), f)
            
            # Test listing all breadcrumbs
            all_breadcrumbs = list_breadcrumbs(
                session_id, 
                sessions_dir=sessions_dir
            )
            assert len(all_breadcrumbs) == 3
            
            # Test filtering by depth
            depth_0_breadcrumbs = list_breadcrumbs(
                session_id, 
                sessions_dir=sessions_dir,
                depth=0
            )
            assert len(depth_0_breadcrumbs) == 1
            assert depth_0_breadcrumbs[0].depth_level == 0

    def test_reconstruct_session_timeline(self):
        """Test reconstructing the session timeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sessions_dir = os.path.join(temp_dir, "docs", "sessions")
            session_id = "test-session-123"
            
            # Create breadcrumbs
            for i in range(3):
                depth_path = Path(sessions_dir) / session_id / "breadcrumbs" / "0"
                depth_path.mkdir(parents=True, exist_ok=True)
                
                breadcrumb = create_breadcrumb(
                    prompt=f"Prompt {i}",
                    response=f"Response {i}",
                    tools_called=[],
                    files_modified=[],
                    parent_session_id=None,
                    depth_level=0,
                    model_used="claude-3-5-sonnet",
                    token_count={"input": 10, "output": 20},
                    cost=0.01 * (i+1)
                )
                
                # Set specific timestamps to ensure ordering
                breadcrumb.timestamp = f"20251220_14302{i}_12345{i}"
                
                breadcrumb_file = depth_path / f"{breadcrumb.timestamp}.json"
                with open(breadcrumb_file, 'w') as f:
                    json.dump(dataclass_to_dict(breadcrumb), f)
            
            # Test timeline reconstruction
            timeline = reconstruct_session_timeline(session_id, sessions_dir=sessions_dir)
            assert len(timeline) == 3
            # Verify chronological order
            for i, breadcrumb in enumerate(timeline):
                assert f"Prompt {i}" in breadcrumb.prompt

    def test_get_breadcrumb_summary(self):
        """Test getting breadcrumb summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sessions_dir = os.path.join(temp_dir, "docs", "sessions")
            session_id = "test-session-123"
            
            # Create breadcrumbs with different costs and tokens
            for i in range(3):
                depth_path = Path(sessions_dir) / session_id / "breadcrumbs" / "0"
                depth_path.mkdir(parents=True, exist_ok=True)
                
                breadcrumb = create_breadcrumb(
                    prompt=f"Prompt {i}",
                    response=f"Response {i}",
                    tools_called=[],
                    files_modified=[],
                    parent_session_id=None,
                    depth_level=0,
                    model_used="claude-3-5-sonnet",
                    token_count={"input": 10 * (i+1), "output": 20 * (i+1)},
                    cost=0.01 * (i+1)
                )
                
                breadcrumb.timestamp = f"20251220_14302{i}_12345{i}"
                
                breadcrumb_file = depth_path / f"{breadcrumb.timestamp}.json"
                with open(breadcrumb_file, 'w') as f:
                    json.dump(dataclass_to_dict(breadcrumb), f)
            
            # Test summary
            summary = get_breadcrumb_summary(session_id, sessions_dir=sessions_dir)
            assert summary["total_breadcrumbs"] == 3
            assert summary["total_tokens"]["input"] == 60  # 10 + 20 + 30
            assert summary["total_tokens"]["output"] == 120  # 20 + 40 + 60
            assert summary["total_cost"] == 0.06  # 0.01 + 0.02 + 0.03

    def test_capture_tool_call(self):
        """Test capturing a tool call."""
        result = capture_tool_call(
            tool_name="test_tool",
            tool_args={"param1": "value1"},
            tool_result={"result": "success"},
            error=None
        )
        
        assert result["tool"] == "test_tool"
        assert result["args"] == {"param1": "value1"}
        assert result["result"] == {"result": "success"}
        assert result["error"] is None
        assert "timestamp" in result

    def test_track_file_modification(self):
        """Test tracking file modification."""
        result = track_file_modification(
            file_path="/path/to/file.txt",
            operation="create",
            diff="test diff"
        )
        
        assert result["path"] == "/path/to/file.txt"
        assert result["operation"] == "create"
        assert result["diff"] == "test diff"
        assert "timestamp" in result

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test sentence for token estimation."
        tokens = estimate_tokens(text)
        # Simple heuristic: ~4 chars per token
        expected = len(text) // 4
        assert tokens == expected

    def test_calculate_cost(self):
        """Test cost calculation."""
        input_tokens = 1000
        output_tokens = 500
        
        # Test with sonnet model
        cost = calculate_cost(input_tokens, output_tokens, "sonnet")
        expected = (1000 * (0.003 / 1000)) + (500 * (0.015 / 1000))
        assert abs(cost - expected) < 0.000001  # Allow for floating point precision
        
        # Test with opus model
        cost = calculate_cost(input_tokens, output_tokens, "opus")
        expected = (1000 * (0.015 / 1000)) + (500 * (0.075 / 1000))
        assert abs(cost - expected) < 0.000001
        
        # Test with haiku model
        cost = calculate_cost(input_tokens, output_tokens, "haiku")
        expected = (1000 * (0.00025 / 1000)) + (500 * (0.00125 / 1000))
        assert abs(cost - expected) < 0.000001

    def test_parse_ai_dialog(self):
        """Test parsing AI dialog into breadcrumbs."""
        dialog = "This is a simple dialog for testing."
        breadcrumbs = parse_ai_dialog(dialog)
        
        # Should return a list with at least one breadcrumb
        assert len(breadcrumbs) >= 1
        assert isinstance(breadcrumbs[0], Breadcrumb)
        assert dialog[:1000] in breadcrumbs[0].prompt

    def test_dataclass_to_dict_and_back(self):
        """Test conversion between dataclass and dict."""
        original = create_breadcrumb(
            prompt="Test prompt",
            response="Test response",
            tools_called=[],
            files_modified=[],
            parent_session_id=None,
            depth_level=0,
            model_used="claude-3-5-sonnet",
            token_count={"input": 10, "output": 20},
            cost=0.01
        )
        
        # Convert to dict
        as_dict = dataclass_to_dict(original)
        
        # Convert back to dataclass
        reconstructed = dict_to_breadcrumb(as_dict)
        
        # Verify they match
        assert reconstructed.breadcrumb_id == original.breadcrumb_id
        assert reconstructed.prompt == original.prompt
        assert reconstructed.response == original.response
        assert reconstructed.depth_level == original.depth_level
        assert reconstructed.model_used == original.model_used
        assert reconstructed.token_count == original.token_count
        assert reconstructed.cost == original.cost


class TestAutoBreadcrumbWrapper:
    """Test the auto_breadcrumb_wrapper decorator."""
    
    def test_auto_breadcrumb_wrapper(self):
        """Test the auto_breadcrumb_wrapper functionality."""
        # Create a simple function to test
        @auto_breadcrumb_wrapper
        def test_function(x, y):
            return x + y
        
        # Call the function
        result = test_function(2, 3)
        assert result == 5

    def test_auto_breadcrumb_wrapper_with_exception(self):
        """Test the auto_breadcrumb_wrapper with an exception."""
        @auto_breadcrumb_wrapper
        def failing_function():
            raise ValueError("Test error")
        
        # Should re-raise the exception
        with pytest.raises(ValueError, match="Test error"):
            failing_function()


if __name__ == "__main__":
    pytest.main([__file__])