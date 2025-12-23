"""
Translator for the Project Operations pipeline.

This module implements the translator that converts validated ProjectOpsResult
actions into typed operations.
"""

from typing import List, Dict, Any
from .operations import CreateTrack, CreatePhase, CreateTask, MoveTaskToDone, SetContext
from .decoder import DecodeError


def actions_to_ops(project_ops_result: Dict[str, Any]) -> List:
    """
    Translate ProjectOpsResult actions into typed operations.

    Args:
        project_ops_result: The validated ProjectOpsResult dictionary

    Returns:
        A list of operation objects
    """
    if project_ops_result.get("scope") != "project":
        raise DecodeError(f"Invalid scope: {project_ops_result.get('scope')}, expected 'project'")

    actions = project_ops_result.get("actions", [])
    ops = []

    for action in actions:
        action_type = action.get("action")

        if action_type == "track_create":
            title = action.get("title")
            if not title:
                raise DecodeError("track_create action requires 'title'")
            ops.append(CreateTrack(title=title))

        elif action_type == "phase_create":
            track = action.get("track")
            title = action.get("title")
            if not track or not title:
                raise DecodeError("phase_create action requires 'track' and 'title'")
            ops.append(CreatePhase(track=track, title=title))

        elif action_type == "task_create":
            track = action.get("track")
            phase = action.get("phase")
            title = action.get("title")
            if not track or not phase or not title:
                raise DecodeError("task_create action requires 'track', 'phase', and 'title'")
            ops.append(CreateTask(track=track, phase=phase, title=title))

        elif action_type == "task_move_to_done":
            track = action.get("track")
            phase = action.get("phase")
            task = action.get("task")
            if not track or not phase or not task:
                raise DecodeError("task_move_to_done action requires 'track', 'phase', and 'task'")
            ops.append(MoveTaskToDone(track=track, phase=phase, task=task))

        elif action_type == "context_set":
            current_track = action.get("current_track")
            current_phase = action.get("current_phase")
            current_task = action.get("current_task")
            ops.append(SetContext(
                current_track=current_track,
                current_phase=current_phase,
                current_task=current_task
            ))

        else:
            raise DecodeError(f"Unknown action type: {action_type}")

    return ops