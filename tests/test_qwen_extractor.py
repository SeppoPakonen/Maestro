"""Tests for Qwen assistant text extractor functionality."""

import pytest
from maestro.ai.qwen_extractor import extract_qwen_assistant_text, filter_qwen_events_for_verbose_mode


def test_extract_qwen_assistant_text_from_result():
    """Test extracting text from result-type events."""
    stream_lines = [
        '{"type":"init","session_id":"test123","model":"qwen-model"}',
        '{"type":"result","result":"Hello, this is the assistant response"}',
        '{"type":"final_result","status":"success"}'
    ]
    
    result = extract_qwen_assistant_text(stream_lines)
    assert result == "Hello, this is the assistant response"


def test_extract_qwen_assistant_text_from_assistant():
    """Test extracting text from assistant-type events."""
    stream_lines = [
        '{"type":"init","session_id":"test123","model":"qwen-model"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"First assistant message"}]}}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Second assistant message"}]}}',
        '{"type":"final_result","status":"success"}'
    ]
    
    result = extract_qwen_assistant_text(stream_lines)
    assert result == "First assistant message\n\nSecond assistant message"


def test_extract_qwen_assistant_text_mixed_events():
    """Test extracting text from mixed event types."""
    stream_lines = [
        '{"type":"init","session_id":"test123","model":"qwen-model"}',
        '{"type":"system","subtype":"init","message":"Initializing..."}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Assistant message"}]}}',
        '{"type":"result","result":"Result message"}',
        '{"type":"final_result","status":"success"}'
    ]
    
    result = extract_qwen_assistant_text(stream_lines)
    assert result == "Assistant message\n\nResult message"


def test_extract_qwen_assistant_text_empty():
    """Test extracting text when there are no assistant messages."""
    stream_lines = [
        '{"type":"init","session_id":"test123","model":"qwen-model"}',
        '{"type":"system","subtype":"init","message":"Initializing..."}',
        '{"type":"final_result","status":"success"}'
    ]
    
    result = extract_qwen_assistant_text(stream_lines)
    assert result == ""


def test_extract_qwen_assistant_text_invalid_json():
    """Test handling of invalid JSON lines."""
    stream_lines = [
        'invalid json line',
        '{"type":"result","result":"Valid result"}',
        'another invalid line'
    ]
    
    result = extract_qwen_assistant_text(stream_lines)
    assert result == "Valid result"


def test_filter_qwen_events_for_verbose_mode():
    """Test filtering events for verbose mode."""
    stream_lines = [
        '{"type":"init","session_id":"test123","model":"qwen-model"}',
        '{"type":"system","subtype":"init","message":"Initializing..."}',
        '{"type":"system","subtype":"other","message":"Other system message"}',
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Assistant message"}]}}',
        '{"type":"result","result":"Result message"}',
        '{"type":"final_result","status":"success"}',
        '{"type":"message","content":"Regular message"}'
    ]
    
    filtered = filter_qwen_events_for_verbose_mode(stream_lines)
    
    # Should include: init, system with subtype init, assistant, result, final_result
    expected_types = ["init", "assistant", "result", "final_result"]
    
    for line in filtered:
        event = eval(line)  # Using eval for simplicity in test, not in production
        assert event['type'] in expected_types or (event['type'] == 'system' and event['subtype'] == 'init')
    
    # Count how many events we expect
    # init, system with subtype init, assistant, result, final_result = 5 events
    assert len(filtered) == 5


def test_filter_qwen_events_for_verbose_mode_no_init_system():
    """Test that system events without 'init' subtype and other non-whitelisted types are filtered out."""
    stream_lines = [
        '{"type":"system","subtype":"other","message":"Other system message"}',
        '{"type":"message","content":"Regular message"}'
    ]

    filtered = filter_qwen_events_for_verbose_mode(stream_lines)

    # Both events should be filtered out since:
    # - system with subtype 'other' is not included (only 'init' subtype)
    # - 'message' is not in the allowed types ['system', 'init', 'assistant', 'result', 'final_result']
    assert len(filtered) == 0


if __name__ == "__main__":
    pytest.main([__file__])