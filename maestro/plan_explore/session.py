"""
Session infrastructure for Plan Explore work sessions.
This module handles the persistence and management of explore sessions.
"""
import json
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from ..work_session import WorkSession, create_session, load_session, save_session, SessionType


class ExploreIterationStatus(Enum):
    """Status of an explore iteration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    APPLIED = "applied"


@dataclass
class ExploreIteration:
    """Represents a single iteration in the explore session."""
    index: int
    prompt_hash: str
    prompt: Optional[str] = None  # Only stored if save_session is enabled
    ai_response: Optional[str] = None  # The raw AI response
    project_ops_json: Optional[Dict[str, Any]] = None  # Validated project_ops JSON
    validation_result: Optional[Dict[str, Any]] = None  # Validation details
    preview_summary: Optional[List[str]] = None  # Preview changes
    applied: bool = False  # Whether the operations were applied
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None  # Error message if any


@dataclass
class ExploreSession:
    """Session for Plan Explore work with detailed iteration tracking."""
    session_id: str
    selected_plans: List[str]  # List of plan titles/numbers
    engine: str = "qwen"
    max_iterations: int = 3
    current_iteration: int = 0
    iterations: List[ExploreIteration] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "running"  # running, paused, completed, interrupted
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional flexible metadata


def _ensure_dir_exists(path: Path) -> None:
    """Ensure directory exists, creating it if needed."""
    path.mkdir(parents=True, exist_ok=True)


def create_explore_session(
    selected_plans: List[str],
    engine: str = "qwen",
    max_iterations: int = 3,
    base_path: Optional[Path] = None
) -> ExploreSession:
    """
    Create new explore session.

    Args:
        selected_plans: List of plan titles/numbers to explore
        engine: AI engine to use
        max_iterations: Maximum number of iterations
        base_path: Base directory for sessions (defaults to docs/sessions/)

    Returns:
        ExploreSession object representing the newly created session
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Determine base path
    if base_path is None:
        base_path = Path("docs") / "sessions"

    # Create explore session directory: docs/sessions/explore/<session-id>/
    session_dir = base_path / "explore" / session_id
    _ensure_dir_exists(session_dir)

    # Create breadcrumbs directory
    breadcrumbs_dir = session_dir / "breadcrumbs"
    _ensure_dir_exists(breadcrumbs_dir)

    # Create explore session instance
    session = ExploreSession(
        session_id=session_id,
        selected_plans=selected_plans,
        engine=engine,
        max_iterations=max_iterations,
        current_iteration=0,
        created=timestamp,
        modified=timestamp,
        status="running"
    )

    # Save initial explore_session.json
    session_path = session_dir / "explore_session.json"
    save_explore_session(session, session_path)

    # Also create a regular work session for tracking
    work_session = create_session(
        session_type="explore",
        related_entity={"explore_session_id": session_id, "plans": selected_plans},
        metadata={"engine": engine, "max_iterations": max_iterations}
    )

    logging.info(f"Created new explore session: {session_id}")
    return session


def load_explore_session(session_path: Union[str, Path]) -> ExploreSession:
    """
    Load existing explore session from disk.

    Args:
        session_path: Path to explore_session.json file

    Returns:
        ExploreSession object loaded from the file

    Raises:
        FileNotFoundError: If session file doesn't exist
        json.JSONDecodeError: If session file contains invalid JSON
        KeyError: If required fields are missing from session data
    """
    path = Path(session_path)
    if not path.exists():
        raise FileNotFoundError(f"Explore session file does not exist: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert iterations back to ExploreIteration objects
    iterations = []
    for iteration_data in data.get("iterations", []):
        iteration = ExploreIteration(
            index=iteration_data["index"],
            prompt_hash=iteration_data["prompt_hash"],
            prompt=iteration_data.get("prompt"),
            ai_response=iteration_data.get("ai_response"),
            project_ops_json=iteration_data.get("project_ops_json"),
            validation_result=iteration_data.get("validation_result"),
            preview_summary=iteration_data.get("preview_summary"),
            applied=iteration_data.get("applied", False),
            timestamp=iteration_data.get("timestamp", datetime.now().isoformat()),
            error=iteration_data.get("error")
        )
        iterations.append(iteration)

    # Create ExploreSession instance from dictionary data
    session = ExploreSession(
        session_id=data["session_id"],
        selected_plans=data["selected_plans"],
        engine=data.get("engine", "qwen"),
        max_iterations=data.get("max_iterations", 3),
        current_iteration=data.get("current_iteration", 0),
        iterations=iterations,
        created=data.get("created", datetime.now().isoformat()),
        modified=data.get("modified", datetime.now().isoformat()),
        status=data.get("status", "running"),
        metadata=data.get("metadata", {})
    )

    logging.info(f"Loaded explore session: {session.session_id}")
    return session


def save_explore_session(session: ExploreSession, session_path: Union[str, Path]) -> None:
    """
    Save explore session updates to disk using atomic write.

    Args:
        session: ExploreSession object to save
        session_path: Path where explore_session.json will be saved
    """
    path = Path(session_path)

    # Update modified timestamp
    session.modified = datetime.now().isoformat()

    # Convert to dict, handling the iterations properly
    session_dict = {
        "session_id": session.session_id,
        "selected_plans": session.selected_plans,
        "engine": session.engine,
        "max_iterations": session.max_iterations,
        "current_iteration": session.current_iteration,
        "iterations": [
            {
                "index": iteration.index,
                "prompt_hash": iteration.prompt_hash,
                "prompt": iteration.prompt,
                "ai_response": iteration.ai_response,
                "project_ops_json": iteration.project_ops_json,
                "validation_result": iteration.validation_result,
                "preview_summary": iteration.preview_summary,
                "applied": iteration.applied,
                "timestamp": iteration.timestamp,
                "error": iteration.error
            }
            for iteration in session.iterations
        ],
        "created": session.created,
        "modified": session.modified,
        "status": session.status,
        "metadata": session.metadata
    }

    # Prepare temporary file path for atomic write
    temp_path = path.with_suffix('.tmp')

    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(session_dict, f, indent=2)

    # Atomically rename the temporary file to the target file
    temp_path.rename(path)

    logging.info(f"Saved explore session: {session.session_id}")


def add_iteration_to_session(
    session: ExploreSession,
    iteration: ExploreIteration
) -> ExploreSession:
    """
    Add an iteration to the explore session.

    Args:
        session: The explore session to update
        iteration: The iteration to add

    Returns:
        Updated ExploreSession object
    """
    # Add the iteration
    session.iterations.append(iteration)
    
    # Update current iteration
    session.current_iteration = iteration.index + 1
    
    # Update status based on iteration result
    if iteration.error:
        session.status = "failed"
    elif session.current_iteration >= session.max_iterations:
        session.status = "completed"
    else:
        session.status = "running"
    
    return session


def resume_explore_session(session_id: str, base_path: Optional[Path] = None) -> ExploreSession:
    """
    Resume an existing explore session.

    Args:
        session_id: ID of the session to resume
        base_path: Base directory for sessions (defaults to docs/sessions/)

    Returns:
        Loaded ExploreSession object ready for resumption
    """
    if base_path is None:
        base_path = Path("docs") / "sessions"

    # Find the session directory
    session_dir = base_path / "explore" / session_id
    session_file = session_dir / "explore_session.json"

    if not session_file.exists():
        raise FileNotFoundError(f"Explore session {session_id} not found")

    session = load_explore_session(session_file)
    
    # Update status to running
    session.status = "running"
    
    logging.info(f"Resumed explore session: {session.session_id}")
    return session


def complete_explore_session(session: ExploreSession) -> ExploreSession:
    """
    Mark an explore session as completed.

    Args:
        session: Session to complete

    Returns:
        Updated ExploreSession object
    """
    session.status = "completed"
    session.modified = datetime.now().isoformat()

    logging.info(f"Completed explore session: {session.session_id}")
    return session


def interrupt_explore_session(session: ExploreSession, reason: Optional[str] = None) -> ExploreSession:
    """
    Handle interruption of an explore session.

    Args:
        session: Session to interrupt
        reason: Optional reason for interruption

    Returns:
        Updated ExploreSession object
    """
    session.status = "interrupted"
    session.modified = datetime.now().isoformat()

    # Add interruption reason to metadata if provided
    if reason:
        session.metadata["interruption_reason"] = reason

    logging.info(f"Interrupted explore session: {session.session_id}, reason: {reason}")
    return session