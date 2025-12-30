"""Breadcrumb system for tracking AI interactions in work sessions."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import tempfile
import logging

from maestro.config.paths import get_docs_root

@dataclass
class Breadcrumb:
    """Records a single interaction step in an AI work session."""
    # Auto-added by maestro (not AI):
    timestamp: str  # ISO 8601 timestamp, auto-added by system
    breadcrumb_id: str  # Unique ID for this breadcrumb

    # AI interaction data:
    prompt: str  # Input prompt text
    response: str  # AI response (can be JSON)
    tools_called: List[Dict[str, Any]]  # List of tool invocations with args and results
    files_modified: List[Dict[str, Any]]  # List of {path, diff, operation}

    # Context:
    parent_session_id: Optional[str]  # Reference if this is a sub-worker
    depth_level: int  # Directory depth in session tree (0 for top-level)

    # Metadata:
    model_used: str  # AI model name (sonnet, opus, haiku)
    token_count: Dict[str, int]  # {input: N, output: M}
    cost: Optional[float]  # Estimated cost in USD
    error: Optional[str]  # Error message if operation failed
    kind: str = "note"  # note, decision, result, handoff, gate, etc.
    tags: List[str] = field(default_factory=list)
    payload: Optional[Dict[str, Any]] = None


def generate_timestamp() -> str:
    """Generate a timestamp in the format YYYYMMDD_HHMMSS_microseconds."""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S_%f")


def generate_breadcrumb_id() -> str:
    """Generate a unique breadcrumb ID."""
    return str(uuid.uuid4())


def create_breadcrumb(
    prompt: str,
    response: str,
    tools_called: List[Dict[str, Any]],
    files_modified: List[Dict[str, Any]],
    parent_session_id: Optional[str],
    depth_level: int,
    model_used: str,
    token_count: Dict[str, int],
    cost: Optional[float] = None,
    error: Optional[str] = None,
    kind: str = "note",
    tags: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Breadcrumb:
    """
    Create a new breadcrumb with auto-generated timestamp and ID.
    
    Args:
        prompt: Input prompt text
        response: AI response (can be JSON)
        tools_called: List of tool invocations with args and results
        files_modified: List of {path, diff, operation}
        parent_session_id: Reference if this is a sub-worker
        depth_level: Directory depth in session tree (0 for top-level)
        model_used: AI model name (sonnet, opus, haiku)
        token_count: {input: N, output: M}
        cost: Estimated cost in USD
        error: Error message if operation failed
    
    Returns:
        Breadcrumb object
    """
    timestamp = generate_timestamp()
    breadcrumb_id = generate_breadcrumb_id()
    
    return Breadcrumb(
        timestamp=timestamp,
        breadcrumb_id=breadcrumb_id,
        prompt=prompt,
        response=response,
        tools_called=tools_called,
        files_modified=files_modified,
        parent_session_id=parent_session_id,
        depth_level=depth_level,
        model_used=model_used,
        token_count=token_count,
        cost=cost,
        error=error,
        kind=kind,
        tags=tags or [],
        payload=payload
    )


def _resolve_sessions_dir(sessions_dir: Optional[str]) -> Path:
    if sessions_dir:
        return Path(sessions_dir)
    return get_docs_root() / "docs" / "sessions"


def write_breadcrumb(breadcrumb: Breadcrumb, session_id: str, sessions_dir: Optional[str] = None) -> str:
    """
    Write breadcrumb to disk.
    
    Args:
        breadcrumb: Breadcrumb object to write
        session_id: Session ID for the breadcrumb
        sessions_dir: Directory containing session data
        
    Returns:
        Path to written file
    """
    # Create session breadcrumbs directory structure
    session_dir = _resolve_sessions_dir(sessions_dir) / session_id
    breadcrumbs_dir = session_dir / "breadcrumbs" / str(breadcrumb.depth_level)
    breadcrumbs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename from timestamp
    filename = f"{breadcrumb.timestamp}.json"
    filepath = breadcrumbs_dir / filename
    
    # Write atomically using temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=breadcrumbs_dir)
    try:
        json.dump(dataclass_to_dict(breadcrumb), temp_file, indent=2)
        temp_file.close()
        
        # Atomically move temp file to final destination
        os.replace(temp_file.name, filepath)
        
        return str(filepath)
    except Exception as e:
        # Clean up temp file if error occurs
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise e


def load_breadcrumb(filepath: str) -> Breadcrumb:
    """
    Load a single breadcrumb from file.
    
    Args:
        filepath: Path to the breadcrumb JSON file
        
    Returns:
        Breadcrumb object
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return dict_to_breadcrumb(data)
    except Exception as e:
        logging.error(f"Failed to load breadcrumb from {filepath}: {str(e)}")
        raise e


def list_breadcrumbs(
    session_id: str,
    sessions_dir: Optional[str] = None,
    depth: Optional[int] = None,
    date_range: Optional[tuple] = None
) -> List[Breadcrumb]:
    """
    List all breadcrumbs for a session.
    
    Args:
        session_id: Session ID to list breadcrumbs for
        sessions_dir: Directory containing session data
        depth: Optional depth level to filter by
        date_range: Optional tuple of (start_date, end_date) to filter by
        
    Returns:
        Sorted list of Breadcrumb objects (by timestamp)
    """
    session_dir = _resolve_sessions_dir(sessions_dir) / session_id
    breadcrumbs_dir = session_dir / "breadcrumbs"
    
    if not breadcrumbs_dir.exists():
        return []
    
    breadcrumbs = []
    
    # If depth is specified, only scan that depth directory
    if depth is not None:
        depth_dirs = [breadcrumbs_dir / str(depth)]
    else:
        # Scan all depth directories
        depth_dirs = [d for d in breadcrumbs_dir.iterdir() if d.is_dir()]
    
    for depth_dir in depth_dirs:
        for json_file in depth_dir.glob("*.json"):
            try:
                breadcrumb = load_breadcrumb(str(json_file))
                
                # Apply date range filter if specified
                if date_range:
                    start_date, end_date = date_range
                    breadcrumb_time = datetime.strptime(
                        breadcrumb.timestamp[:15], "%Y%m%d_%H%M%S"
                    )
                    
                    if not (start_date <= breadcrumb_time <= end_date):
                        continue
                
                breadcrumbs.append(breadcrumb)
            except Exception as e:
                logging.warning(f"Could not load breadcrumb {json_file}: {e}")
    
    # Sort by timestamp
    breadcrumbs.sort(key=lambda b: b.timestamp)
    return breadcrumbs


def reconstruct_session_timeline(session_id: str, sessions_dir: Optional[str] = None) -> List[Breadcrumb]:
    """
    Build full session history by loading all breadcrumbs for a session.
    
    Args:
        session_id: Session ID to reconstruct timeline for
        sessions_dir: Directory containing session data
        
    Returns:
        Chronologically sorted list of Breadcrumb objects with parent-child relationships
    """
    breadcrumbs = list_breadcrumbs(session_id, sessions_dir)
    # Already sorted in list_breadcrumbs function
    return breadcrumbs


def get_breadcrumb_summary(session_id: str, sessions_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Summarize breadcrumbs for a session.
    
    Args:
        session_id: Session ID to summarize
        sessions_dir: Directory containing session data
        
    Returns:
        Dictionary with {total_breadcrumbs, total_tokens, total_cost, duration}
    """
    breadcrumbs = list_breadcrumbs(session_id, sessions_dir)
    
    if not breadcrumbs:
        return {
            "total_breadcrumbs": 0,
            "total_tokens": {"input": 0, "output": 0},
            "total_cost": 0.0,
            "duration": 0
        }
    
    total_tokens = {"input": 0, "output": 0}
    total_cost = 0.0
    
    for breadcrumb in breadcrumbs:
        total_tokens["input"] += breadcrumb.token_count.get("input", 0)
        total_tokens["output"] += breadcrumb.token_count.get("output", 0)
        if breadcrumb.cost:
            total_cost += breadcrumb.cost
    
    # Calculate duration in seconds
    start_time = datetime.strptime(breadcrumbs[0].timestamp[:15], "%Y%m%d_%H%M%S")
    end_time = datetime.strptime(breadcrumbs[-1].timestamp[:15], "%Y%m%d_%H%M%S")
    duration = (end_time - start_time).total_seconds()
    
    return {
        "total_breadcrumbs": len(breadcrumbs),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "duration": duration
    }


def capture_tool_call(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture a single tool invocation for breadcrumb.
    Returns structured dict with tool call details.
    """
    return {
        "tool": tool_name,
        "args": tool_args,
        "result": serialize_result(tool_result),
        "error": error,
        "timestamp": datetime.now().isoformat()
    }


def serialize_result(result: Any) -> Any:
    """Serialize tool result for storage in breadcrumb."""
    try:
        # Try to convert to JSON-serializable format
        json.dumps(result)
        return result
    except TypeError:
        # If not serializable, convert to string representation
        return str(result)


def track_file_modification(
    file_path: str,
    operation: str,  # "create", "modify", "delete"
    diff: Optional[str] = None
) -> Dict[str, Any]:
    """
    Track a file modification for breadcrumb.
    Returns structured dict with file change details.
    """
    return {
        "path": file_path,
        "operation": operation,
        "diff": diff,
        "timestamp": datetime.now().isoformat(),
        "size": get_file_size(file_path) if operation != "delete" else None
    }


def get_file_size(file_path: str) -> Optional[int]:
    """Get the size of a file in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None


def estimate_tokens(text: str, model: str = "claude") -> int:
    """
    Estimate token count for text.
    Simple heuristic: ~4 chars per token for English.
    """
    return len(text) // 4


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Calculate estimated cost in USD.
    Use current pricing for Claude models.
    """
    # Pricing as of 2025 (approximate)
    pricing = {
        "sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
        "opus": {"input": 0.015 / 1000, "output": 0.075 / 1000},
        "haiku": {"input": 0.00025 / 1000, "output": 0.00125 / 1000},
    }
    rates = pricing.get(model.lower(), pricing["sonnet"])
    return (input_tokens * rates["input"]) + (output_tokens * rates["output"])


def parse_ai_dialog(ai_dialog: str) -> List[Breadcrumb]:
    """
    Parse AI conversation into breadcrumbs.
    Input: Full AI dialog with multiple turns.
    Output: List of Breadcrumb objects (one per turn).
    Note: This is a simplified implementation. A full implementation would require
    parsing the ai_dialog structure properly.
    """
    # This is a simplified implementation.
    # A full implementation would parse the actual dialog structure.
    # For now, we'll create a single breadcrumb for the entire dialog
    tokens_input = estimate_tokens(ai_dialog)
    tokens_output = estimate_tokens(ai_dialog)
    
    # Create a simple breadcrumb representing the dialog
    breadcrumb = create_breadcrumb(
        prompt=ai_dialog[:1000],  # Limit prompt length
        response=ai_dialog[:1000],  # Limit response length
        tools_called=[],
        files_modified=[],
        parent_session_id=None,
        depth_level=0,
        model_used="unknown",
        token_count={"input": tokens_input, "output": tokens_output},
        cost=calculate_cost(tokens_input, tokens_output, "sonnet")
    )
    return [breadcrumb]


def dataclass_to_dict(obj):
    """Convert a Breadcrumb dataclass to a dictionary."""
    from dataclasses import asdict
    return asdict(obj)


def dict_to_breadcrumb(data: Dict[str, Any]) -> Breadcrumb:
    """Convert a dictionary to a Breadcrumb dataclass."""
    return Breadcrumb(**data)


def auto_breadcrumb_wrapper(func):
    """
    Decorator for functions to automatically create breadcrumb.
    Capture function args, return value, exceptions.
    Write breadcrumb before returning.
    Use for AI interaction functions.
    """
    def wrapper(*args, **kwargs):
        # Create a breadcrumb for the function call
        # Note: This is a simplified implementation
        # A full implementation would capture more details
        result = None
        error = None
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error = str(e)
            raise
        finally:
            # In a real implementation, we would create and write the breadcrumb here
            # For now, we'll just return the result
            pass
        
        return result
    
    return wrapper
