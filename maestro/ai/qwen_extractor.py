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
    result_texts = []
    assistant_texts = []
    has_final_result = False
    for line in stream_lines:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Skip invalid JSON lines
            continue

        event_type = event.get('type')
        if event_type == 'final_result':
            has_final_result = True

        if event_type == 'result' and 'result' in event:
            result_texts.append(event['result'])
            continue

        # Collect assistant content for optional use
        if event_type == 'assistant' and 'message' in event:
            message = event['message']
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if content_item.get('type') == 'text' and 'text' in content_item:
                        assistant_texts.append(content_item['text'])

    if result_texts:
        result_text = _normalize_text(result_texts[-1])
        if assistant_texts and has_final_result:
            assistant_text = _normalize_text('\n\n'.join(assistant_texts))
            if assistant_text == result_text or assistant_text in result_text:
                return result_text
            return _normalize_text(f"{assistant_text}\n\n{result_text}")
        return result_text

    if assistant_texts:
        return _normalize_text('\n\n'.join(assistant_texts))

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
