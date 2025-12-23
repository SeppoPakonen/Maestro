"""
JSON Schemas for the Plan Operations pipeline.

This module defines the contract for canonical PlanOpsResult JSON:
- Single canonical JSON object that Maestro consumes
- No nested JSON or engine-specific wrapping
"""

from typing import Dict, Any, List, Union
import json


def validate_plan_ops_result(data: Union[str, Dict]) -> Dict[str, Any]:
    """
    Validate data against the canonical PlanOpsResult schema.

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
        raise ValueError("PlanOpsResult data must be a dictionary")

    required_fields = ["kind", "version", "scope", "actions"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in PlanOpsResult")

    # Validate field types and values
    if data["kind"] != "plan_ops":
        raise ValueError(f"Invalid kind '{data['kind']}', expected 'plan_ops'")

    if not isinstance(data["version"], (str, int)):
        raise ValueError(f"Version must be string or integer, got {type(data['version'])}")

    if data["scope"] != "plan":
        raise ValueError(f"Invalid scope '{data['scope']}', expected 'plan'")

    # Check for additional properties
    allowed_fields = {"kind", "version", "scope", "actions", "notes"}
    for key in data.keys():
        if key not in allowed_fields:
            raise ValueError(f"Unexpected field '{key}' in PlanOpsResult")

    # Validate actions
    if not isinstance(data["actions"], list):
        raise ValueError(f"Actions must be a list, got {type(data['actions'])}")

    # Define valid action types and their required fields
    valid_actions = {
        "plan_create": {"required": ["action", "title"], "optional": []},
        "plan_delete": {"required": ["action", "selector"], "optional": []},
        "plan_item_add": {"required": ["action", "selector", "text"], "optional": []},
        "plan_item_remove": {"required": ["action", "selector", "item_index"], "optional": []},
        "commentary": {"required": ["action", "text"], "optional": []}
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

        # Validate selector if present
        if "selector" in action:
            selector = action["selector"]
            if not isinstance(selector, dict):
                raise ValueError(f"Selector in action '{action_type}' at index {i} must be a dictionary")

            # Selector must have exactly one of 'title' or 'index'
            selector_keys = set(selector.keys())
            valid_selector_keys = {"title", "index"}

            if not selector_keys.issubset(valid_selector_keys):
                raise ValueError(f"Selector in action '{action_type}' at index {i} has invalid keys: {selector_keys - valid_selector_keys}")

            if len(selector_keys) != 1:
                raise ValueError(f"Selector in action '{action_type}' at index {i} must have exactly one key, got {selector_keys}")

            if "title" in selector and not isinstance(selector["title"], str):
                raise ValueError(f"Selector title in action '{action_type}' at index {i} must be a string")

            if "index" in selector:
                if not isinstance(selector["index"], int):
                    raise ValueError(f"Selector index in action '{action_type}' at index {i} must be an integer")
                if selector["index"] < 1:
                    raise ValueError(f"Selector index in action '{action_type}' at index {i} must be >= 1")

        # Validate specific field types
        if action_type in ["plan_create", "commentary"] and "text" in action:
            raise ValueError(f"Action '{action_type}' at index {i} should not have 'text' field")

        if action_type == "plan_create" and not isinstance(action["title"], str):
            raise ValueError(f"Title in 'plan_create' action at index {i} must be a string")

        if action_type in ["plan_item_add", "commentary"] and not isinstance(action["text"], str):
            raise ValueError(f"Text in '{action_type}' action at index {i} must be a string")

        if action_type == "plan_item_remove" and not isinstance(action["item_index"], int):
            raise ValueError(f"Item_index in 'plan_item_remove' action at index {i} must be an integer")

        if action_type == "plan_item_remove" and action["item_index"] < 1:
            raise ValueError(f"Item_index in 'plan_item_remove' action at index {i} must be >= 1")

    return data