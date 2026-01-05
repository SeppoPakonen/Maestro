"""
Common data handling utilities for Maestro CLI.

This module provides unified functions for parsing, data handling,
and common operations that are used across multiple CLI modules.

Updated to use JSON storage instead of markdown.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import sys

# Import JSON storage
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track, Phase, Task
from maestro.data.track_cache import TrackDataCache, cache_validation_enabled


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


def _extract_phase_ids(track: Track) -> List[str]:
    """Normalize phase references from a track to a list of phase IDs."""
    phase_ids: List[str] = []
    for entry in getattr(track, "phases", []) or []:
        if isinstance(entry, Phase):
            phase_ids.append(entry.phase_id)
        elif isinstance(entry, str):
            phase_ids.append(entry)
    return phase_ids


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
        cache = TrackDataCache(Path('.'))
        result = cache.load_or_rebuild(json_store, validate=cache_validation_enabled())
        if not result.cached:
            print_warning(f"Track cache not used ({result.reason or 'rebuilt'}); reloading from JSON.")
        snapshot = result.snapshot

        tracks_dicts = []
        for track_id in snapshot.track_order:
            track = snapshot.tracks.get(track_id)
            if not track:
                continue

            track_phases = []
            all_tasks = []
            phase_ids = _extract_phase_ids(track)

            for phase_id in phase_ids:
                phase = snapshot.phases.get(phase_id)
                if not phase or phase.track_id != track_id:
                    continue

                track_phases.append(phase)
                all_tasks.extend(snapshot.tasks_by_phase.get(phase_id, []))

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
        cache = TrackDataCache(Path('.'))
        result = cache.load_or_rebuild(json_store, validate=cache_validation_enabled())
        if not result.cached:
            print_warning(f"Track cache not used ({result.reason or 'rebuilt'}); reloading from JSON.")
        snapshot = result.snapshot

        # Load the archive index
        archive = json_store.load_archive(load_tracks=True, load_phases=False, load_tasks=False)

        # Convert archived tracks to dict format
        tracks_dicts = []
        for track in archive.tracks:
            # Handle both Track objects and track IDs
            if isinstance(track, str):
                # It's just a track ID, load it from archive
                archive_track_file = json_store.archive_dir / "tracks" / f"{track}.json"
                if not archive_track_file.exists():
                    continue
                import json
                track_data = json.loads(archive_track_file.read_text(encoding='utf-8'))

                # Reconstruct Track object
                from maestro.tracks.models import Track
                track = Track(
                    track_id=track_data["track_id"],
                    name=track_data.get("name", ""),
                    status=track_data.get("status", "unknown"),
                    completion=track_data.get("completion", 0),
                    description=track_data.get("description", []),
                    phases=track_data.get("phases", []),
                    priority=track_data.get("priority", 0),
                    created_at=track_data.get("created_at"),
                    updated_at=track_data.get("updated_at"),
                    tags=track_data.get("tags", []),
                    owner=track_data.get("owner"),
                    is_top_priority=track_data.get("is_top_priority", False)
                )

            # Get phase IDs for this track
            phase_ids = track.phases if isinstance(track.phases, list) else []

            # Load phases for this track
            track_phases = []
            all_tasks = []

            for phase_id in phase_ids:
                phase = snapshot.phases.get(phase_id)
                if not phase:
                    continue

                track_phases.append(phase)
                all_tasks.extend(snapshot.tasks_by_phase.get(phase_id, []))

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
