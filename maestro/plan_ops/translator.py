"""
Translator for the Plan Operations pipeline.

This module implements the translator that converts validated PlanOpsResult
actions into typed operations.
"""

from typing import List, Dict, Any
from .operations import Selector, CreatePlan, DeletePlan, AddPlanItem, RemovePlanItem, Commentary
from .decoder import DecodeError


def create_selector(selector_dict: Dict[str, Any]) -> Selector:
    """Create a Selector object from a dictionary."""
    title = selector_dict.get("title")
    index = selector_dict.get("index")
    
    if title is not None and index is not None:
        # If both are provided, they should match - for now we'll require exactly one
        raise DecodeError("Selector must have either title or index, not both")
    
    if title is None and index is None:
        raise DecodeError("Selector must have either title or index")
    
    return Selector(title=title, index=index)


def actions_to_ops(plan_ops_result: Dict[str, Any]) -> List:
    """
    Translate PlanOpsResult actions into typed operations.

    Args:
        plan_ops_result: The validated PlanOpsResult dictionary

    Returns:
        A list of operation objects
    """
    if plan_ops_result.get("scope") != "plan":
        raise DecodeError(f"Invalid scope: {plan_ops_result.get('scope')}, expected 'plan'")

    actions = plan_ops_result.get("actions", [])
    ops = []

    for action in actions:
        action_type = action.get("action")

        if action_type == "plan_create":
            title = action.get("title")
            if not title:
                raise DecodeError("plan_create action requires 'title'")
            ops.append(CreatePlan(title=title))

        elif action_type == "plan_delete":
            selector_dict = action.get("selector", {})
            selector = create_selector(selector_dict)
            ops.append(DeletePlan(selector=selector))

        elif action_type == "plan_item_add":
            selector_dict = action.get("selector", {})
            selector = create_selector(selector_dict)
            text = action.get("text")
            if not text:
                raise DecodeError("plan_item_add action requires 'text'")
            ops.append(AddPlanItem(selector=selector, text=text))

        elif action_type == "plan_item_remove":
            selector_dict = action.get("selector", {})
            selector = create_selector(selector_dict)
            item_index = action.get("item_index")
            if item_index is None:
                raise DecodeError("plan_item_remove action requires 'item_index'")
            ops.append(RemovePlanItem(selector=selector, item_index=item_index))

        elif action_type == "commentary":
            text = action.get("text")
            if not text:
                raise DecodeError("commentary action requires 'text'")
            ops.append(Commentary(text=text))

        else:
            raise DecodeError(f"Unknown action type: {action_type}")

    return ops