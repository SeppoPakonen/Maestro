"""
UI Facade for Root Task Operations

This module provides structured data access to root task information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from maestro.session_model import Session, load_session


def _find_session_files(sessions_dir: str = "./.maestro/sessions") -> List[str]:
    """Find all session JSON files in the specified directory."""
    if not os.path.exists(sessions_dir):
        return []
    
    session_files = []
    for filename in os.listdir(sessions_dir):
        if filename.endswith('.json'):
            session_files.append(os.path.join(sessions_dir, filename))
    return session_files


@dataclass
class RootTaskInfo:
    """Information about a root task."""
    id: str
    task_text: str
    raw_text: Optional[str]
    clean_text: Optional[str]
    summary: Optional[str]
    categories: List[str]


@dataclass
class RootSummaryInfo:
    """Summary information about a root task."""
    id: str
    task_preview: str
    category_count: int
    has_summary: bool


def get_root_task(session_id: str, sessions_dir: str = "./.maestro/sessions") -> RootTaskInfo:
    """
    Get the root task information for a specific session.
    
    Args:
        session_id: ID of the session containing the root task
        sessions_dir: Directory containing session files
        
    Returns:
        Root task information
        
    Raises:
        ValueError: If session with given ID is not found
    """
    session_files = _find_session_files(sessions_dir)
    
    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id:
                return RootTaskInfo(
                    id=session.id,
                    task_text=session.root_task,
                    raw_text=session.root_task_raw,
                    clean_text=session.root_task_clean,
                    summary=session.root_task_summary,
                    categories=session.root_task_categories or []
                )
        except Exception:
            # Skip corrupted or inaccessible session files
            continue
    
    raise ValueError(f"Session with ID '{session_id}' not found")


def get_root_summary(session_id: str, sessions_dir: str = "./.maestro/sessions") -> RootSummaryInfo:
    """
    Get a summary of the root task for a specific session.
    
    Args:
        session_id: ID of the session containing the root task
        sessions_dir: Directory containing session files
        
    Returns:
        Root task summary information
        
    Raises:
        ValueError: If session with given ID is not found
    """
    session_files = _find_session_files(sessions_dir)
    
    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id:
                preview = session.root_task[:100] + "..." if len(session.root_task) > 100 else session.root_task
                return RootSummaryInfo(
                    id=session.id,
                    task_preview=preview,
                    category_count=len(session.root_task_categories or []),
                    has_summary=bool(session.root_task_summary)
                )
        except Exception:
            # Skip corrupted or inaccessible session files
            continue
    
    raise ValueError(f"Session with ID '{session_id}' not found")