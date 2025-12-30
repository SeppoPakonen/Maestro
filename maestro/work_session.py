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
import yaml

from maestro.config.paths import get_docs_root


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
    WORK_TASK = "work_task"
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
    parent_wsession_id: Optional[str] = None  # Canonical parent reference for subwork
    children_wsession_ids: List[str] = field(default_factory=list)
    status: str = SessionStatus.RUNNING.value  # running, paused, completed, interrupted, failed
    state: str = "running"  # running, paused, closed
    purpose: Optional[str] = None  # human label for the session
    context: Dict[str, Any] = field(default_factory=dict)  # {kind, ref}
    created: str = field(default_factory=lambda: datetime.now().isoformat())  # ISO 8601 timestamp
    modified: str = field(default_factory=lambda: datetime.now().isoformat())  # ISO 8601 timestamp
    created_at: Optional[str] = None  # ISO 8601 timestamp (alias for created)
    closed_at: Optional[str] = None  # ISO 8601 timestamp
    related_entity: Dict[str, Any] = field(default_factory=dict)  # {track_id: ..., phase_id: ..., issue_id: ..., etc.}
    breadcrumbs_dir: str = ""  # Path to breadcrumbs subdirectory
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional flexible metadata


def _ensure_dir_exists(path: Path) -> None:
    """Ensure directory exists, creating it if needed."""
    path.mkdir(parents=True, exist_ok=True)


def get_sessions_base_path(base_path: Optional[Path] = None) -> Path:
    """Resolve the base path for work sessions."""
    if base_path is not None:
        return Path(base_path)
    return get_docs_root() / "docs" / "sessions"


def _derive_state_from_status(status: str) -> str:
    if status == SessionStatus.PAUSED.value:
        return "paused"
    if status in {
        SessionStatus.COMPLETED.value,
        SessionStatus.INTERRUPTED.value,
        SessionStatus.FAILED.value,
    }:
        return "closed"
    return "running"


def _normalize_state(state: Optional[str], status: str) -> str:
    derived = _derive_state_from_status(status)
    if state in {"running", "paused", "closed"}:
        if state != derived:
            return derived
        return state
    return derived


def create_session(
    session_type: str,
    parent_session_id: Optional[str] = None,
    parent_wsession_id: Optional[str] = None,
    related_entity: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    base_path: Optional[Path] = None,
    status: Optional[str] = None,
    purpose: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
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
    base_path = get_sessions_base_path(base_path)
    parent_id = parent_wsession_id or parent_session_id

    # Create session directory structure
    if parent_id:
        # Nested session: docs/sessions/<parent-id>/<child-id>/
        session_dir = base_path / parent_id / session_id
    else:
        # Top-level session: docs/sessions/<session-id>/
        session_dir = base_path / session_id

    _ensure_dir_exists(session_dir)

    # Create breadcrumbs directory
    breadcrumbs_dir = session_dir / "breadcrumbs"
    _ensure_dir_exists(breadcrumbs_dir)

    # Create WorkSession instance
    status_value = status or SessionStatus.RUNNING.value
    session = WorkSession(
        session_id=session_id,
        session_type=session_type,
        parent_session_id=parent_id,
        parent_wsession_id=parent_id,
        status=status_value,
        state=_normalize_state(None, status_value),
        purpose=purpose,
        context=context or {},
        created=timestamp,
        modified=timestamp,
        created_at=timestamp,
        closed_at=None,
        related_entity=related_entity or {},
        breadcrumbs_dir=str(breadcrumbs_dir),
        metadata=metadata or {}
    )

    session.metadata.setdefault("cookie", session_id)
    try:
        from maestro.git_guard import get_current_branch, get_git_root

        session.metadata.setdefault("git_branch", get_current_branch())
        session.metadata.setdefault("git_root", get_git_root())
    except Exception:
        pass

    # Save initial session.json
    session_path = session_dir / "session.json"
    save_session(session, session_path)

    if parent_id:
        _register_child_session(base_path, parent_id, session_id)

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
    status = data.get("status", SessionStatus.RUNNING.value)
    parent_wsession_id = data.get("parent_wsession_id") or data.get("parent_session_id")
    parent_session_id = data.get("parent_session_id") or parent_wsession_id
    created = data.get("created", datetime.now().isoformat())
    session = WorkSession(
        session_id=data["session_id"],
        session_type=data["session_type"],
        parent_session_id=parent_session_id,
        parent_wsession_id=parent_wsession_id,
        children_wsession_ids=list(data.get("children_wsession_ids", [])),
        status=status,
        state=_normalize_state(data.get("state"), status),
        purpose=data.get("purpose"),
        context=data.get("context", {}),
        created=created,
        modified=data.get("modified", datetime.now().isoformat()),
        created_at=data.get("created_at") or created,
        closed_at=data.get("closed_at"),
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
    session.state = _normalize_state(session.state, session.status)
    if not session.created_at:
        session.created_at = session.created

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
        "parent_wsession_id": session.parent_wsession_id,
        "children_wsession_ids": session.children_wsession_ids,
        "status": session.status,
        "state": session.state,
        "purpose": session.purpose,
        "context": session.context,
        "created": session.created,
        "modified": session.modified,
        "created_at": session.created_at,
        "closed_at": session.closed_at,
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
    base_path = get_sessions_base_path(base_path)
    
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
    base_path = get_sessions_base_path(base_path)

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
    session.state = _normalize_state(session.state, session.status)
    session.modified = datetime.now().isoformat()
    session.closed_at = datetime.now().isoformat()
    
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
    if session.status in {SessionStatus.COMPLETED.value, SessionStatus.FAILED.value}:
        raise ValueError("Session is closed and cannot be resumed.")

    session.status = SessionStatus.RUNNING.value
    session.state = _normalize_state(session.state, session.status)
    session.modified = datetime.now().isoformat()
    session.closed_at = None
    
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
    session.state = _normalize_state(session.state, session.status)
    session.modified = datetime.now().isoformat()
    session.closed_at = datetime.now().isoformat()
    
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


def get_session_cookie(session: WorkSession) -> str:
    """Return the session cookie for breadcrumb operations."""
    return session.metadata.get("cookie", session.session_id)


def is_session_closed(session: WorkSession) -> bool:
    """Return True if a session is closed (completed/interrupted/failed)."""
    return session.status in {
        SessionStatus.COMPLETED.value,
        SessionStatus.INTERRUPTED.value,
        SessionStatus.FAILED.value,
    }


def pause_session(session: WorkSession) -> WorkSession:
    """Pause a running session."""
    session.status = SessionStatus.PAUSED.value
    session.state = _normalize_state(session.state, session.status)
    session.modified = datetime.now().isoformat()
    return session


def get_child_sessions(parent_session_id: str, base_path: Optional[Path] = None) -> List[WorkSession]:
    """Get direct child sessions for a parent session."""
    sessions = list_sessions(base_path=base_path)
    return [
        session for session in sessions
        if (session.parent_wsession_id or session.parent_session_id) == parent_session_id
    ]


def get_open_child_sessions(parent_session_id: str, base_path: Optional[Path] = None) -> List[WorkSession]:
    """Get child sessions that are not closed."""
    return [
        session for session in get_child_sessions(parent_session_id, base_path=base_path)
        if session.state in {"running", "paused"}
    ]


def find_session_by_id(session_id: str, base_path: Optional[Path] = None) -> Optional[tuple[WorkSession, Path]]:
    """Find a session by full ID or prefix."""
    base_path = get_sessions_base_path(base_path)
    if not base_path.exists():
        return None

    for session_dir in base_path.iterdir():
        if session_dir.is_dir() and session_id.startswith(session_dir.name):
            session_file = session_dir / "session.json"
            if session_file.exists():
                return load_session(session_file), session_file
        if session_dir.is_dir():
            for nested_dir in session_dir.iterdir():
                if nested_dir.is_dir() and session_id.startswith(nested_dir.name):
                    session_file = nested_dir / "session.json"
                    if session_file.exists():
                        return load_session(session_file), session_file
    return None


def _register_child_session(base_path: Path, parent_session_id: str, child_session_id: str) -> None:
    """Register a child session ID on the parent session if possible."""
    parent_path = base_path / parent_session_id / "session.json"
    if not parent_path.exists():
        return
    try:
        parent_session = load_session(parent_path)
    except Exception as exc:
        logging.warning("Failed to load parent session %s: %s", parent_session_id, exc)
        return

    if child_session_id not in parent_session.children_wsession_ids:
        parent_session.children_wsession_ids.append(child_session_id)
        save_session(parent_session, parent_path)


def load_breadcrumb_settings(settings_path: str = "docs/Settings.md") -> Dict[str, Any]:
    """
    Load breadcrumb settings from Settings.md.

    Args:
        settings_path: Path to the settings file

    Returns:
        Dictionary with breadcrumb settings
    """
    # Default settings
    default_settings = {
        "breadcrumb_enabled": True,
        "breadcrumb_auto_write": True,
        "breadcrumb_include_tool_results": True,
        "breadcrumb_max_response_length": 50000,
        "breadcrumb_cost_tracking": True
    }

    try:
        # Check if settings file exists
        if not Path(settings_path).exists():
            logging.info(f"Settings file {settings_path} not found. Using defaults.")
            return default_settings

        # Read the settings file
        with open(settings_path, 'r') as f:
            content = f.read()

        # Simple parsing for markdown settings section
        lines = content.split('\n')
        settings_section = False
        settings_data = {}

        for line in lines:
            if line.strip().startswith('## Work Session Settings'):
                settings_section = True
                continue

            if settings_section and line.strip().startswith('#'):
                # Stop when we reach another header
                break

            # Look for key: value pairs
            if settings_section and ':' in line and line.strip()[0] not in ['#', '-', '*']:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()

                    # Convert value to appropriate type
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    elif value.replace('.', '').isdigit():
                        value = float(value)

                    settings_data[key] = value

        # Merge with defaults
        final_settings = default_settings.copy()
        final_settings.update(settings_data)

        return final_settings
    except Exception as e:
        logging.error(f"Error loading breadcrumb settings: {e}")
        return default_settings


def is_breadcrumb_enabled(settings_path: str = "docs/Settings.md") -> bool:
    """
    Check if breadcrumbs are enabled in the settings.

    Args:
        settings_path: Path to the settings file

    Returns:
        Boolean indicating if breadcrumbs are enabled
    """
    settings = load_breadcrumb_settings(settings_path)
    return settings.get("breadcrumb_enabled", True)
