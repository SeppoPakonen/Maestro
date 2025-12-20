"""
Session infrastructure for AI work interactions with hierarchical tracking.
This is separate from the legacy session_model.py and implements the Work & Session Framework.
"""
import json
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class SessionStatus(Enum):
    """Possible session statuses."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class SessionType(Enum):
    """Types of work sessions."""
    WORK_TRACK = "work_track"
    WORK_PHASE = "work_phase"
    WORK_ISSUE = "work_issue"
    DISCUSSION = "discussion"
    ANALYZE = "analyze"
    FIX = "fix"


@dataclass
class WorkSession:
    """Session for AI work interactions with hierarchical tracking."""
    session_id: str  # UUID or timestamp-based ID
    session_type: str  # work_track, work_phase, work_issue, discussion, analyze, fix
    parent_session_id: Optional[str] = None  # Link to parent if this is a sub-worker
    status: str = SessionStatus.RUNNING.value  # running, paused, completed, interrupted, failed
    created: str = field(default_factory=lambda: datetime.now().isoformat())  # ISO 8601 timestamp
    modified: str = field(default_factory=lambda: datetime.now().isoformat())  # ISO 8601 timestamp
    related_entity: Dict[str, Any] = field(default_factory=dict)  # {track_id: ..., phase_id: ..., issue_id: ..., etc.}
    breadcrumbs_dir: str = ""  # Path to breadcrumbs subdirectory
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional flexible metadata


def _ensure_dir_exists(path: Path) -> None:
    """Ensure directory exists, creating it if needed."""
    path.mkdir(parents=True, exist_ok=True)


def create_session(
    session_type: str,
    parent_session_id: Optional[str] = None,
    related_entity: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    base_path: Optional[Path] = None,
    status: Optional[str] = None
) -> WorkSession:
    """
    Create new session.

    Args:
        session_type: Type of session (work_track, work_phase, work_issue, discussion, analyze, fix)
        parent_session_id: Parent session ID if this is a sub-worker
        related_entity: Dictionary with track_id, phase_id, issue_id, etc.
        metadata: Additional flexible metadata
        base_path: Base directory for sessions (defaults to docs/sessions/)
        status: Initial status for the session (defaults to RUNNING)

    Returns:
        WorkSession object representing the newly created session
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Determine base path
    if base_path is None:
        base_path = Path("docs") / "sessions"

    # Create session directory structure
    if parent_session_id:
        # Nested session: docs/sessions/<parent-id>/<child-id>/
        session_dir = base_path / parent_session_id / session_id
    else:
        # Top-level session: docs/sessions/<session-id>/
        session_dir = base_path / session_id

    _ensure_dir_exists(session_dir)

    # Create breadcrumbs directory
    breadcrumbs_dir = session_dir / "breadcrumbs"
    _ensure_dir_exists(breadcrumbs_dir)

    # Create WorkSession instance
    session = WorkSession(
        session_id=session_id,
        session_type=session_type,
        parent_session_id=parent_session_id,
        status=status or SessionStatus.RUNNING.value,
        created=timestamp,
        modified=timestamp,
        related_entity=related_entity or {},
        breadcrumbs_dir=str(breadcrumbs_dir),
        metadata=metadata or {}
    )

    # Save initial session.json
    session_path = session_dir / "session.json"
    save_session(session, session_path)

    logging.info(f"Created new work session: {session_id}")
    return session


def load_session(session_path: Union[str, Path]) -> WorkSession:
    """
    Load existing session from disk.
    
    Args:
        session_path: Path to session.json file
        
    Returns:
        WorkSession object loaded from the file
        
    Raises:
        FileNotFoundError: If session file doesn't exist
        json.JSONDecodeError: If session file contains invalid JSON
        KeyError: If required fields are missing from session data
    """
    path = Path(session_path)
    if not path.exists():
        raise FileNotFoundError(f"Session file does not exist: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create WorkSession instance from dictionary data
    session = WorkSession(
        session_id=data["session_id"],
        session_type=data["session_type"],
        parent_session_id=data.get("parent_session_id"),
        status=data.get("status", SessionStatus.RUNNING.value),
        created=data.get("created", datetime.now().isoformat()),
        modified=data.get("modified", datetime.now().isoformat()),
        related_entity=data.get("related_entity", {}),
        breadcrumbs_dir=data.get("breadcrumbs_dir", ""),
        metadata=data.get("metadata", {})
    )
    
    logging.info(f"Loaded work session: {session.session_id}")
    return session


def save_session(session: WorkSession, session_path: Union[str, Path]) -> None:
    """
    Save session updates to disk using atomic write.
    
    Args:
        session: WorkSession object to save
        session_path: Path where session.json will be saved
    """
    path = Path(session_path)
    
    # Update modified timestamp
    session.modified = datetime.now().isoformat()
    
    # Prepare temporary file path for atomic write
    temp_path = path.with_suffix('.tmp')
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(_work_session_to_dict(session), f, indent=2)
    
    # Atomically rename the temporary file to the target file
    temp_path.rename(path)
    
    logging.info(f"Saved work session: {session.session_id}")


def _work_session_to_dict(session: WorkSession) -> Dict[str, Any]:
    """Convert WorkSession to dictionary."""
    return {
        "session_id": session.session_id,
        "session_type": session.session_type,
        "parent_session_id": session.parent_session_id,
        "status": session.status,
        "created": session.created,
        "modified": session.modified,
        "related_entity": session.related_entity,
        "breadcrumbs_dir": session.breadcrumbs_dir,
        "metadata": session.metadata
    }


def list_sessions(base_path: Optional[Path] = None, session_type: Optional[str] = None, 
                 status: Optional[str] = None) -> List[WorkSession]:
    """
    List all sessions with optional filtering.
    
    Args:
        base_path: Base directory for sessions (defaults to docs/sessions/)
        session_type: Filter by session type
        status: Filter by status
        
    Returns:
        List of WorkSession objects
    """
    if base_path is None:
        base_path = Path("docs") / "sessions"
    
    sessions = []
    
    # Check top-level session directories
    if base_path.exists():
        for session_dir in base_path.iterdir():
            if session_dir.is_dir():
                # Check for direct session
                session_file = session_dir / "session.json"
                if session_file.exists():
                    try:
                        session = load_session(session_file)
                        if _matches_filters(session, session_type, status):
                            sessions.append(session)
                    except (json.JSONDecodeError, KeyError) as e:
                        logging.warning(f"Failed to load session from {session_file}: {e}")
                
                # Also check for nested sessions (subdirectories)
                for nested_dir in session_dir.iterdir():
                    if nested_dir.is_dir():
                        nested_session_file = nested_dir / "session.json"
                        if nested_session_file.exists():
                            try:
                                session = load_session(nested_session_file)
                                if _matches_filters(session, session_type, status):
                                    sessions.append(session)
                            except (json.JSONDecodeError, KeyError) as e:
                                logging.warning(f"Failed to load nested session from {nested_session_file}: {e}")
    
    return sessions


def _matches_filters(session: WorkSession, session_type: Optional[str], 
                    status: Optional[str]) -> bool:
    """Check if session matches the given filters."""
    if session_type and session.session_type != session_type:
        return False
    if status and session.status != status:
        return False
    return True


def get_session_hierarchy(base_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get parent-child session tree.

    Args:
        base_path: Base directory for sessions (defaults to docs/sessions/)

    Returns:
        Hierarchical representation of sessions as a tree
    """
    if base_path is None:
        base_path = Path("docs") / "sessions"

    # Load all sessions first
    all_sessions = list_sessions(base_path)

    # Build the tree structure
    tree: Dict[str, Any] = {"root": []}

    # First, organize sessions by parent ID for easier lookup
    children_map: Dict[str, List[WorkSession]] = {}
    root_sessions: List[WorkSession] = []

    for session in all_sessions:
        if session.parent_session_id:
            if session.parent_session_id not in children_map:
                children_map[session.parent_session_id] = []
            children_map[session.parent_session_id].append(session)
        else:
            root_sessions.append(session)

    # Build the tree structure starting with root sessions
    def build_tree_node(session: WorkSession) -> Dict[str, Any]:
        node = {
            "session": session,
            "children": []
        }

        # Add children if they exist
        if session.session_id in children_map:
            for child_session in children_map[session.session_id]:
                node["children"].append(build_tree_node(child_session))

        return node

    # Add root sessions to the tree
    for root_session in root_sessions:
        tree["root"].append(build_tree_node(root_session))

    return tree


def interrupt_session(session: WorkSession, reason: Optional[str] = None) -> WorkSession:
    """
    Handle interruption of a session.
    
    Args:
        session: Session to interrupt
        reason: Optional reason for interruption
        
    Returns:
        Updated WorkSession object
    """
    session.status = SessionStatus.INTERRUPTED.value
    session.modified = datetime.now().isoformat()
    
    # Add interruption reason to metadata if provided
    if reason:
        session.metadata["interruption_reason"] = reason
    
    logging.info(f"Interrupted work session: {session.session_id}, reason: {reason}")
    return session


def resume_session(session: WorkSession) -> WorkSession:
    """
    Resume an interrupted session.
    
    Args:
        session: Session to resume (should be in 'interrupted' status)
        
    Returns:
        Updated WorkSession object with new context for continuation
    """
    session.status = SessionStatus.RUNNING.value
    session.modified = datetime.now().isoformat()
    
    logging.info(f"Resumed work session: {session.session_id}")
    return session


def complete_session(session: WorkSession) -> WorkSession:
    """
    Mark a session as completed.
    
    Args:
        session: Session to complete
        
    Returns:
        Updated WorkSession object
    """
    session.status = SessionStatus.COMPLETED.value
    session.modified = datetime.now().isoformat()
    
    # Add completion timestamp to metadata
    session.metadata["completion_time"] = datetime.now().isoformat()
    
    logging.info(f"Completed work session: {session.session_id}")
    return session


def pause_session_for_user_input(session: WorkSession, question: str) -> None:
    """
    STUB: Pause session and request user input.
    TODO: Implement in future phase.
    
    This function will eventually:
    - Allow AI to ask questions via JSON response
    - Block execution waiting for user response
    - Continue with user's answer in new context
    """
    raise NotImplementedError("Session pausing not yet implemented")