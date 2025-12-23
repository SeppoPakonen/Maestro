"""Stream renderer for AI engine output with human-friendly and verbose modes."""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from enum import Enum


class EventType(Enum):
    """Normalized event types for AI streaming."""
    INIT = "init"
    DELTA = "delta"
    MESSAGE = "message"
    RESULT = "result"
    ERROR = "error"


@dataclass
class AiStreamEvent:
    """Normalized event from AI engines."""
    type: EventType
    role: Optional[str] = None
    text_delta: Optional[str] = None
    text_full: Optional[str] = None
    session_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    ts: Optional[datetime] = None
    stats: Optional[Dict[str, Any]] = field(default_factory=dict)
    level: str = "info"  # debug, info, warning, error

    def __post_init__(self):
        if self.ts is None:
            self.ts = datetime.now()


class StreamRenderer:
    """Renders AI engine output in human-friendly or verbose mode."""
    
    def __init__(self, engine: str, verbose: bool = False):
        self.engine = engine
        self.verbose = verbose
        self.session_id: Optional[str] = None
        self.accumulated_text = ""
        self.start_time = datetime.now()
    
    def render_event(self, event: AiStreamEvent):
        """Render a single event based on the mode."""
        if event.session_id:
            self.session_id = event.session_id
            
        # In verbose mode, always show the parsed event
        if self.verbose:
            self._render_verbose_event(event)
        
        # Handle different event types for human output
        if event.type == EventType.DELTA and event.text_delta:
            self._render_delta(event.text_delta)
        elif event.type == EventType.MESSAGE and event.text_full:
            self._render_message(event.text_full)
        elif event.type == EventType.ERROR and not self.verbose:
            print(f"[{self.engine}] Error: {event.text_delta or 'Unknown error'}", file=sys.stderr)
    
    def _render_verbose_event(self, event: AiStreamEvent):
        """Render event in verbose mode."""
        event_info = {
            "type": event.type.value,
        }
        
        if event.role:
            event_info["role"] = event.role
        if event.session_id:
            event_info["session_id"] = event.session_id
        if event.stats:
            # Truncate stats to keep output compact
            truncated_stats = {}
            for k, v in event.stats.items():
                str_val = str(v)
                if len(str_val) > 50:
                    truncated_stats[k] = str_val[:47] + "..."
                else:
                    truncated_stats[k] = v
            event_info["stats"] = truncated_stats
        
        # Add text info if present
        if event.text_delta:
            text_preview = event.text_delta[:50] + "..." if len(event.text_delta) > 50 else event.text_delta
            event_info["text_delta"] = text_preview
        elif event.text_full:
            text_preview = event.text_full[:50] + "..." if len(event.text_full) > 50 else event.text_full
            event_info["text"] = text_preview
        
        print(f"[{self.engine}] {json.dumps(event_info)}")
    
    def _render_delta(self, text_delta: str):
        """Render a text delta in human mode."""
        print(text_delta, end="", flush=True)
        self.accumulated_text += text_delta
    
    def _render_message(self, text_full: str):
        """Render a full message in human mode."""
        print(text_full, end="", flush=True)
        self.accumulated_text = text_full
    
    def finalize(self, exit_code: int = 0):
        """Finalize rendering and show summary."""
        duration = datetime.now() - self.start_time
        
        if self.verbose:
            # In verbose mode, show final result event
            result_info = {
                "type": "final_result",
                "status": "success" if exit_code == 0 else "error",
                "exit_code": exit_code,
                "duration_ms": int(duration.total_seconds() * 1000),
            }
            if self.session_id:
                result_info["session_id"] = self.session_id
            print(f"[{self.engine}] {json.dumps(result_info)}")
        else:
            # In human mode, show a minimal summary
            status = "ok" if exit_code == 0 else "error"
            session_part = f" • session {self.session_id[:10]}…" if self.session_id else ""
            print(f"\n[{self.engine}] {status}{session_part} • {duration.total_seconds():.1f}s")
    
    def handle_interrupt(self):
        """Handle interruption with appropriate messaging."""
        if self.verbose and self.session_id:
            print(f"[{self.engine}] [Interrupted] partial session_id={self.session_id[:10]}…")
        elif self.verbose:
            print(f"[{self.engine}] [Interrupted]")
        else:
            print("\n[Interrupted]")