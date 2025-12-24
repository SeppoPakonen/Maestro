"""Tests for Qwen assistant text deduplication functionality."""

import json
from maestro.ai.qwen_extractor import extract_qwen_assistant_text


def test_extractor_prefers_result_over_assistant():
    """Test that extractor prefers 'result' events over 'assistant' events when both exist."""
    # Stream with both result and assistant events containing the same text
    stream_lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello world"}]}}),
        json.dumps({"type": "result", "result": "Hello world"})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return the result text, not concatenated
    assert extracted_text == "Hello world"


def test_extractor_fallback_to_assistant_when_no_result():
    """Test that extractor falls back to 'assistant' events when no 'result' events exist."""
    # Stream with only assistant events
    stream_lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello world"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "How are you?"}]}})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return concatenated assistant text
    assert extracted_text == "Hello world\n\nHow are you?"


def test_extractor_multiple_result_events_uses_last():
    """Test that extractor uses the last result when multiple result events exist."""
    # Stream with multiple result events
    stream_lines = [
        json.dumps({"type": "result", "result": "First result"}),
        json.dumps({"type": "result", "result": "Second result (should be used)"})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return the last result text
    assert extracted_text == "Second result (should be used)"


def test_extractor_with_different_content():
    """Test that extractor handles different content in result vs assistant properly."""
    # Stream with different content in result vs assistant
    stream_lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Assistant text"}]}}),
        json.dumps({"type": "result", "result": "Result text"})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return result text since it has priority
    assert extracted_text == "Result text"


def test_extractor_normalizes_whitespace():
    """Test that extractor normalizes whitespace properly."""
    # Stream with text that has extra whitespace
    stream_lines = [
        json.dumps({"type": "result", "result": "  Hello    world  \n\n\n  with   extra  \n\n\n\n  spacing  "})
    ]

    extracted_text = extract_qwen_assistant_text(stream_lines)

    # Should have leading/trailing whitespace trimmed
    assert extracted_text.startswith("Hello")
    assert extracted_text.endswith("spacing")
    # Verify the text was normalized (not exactly the same as input)
    assert extracted_text != "  Hello    world  \n\n\n  with   extra  \n\n\n\n  spacing  "


def test_extractor_handles_empty_stream():
    """Test that extractor handles empty stream properly."""
    stream_lines = []
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return empty string
    assert extracted_text == ""


def test_extractor_handles_no_relevant_events():
    """Test that extractor handles stream with no relevant events."""
    stream_lines = [
        json.dumps({"type": "system", "message": "System message"}),
        json.dumps({"type": "init", "version": "1.0"})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return empty string
    assert extracted_text == ""


def test_extractor_handles_malformed_json():
    """Test that extractor handles malformed JSON gracefully."""
    stream_lines = [
        "invalid json {",
        json.dumps({"type": "result", "result": "Valid result"}),
        "another invalid json [",
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return the valid result, ignoring malformed lines
    assert extracted_text == "Valid result"


def test_deduplication_scenario():
    """Test a realistic scenario where duplicate content might occur."""
    # Simulate a stream where the same answer appears in both assistant and result events
    stream_lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "The answer is 42."}]}}),
        json.dumps({"type": "tool_call", "tool_name": "calculator", "args": {"expression": "21*2"}}),
        json.dumps({"type": "tool_result", "result": "42"}),
        json.dumps({"type": "result", "result": "The answer is 42."})
    ]
    
    extracted_text = extract_qwen_assistant_text(stream_lines)
    
    # Should return the result text only (once), not duplicated
    assert extracted_text == "The answer is 42."


if __name__ == "__main__":
    # Run tests
    test_extractor_prefers_result_over_assistant()
    test_extractor_fallback_to_assistant_when_no_result()
    test_extractor_multiple_result_events_uses_last()
    test_extractor_with_different_content()
    test_extractor_normalizes_whitespace()
    test_extractor_handles_empty_stream()
    test_extractor_handles_no_relevant_events()
    test_extractor_handles_malformed_json()
    test_deduplication_scenario()
    print("All tests passed!")