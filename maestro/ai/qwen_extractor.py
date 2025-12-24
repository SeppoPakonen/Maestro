"""Qwen assistant text extractor for parsing stream events and extracting the actual assistant response."""

import json
from typing import List, Optional


def extract_qwen_assistant_text(stream_lines: List[str]) -> str:
    """
    Extract assistant text from Qwen stream JSON lines.

    Supports these cases with priority:
    1. Preferred: {"type":"result", ... "result":"<TEXT>"}
       - Extract `result` string as the assistant response.
       - If any 'result' events exist, return only the result text (no fallback to assistant events).
    2. Fallback: {"type":"assistant", ... "message": { "content":[{"type":"text","text":"<TEXT>"}] }}
       - Extract and concatenate all `content[].text` entries.
       - Only used if no 'result' events are found.

    Args:
        stream_lines: List of JSON lines from Qwen's stream output

    Returns:
        The extracted assistant text, or empty string if no assistant text found
    """
    # First, check for 'result' type events (preferred)
    result_texts = []
    for line in stream_lines:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Skip invalid JSON lines
            continue

        # Check for 'result' type events (preferred)
        if event.get('type') == 'result' and 'result' in event:
            result_texts.append(event['result'])

    # If we found result events, return them (preferably just the last one if multiple exist)
    if result_texts:
        # Return the last result text (most complete/final answer)
        return _normalize_text(result_texts[-1])

    # If no result events, fall back to 'assistant' type events
    assistant_texts = []
    for line in stream_lines:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Skip invalid JSON lines
            continue

        # Check for 'assistant' type events (fallback)
        if event.get('type') == 'assistant' and 'message' in event:
            message = event['message']
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if content_item.get('type') == 'text' and 'text' in content_item:
                        assistant_texts.append(content_item['text'])

    # Join assistant texts with newlines and normalize
    if assistant_texts:
        combined_text = '\n\n'.join(assistant_texts)
        return _normalize_text(combined_text)

    return ""


def _normalize_text(text: str) -> str:
    """
    Normalize text by trimming whitespace and normalizing blank lines.
    """
    if not text:
        return text

    # Trim leading and trailing whitespace
    text = text.strip()

    # Normalize excessive blank lines (convert multiple blank lines to single blank lines)
    import re
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

    return text


def filter_qwen_events_for_verbose_mode(stream_lines: List[str]) -> List[str]:
    """
    Filter Qwen stream events to show only those useful for debugging in verbose mode.
    
    Args:
        stream_lines: List of JSON lines from Qwen's stream output
        
    Returns:
        Filtered list of JSON lines that are useful for debugging
    """
    filtered_lines = []
    
    for line in stream_lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Keep invalid JSON lines as they might be important
            filtered_lines.append(line)
            continue
            
        event_type = event.get('type')
        
        # Only include event types that help with debugging
        if event_type in ['system', 'init', 'assistant', 'result', 'final_result']:
            # For 'system' events, only show 'init' subtype
            if event_type == 'system':
                subtype = event.get('subtype')
                if subtype == 'init':
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
    
    return filtered_lines