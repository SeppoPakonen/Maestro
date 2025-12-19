"""
UI Facade for Phase Operations

This module provides structured data access to phase information using markdown backend without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from pathlib import Path
from maestro.session_model import Session, load_session, PlanNode, save_session
from maestro.data import parse_todo_md, parse_done_md, parse_phase_md, parse_config_md


@dataclass
class PhaseInfo:
    """Basic information about a phase."""
    phase_id: str
    label: str
    status: str
    created_at: str
    parent_phase_id: Optional[str]
    subtask_count: int


@dataclass
class PhaseTreeNode:
    """Tree structure representing a phase and its hierarchy."""
    phase_id: str
    label: str
    status: str
    created_at: str
    parent_phase_id: Optional[str]
    children: List['PhaseTreeNode']
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


def _get_phase_status_from_emoji(emoji_status: Optional[str]) -> str:
    """Convert emoji status to internal status string."""
    if not emoji_status:
        return "planned"

    status_mapping = {
        "✅": "done",
        "🚧": "in_progress",
        "📋": "planned",
        "💡": "proposed"
    }
    return status_mapping.get(emoji_status, "planned")


def get_phase_tree(session_id: Optional[str] = None) -> PhaseTreeNode:
    """
    Get the complete phase tree, with roots being phases without parents.

    Args:
        session_id: Optional session ID (not used in markdown backend)

    Returns:
        Root phase tree node with all phases organized hierarchically
    """
    # First try markdown backend
    try:
        tracks_data = parse_todo_md("docs/todo.md")

        # Create a mapping of all phases by ID for building the tree
        phase_nodes_map = {}

        # First, create all phase nodes
        for track in tracks_data.get('tracks', []):
            track_name = track.get('name', 'Unnamed Track')
            for phase_data in track.get('phases', []):
                phase_id = phase_data.get('phase_id', track_name.replace(' ', '_'))
                phase_name = phase_data.get('name', phase_id)

                # Create a PhaseTreeNode from the phase data
                phase_node = PhaseTreeNode(
                    phase_id=phase_id,
                    label=phase_name,
                    status=_get_phase_status_from_emoji(phase_data.get('status_emoji')),
                    created_at=phase_data.get('created_at', ''),
                    parent_phase_id=None,  # For now, phases are top-level within tracks
                    children=[],  # Will fill this in next step
                    subtasks=[]  # Using empty list for now, or phase_data.get('tasks', [])
                )

                phase_nodes_map[phase_id] = phase_node

        # Now build the tree structure by linking children to parents
        # In the current markdown format, we don't have explicit parent-child relationships
        # So each track will be a root-level node with its phases as children
        root_nodes = []
        for track in tracks_data.get('tracks', []):
            track_name = track.get('name', 'Unnamed Track')
            track_id = track_name.replace(' ', '_')

            # Create a track node that will contain all phases in this track
            track_node = PhaseTreeNode(
                phase_id=track_id,
                label=track_name,
                status="planned",  # Track status is aggregate of phase statuses
                created_at=track.get('created_at', ''),
                parent_phase_id=None,
                children=[],
                subtasks=[]
            )

            # Add all phases in this track as children of the track node
            for phase_data in track.get('phases', []):
                phase_id = phase_data.get('phase_id', track_name.replace(' ', '_'))
                if phase_id in phase_nodes_map:
                    phase_node = phase_nodes_map[phase_id]
                    phase_node.parent_phase_id = track_id  # Set parent for the phase
                    track_node.children.append(phase_node)

            root_nodes.append(track_node)

        # If we have multiple roots, create a virtual root
        if len(root_nodes) == 0:
            # No phases in session
            raise ValueError("No phases found in docs/todo.md")
        elif len(root_nodes) == 1:
            # Single root (one track)
            return root_nodes[0]
        else:
            # Multiple root tracks - create a virtual root
            virtual_root = PhaseTreeNode(
                phase_id="virtual_root",
                label="All Tracks",
                status="planned",
                created_at="",
                parent_phase_id=None,
                children=root_nodes,
                subtasks=[]
            )
            return virtual_root
    except Exception as e:
        # Fallback to JSON backend if markdown files don't exist
        print(f"Warning: Using fallback JSON backend due to: {e}")
        # This maintains backward compatibility
        return _get_phase_tree_json_backend(session_id)


def _get_phase_tree_json_backend(session_id: Optional[str] = None) -> PhaseTreeNode:
    """Fallback implementation using JSON backend for backward compatibility."""
    if session_id is None:
        raise ValueError("Session ID is required for JSON backend")

    # Find session by ID using original method
    session = _find_session_by_id(session_id)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Create a mapping of all plans by ID
    plan_map = {plan.plan_id: plan for plan in session.plans}

    # Create tree nodes for all plans
    nodes_map = {}
    for plan_id, plan_obj in plan_map.items():
        nodes_map[plan_id] = PhaseTreeNode(
            phase_id=plan_obj.plan_id,
            label=plan_obj.label,
            status=plan_obj.status,
            created_at=plan_obj.created_at,
            parent_phase_id=plan_obj.parent_plan_id,
            children=[],
            subtasks=plan_obj.subtask_ids
        )

    # Build the tree structure by linking children to parents
    root_nodes = []
    for plan_id, node in nodes_map.items():
        if node.parent_phase_id and node.parent_phase_id in nodes_map:
            # This is a child node, add it to its parent's children
            parent_node = nodes_map[node.parent_phase_id]
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


def list_phases(session_id: Optional[str] = None) -> List[PhaseInfo]:
    """
    Get list of all phases from docs/todo.md

    Args:
        session_id: Optional session ID (not used in markdown backend)

    Returns:
        List of phase information
    """
    try:
        tracks_data = parse_todo_md("docs/todo.md")

        phases_info = []
        for track in tracks_data.get('tracks', []):
            for phase_data in track.get('phases', []):
                phase_id = phase_data.get('phase_id', track.get('name', 'Unnamed').replace(' ', '_'))
                phase_name = phase_data.get('name', phase_id)

                phase_info = PhaseInfo(
                    phase_id=phase_id,
                    label=phase_name,
                    status=_get_phase_status_from_emoji(phase_data.get('status_emoji')),
                    created_at=phase_data.get('created_at', ''),
                    parent_phase_id=None,
                    subtask_count=len(phase_data.get('tasks', []))
                )
                phases_info.append(phase_info)

        return phases_info
    except Exception as e:
        # Fallback to JSON backend
        print(f"Warning: Using fallback JSON backend due to: {e}")
        return _list_phases_json_backend(session_id)


def _list_phases_json_backend(session_id: Optional[str] = None) -> List[PhaseInfo]:
    """Fallback implementation using JSON backend for backward compatibility."""
    if session_id is None:
        return []

    session = _find_session_by_id(session_id)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    phases_info = []
    for plan_node in session.plans:
        phases_info.append(PhaseInfo(
            phase_id=plan_node.plan_id,
            label=plan_node.label,
            status=plan_node.status,
            created_at=plan_node.created_at,
            parent_phase_id=plan_node.parent_plan_id,
            subtask_count=len(plan_node.subtask_ids)
        ))

    return phases_info


def get_phase_details(phase_id: str) -> Optional[PhaseInfo]:
    """
    Get details for a specific phase from markdown files

    Args:
        phase_id: ID of the phase to get details for

    Returns:
        Detailed information about the phase or None
    """
    try:
        # First check in todo.md
        tracks_data = parse_todo_md("docs/todo.md")

        for track in tracks_data.get('tracks', []):
            for phase_data in track.get('phases', []):
                if phase_data.get('phase_id') == phase_id:
                    return PhaseInfo(
                        phase_id=phase_data.get('phase_id', phase_id),
                        label=phase_data.get('name', phase_id),
                        status=_get_phase_status_from_emoji(phase_data.get('status_emoji')),
                        created_at=phase_data.get('created_at', ''),
                        parent_phase_id=None,  # No parent in current structure
                        subtask_count=len(phase_data.get('tasks', []))
                    )

        # If not found in todo, check in done.md
        done_tracks_data = parse_done_md("docs/done.md")
        for track in done_tracks_data.get('tracks', []):
            for phase_data in track.get('phases', []):
                if phase_data.get('phase_id') == phase_id:
                    return PhaseInfo(
                        phase_id=phase_data.get('phase_id', phase_id),
                        label=phase_data.get('name', phase_id),
                        status=_get_phase_status_from_emoji(phase_data.get('status_emoji')),
                        created_at=phase_data.get('created_at', ''),
                        parent_phase_id=None,
                        subtask_count=len(phase_data.get('tasks', []))
                    )

        # If individual phase file exists, parse that too
        phase_file_path = f"docs/phases/{phase_id}.md"
        if os.path.exists(phase_file_path):
            phase_data = parse_phase_md(phase_file_path)
            if phase_data.get('phase_id') == phase_id:
                return PhaseInfo(
                    phase_id=phase_data.get('phase_id', phase_id),
                    label=phase_data.get('name', phase_id),
                    status=_get_phase_status_from_emoji(phase_data.get('status_emoji')),
                    created_at=phase_data.get('created_at', ''),
                    parent_phase_id=None,
                    subtask_count=len(phase_data.get('tasks', []))
                )

        return None
    except Exception as e:
        # Fallback to JSON backend
        print(f"Warning: Using fallback JSON backend due to: {e}")
        return _get_phase_details_json_backend(phase_id)


def _get_phase_details_json_backend(phase_id: str) -> Optional[PhaseInfo]:
    """Fallback implementation using JSON backend for backward compatibility."""
    # This would require searching through all sessions which is inefficient
    # For now, return None to indicate phase not found in JSON
    return None


def get_active_phase(session_id: str) -> Optional[PhaseInfo]:
    """
    Get the active phase for a session from docs/config.md

    Args:
        session_id: ID of the session

    Returns:
        Information about the active phase or None
    """
    try:
        config_data = parse_config_md("docs/config.md")

        # Get active phase from config, which might be stored differently depending on format
        active_phase_id = config_data.get('active_phase_id') or config_data.get('active_phase')

        if active_phase_id:
            return get_phase_details(active_phase_id)

        return None
    except Exception as e:
        # Fallback to JSON backend
        print(f"Warning: Using fallback JSON backend due to: {e}")
        return _get_active_phase_json_backend(session_id)


def _get_active_phase_json_backend(session_id: str) -> Optional[PhaseInfo]:
    """Fallback implementation using JSON backend for backward compatibility."""
    session = _find_session_by_id(session_id)
    if session is None or session.active_plan_id is None:
        return None

    for plan_node in session.plans:
        if plan_node.plan_id == session.active_plan_id:
            return PhaseInfo(
                phase_id=plan_node.plan_id,
                label=plan_node.label,
                status=plan_node.status,
                created_at=plan_node.created_at,
                parent_phase_id=plan_node.parent_plan_id,
                subtask_count=len(plan_node.subtask_ids)
            )

    return None


def set_active_phase(session_id: str, phase_id: str) -> PhaseInfo:
    """
    Set the active phase in docs/config.md

    Args:
        session_id: ID of the session
        phase_id: ID of the phase to set as active

    Returns:
        Updated PhaseInfo for the active phase
    """
    try:
        # For now, we'll update the config markdown file
        # A proper implementation would use a markdown writer
        config_path = Path("docs/config.md")
        if not config_path.exists():
            # Create basic config file if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            content = f'## Configuration\n\n"active_phase_id": "{phase_id}"\n'
            config_path.write_text(content)
        else:
            # Read existing content and update the active phase
            content = config_path.read_text()
            # This is a simplified approach; in a real implementation,
            # we'd want to properly update the markdown structure
            import re
            # Try to find and replace the active_phase_id value
            updated_content = re.sub(r'"active_phase_id":\s*"[^"]*"', f'"active_phase_id": "{phase_id}"', content)
            if updated_content == content:
                # If no replacement was made, append the active phase
                updated_content = content.strip() + f'\n\n"active_phase_id": "{phase_id}"\n'
            config_path.write_text(updated_content)

        # Return updated phase info
        phase_details = get_phase_details(phase_id)
        if not phase_details:
            # Create a basic PhaseInfo object if we can't get details
            phase_details = PhaseInfo(
                phase_id=phase_id,
                label=phase_id,
                status="active",  # Set as active
                created_at="",
                parent_phase_id=None,
                subtask_count=0
            )
        return phase_details
    except Exception as e:
        # Fallback to JSON backend
        print(f"Warning: Using fallback JSON backend due to: {e}")
        return _set_active_phase_json_backend(session_id, phase_id)


def _set_active_phase_json_backend(session_id: str, phase_id: str) -> PhaseInfo:
    """Fallback implementation using JSON backend for backward compatibility."""
    session = _find_session_by_id(session_id)
    if session is None:
        raise ValueError(f"Session with ID '{session_id}' not found")

    # Check if the phase exists in this session
    phase_exists = any(plan.plan_id == phase_id for plan in session.plans)
    if not phase_exists:
        raise ValueError(f"Phase with ID '{phase_id}' not found in session '{session_id}'")

    # Set the active plan ID
    session.active_plan_id = phase_id

    # Find the session file and update it
    session_files = _find_session_files()
    for session_file in session_files:
        try:
            temp_session = load_session(session_file)
            if temp_session.id == session_id:
                # Update the session file with the new active plan
                temp_session.active_plan_id = phase_id
                save_session(temp_session, session_file)
                break
        except Exception:
            continue

    # Return updated phase info
    for plan_node in session.plans:
        if plan_node.plan_id == phase_id:
            return PhaseInfo(
                phase_id=plan_node.plan_id,
                label=plan_node.label,
                status=plan_node.status,
                created_at=plan_node.created_at,
                parent_phase_id=plan_node.parent_plan_id,
                subtask_count=len(plan_node.subtask_ids)
            )

    # Should not reach here if phase existed
    raise ValueError(f"Unexpected error: Phase '{phase_id}' not found")


def kill_phase(phase_id: str) -> None:
    """
    Mark a phase as killed/cancelled in docs/todo.md

    Args:
        phase_id: ID of the phase to mark as killed
    """
    try:
        # Read todo.md and update the phase status
        # This is a simplified approach; in a real implementation,
        # we'd want to properly update the markdown structure
        todo_path = Path("docs/todo.md")
        if todo_path.exists():
            content = todo_path.read_text()
            # For now we'll just indicate the change - a proper implementation
            # would use a markdown writer to update the specific phase status
            print(f"Marking phase {phase_id} as killed in todo.md - implementation needed")
        else:
            raise FileNotFoundError("docs/todo.md not found")
    except Exception as e:
        # Fallback to JSON backend
        print(f"Warning: Using fallback JSON backend due to: {e}")
        _kill_phase_json_backend(phase_id)


def _kill_phase_json_backend(phase_id: str) -> None:
    """Fallback implementation using JSON backend for backward compatibility."""
    # Since we don't have the session context, this is a simplified version
    # A more complete implementation would need to search across all sessions
    import glob
    session_files = glob.glob("./.maestro/sessions/*.json")

    for session_file in session_files:
        try:
            session = load_session(session_file)
            # Find the phase to mark as dead
            target_plan = None
            for plan_node in session.plans:
                if plan_node.plan_id == phase_id:
                    target_plan = plan_node
                    break

            if target_plan is not None:
                # Mark the plan as dead
                target_plan.status = "dead"
                # Update the session file with the changes
                save_session(session, session_file)
                return  # Found and updated the phase
        except Exception:
            continue  # Skip corrupted session files