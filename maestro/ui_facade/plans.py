"""
UI Facade for Plan Operations

This module provides structured data access to plan information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from maestro.session_model import Session, load_session, PlanNode, save_session


@dataclass
class PlanInfo:
    """Basic information about a plan."""
    plan_id: str
    label: str
    status: str
    created_at: str
    parent_plan_id: Optional[str]
    subtask_count: int


@dataclass
class PlanTreeNode:
    """Tree structure representing a plan and its hierarchy."""
    plan_id: str
    label: str
    status: str
    created_at: str
    parent_plan_id: Optional[str]
    children: List['PlanTreeNode']
    subtasks: List[str]  # List of subtask IDs


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


def list_plans(session_id: str, sessions_dir: str = "./.maestro/sessions") -> List[PlanInfo]:
    """
    List all plans for a specific session.

    Args:
        session_id: ID of the session containing the plans
        sessions_dir: Directory containing session files

    Returns:
        List of plan information

    Raises:
        ValueError: If session with given ID is not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    plans_info = []
    for plan_node in session.plans:
        plans_info.append(PlanInfo(
            plan_id=plan_node.plan_id,
            label=plan_node.label,
            status=plan_node.status,
            created_at=plan_node.created_at,
            parent_plan_id=plan_node.parent_plan_id,
            subtask_count=len(plan_node.subtask_ids)
        ))

    return plans_info


def get_active_plan(session_id: str, sessions_dir: str = "./.maestro/sessions") -> Optional[PlanInfo]:
    """
    Get the active plan for a specific session.

    Args:
        session_id: ID of the session
        sessions_dir: Directory containing session files

    Returns:
        Information about the active plan or None
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None or session.active_plan_id is None:
        return None

    for plan_node in session.plans:
        if plan_node.plan_id == session.active_plan_id:
            return PlanInfo(
                plan_id=plan_node.plan_id,
                label=plan_node.label,
                status=plan_node.status,
                created_at=plan_node.created_at,
                parent_plan_id=plan_node.parent_plan_id,
                subtask_count=len(plan_node.subtask_ids)
            )

    return None


def get_plan_tree(session_id: str, sessions_dir: str = "./.maestro/sessions") -> PlanTreeNode:
    """
    Get the complete plan tree for a session, with roots being plans without parents.
    
    Args:
        session_id: ID of the session containing the plans
        sessions_dir: Directory containing session files

    Returns:
        Root plan tree node with all plans organized hierarchically
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Create a mapping of all plans by ID
    plan_map = {plan.plan_id: plan for plan in session.plans}
    
    # Create tree nodes for all plans
    nodes_map = {}
    for plan_id, plan_obj in plan_map.items():
        nodes_map[plan_id] = PlanTreeNode(
            plan_id=plan_obj.plan_id,
            label=plan_obj.label,
            status=plan_obj.status,
            created_at=plan_obj.created_at,
            parent_plan_id=plan_obj.parent_plan_id,
            children=[],
            subtasks=plan_obj.subtask_ids
        )
    
    # Build the tree structure by linking children to parents
    root_nodes = []
    for plan_id, node in nodes_map.items():
        if node.parent_plan_id and node.parent_plan_id in nodes_map:
            # This is a child node, add it to its parent's children
            parent_node = nodes_map[node.parent_plan_id]
            parent_node.children.append(node)
        else:
            # This is a root node (no parent or parent not found)
            root_nodes.append(node)
    
    # If we have multiple roots, create a virtual root
    if len(root_nodes) == 0:
        # No plans in session
        raise ValueError(f"No plans found in session '{session_id}'")
    elif len(root_nodes) == 1:
        # Single root plan
        return root_nodes[0]
    else:
        # Multiple root plans - create a virtual root with children
        # Just use the first root as the main root, and put others under it for display purposes
        main_root = root_nodes[0]
        # Add remaining roots as children of the first root
        for root in root_nodes[1:]:
            main_root.children.append(root)
        return main_root


def set_active_plan(session_id: str, plan_id: str, sessions_dir: str = "./.maestro/sessions") -> PlanInfo:
    """
    Set the specified plan as active for the session.
    
    Args:
        session_id: ID of the session
        plan_id: ID of the plan to set as active
        sessions_dir: Directory containing session files
    
    Returns:
        Updated PlanInfo for the active plan
        
    Raises:
        ValueError: If session or plan is not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Check if the plan exists in this session
    plan_exists = any(plan.plan_id == plan_id for plan in session.plans)
    if not plan_exists:
        raise ValueError(f"Plan with ID '{plan_id}' not found in session '{session_id}'")

    # Set the active plan ID
    session.active_plan_id = plan_id
    
    # Find the session file and update it
    session_files = _find_session_files(sessions_dir)
    for session_file in session_files:
        try:
            temp_session = load_session(session_file)
            if temp_session.id == session_id:
                # Update the session file with the new active plan
                temp_session.active_plan_id = plan_id
                save_session(temp_session, session_file)
                break
        except Exception:
            continue
    
    # Return updated plan info
    for plan_node in session.plans:
        if plan_node.plan_id == plan_id:
            return PlanInfo(
                plan_id=plan_node.plan_id,
                label=plan_node.label,
                status=plan_node.status,
                created_at=plan_node.created_at,
                parent_plan_id=plan_node.parent_plan_id,
                subtask_count=len(plan_node.subtask_ids)
            )
    
    # Should not reach here if plan existed
    raise ValueError(f"Unexpected error: Plan '{plan_id}' not found")


def kill_plan(session_id: str, plan_id: str, sessions_dir: str = "./.maestro/sessions") -> None:
    """
    Mark the specified plan as dead.
    
    Args:
        session_id: ID of the session
        plan_id: ID of the plan to mark as dead
        sessions_dir: Directory containing session files
        
    Raises:
        ValueError: If session or plan is not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Find the plan to mark as dead
    target_plan = None
    for plan_node in session.plans:
        if plan_node.plan_id == plan_id:
            target_plan = plan_node
            break

    if target_plan is None:
        raise ValueError(f"Plan with ID '{plan_id}' not found in session '{session_id}'")

    # Mark the plan as dead
    target_plan.status = "dead"

    # Find the session file and update it
    session_files = _find_session_files(sessions_dir)
    for session_file in session_files:
        try:
            temp_session = load_session(session_file)
            if temp_session.id == session_id:
                # Update the plan status in the stored session
                for stored_plan in temp_session.plans:
                    if stored_plan.plan_id == plan_id:
                        stored_plan.status = "dead"
                        break
                save_session(temp_session, session_file)
                break
        except Exception:
            continue


def get_plan_details(session_id: str, plan_id: str, sessions_dir: str = "./.maestro/sessions") -> PlanInfo:
    """
    Get detailed information about a specific plan.
    
    Args:
        session_id: ID of the session
        plan_id: ID of the plan to get details for
        sessions_dir: Directory containing session files
    
    Returns:
        Detailed information about the plan
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    for plan_node in session.plans:
        if plan_node.plan_id == plan_id:
            return PlanInfo(
                plan_id=plan_node.plan_id,
                label=plan_node.label,
                status=plan_node.status,
                created_at=plan_node.created_at,
                parent_plan_id=plan_node.parent_plan_id,
                subtask_count=len(plan_node.subtask_ids)
            )

    raise ValueError(f"Plan with ID '{plan_id}' not found in session '{session_id}'")