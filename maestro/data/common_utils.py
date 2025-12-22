"""
Common data handling utilities for Maestro CLI.

This module provides unified functions for parsing, data handling,
and common operations that are used across multiple CLI modules.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import sys

from maestro.data import parse_todo_md, parse_done_md


def parse_todo_safe(todo_path: Path, verbose: bool = False) -> Optional[dict]:
    """Safely parse a todo.md file with error handling."""
    try:
        return parse_todo_md(str(todo_path))
    except Exception as exc:
        if verbose:
            print(f"Verbose: Error parsing {todo_path}: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error parsing {todo_path}. Use --verbose for more details.")
        return None


def parse_done_safe(done_path: Path, verbose: bool = False) -> Optional[dict]:
    """Safely parse a done.md file with error handling."""
    try:
        return parse_done_md(str(done_path))
    except Exception as exc:
        if verbose:
            print(f"Verbose: Error parsing {done_path}: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error parsing {done_path}. Use --verbose for more details.")
        return None


def get_all_tracks_with_phases_and_tasks(verbose: bool = False) -> List[Dict[str, Any]]:
    """Get all tracks with their phases and tasks from both todo.md and done.md."""
    todo_path = Path('docs/todo.md')
    done_path = Path('docs/done.md')

    all_tracks = []

    # Process done.md first to get precedence phases
    done_phase_ids = set()  # Track which phase IDs we've seen in done.md
    processed_track_map = {}  # Map of track_id to track data to consolidate

    # Parse done.md and store its phases with precedence
    if done_path.exists():
        try:
            done_data = parse_done_md(str(done_path))
            for track in done_data.get('tracks', []):
                track_id = track.get('track_id')
                if track_id not in processed_track_map:
                    processed_track_map[track_id] = {
                        'name': track.get('name', 'Unknown Track'),
                        'track_id': track_id,
                        'description': track.get('description', []),
                        'phases': []
                    }

                for phase in track.get('phases', []):
                    phase_id = phase.get('phase_id')
                    if phase_id:
                        done_phase_ids.add(phase_id)
                        # Add this phase to its track
                        processed_track_map[track_id]['phases'].append(phase)
        except Exception as e:
            print(f"Warning: Error parsing {done_path}: {e}")

    # Parse todo.md and add only phases that weren't in done.md
    if todo_path.exists():
        try:
            todo_data = parse_todo_md(str(todo_path))
            for track in todo_data.get('tracks', []):
                track_id = track.get('track_id')
                if track_id not in processed_track_map:
                    processed_track_map[track_id] = {
                        'name': track.get('name', 'Unknown Track'),
                        'track_id': track_id,
                        'description': track.get('description', []),
                        'phases': []
                    }

                for phase in track.get('phases', []):
                    phase_id = phase.get('phase_id')
                    if phase_id and phase_id not in done_phase_ids:
                        # Add phase from todo.md only if not present in done.md
                        processed_track_map[track_id]['phases'].append(phase)
        except Exception as e:
            print(f"Warning: Error parsing {todo_path}: {e}")

    # Add all processed tracks to all_tracks
    all_tracks.extend(processed_track_map.values())

    return all_tracks


def resolve_identifier_by_type(identifier: str, item_type: str, verbose: bool = False) -> Optional[str]:
    """
    Resolve an identifier (number or ID) to the appropriate ID based on type.
    
    Args:
        identifier: Either a number (1, 2, 3) or ID (umk, cli-tpt)
        item_type: 'track', 'phase', or 'task'
        
    Returns:
        Item ID if found, None otherwise
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return None

    data = parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return None
    
    if item_type == 'track':
        items = data.get('tracks', [])
        if identifier.isdigit():
            index = int(identifier) - 1
            if 0 <= index < len(items):
                return items[index].get('track_id')
            return None

        for item in items:
            if item.get('track_id') == identifier:
                return identifier
    elif item_type == 'phase':
        # Get all phases across all tracks
        all_phases = []
        for track in data.get('tracks', []):
            for phase in track.get('phases', []):
                all_phases.append(phase)
        
        if identifier.isdigit():
            index = int(identifier) - 1
            if 0 <= index < len(all_phases):
                return all_phases[index].get('phase_id')
            return None

        for phase in all_phases:
            if phase.get('phase_id') == identifier:
                return identifier
    elif item_type == 'task':
        # Get all tasks across all phases and tracks
        all_tasks = []
        for track in data.get('tracks', []):
            for phase in track.get('phases', []):
                for task in phase.get('tasks', []):
                    all_tasks.append(task)
        
        if identifier.isdigit():
            index = int(identifier) - 1
            if 0 <= index < len(all_tasks):
                return all_tasks[index].get('task_id')
            return None

        for task in all_tasks:
            if task.get('task_id') == identifier:
                return identifier

    return None


def filter_items_by_track(items: List[Dict[str, Any]], track_id: str) -> List[Dict[str, Any]]:
    """Filter a list of items (phases or tasks) by track ID."""
    return [item for item in items if item.get('_track_id') == track_id]


def get_available_ids(item_type: str, verbose: bool = False) -> List[str]:
    """Get available IDs for a specific item type (track, phase, task)."""
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return []
    
    data = parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return []
    
    if item_type == 'track':
        return [track.get('track_id') for track in data.get('tracks', []) if track.get('track_id')]
    elif item_type == 'phase':
        phase_ids = []
        for track in data.get('tracks', []):
            for phase in track.get('phases', []):
                phase_id = phase.get('phase_id')
                if phase_id:
                    phase_ids.append(phase_id)
        return phase_ids
    elif item_type == 'task':
        task_ids = []
        for track in data.get('tracks', []):
            for phase in track.get('phases', []):
                for task in phase.get('tasks', []):
                    task_id = task.get('task_id')
                    if task_id:
                        task_ids.append(task_id)
        return task_ids
    
    return []


def print_error(message: str, exit_code: int = 1):
    """Print an error message to stderr and optionally exit."""
    print(f"Error: {message}", file=sys.stderr)
    if exit_code:
        sys.exit(exit_code)


def print_warning(message: str):
    """Print a warning message to stderr."""
    print(f"Warning: {message}", file=sys.stderr)


def print_info(message: str):
    """Print an informational message."""
    print(message)