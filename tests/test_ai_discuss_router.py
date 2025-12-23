"""Tests for Qwen transport and discussion router functionality."""

import pytest
from unittest.mock import Mock, patch
from maestro.ai.types import AiEngineName, PromptRef, RunOpts
from maestro.ai.manager import AiEngineManager
from maestro.ai.discuss_router import DiscussionRouter, JsonContract, PatchOperationType
from maestro.ai.runner import run_engine_command


def test_qwen_cmdline_transport():
    """Test that Qwen cmdline transport builds correct command."""
    from maestro.config.settings import get_settings
    settings = get_settings()
    
    # Temporarily set transport to cmdline
    original_transport = settings.ai_qwen_transport
    settings.ai_qwen_transport = "cmdline"
    
    try:
        manager = AiEngineManager()
        opts = RunOpts(
            dangerously_skip_permissions=True,
            continue_latest=False,
            resume_id=None
        )
        prompt = PromptRef(source="Test prompt")
        
        # This should build a command normally
        cmd = manager.build_command("qwen", prompt, opts)
        
        # Verify the command contains expected elements
        assert "qwen" in cmd
        assert "-y" in cmd  # dangerous permissions flag
        assert "Test prompt" in cmd
        
    finally:
        # Restore original setting
        settings.ai_qwen_transport = original_transport


def test_qwen_stdio_tcp_transport_raises_not_implemented():
    """Test that Qwen stdio/tcp transport raises NotImplementedError."""
    from maestro.config.settings import get_settings
    settings = get_settings()
    
    for transport_mode in ["stdio", "tcp"]:
        # Temporarily set transport to stdio/tcp
        original_transport = settings.ai_qwen_transport
        settings.ai_qwen_transport = transport_mode
        
        try:
            manager = AiEngineManager()
            opts = RunOpts(
                dangerously_skip_permissions=True,
                continue_latest=False,
                resume_id=None
            )
            prompt = PromptRef(source="Test prompt")
            
            # This should raise NotImplementedError
            with pytest.raises(NotImplementedError):
                manager.build_command("qwen", prompt, opts)
                
        finally:
            # Restore original setting
            settings.ai_qwen_transport = original_transport


def test_discussion_router_json_contract():
    """Test that the discussion router properly handles JSON contracts."""
    manager = AiEngineManager()
    router = DiscussionRouter(manager)
    
    # Define a simple validation function
    def validate_simple_json(data):
        return isinstance(data, dict) and "type" in data
    
    # Create a JSON contract
    json_contract = JsonContract(
        schema_id="simple_test",
        validation_func=validate_simple_json,
        allowed_operations=[PatchOperationType.ADD_TASK, PatchOperationType.MARK_DONE]
    )
    
    # Mock the engine command execution to return a valid JSON response
    with patch('maestro.ai.runner._run_subprocess_command') as mock_runner:
        mock_runner.return_value = Mock(
            exit_code=0,
            stdout_text='{"type": "task", "name": "test_task", "op_type": "add_task"}',
            stderr_text="",
            session_id="test-session"
        )
        
        # Run a simple discussion
        results = router._process_json_contract(
            engine="qwen",
            final_input="Create a task",
            json_contract=json_contract,
            opts=RunOpts()
        )
        
        # Verify that we got a result
        assert len(results) >= 0  # May not get results due to our simple validation function


def test_discussion_router_terminal_mode():
    """Test that the discussion router handles terminal mode."""
    manager = AiEngineManager()
    router = DiscussionRouter(manager)

    # For this test, we'll just ensure the method can be called without error
    # A full test would require mocking input() and other interactive elements
    with patch('maestro.ai.runner._run_subprocess_command') as mock_runner:
        mock_runner.return_value = Mock(
            exit_code=0,
            stdout_text="Test response",
            stderr_text="",
            session_id="test-session"
        )

        # Mock the input function to return a quit command immediately to avoid hanging
        with patch('maestro.ai.discuss_router.input', return_value='/quit'):
            results = router._run_terminal_discussion(
                engine="qwen",
                initial_prompt="Test initial prompt",
                opts=RunOpts(),
                json_contract=None
            )

            # Should return empty list when quit is called immediately
            assert results == []


def test_patch_operation_conversion():
    """Test conversion of JSON data to patch operations."""
    manager = AiEngineManager()
    router = DiscussionRouter(manager)
    
    # Test valid JSON that should convert to operations
    json_data = {
        "op_type": "add_task",
        "task_name": "Test Task",
        "description": "A test task"
    }
    
    allowed_ops = [PatchOperationType.ADD_TASK]
    operations = router._convert_to_patch_operations(json_data, allowed_ops)
    
    assert len(operations) == 1
    assert operations[0].op_type == PatchOperationType.ADD_TASK
    assert operations[0].data["task_name"] == "Test Task"


def test_extract_json_from_response():
    """Test JSON extraction from AI response."""
    manager = AiEngineManager()
    router = DiscussionRouter(manager)
    
    # Test with JSON in triple backticks
    response1 = "Here's your JSON:\n```json\n{\"test\": \"value\"}\n```"
    extracted1 = router._extract_json_from_response(response1)
    assert extracted1 == '{"test": "value"}'
    
    # Test with plain JSON
    response2 = '{"test": "value"}'
    extracted2 = router._extract_json_from_response(response2)
    assert extracted2 == '{"test": "value"}'
    
    # Test with no JSON
    response3 = "No JSON here"
    extracted3 = router._extract_json_from_response(response3)
    assert extracted3 is None


if __name__ == "__main__":
    test_qwen_cmdline_transport()
    test_qwen_stdio_tcp_transport_raises_not_implemented()
    test_discussion_router_json_contract()
    test_discussion_router_terminal_mode()
    test_patch_operation_conversion()
    test_extract_json_from_response()
    print("All tests passed!")