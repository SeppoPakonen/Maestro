"""
JSON Schemas for the Project Operations pipeline.

This module defines the contract for canonical ProjectOpsResult JSON:
- Single canonical JSON object that Maestro consumes
- No nested JSON or engine-specific wrapping
"""

from typing import Dict, Any, List, Union
import json


def validate_project_ops_result(data: Union[str, Dict]) -> Dict[str, Any]:
    """
    Validate data against the canonical ProjectOpsResult schema.

    Args:
        data: Either a JSON string or parsed dict to validate

    Returns:
        The validated data as a dict

    Raises:
        ValueError: If validation fails
        json.JSONDecodeError: If string input is not valid JSON
    """
    if isinstance(data, str):
        data = json.loads(data)

    # Check required fields
    if not isinstance(data, dict):
        raise ValueError("ProjectOpsResult data must be a dictionary")

    required_fields = ["kind", "version", "scope", "actions"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in ProjectOpsResult")

    # Validate field types and values
    if data["kind"] != "project_ops":
        raise ValueError(f"Invalid kind '{data['kind']}', expected 'project_ops'")

    if not isinstance(data["version"], (str, int)):
        raise ValueError(f"Version must be string or integer, got {type(data['version'])}")

    if data["scope"] != "project":
        raise ValueError(f"Invalid scope '{data['scope']}', expected 'project'")

    # Check for additional properties
    allowed_fields = {"kind", "version", "scope", "actions", "notes"}
    for key in data.keys():
        if key not in allowed_fields:
            raise ValueError(f"Unexpected field '{key}' in ProjectOpsResult")

    # Validate actions
    if not isinstance(data["actions"], list):
        raise ValueError(f"Actions must be a list, got {type(data['actions'])}")

    # Define valid action types and their required fields
    valid_actions = {
        "track_create": {"required": ["action", "title"], "optional": []},
        "phase_create": {"required": ["action", "track", "title"], "optional": []},
        "task_create": {"required": ["action", "track", "phase", "title"], "optional": []},
        "task_move_to_done": {"required": ["action", "track", "phase", "task"], "optional": []},
        "context_set": {"required": ["action"], "optional": ["current_track", "current_phase", "current_task"]}
    }

    for i, action in enumerate(data["actions"]):
        if not isinstance(action, dict):
            raise ValueError(f"Action at index {i} must be a dictionary")

        if "action" not in action:
            raise ValueError(f"Action at index {i} missing 'action' field")

        action_type = action["action"]
        if action_type not in valid_actions:
            raise ValueError(f"Unknown action type '{action_type}' at index {i}")

        # Check required fields
        required_fields = valid_actions[action_type]["required"]
        for field in required_fields:
            if field not in action:
                raise ValueError(f"Action '{action_type}' at index {i} missing required field '{field}'")

        # Validate field types
        if action_type == "track_create" and not isinstance(action["title"], str):
            raise ValueError(f"Title in 'track_create' action at index {i} must be a string")

        if action_type == "phase_create":
            if not isinstance(action["track"], str):
                raise ValueError(f"Track in 'phase_create' action at index {i} must be a string")
            if not isinstance(action["title"], str):
                raise ValueError(f"Title in 'phase_create' action at index {i} must be a string")

        if action_type == "task_create":
            if not isinstance(action["track"], str):
                raise ValueError(f"Track in 'task_create' action at index {i} must be a string")
            if not isinstance(action["phase"], str):
                raise ValueError(f"Phase in 'task_create' action at index {i} must be a string")
            if not isinstance(action["title"], str):
                raise ValueError(f"Title in 'task_create' action at index {i} must be a string")

        if action_type == "task_move_to_done":
            if not isinstance(action["track"], str):
                raise ValueError(f"Track in 'task_move_to_done' action at index {i} must be a string")
            if not isinstance(action["phase"], str):
                raise ValueError(f"Phase in 'task_move_to_done' action at index {i} must be a string")
            if not isinstance(action["task"], str):
                raise ValueError(f"Task in 'task_move_to_done' action at index {i} must be a string")

        if action_type == "context_set":
            for key in ["current_track", "current_phase", "current_task"]:
                if key in action and not isinstance(action[key], str):
                    raise ValueError(f"Field '{key}' in 'context_set' action at index {i} must be a string")

    return data