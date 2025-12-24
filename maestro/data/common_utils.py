"""
Common data handling utilities for Maestro CLI.

This module provides unified functions for parsing, data handling,
and common operations that are used across multiple CLI modules.

Updated to use JSON storage instead of markdown.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import sys

# Keep markdown imports for backward compatibility / fallback
from maestro.data import parse_todo_md, parse_done_md

# Import JSON storage
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track, Phase, Task


def _track_to_dict(track: Track, phases: List[Phase] = None, tasks: List[Task] = None) -> Dict[str, Any]:
    """Convert a Track dataclass to the dict format expected by commands."""
    track_dict = {
        'track_id': track.track_id,
        'name': track.name,
        'status': track.status,
        'completion': track.completion,
        'description': track.description if isinstance(track.description, list) else [track.description] if track.description else [],
        'priority': track.priority,
        'phases': []
    }

    # If phases provided, convert them
    if phases:
        for phase in phases:
            if phase.track_id == track.track_id:
                phase_dict = _phase_to_dict(phase, tasks)
                track_dict['phases'].append(phase_dict)

    return track_dict


def _phase_to_dict(phase: Phase, tasks: List[Task] = None) -> Dict[str, Any]:
    """Convert a Phase dataclass to the dict format expected by commands."""
    phase_dict = {
        'phase_id': phase.phase_id,
        'name': phase.name,
        'status': phase.status,
        'completion': phase.completion,
        'description': phase.description if isinstance(phase.description, list) else [phase.description] if phase.description else [],
        'track_id': phase.track_id,
        'priority': phase.priority,
        'tasks': []
    }

    # If tasks provided, convert them
    if tasks:
        for task in tasks:
            if task.phase_id == phase.phase_id:
                task_dict = _task_to_dict(task)
                phase_dict['tasks'].append(task_dict)

    return phase_dict


def _task_to_dict(task: Task) -> Dict[str, Any]:
    """Convert a Task dataclass to the dict format expected by commands."""
    return {
        'task_id': task.task_id,
        'name': task.name,
        'status': task.status,
        'completed': task.completed,
        'priority': task.priority,
        'estimated_hours': task.estimated_hours,
        'description': task.description if isinstance(task.description, list) else [task.description] if task.description else [],
        'phase_id': task.phase_id,
        'tags': task.tags if task.tags else [],
        'owner': task.owner,
        'dependencies': task.dependencies if task.dependencies else [],
        'subtasks': task.subtasks if task.subtasks else []
    }


def parse_todo_safe(todo_path: Path = None, verbose: bool = False) -> Optional[dict]:
    """
    Safely load todo data from JSON storage with error handling.

    Args:
        todo_path: Ignored (kept for backward compatibility)
        verbose: Whether to print verbose error messages

    Returns:
        Dict with 'tracks' key containing list of track dicts, or None on error
    """
    try:
        json_store = JsonStore()

        # Get list of all track IDs
        track_ids = json_store.list_all_tracks()

        # Load each track with its nested data
        tracks_dicts = []
        for track_id in track_ids:
            track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if not track:
                continue

            # Load phases for this track
            phase_ids = json_store.list_all_phases()
            track_phases = []
            all_tasks = []

            for phase_id in phase_ids:
                phase = json_store.load_phase(phase_id, load_tasks=False)
                if phase and phase.track_id == track_id:
                    track_phases.append(phase)

                    # Load tasks for this phase
                    task_ids = json_store.list_all_tasks()
                    for task_id in task_ids:
                        task = json_store.load_task(task_id)
                        if task and task.phase_id == phase_id:
                            all_tasks.append(task)

            track_dict = _track_to_dict(track, track_phases, all_tasks)
            tracks_dicts.append(track_dict)

        return {'tracks': tracks_dicts}

    except Exception as exc:
        if verbose:
            print(f"Verbose: Error loading JSON data: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error loading JSON data. Use --verbose for more details.")
        return None


def parse_done_safe(done_path: Path = None, verbose: bool = False) -> Optional[dict]:
    """
    Safely load archived data from JSON storage with error handling.

    Args:
        done_path: Ignored (kept for backward compatibility)
        verbose: Whether to print verbose error messages

    Returns:
        Dict with 'tracks' key containing list of archived track dicts, or None on error
    """
    try:
        json_store = JsonStore()

        # Load the archive index
        archive = json_store.load_archive(load_tracks=True, load_phases=True, load_tasks=True)

        # Convert archived tracks to dict format
        tracks_dicts = []
        for track in archive.tracks:
            # Get phases for this track from archive
            track_phases = []
            all_tasks = []

            # Note: archived data is loaded nested, so phases are in track.phases
            # But we need to handle the case where they might not be loaded
            # For now, return empty lists as archive operations need more work
            track_dict = _track_to_dict(track, track_phases, all_tasks)
            tracks_dicts.append(track_dict)

        return {'tracks': tracks_dicts}

    except Exception as exc:
        if verbose:
            print(f"Verbose: Error loading archived JSON data: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error loading archived JSON data. Use --verbose for more details.")
        return None


def get_all_tracks_with_phases_and_tasks(verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Get all tracks with their phases and tasks from JSON storage.

    Combines active and archived tracks.
    """
    all_tracks = []

    try:
        # Load active tracks
        todo_data = parse_todo_safe(verbose=verbose)
        if todo_data:
            all_tracks.extend(todo_data.get('tracks', []))

        # Load archived tracks
        done_data = parse_done_safe(verbose=verbose)
        if done_data:
            all_tracks.extend(done_data.get('tracks', []))

    except Exception as e:
        if verbose:
            print(f"Warning: Error loading tracks from JSON: {e}")
            import traceback
            traceback.print_exc()

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
    data = parse_todo_safe(verbose=verbose)
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
    data = parse_todo_safe(verbose=verbose)
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
