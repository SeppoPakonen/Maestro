"""
UI Facade for Session Operations

This module provides structured data access to session information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from datetime import datetime
from maestro.session_model import Session, load_session


@dataclass
class SessionInfo:
    """Basic information about a session."""
    id: str
    created_at: str
    updated_at: str
    root_task: str
    status: str
    active_plan_id: Optional[str] = None


@dataclass
class SessionDetails:
    """Detailed information about a session."""
    id: str
    created_at: str
    updated_at: str
    root_task: str
    rules_path: Optional[str]
    status: str
    root_task_summary: Optional[str]
    root_task_categories: List[str]
    active_plan_id: Optional[str]


def _find_session_files(sessions_dir: str = "./.maestro/sessions") -> List[str]:
    """Find all session JSON files in the specified directory."""
    if not os.path.exists(sessions_dir):
        return []
    
    session_files = []
    for filename in os.listdir(sessions_dir):
        if filename.endswith('.json'):
            session_files.append(os.path.join(sessions_dir, filename))
    return session_files


def list_sessions(sessions_dir: str = "./.maestro/sessions") -> List[SessionInfo]:
    """
    List all available sessions with basic information.
    
    Args:
        sessions_dir: Directory containing session files
        
    Returns:
        List of basic session information
    """
    session_files = _find_session_files(sessions_dir)
    sessions_info = []
    
    for session_file in session_files:
        try:
            session = load_session(session_file)
            sessions_info.append(SessionInfo(
                id=session.id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                root_task=session.root_task[:50] + "..." if len(session.root_task) > 50 else session.root_task,
                status=session.status,
                active_plan_id=session.active_plan_id
            ))
        except Exception:
            # Skip corrupted or inaccessible session files
            continue
    
    return sessions_info


def get_active_session(sessions_dir: str = "./.maestro/sessions") -> Optional[SessionInfo]:
    """
    Get the most recently created or updated session.
    
    Args:
        sessions_dir: Directory containing session files
        
    Returns:
        Information about the active session or None
    """
    all_sessions = list_sessions(sessions_dir)
    if not all_sessions:
        return None
    
    # Sort by creation time to get the most recent session
    most_recent = max(all_sessions, key=lambda s: s.created_at)
    return most_recent


def get_session_details(session_id: str, sessions_dir: str = "./.maestro/sessions") -> SessionDetails:
    """
    Get detailed information about a specific session.
    
    Args:
        session_id: ID of the session to retrieve
        sessions_dir: Directory containing session files
        
    Returns:
        Detailed session information
        
    Raises:
        ValueError: If session with given ID is not found
    """
    session_files = _find_session_files(sessions_dir)
    
    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id:
                return SessionDetails(
                    id=session.id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    root_task=session.root_task,
                    rules_path=session.rules_path,
                    status=session.status,
                    root_task_summary=session.root_task_summary,
                    root_task_categories=session.root_task_categories or [],
                    active_plan_id=session.active_plan_id
                )
        except Exception:
            # Skip corrupted or inaccessible session files
            continue
    
    raise ValueError(f"Session with ID '{session_id}' not found")