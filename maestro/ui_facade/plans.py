"""
UI Facade for Plan Operations

This module provides structured data access to plan information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from maestro.session_model import Session, load_session, PlanNode


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


def get_plan_tree(session_id: str, plan_id: str, sessions_dir: str = "./.maestro/sessions") -> PlanTreeNode:
    """
    Get a plan as a tree node with its hierarchy.
    
    Args:
        session_id: ID of the session containing the plan
        plan_id: ID of the plan to retrieve
        sessions_dir: Directory containing session files
        
    Returns:
        Plan tree node with children and subtasks
        
    Raises:
        ValueError: If session or plan with given IDs are not found
    """
    session = _find_session_by_id(session_id, sessions_dir)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")
    
    plan_map = {plan.plan_id: plan for plan in session.plans}
    if plan_id not in plan_map:
        raise ValueError(f"Plan with ID '{plan_id}' not found in session '{session_id}'")
    
    plan = plan_map[plan_id]
    
    # Find direct children of this plan
    children = []
    for potential_child_id, potential_child_plan in plan_map.items():
        if potential_child_plan.parent_plan_id == plan_id:
            child_node = get_plan_tree(session_id, potential_child_id, sessions_dir)
            children.append(child_node)
    
    return PlanTreeNode(
        plan_id=plan.plan_id,
        label=plan.label,
        status=plan.status,
        created_at=plan.created_at,
        parent_plan_id=plan.parent_plan_id,
        children=children,
        subtasks=plan.subtask_ids
    )