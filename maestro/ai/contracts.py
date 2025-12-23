"""JSON contracts for different scopes in Maestro AI interactions."""

from enum import Enum
from typing import Any, Callable, Dict, List
from .discuss_router import JsonContract, PatchOperationType


class ContractType(Enum):
    """Types of contracts for different scopes."""
    TRACK = "track"
    PHASE = "phase"
    TASK = "task"
    GLOBAL = "global"


def validate_track_json(data: Any) -> bool:
    """Validate JSON for track operations."""
    if isinstance(data, dict):
        op_type = data.get("op_type", data.get("operation", data.get("type", "")))
        if op_type in ["add_track", "add_phase", "add_task", "mark_done", "mark_todo"]:
            return True
        # Validate specific track operations
        if op_type == "add_track":
            return "track_name" in data
        elif op_type == "add_phase":
            return "phase_name" in data and "track_id" in data
        elif op_type == "add_task":
            return "task_name" in data and "phase_id" in data
    elif isinstance(data, list):
        return all(validate_track_json(item) for item in data)
    return False


def validate_phase_json(data: Any) -> bool:
    """Validate JSON for phase operations."""
    if isinstance(data, dict):
        op_type = data.get("op_type", data.get("operation", data.get("type", "")))
        if op_type in ["add_phase", "add_task", "move_task", "edit_task_fields", "mark_done", "mark_todo"]:
            return True
        # Validate specific phase operations
        if op_type == "add_phase":
            return "phase_name" in data and "track_id" in data
        elif op_type == "add_task":
            return "task_name" in data and "phase_id" in data
        elif op_type == "move_task":
            return "task_id" in data and "target_phase_id" in data
    elif isinstance(data, list):
        return all(validate_phase_json(item) for item in data)
    return False


def validate_task_json(data: Any) -> bool:
    """Validate JSON for task operations."""
    if isinstance(data, dict):
        op_type = data.get("op_type", data.get("operation", data.get("type", "")))
        if op_type in ["add_task", "move_task", "edit_task_fields", "mark_done", "mark_todo"]:
            return True
        # Validate specific task operations
        if op_type == "add_task":
            return "task_name" in data and "phase_id" in data
        elif op_type == "edit_task_fields":
            return "task_id" in data and "fields" in data
        elif op_type == "move_task":
            return "task_id" in data and "target_phase_id" in data
    elif isinstance(data, list):
        return all(validate_task_json(item) for item in data)
    return False


def validate_global_json(data: Any) -> bool:
    """Validate JSON for global operations (read-only or proposal only)."""
    if isinstance(data, dict):
        op_type = data.get("op_type", data.get("operation", data.get("type", "")))
        # For global discussions, only allow read operations or proposals
        if op_type in ["add_track", "add_phase", "add_task", "move_task", "edit_task_fields", "mark_done", "mark_todo"]:
            return True  # We allow these but they should be applied with caution
    elif isinstance(data, list):
        return all(validate_global_json(item) for item in data)
    return False


# Define the contracts
TrackContract = JsonContract(
    schema_id="track_operations",
    validation_func=validate_track_json,
    allowed_operations=[
        PatchOperationType.ADD_TRACK,
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ],
    description="Operations allowed when discussing tracks - can add tracks, phases, and tasks"
)


PhaseContract = JsonContract(
    schema_id="phase_operations",
    validation_func=validate_phase_json,
    allowed_operations=[
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ],
    description="Operations allowed when discussing phases - can add phases and tasks, move tasks"
)


TaskContract = JsonContract(
    schema_id="task_operations",
    validation_func=validate_task_json,
    allowed_operations=[
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ],
    description="Operations allowed when discussing tasks - can add, move, edit, and mark tasks"
)


GlobalContract = JsonContract(
    schema_id="global_operations",
    validation_func=validate_global_json,
    allowed_operations=[
        PatchOperationType.ADD_TRACK,
        PatchOperationType.ADD_PHASE,
        PatchOperationType.ADD_TASK,
        PatchOperationType.MOVE_TASK,
        PatchOperationType.EDIT_TASK_FIELDS,
        PatchOperationType.MARK_DONE,
        PatchOperationType.MARK_TODO,
    ],
    description="Operations allowed for global discussions - all operations but should be applied with caution"
)