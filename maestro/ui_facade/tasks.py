"""
UI Facade for Task Operations

This module provides structured data access to task information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Callable
import json
import os
from datetime import datetime
import threading
import queue
from maestro.session_model import Session, load_session, Subtask
from maestro.engines import get_engine, EngineResult
import subprocess
import signal


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


# Global execution state tracking
_execution_state = {
    "is_running": False,
    "current_task_id": None,
    "interrupt_requested": False,
    "thread": None
}


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


def run_tasks(session_id: str, limit: Optional[int] = None, on_status_change: Optional[Callable] = None,
              on_output: Optional[Callable] = None, sessions_dir: str = "./.maestro/sessions") -> bool:
    """
    Run tasks in the session.

    Args:
        session_id: ID of the session containing the tasks
        limit: Optional limit on number of tasks to run
        on_status_change: Optional callback for status changes
        on_output: Optional callback for output streaming
        sessions_dir: Directory containing session files

    Returns:
        True if successful, False if interrupted or failed
    """
    global _execution_state

    # Check if execution is already running
    if _execution_state["is_running"]:
        return False

    # Get the session
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    # Note: This function doesn't exist in our import scope, so we skip it for now
    # migrate_session_if_needed(session)

    # Determine active plan and get tasks to run
    active_plan_id = session.active_plan_id
    active_plan = None
    if active_plan_id:
        for plan in session.plans:
            if plan.plan_id == active_plan_id:
                active_plan = plan
                break

    # If no active plan exists, raise an error
    if not active_plan:
        raise ValueError("Cannot execute tasks: No active plan exists.")

    # Validate that the active plan is not dead
    if active_plan and active_plan.status == "dead":
        raise ValueError(f"Cannot execute tasks: Active plan '{active_plan_id}' is marked as dead.")

    # Determine eligible subtasks from the active plan only
    pending_subtasks = [
        subtask for subtask in session.subtasks
        if subtask.status == "pending" and subtask.plan_id == active_plan_id
    ]

    interrupted_subtasks = []
    # Only include interrupted if we're resuming, not running from scratch
    # For now, we'll focus on pending tasks
    eligible_subtasks = pending_subtasks

    # Apply execution limit if specified
    if limit is not None and limit > 0:
        target_subtasks = eligible_subtasks[:limit]
    else:
        target_subtasks = eligible_subtasks

    # If no tasks to process, return
    if not target_subtasks:
        if on_status_change:
            on_status_change("No tasks to process")
        return True

    # Set execution state
    _execution_state["is_running"] = True
    _execution_state["interrupt_requested"] = False

    # Create outputs directory for the session
    import os
    from pathlib import Path
    maestro_dir = os.path.join(sessions_dir, session_id[:8])  # Simplified for this facade
    outputs_dir = os.path.join(maestro_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    # Also create partials directory in the maestro directory
    partials_dir = os.path.join(maestro_dir, "partials")
    os.makedirs(partials_dir, exist_ok=True)

    # Process each target subtask in order
    tasks_processed = 0
    for i, subtask in enumerate(target_subtasks):
        # Check for interrupt
        if _execution_state["interrupt_requested"]:
            session.status = "interrupted"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
            if on_status_change:
                on_status_change(f"Execution interrupted at task {i+1}/{len(target_subtasks)}")
            _execution_state["is_running"] = False
            return False

        # Update current task
        _execution_state["current_task_id"] = subtask.id

        if on_status_change:
            on_status_change(f"Running task {i+1}/{len(target_subtasks)}: {subtask.title}")

        # Set the summary file path if not already set
        if not subtask.summary_file:
            subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

        # Change subtask status to in_progress
        subtask.status = "in_progress"
        session.updated_at = datetime.now().isoformat()
        save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

        # Simulate a basic prompt for the task - in a real implementation this would be more complex
        prompt = f"Complete the subtask: {subtask.title}\nDescription: {subtask.description}\nWrite a summary to file: {subtask.summary_file}"

        # Look up the worker engine
        try:
            # Instead of using stream_output=False, we'll allow streaming by using a custom callback
            # In a real implementation, the engine would need to support real-time output
            def output_callback(text):
                if on_output:
                    on_output(f"[{subtask.id}] {text}")

            engine = get_engine(subtask.worker_model + "_worker", debug=False, stream_output=False)
        except ValueError:
            # If we don't have the specific model with "_worker" suffix, try directly
            try:
                engine = get_engine(subtask.worker_model, debug=False, stream_output=False)
            except ValueError:
                if on_status_change:
                    on_status_change(f"Unknown worker model '{subtask.worker_model}' for task {subtask.id}")
                subtask.status = "error"
                session.updated_at = datetime.now().isoformat()
                save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
                _execution_state["is_running"] = False
                return False

        # Call engine.generate(prompt) with interruption handling
        try:
            # For now, we'll simulate output as the engine.generate call is complex to handle interruption
            # In a real implementation, this would call the engine with a streaming callback
            if on_output:
                on_output(f"Processing task {subtask.id}: {subtask.title}\n")

            # Simulate task processing with interruption check
            # In a real implementation, the engine would handle the interruption
            output = f"Output for task {subtask.id}: {subtask.title}\nThis is simulated output for demonstration.\n"

            # If we had a real streaming implementation, we would call the on_output callback
            # at intervals during processing
            simulated_chunks = [
                f"Starting task {subtask.id}...\n",
                f"Processing step 1 for {subtask.title}\n",
                f"Processing step 2 for {subtask.title}\n",
                f"Completing task {subtask.id}\n"
            ]

            for chunk in simulated_chunks:
                if _execution_state["interrupt_requested"]:
                    break
                if on_output:
                    on_output(chunk)

            # Save the output to the designated file
            output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(output)

            # Create a summary file as well
            with open(subtask.summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Summary for task {subtask.id}: Completed successfully")

        except KeyboardInterrupt:
            # Handle user interruption
            subtask.status = "interrupted"
            session.status = "interrupted"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

            # Save partial output if available
            partial_filename = os.path.join(partials_dir, f"worker_{subtask.id}.partial.txt")
            with open(partial_filename, 'w', encoding='utf-8') as f:
                f.write(output if 'output' in locals() else "")

            # Also create an empty summary file to prevent error on resume
            if subtask.summary_file and not os.path.exists(subtask.summary_file):
                with open(subtask.summary_file, 'w', encoding='utf-8') as f:
                    f.write("")

            if on_status_change:
                on_status_change(f"Task {subtask.id} interrupted by user")
            _execution_state["is_running"] = False
            return False
        except Exception as e:
            if on_status_change:
                on_status_change(f"Error processing task {subtask.id}: {str(e)}")
            subtask.status = "error"
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
            _execution_state["is_running"] = False
            return False

        # Mark subtask.status as "done"
        subtask.status = "done"
        session.updated_at = datetime.now().isoformat()
        tasks_processed += 1

        # Update status after task completion
        if on_status_change:
            on_status_change(f"Completed task {subtask.id}: {subtask.title}")

    # Update session status based on subtask completion
    all_done = all(subtask.status == "done" for subtask in session.subtasks if subtask.plan_id == active_plan_id)
    if all_done and any(subtask.plan_id == active_plan_id for subtask in session.subtasks):
        session.status = "done"
    else:
        session.status = "in_progress"

    # Save the updated session
    save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

    _execution_state["is_running"] = False
    _execution_state["current_task_id"] = None
    if on_status_change:
        on_status_change(f"Processed {tasks_processed} tasks. Session status: {session.status}")

    return True


def resume_tasks(session_id: str, limit: Optional[int] = None, on_status_change: Optional[Callable] = None,
                 on_output: Optional[Callable] = None, sessions_dir: str = "./.maestro/sessions") -> bool:
    """
    Resume tasks in the session that were interrupted.

    Args:
        session_id: ID of the session containing the tasks
        limit: Optional limit on number of tasks to resume
        on_status_change: Optional callback for status changes
        on_output: Optional callback for output streaming
        sessions_dir: Directory containing session files

    Returns:
        True if successful, False if interrupted or failed
    """
    global _execution_state

    # Check if execution is already running
    if _execution_state["is_running"]:
        return False

    # Get the session
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Determine active plan
    active_plan_id = session.active_plan_id
    active_plan = None
    if active_plan_id:
        for plan in session.plans:
            if plan.plan_id == active_plan_id:
                active_plan = plan
                break

    # If no active plan exists, raise an error
    if not active_plan:
        raise ValueError("Cannot resume tasks: No active plan exists.")

    # Validate that the active plan is not dead
    if active_plan and active_plan.status == "dead":
        raise ValueError(f"Cannot resume tasks: Active plan '{active_plan_id}' is marked as dead.")

    # Get interrupted subtasks from the active plan
    interrupted_subtasks = [
        subtask for subtask in session.subtasks
        if subtask.status == "interrupted" and subtask.plan_id == active_plan_id
    ]

    # Apply execution limit if specified
    if limit is not None and limit > 0:
        target_subtasks = interrupted_subtasks[:limit]
    else:
        target_subtasks = interrupted_subtasks

    # If no tasks to process, return
    if not target_subtasks:
        if on_status_change:
            on_status_change("No interrupted tasks to resume")
        return True

    # Set execution state
    _execution_state["is_running"] = True
    _execution_state["interrupt_requested"] = False

    # Create outputs directory for the session
    import os
    maestro_dir = os.path.join(sessions_dir, session_id[:8])  # Simplified for this facade
    outputs_dir = os.path.join(maestro_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    # Also create partials directory in the maestro directory
    partials_dir = os.path.join(maestro_dir, "partials")
    os.makedirs(partials_dir, exist_ok=True)

    # Process each target subtask in order
    tasks_processed = 0
    for i, subtask in enumerate(target_subtasks):
        # Check for interrupt
        if _execution_state["interrupt_requested"]:
            session.status = "interrupted"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
            if on_status_change:
                on_status_change(f"Resume interrupted at task {i+1}/{len(target_subtasks)}")
            _execution_state["is_running"] = False
            return False

        # Update current task
        _execution_state["current_task_id"] = subtask.id

        if on_status_change:
            on_status_change(f"Resuming task {i+1}/{len(target_subtasks)}: {subtask.title}")

        # Change subtask status to in_progress
        subtask.status = "in_progress"
        session.updated_at = datetime.now().isoformat()
        save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

        # Load partial output to inject into the next prompt (simplified)
        partial_filename = os.path.join(partials_dir, f"worker_{subtask.id}.partial.txt")
        partial_output_content = ""
        if os.path.exists(partial_filename):
            with open(partial_filename, 'r', encoding='utf-8') as f:
                partial_output_content = f.read().strip()

        # Set the summary file path if not already set
        if not subtask.summary_file:
            subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

        # Look up the worker engine
        try:
            engine = get_engine(subtask.worker_model + "_worker", debug=False, stream_output=False)
        except ValueError:
            # If we don't have the specific model with "_worker" suffix, try directly
            try:
                engine = get_engine(subtask.worker_model, debug=False, stream_output=False)
            except ValueError:
                if on_status_change:
                    on_status_change(f"Unknown worker model '{subtask.worker_model}' for task {subtask.id}")
                subtask.status = "error"
                session.updated_at = datetime.now().isoformat()
                save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
                _execution_state["is_running"] = False
                return False

        # Call engine.generate(prompt) with interruption handling
        try:
            # For now, we'll simulate output as the engine.generate call is complex to handle interruption
            if on_output:
                on_output(f"Resuming task {subtask.id}: {subtask.title}\n")

            # Simulate task processing with interruption check
            output = f"Resumed output for task {subtask.id}: {subtask.title}\nContinuing from partial result: {partial_output_content[:100] if partial_output_content else 'None'}\n"

            # If we had a real streaming implementation, we would call the on_output callback
            # at intervals during processing
            simulated_chunks = [
                f"Starting resume for task {subtask.id}...\n",
                f"Continuing from partial result: {partial_output_content[:50] if partial_output_content else 'None'}...\n",
                f"Processing step 1 for {subtask.title}\n",
                f"Processing step 2 for {subtask.title}\n",
                f"Completing resumed task {subtask.id}\n"
            ]

            for chunk in simulated_chunks:
                if _execution_state["interrupt_requested"]:
                    break
                if on_output:
                    on_output(chunk)

            # Save the output to the designated file
            output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(output)

            # Update summary file
            with open(subtask.summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Resume summary for task {subtask.id}: Resumed successfully")

        except KeyboardInterrupt:
            # Handle user interruption
            subtask.status = "interrupted"
            session.status = "interrupted"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

            # Save partial output if available
            partial_filename = os.path.join(partials_dir, f"worker_{subtask.id}.partial.txt")
            with open(partial_filename, 'w', encoding='utf-8') as f:
                f.write(output if 'output' in locals() else "")

            if on_status_change:
                on_status_change(f"Task {subtask.id} interrupted by user during resume")
            _execution_state["is_running"] = False
            return False
        except Exception as e:
            if on_status_change:
                on_status_change(f"Error resuming task {subtask.id}: {str(e)}")
            subtask.status = "error"
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))
            _execution_state["is_running"] = False
            return False

        # Mark subtask.status as "done"
        subtask.status = "done"
        session.updated_at = datetime.now().isoformat()
        tasks_processed += 1

        # Update status after task completion
        if on_status_change:
            on_status_change(f"Resumed task {subtask.id}: {subtask.title}")

    # Update session status based on subtask completion
    all_done = all(subtask.status in ["done"] for subtask in session.subtasks if subtask.plan_id == active_plan_id)
    if all_done and any(subtask.plan_id == active_plan_id for subtask in session.subtasks):
        session.status = "done"
    else:
        session.status = "in_progress"

    # Save the updated session
    save_session(session, os.path.join(sessions_dir, f"{session.id}.json"))

    _execution_state["is_running"] = False
    _execution_state["current_task_id"] = None
    if on_status_change:
        on_status_change(f"Resumed {tasks_processed} tasks. Session status: {session.status}")

    return True


def stop_tasks() -> bool:
    """
    Request graceful stop of current execution.

    Returns:
        True if stop was requested, False if no execution was running
    """
    global _execution_state

    if _execution_state["is_running"]:
        _execution_state["interrupt_requested"] = True
        return True
    return False


def get_current_execution_state() -> dict:
    """
    Get current execution state information.

    Returns:
        Dictionary with execution state information
    """
    global _execution_state
    return {
        "is_running": _execution_state["is_running"],
        "current_task_id": _execution_state["current_task_id"],
        "interrupt_requested": _execution_state["interrupt_requested"]
    }


def get_task_logs(task_id: str, session_id: str, sessions_dir: str = "./.maestro/sessions") -> str:
    """
    Get logs for a specific task.

    Args:
        task_id: ID of the task
        session_id: ID of the session
        sessions_dir: Directory containing session files

    Returns:
        Log content as string
    """
    import os
    maestro_dir = os.path.join(sessions_dir, session_id[:8])  # Simplified for this facade
    outputs_dir = os.path.join(maestro_dir, "outputs")

    # Look for output files associated with the task
    output_file_path = os.path.join(outputs_dir, f"{task_id}.txt")
    partial_file_path = os.path.join(maestro_dir, "partials", f"worker_{task_id}.partial.txt")

    log_content = ""

    # Add output file content if it exists
    if os.path.exists(output_file_path):
        with open(output_file_path, 'r', encoding='utf-8') as f:
            log_content += f.read()

    # Add partial file content if it exists (for interrupted tasks)
    if os.path.exists(partial_file_path):
        with open(partial_file_path, 'r', encoding='utf-8') as f:
            log_content += f"\n--- PARTIAL OUTPUT ---\n{f.read()}"

    return log_content if log_content else f"No logs available for task {task_id}"


def save_session(session: Session, path: str) -> None:
    '''
    Save a session to the specified JSON file path.
    This is a copy of the function from session_model to avoid circular imports.
    '''
    import json
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(session.to_dict(), f, indent=2)