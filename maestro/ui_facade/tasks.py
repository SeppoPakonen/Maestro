"""
UI Facade for Task Operations

This module provides structured data access to task information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from maestro.session_model import Session, load_session, Subtask


@dataclass
class TaskInfo:
    """Information about a task."""
    id: str
    title: str
    description: str
    status: str
    planner_model: str
    worker_model: str
    summary_file: str
    categories: List[str]
    plan_id: Optional[str]


@dataclass
class TaskStatus:
    """Status information for a task."""
    id: str
    status: str
    title: str
    is_completed: bool


def _find_session_files(sessions_dir: str = "./.maestro/sessions") -> List[str]:
    """Find all session JSON files in the specified directory."""
    if not os.path.exists(sessions_dir):
        return []
    
    session_files = []
    for filename in os.listdir(sessions_dir):
        if filename.endswith('.json'):
            session_files.append(os.path.join(sessions_dir, filename))
    return session_files


def _find_session_by_id(session_id: str, sessions_dir: str = "./.maestro/sessions") -> Optional[Session]:
    """Find a session by its ID."""
    session_files = _find_session_files(sessions_dir)
    
    for session_file in session_files:
        try:
            session = load_session(session_file)
            if session.id == session_id:
                return session
        except Exception:
            # Skip corrupted or inaccessible session files
            continue
    
    return None


def list_tasks(session_id: str, plan_id: Optional[str] = None, sessions_dir: str = "./.maestro/sessions") -> List[TaskInfo]:
    """
    List all tasks for a specific session, optionally filtered by plan.
    
    Args:
        session_id: ID of the session containing the tasks
        plan_id: Optional plan ID to filter tasks
        sessions_dir: Directory containing session files
        
    Returns:
        List of task information
        
    Raises:
        ValueError: If session with given ID is not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")
    
    tasks_info = []
    for subtask in session.subtasks:
        # If plan_id is specified, only include tasks that belong to that plan
        if plan_id is None or subtask.plan_id == plan_id:
            tasks_info.append(TaskInfo(
                id=subtask.id,
                title=subtask.title,
                description=subtask.description,
                status=subtask.status,
                planner_model=subtask.planner_model,
                worker_model=subtask.worker_model,
                summary_file=subtask.summary_file,
                categories=subtask.categories,
                plan_id=subtask.plan_id
            ))
    
    return tasks_info


def get_task_status(session_id: str, task_id: str, sessions_dir: str = "./.maestro/sessions") -> TaskStatus:
    """
    Get the status of a specific task.
    
    Args:
        session_id: ID of the session containing the task
        task_id: ID of the task to retrieve
        sessions_dir: Directory containing session files
        
    Returns:
        Task status information
        
    Raises:
        ValueError: If session or task with given IDs are not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")
    
    for subtask in session.subtasks:
        if subtask.id == task_id:
            return TaskStatus(
                id=subtask.id,
                status=subtask.status,
                title=subtask.title,
                is_completed=subtask.status == "done"
            )
    
    raise ValueError(f"Task with ID '{task_id}' not found in session '{session_id}'")