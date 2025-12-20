"""
Session statistics calculation module.
"""
from dataclasses import dataclass
from typing import List
from datetime import datetime
from ..work_session import WorkSession
from ..breadcrumb import list_breadcrumbs, Breadcrumb


@dataclass
class SessionStats:
    """Session statistics."""
    total_breadcrumbs: int
    total_tokens_input: int
    total_tokens_output: int
    estimated_cost: float
    files_modified: int
    tools_called: int
    duration_seconds: float
    success_rate: float  # % of successful operations


def calculate_session_stats(session: WorkSession) -> SessionStats:
    """
    Calculate comprehensive session statistics.

    Args:
        session: WorkSession to analyze

    Returns:
        SessionStats object with calculated metrics
    """
    # Load all breadcrumbs for this session
    breadcrumbs = list_breadcrumbs(session.session_id)
    
    # Initialize statistics
    total_breadcrumbs = len(breadcrumbs)
    total_tokens_input = 0
    total_tokens_output = 0
    estimated_cost = 0.0
    files_modified = 0
    tools_called = 0
    success_count = 0
    
    # Process each breadcrumb to accumulate stats
    for breadcrumb in breadcrumbs:
        total_tokens_input += breadcrumb.token_count.get('input', 0)
        total_tokens_output += breadcrumb.token_count.get('output', 0)
        
        if breadcrumb.cost:
            estimated_cost += breadcrumb.cost
        
        files_modified += len(breadcrumb.files_modified)
        tools_called += len(breadcrumb.tools_called)
        
        # Count as successful if no error
        if not breadcrumb.error:
            success_count += 1
    
    # Calculate duration in seconds
    duration_seconds = 0.0
    if breadcrumbs:
        try:
            # Extract the first and last breadcrumb timestamps
            first_time_str = breadcrumbs[0].timestamp[:15]  # First 15 chars (YYYYMMDD_HHMMSS)
            last_time_str = breadcrumbs[-1].timestamp[:15]
            
            # Convert to datetime objects
            first_time = datetime.strptime(first_time_str, "%Y%m%d_%H%M%S")
            last_time = datetime.strptime(last_time_str, "%Y%m%d_%H%M%S")
            
            # Calculate duration
            duration = last_time - first_time
            duration_seconds = duration.total_seconds()
        except Exception:
            # If timestamp parsing fails, try with session created/modified times
            try:
                created_dt = datetime.fromisoformat(session.created.replace('Z', '+00:00'))
                modified_dt = datetime.fromisoformat(session.modified.replace('Z', '+00:00'))
                duration = modified_dt - created_dt
                duration_seconds = duration.total_seconds()
            except Exception:
                duration_seconds = 0.0
    
    # Calculate success rate
    success_rate = 0.0
    if total_breadcrumbs > 0:
        success_rate = (success_count / total_breadcrumbs) * 100.0
    
    return SessionStats(
        total_breadcrumbs=total_breadcrumbs,
        total_tokens_input=total_tokens_input,
        total_tokens_output=total_tokens_output,
        estimated_cost=estimated_cost,
        files_modified=files_modified,
        tools_called=tools_called,
        duration_seconds=duration_seconds,
        success_rate=success_rate
    )


def calculate_tree_stats(root_session: WorkSession) -> SessionStats:
    """
    Calculate statistics for session and all children.

    Args:
        root_session: Root of session tree

    Returns:
        Aggregated SessionStats for entire tree
    """
    # First, calculate stats for the root session
    root_stats = calculate_session_stats(root_session)
    
    # Then, we need to find all child sessions and aggregate their stats too
    # This requires finding all sessions that have this root_session as a parent
    from ..work_session import list_sessions
    
    # Find all child sessions
    all_sessions = list_sessions()
    child_sessions = [
        s for s in all_sessions 
        if s.parent_session_id == root_session.session_id
    ]
    
    # Aggregate stats from all children
    total_breadcrumbs = root_stats.total_breadcrumbs
    total_tokens_input = root_stats.total_tokens_input
    total_tokens_output = root_stats.total_tokens_output
    estimated_cost = root_stats.estimated_cost
    files_modified = root_stats.files_modified
    tools_called = root_stats.tools_called
    
    # Add stats from each child recursively
    for child_session in child_sessions:
        child_stats = calculate_tree_stats(child_session)  # Recursive call
        total_breadcrumbs += child_stats.total_breadcrumbs
        total_tokens_input += child_stats.total_tokens_input
        total_tokens_output += child_stats.total_tokens_output
        estimated_cost += child_stats.estimated_cost
        files_modified += child_stats.files_modified
        tools_called += child_stats.tools_called
    
    # For tree stats, use the root session's duration but with aggregate data
    success_rate = 0.0
    if total_breadcrumbs > 0:
        # Calculate success rate for the entire tree
        all_breadcrumbs = []
        all_breadcrumbs.extend(list_breadcrumbs(root_session.session_id))
        
        # Add breadcrumbs from all children
        for child_session in child_sessions:
            all_breadcrumbs.extend(list_breadcrumbs(child_session.session_id))
        
        success_count = sum(1 for b in all_breadcrumbs if not b.error)
        success_rate = (success_count / len(all_breadcrumbs)) * 100.0 if all_breadcrumbs else 0.0
    
    return SessionStats(
        total_breadcrumbs=total_breadcrumbs,
        total_tokens_input=total_tokens_input,
        total_tokens_output=total_tokens_output,
        estimated_cost=estimated_cost,
        files_modified=files_modified,
        tools_called=tools_called,
        duration_seconds=root_stats.duration_seconds,  # Using root session duration
        success_rate=success_rate
    )