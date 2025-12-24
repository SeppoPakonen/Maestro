"""Qwen assistant text extractor for parsing stream events and extracting the actual assistant response."""

import json
from typing import List, Optional


def extract_qwen_assistant_text(stream_lines: List[str]) -> str:
    """
    Extract assistant text from Qwen stream JSON lines.
    
    Supports these cases:
    1. Preferred: {"type":"result", ... "result":"<TEXT>"}
       - Extract `result` string as the assistant response.
    2. Fallback: {"type":"assistant", ... "message": { "content":[{"type":"text","text":"<TEXT>"}] }}
       - Extract and concatenate all `content[].text` entries.
    
    Args:
        stream_lines: List of JSON lines from Qwen's stream output
        
    Returns:
        The extracted assistant text, or empty string if no assistant text found
    """
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
            
        # Check for 'result' type events (preferred)
        if event.get('type') == 'result' and 'result' in event:
            assistant_texts.append(event['result'])
            
        # Check for 'assistant' type events (fallback)
        elif event.get('type') == 'assistant' and 'message' in event:
            message = event['message']
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if content_item.get('type') == 'text' and 'text' in content_item:
                        assistant_texts.append(content_item['text'])
    
    # Join all assistant texts with double newlines
    return '\n\n'.join(assistant_texts)


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