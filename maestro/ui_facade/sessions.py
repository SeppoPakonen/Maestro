"""
UI Facade for Session Operations

This module provides structured data access to session information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from datetime import datetime
from maestro.session_model import Session, load_session, save_session
import uuid


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


def _get_sessions_dir() -> str:
    """Get the sessions directory path."""
    return "./.maestro/sessions"


def _find_session_files(sessions_dir: str = "./.maestro/sessions") -> List[str]:
    """Find all session JSON files in the specified directory."""
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir, exist_ok=True)
        return []

    session_files = []
    for filename in os.listdir(sessions_dir):
        if filename.endswith('.json'):
            session_files.append(os.path.join(sessions_dir, filename))
    return session_files


def _session_file_path(session_id: str, sessions_dir: str = "./.maestro/sessions") -> str:
    """Get the file path for a specific session."""
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"{session_id}.json")


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


def create_session(name: str, root_task_text: Optional[str] = None, sessions_dir: str = "./.maestro/sessions") -> SessionInfo:
    """
    Create a new session.

    Args:
        name: Name of the new session
        root_task_text: Optional root task text for the session
        sessions_dir: Directory to store session files

    Returns:
        Information about the created session

    Raises:
        Exception: If session creation fails
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Create empty root task if not provided
    root_task = root_task_text or name or "New session"

    session = Session(
        id=session_id,
        created_at=timestamp,
        updated_at=timestamp,
        root_task=root_task,
        subtasks=[],
        rules_path=None,
        status="new"
    )

    # Save the session to file
    session_path = _session_file_path(session_id, sessions_dir)
    save_session(session, session_path)

    # Return session info
    return SessionInfo(
        id=session.id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        root_task=session.root_task[:50] + "..." if len(session.root_task) > 50 else session.root_task,
        status=session.status
    )


def set_active_session(session_id_or_name: str, sessions_dir: str = "./.maestro/sessions") -> SessionInfo:
    """
    Set the specified session as active by ensuring it's the most recent.
    In this implementation, we'll update the updated_at timestamp to make it most recent.

    Args:
        session_id_or_name: ID or name of the session to set as active
        sessions_dir: Directory containing session files

    Returns:
        Information about the activated session

    Raises:
        ValueError: If session with given ID/name is not found
    """
    # Find the session by ID or by name (root_task)
    session_files = _find_session_files(sessions_dir)
    target_session_file = None
    target_session = None

    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id_or_name or session.root_task.startswith(session_id_or_name):
                target_session = session
                target_session_file = session_file
                break
        except Exception:
            # Skip corrupted or inaccessible session files
            continue

    if target_session is None:
        raise ValueError(f"Session with ID/name '{session_id_or_name}' not found")

    # Update the updated_at timestamp to make it the most recent (active)
    target_session.updated_at = datetime.now().isoformat()

    # Save the updated session
    save_session(target_session, target_session_file)

    # Return session info
    return SessionInfo(
        id=target_session.id,
        created_at=target_session.created_at,
        updated_at=target_session.updated_at,
        root_task=target_session.root_task[:50] + "..." if len(target_session.root_task) > 50 else target_session.root_task,
        status=target_session.status,
        active_plan_id=target_session.active_plan_id
    )


def remove_session(session_id_or_name: str, sessions_dir: str = "./.maestro/sessions") -> None:
    """
    Remove a session by ID or name.

    Args:
        session_id_or_name: ID or name of the session to remove
        sessions_dir: Directory containing session files

    Raises:
        ValueError: If session with given ID/name is not found
    """
    # Find the session by ID or by name (root_task)
    session_files = _find_session_files(sessions_dir)
    target_session_file = None

    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id_or_name or session.root_task.startswith(session_id_or_name):
                target_session_file = session_file
                break
        except Exception:
            # Skip corrupted or inaccessible session files
            continue

    if target_session_file is None:
        raise ValueError(f"Session with ID/name '{session_id_or_name}' not found")

    # Remove the session file
    os.remove(target_session_file)


def update_session(session_id: str, updated_session: Session, sessions_dir: str = "./.maestro/sessions") -> SessionInfo:
    """
    Update an existing session with new data.

    Args:
        session_id: ID of the session to update
        updated_session: Updated session object
        sessions_dir: Directory containing session files

    Returns:
        Information about the updated session

    Raises:
        ValueError: If the session is not found
    """
    session_path = _session_file_path(session_id, sessions_dir)

    if not os.path.exists(session_path):
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Update the timestamps
    updated_session.updated_at = datetime.now().isoformat()

    # Save the updated session
    save_session(updated_session, session_path)

    # Return session info
    return SessionInfo(
        id=updated_session.id,
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at,
        root_task=updated_session.root_task[:50] + "..." if len(updated_session.root_task) > 50 else updated_session.root_task,
        status=updated_session.status,
        active_plan_id=updated_session.active_plan_id
    )