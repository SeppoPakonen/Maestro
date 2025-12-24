"""Comprehensive tests for Qwen integration with the AI engine manager."""

import json
import tempfile
from pathlib import Path

import pytest
from maestro.ai import AiEngineManager, PromptRef, RunOpts
from maestro.ai.qwen_extractor import extract_qwen_assistant_text, filter_qwen_events_for_verbose_mode


def test_qwen_extractor_with_realistic_events():
    """Test the Qwen extractor with realistic stream events."""
    # Simulate a realistic Qwen stream
    stream_lines = [
        '{"type":"system","subtype":"init","session_id":"sess-123","model":"qwen-model","qwen_code_version":"0.5.1"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello! I understand you need help with"}]}}',
        '{"type":"user","message":{"content":"How do I implement a function to reverse a string?"}}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Sure, I can help you with that. Here is a simple function to reverse a string:"}]}}',
        '{"type":"result","result":"def reverse_string(s): return s[::-1]"}',
        '{"type":"final_result","status":"success","session_id":"sess-123"}'
    ]
    
    # Test assistant text extraction
    assistant_text = extract_qwen_assistant_text(stream_lines)
    expected_text = "Hello! I understand you need help with\n\nSure, I can help you with that. Here is a simple function to reverse a string:\n\n```\ndef reverse_string(s): return s[::-1]\n```"
    
    # The actual result should contain the assistant responses
    assert "Hello! I understand you need help with" in assistant_text
    assert "Sure, I can help you with that" in assistant_text
    assert "def reverse_string(s): return s[::-1]" in assistant_text


def test_qwen_extractor_empty_assistant_payload():
    """Test that empty assistant payload is handled properly."""
    stream_lines = [
        '{"type":"system","subtype":"init","session_id":"sess-123","model":"qwen-model"}',
        '{"type":"user","message":{"content":"Hello"}}',
        '{"type":"final_result","status":"success"}'
    ]
    
    assistant_text = extract_qwen_assistant_text(stream_lines)
    assert assistant_text == ""


def test_qwen_filter_verbose_mode_events():
    """Test filtering events for verbose mode."""
    stream_lines = [
        '{"type":"system","subtype":"init","session_id":"sess-123","model":"qwen-model"}',
        '{"type":"system","subtype":"other","message":"This should be filtered"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Assistant response"}]}}',
        '{"type":"user","message":{"content":"User input"}}',
        '{"type":"result","result":"Final result"}',
        '{"type":"final_result","status":"success"}',
        '{"type":"error","message":"Some error"}'
    ]
    
    # Filter for verbose mode
    filtered = filter_qwen_events_for_verbose_mode(stream_lines)
    
    # Check that the right events are kept
    filtered_types = []
    for line in filtered:
        event = json.loads(line)
        filtered_types.append(event['type'])
    
    # Should include: system (with subtype init), assistant, result, final_result, error
    # Should NOT include: system (with other subtype), user
    expected_types = ["system", "assistant", "result", "final_result"]  # Assuming error is also included
    for event_type in ["system", "assistant", "result", "final_result"]:
        assert event_type in filtered_types
    
    # Should not include user or system with other subtype
    # Actually, looking at the filter function again, 'error' should also be included
    # because it's not specifically excluded, only certain types are specifically included
    # Wait, let me reread the function:
    # if event_type in ['system', 'init', 'assistant', 'result', 'final_result']:
    # So 'error' is not in this list, so it should NOT be included
    assert "user" not in filtered_types
    assert not any(json.loads(line).get('subtype') == 'other' for line in filtered if json.loads(line)['type'] == 'system')


def test_qwen_filter_verbose_mode_with_error():
    """Test filtering events including error types."""
    stream_lines = [
        '{"type":"system","subtype":"init","session_id":"sess-123","model":"qwen-model"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Assistant response"}]}}',
        '{"type":"error","message":"Some error"}',
        '{"type":"final_result","status":"success"}'
    ]
    
    filtered = filter_qwen_events_for_verbose_mode(stream_lines)
    
    # Check what types are actually included
    filtered_types = [json.loads(line)['type'] for line in filtered]
    
    # According to the filter, only 'system' (with init subtype), 'init', 'assistant', 'result', 'final_result' are kept
    # 'error' is not in the allowed list, so it should not be included
    assert "error" not in filtered_types
    assert "assistant" in filtered_types
    assert "final_result" in filtered_types


def test_normal_vs_verbose_output_simulation():
    """Simulate how normal vs verbose output would work."""
    # This test doesn't execute the actual commands but verifies the logic
    stream_lines = [
        '{"type":"system","subtype":"init","session_id":"sess-123","model":"qwen-model"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"This is the assistant response"}]}}',
        '{"type":"result","result":"Additional result"}',
        '{"type":"final_result","status":"success"}'
    ]
    
    # In normal mode, only assistant text should be shown
    assistant_text = extract_qwen_assistant_text(stream_lines)
    assert "This is the assistant response" in assistant_text
    assert "Additional result" in assistant_text
    
    # In verbose mode, filtered events should be shown along with extracted text
    filtered_events = filter_qwen_events_for_verbose_mode(stream_lines)
    # Should have multiple events
    assert len(filtered_events) > 0
    
    # Check that the filtered events are the ones we expect for debugging
    for event_line in filtered_events:
        event = json.loads(event_line)
        # Should only be allowed event types
        assert event['type'] in ['system', 'init', 'assistant', 'result', 'final_result']
        if event['type'] == 'system':
            assert event.get('subtype') == 'init'  # Only init subtype should be included


if __name__ == "__main__":
    pytest.main([__file__])