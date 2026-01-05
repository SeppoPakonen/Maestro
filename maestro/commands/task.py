"""
Task command implementation for Maestro CLI.

Commands:
- maestro task list [filters] - List tasks across all tracks/phases
- maestro task add <name> - Add new task
- maestro task remove <id> - Remove task
- maestro task <id> - Show task details
- maestro task <id> show - Show task details
- maestro task <id> edit - Edit task in $EDITOR
- maestro task <id> complete - Mark task as complete
- maestro task <id> set - Set current task context
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from maestro.tracks.json_store import JsonStore
from maestro.display.table_renderer import render_task_table, _status_display
from maestro.data.common_utils import (
    get_all_tracks_with_phases_and_tasks,
    resolve_identifier_by_type,
    filter_items_by_track,
    get_available_ids,
    print_error,
    print_warning,
    print_info,
)
from .status_utils import allowed_statuses, normalize_status, status_badge, status_timestamp


def _available_phase_ids(verbose: bool = False) -> List[str]:
    return get_available_ids('phase', verbose=verbose)


def _available_track_ids(verbose: bool = False) -> List[str]:
    return get_available_ids('track', verbose=verbose)


def _normalize_task_status(status: Optional[str], completed: bool, phase_status: Optional[str]) -> str:
    if completed:
        return "done"
    if status:
        normalized = status.strip().lower().replace("-", "_")
        if normalized in {"done", "completed", "complete"}:
            return "done"
        if normalized in {"in_progress", "inprogress", "in-progress"}:
            return "in_progress"
        if normalized in {"planned", "plan", "todo"}:
            return "planned"
        if normalized in {"proposed", "prop"}:
            return "proposed"
        return normalized
    if phase_status:
        phase_normalized = phase_status.strip().lower()
        if phase_normalized in {"done", "in_progress", "planned", "proposed"}:
            return phase_normalized
    return "planned"


def _collect_phase_index(verbose: bool = False) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    phase_index: Dict[str, Dict[str, str]] = {}
    phase_order: List[str] = []

    def add_phase(track: Dict, phase: Dict) -> None:
        phase_id = phase.get('phase_id')
        if not phase_id:
            return
        entry = phase_index.setdefault(phase_id, {})
        track_id = track.get('track_id')
        track_name = track.get('name')
        if track_id and not entry.get('track_id'):
            entry['track_id'] = track_id
        if track_name and not entry.get('track_name'):
            entry['track_name'] = track_name
        if phase.get('name') and not entry.get('phase_name'):
            entry['phase_name'] = phase.get('name')
        if phase.get('status') and not entry.get('phase_status'):
            entry['phase_status'] = phase.get('status')
        if phase_id not in phase_order:
            phase_order.append(phase_id)

    json_store = JsonStore()
    tracks = get_all_tracks_with_phases_and_tasks(verbose=verbose)
    for track in tracks:
        for phase in track.get('phases', []):
            add_phase(track, phase)

    for phase_id in json_store.list_all_phases():
        if phase_id not in phase_index:
            phase_index[phase_id] = {}
        if phase_id not in phase_order:
            phase_order.append(phase_id)

    return phase_index, phase_order


def _collect_task_entries(verbose: bool = False) -> List[Dict[str, str]]:
    """Collect all task entries from JSON storage."""
    from maestro.tracks.json_store import JsonStore

    try:
        json_store = JsonStore()
        tasks: List[Dict[str, str]] = []

        # Build a map of track_id -> track info (both active and archived)
        track_map = {}

        # Load active tracks
        for track_id in json_store.list_all_tracks():
            track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if track:
                track_map[track_id] = {
                    "name": track.name,
                    "status": track.status
                }

        # Load archived tracks
        archive = json_store.load_archive(load_tracks=True, load_phases=False, load_tasks=False)
        if archive and archive.tracks:
            for track in archive.tracks:
                if isinstance(track, str):
                    # It's just a track ID, load it from archive
                    archive_track_file = json_store.archive_dir / "tracks" / f"{track}.json"
                    if archive_track_file.exists():
                        import json
                        track_data = json.loads(archive_track_file.read_text(encoding='utf-8'))
                        track_map[track_data["track_id"]] = {
                            "name": track_data.get("name", "Unnamed Track"),
                            "status": track_data.get("status", "unknown")
                        }
                else:
                    # It's already a Track object
                    track_map[track.track_id] = {
                        "name": track.name,
                        "status": track.status
                    }

        # Scan ALL phases regardless of track association
        phase_ids = json_store.list_all_phases()

        for phase_id in phase_ids:
            # Load phase with its tasks
            phase = json_store.load_phase(phase_id, load_tasks=True)
            if not phase:
                continue

            phase_name = phase.name
            phase_status = phase.status

            # Get track info for this phase
            track_id = phase.track_id or "N/A"
            track_info = track_map.get(track_id, {"name": "Unnamed Track", "status": "unknown"})
            track_name = track_info["name"]

            # Get tasks for this phase
            task_objects = phase.tasks if isinstance(phase.tasks, list) else []

            for task_obj in task_objects:
                # Handle both Task objects and task IDs
                if isinstance(task_obj, str):
                    # It's a task ID, load it
                    task = json_store.load_task(task_obj)
                    if not task:
                        continue
                else:
                    # It's already a Task object
                    task = task_obj

                # Convert Task object to dict format expected by the rest of the code
                task_id = task.task_id
                completed = task.completed
                task_status = _normalize_task_status(task.status, completed, phase_status)

                # Build task entry matching the old format
                phase_file_path = Path('docs/maestro/phases') / f"{phase_id}.json"
                tasks.append({
                    "task_id": task_id,
                    "name": task.name,
                    "status": task_status,
                    "priority": task.priority or 'N/A',
                    "phase_id": phase_id,
                    "phase_name": phase_name,
                    "phase_status": phase_status,
                    "track_id": track_id,
                    "track_name": track_name,
                    "phase_file": str(phase_file_path),  # Keep for backward compatibility
                    "_task": {
                        "task_id": task.task_id,
                        "name": task.name,
                        "status": task.status,
                        "priority": task.priority,
                        "estimated_hours": task.estimated_hours,
                        "description": task.description,
                        "completed": task.completed,
                        "tags": task.tags,
                        "owner": task.owner,
                        "dependencies": task.dependencies,
                        "subtasks": task.subtasks,
                    },
                })

        # Add list numbers
        for idx, task in enumerate(tasks, 1):
            task["list_number"] = idx

        return tasks

    except Exception as e:
        if verbose:
            print(f"Error loading tasks from JSON storage: {e}")
            import traceback
            traceback.print_exc()
        # Fall back to empty list on error
        return []


def _parse_task_list_filters(tokens: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    status_filter = None
    track_filter = None
    phase_filter = None
    extras: List[str] = []
    status_aliases = {
        'plan': 'planned',
        'planned': 'planned',
        'prop': 'proposed',
        'proposed': 'proposed',
        'done': 'done',
        'inprogress': 'in_progress',
        'in-progress': 'in_progress',
        'in_progress': 'in_progress',
    }
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        normalized = token.lower()
        if normalized in status_aliases:
            status_filter = status_aliases[normalized]
            idx += 1
            continue
        if normalized in {'track', 'tr'}:
            if idx + 1 >= len(tokens):
                extras.append(token)
                break
            track_filter = tokens[idx + 1]
            idx += 2
            continue
        if normalized in {'phase', 'ph'}:
            if idx + 1 >= len(tokens):
                extras.append(token)
                break
            phase_filter = tokens[idx + 1]
            idx += 2
            continue
        if len(tokens) == 1 and not phase_filter and not track_filter and not status_filter:
            phase_filter = token
            idx += 1
            continue
        if not phase_filter:
            phase_filter = token
            idx += 1
            continue
        extras.append(token)
        idx += 1

    return status_filter, track_filter, phase_filter, extras


def list_tasks(args):
    """
    List all tasks from phase files.

    Supports optional filters:
      - plan/prop/done for status
      - track <id|#> to filter by track
      - phase <id> to filter by phase
    """
    tokens = getattr(args, 'filters', None) or []
    status_filter, track_filter, phase_filter, extras = _parse_task_list_filters(tokens)
    if extras:
        print(f"Error: Unrecognized filters: {' '.join(extras)}")
        print("Use 'maestro task help' for list filter usage.")
        return 1

    if track_filter:
        verbose = getattr(args, 'verbose', False)
        # Use the unified identifier resolver
        resolved = resolve_identifier_by_type(track_filter, 'track', verbose=verbose) if track_filter.isdigit() else track_filter
        if track_filter.isdigit() and not resolved:
            print(f"Error: Track '{track_filter}' not found.")
            if verbose:
                available = get_available_ids('track', verbose=verbose)
                if available:
                    print(f"Verbose: Available tracks: {', '.join(available)}")
            return 1
        track_filter = resolved

    tasks = _collect_task_entries(verbose=getattr(args, 'verbose', False))

    if phase_filter:
        tasks = [task for task in tasks if task.get('phase_id') == phase_filter]
    if track_filter:
        tasks = [task for task in tasks if task.get('track_id') == track_filter]
    if status_filter:
        tasks = [task for task in tasks if task.get('status') == status_filter]

    if not tasks:
        print("No tasks found.")
        return 0

    # Format the data with index values for the table renderer
    formatted_tasks = []
    for i, task in enumerate(tasks, 1):
        formatted_task = {
            'idx': str(i),
            'task_id': task.get('task_id', 'N/A'),
            'name': task.get('name', 'Unnamed Task'),
            'track': task.get('track_id', 'N/A'),
            'phase': task.get('phase_id', 'N/A'),
            'status': task.get('status', 'unknown')
        }
        formatted_tasks.append(formatted_task)

    # Render the table using unified renderer
    table_lines = render_task_table(formatted_tasks)
    for line in table_lines:
        print(line)

    return 0


def _resolve_task_identifier(task_identifier: str, verbose: bool = False) -> Optional[Dict[str, str]]:
    tasks = _collect_task_entries(verbose=verbose)

    for task in tasks:
        if task.get('task_id') == task_identifier or task.get('_task', {}).get('task_number') == task_identifier:
            return task

    if task_identifier.isdigit():
        index = int(task_identifier)
        for task in tasks:
            if task.get('list_number') == index:
                return task

    return None


def show_task(task_id: str, args):
    """
    Show detailed information about a specific task.

    Searches through all phase files to find the task.
    """
    verbose = getattr(args, 'verbose', False)
    task_entry = _resolve_task_identifier(task_id, verbose=verbose)
    if not task_entry:
        print(f"Error: Task '{task_id}' not found.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1
    task = task_entry.get('_task', {})
    phase_info = {
        'id': task_entry.get('phase_id', 'N/A'),
        'name': task_entry.get('phase_name', 'Unnamed'),
        'file': task_entry.get('phase_file', 'N/A'),
    }
    completed = bool(task.get('completed', False))
    status_value = _normalize_task_status(task.get('status'), completed, task_entry.get('phase_status'))
    from maestro.config.settings import get_settings
    settings = get_settings()
    status_display, _ = _status_display(status_value, settings.unicode_symbols)

    # Display task details
    print()
    print("=" * 80)
    print(f"TASK: {task.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    # Metadata
    print(f"ID:          {task.get('task_id', task.get('task_number', 'N/A'))}")
    print(f"Phase:       {phase_info['name']} ({phase_info['id']})")
    print(f"Priority:    {task.get('priority', 'N/A')}")
    print(f"Status:      {status_display}")
    print(f"Est. Hours:  {task.get('estimated_hours', 'N/A')}")
    print()

    # Description
    description = task.get('description', [])
    if description:
        print("Description:")
        for line in description:
            if line.strip():
                print(f"  {line}")
        print()

    # Subtasks
    subtasks = task.get('subtasks', [])
    if subtasks:
        print(f"Subtasks ({len(subtasks)}):")
        for i, subtask in enumerate(subtasks, 1):
            status = '✅' if subtask.get('completed', False) else '☐'
            content = subtask.get('content', 'Unnamed')
            indent = subtask.get('indent', 0)
            indent_str = '  ' * (indent // 2)
            print(f"  {indent_str}{status} {content}")
        print()

    # Source file
    print(f"Source: {phase_info['file']}")
    print()

    return 0


def _resolve_text_input(args) -> str:
    if getattr(args, 'text_file', None):
        return Path(args.text_file).read_text(encoding='utf-8')
    return sys.stdin.read()




def add_task(name: str, args):
    """
    Add a new task to a phase.

    Args:
        name: Name of the new task
        args: Command arguments
    """
    from maestro.config.settings import get_settings
    from maestro.tracks.json_store import JsonStore
    from maestro.tracks.models import Task

    verbose = getattr(args, 'verbose', False)
    phase_id = getattr(args, 'phase_id', None)
    if not phase_id:
        settings = get_settings()
        phase_id = settings.current_phase
    if not phase_id:
        print("Error: Phase ID required. Usage: maestro task add --phase <phase_id> <name>")
        return 1

    json_store = JsonStore()

    # Load the phase
    phase = json_store.load_phase(phase_id, load_tasks=True)
    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        if verbose:
            available = json_store.list_all_phases()
            if available:
                print(f"Verbose: Available phases: {', '.join(available)}")
        return 1

    # Generate task ID if not provided
    task_id = getattr(args, 'task_id_opt', None)
    if not task_id:
        # Auto-generate task ID based on existing tasks
        existing_task_ids = [t.task_id if hasattr(t, 'task_id') else t for t in (phase.tasks or [])]
        # Find next available number
        base_num = 1
        while f"{phase_id}.{base_num}" in existing_task_ids:
            base_num += 1
        task_id = f"{phase_id}.{base_num}"

    # Check if task already exists
    if json_store.load_task(task_id):
        print(f"Error: Task '{task_id}' already exists.")
        return 1

    # Get description
    desc_lines = getattr(args, 'desc', None) or []

    # Create new task
    task = Task(
        task_id=task_id,
        name=name,
        status='planned',
        priority='P2',
        estimated_hours=None,
        description=desc_lines,
        phase_id=phase_id,
        completed=False,
        tags=[],
        owner=None,
        dependencies=[],
        subtasks=[]
    )

    # Save task
    json_store.save_task(task)

    # Add task to phase's task list
    if not phase.tasks:
        phase.tasks = []

    # Handle task IDs vs Task objects
    if phase.tasks and isinstance(phase.tasks[0], str):
        phase.tasks.append(task_id)
    else:
        phase.tasks.append(task)

    json_store.save_phase(phase)

    print(f"Added task '{task_id}' ({name}) to phase '{phase_id}'.")
    return 0


def remove_task(task_id: str, args):
    """
    Remove a task from a phase.

    Args:
        task_id: Task ID to remove
        args: Command arguments
    """
    from maestro.tracks.json_store import JsonStore

    verbose = getattr(args, 'verbose', False)
    json_store = JsonStore()

    # Load the task to get its phase_id
    task = json_store.load_task(task_id)
    if not task:
        print(f"Error: Task '{task_id}' not found.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1

    phase_id = task.phase_id

    # Load the phase
    phase = json_store.load_phase(phase_id, load_tasks=True)
    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        return 1

    # Remove task from phase's task list
    if phase.tasks:
        # Handle both task IDs and Task objects
        if isinstance(phase.tasks[0], str):
            phase.tasks = [t for t in phase.tasks if t != task_id]
        else:
            phase.tasks = [t for t in phase.tasks if t.task_id != task_id]

        json_store.save_phase(phase)

    # Delete the task file
    task_file = json_store.tasks_dir / f"{task_id}.json"
    if task_file.exists():
        task_file.unlink()

    print(f"Removed task: {task_id}")
    return 0


def complete_task(task_id: str, args):
    """
    Mark a task as complete.

    Args:
        task_id: Task ID to complete
        args: Command arguments
    """
    setattr(args, 'status', 'done')
    return set_task_status(task_id, args)


def set_task_status(task_id: str, args) -> int:
    """
    Update a task status in JSON storage.
    """
    from maestro.tracks.json_store import JsonStore

    status_value = normalize_status(getattr(args, 'status', None))
    if not status_value:
        print(f"Error: Unknown status. Allowed: {allowed_statuses()}.")
        return 1

    verbose = getattr(args, 'verbose', False)
    json_store = JsonStore()

    # Load the task
    task = json_store.load_task(task_id)
    if not task:
        print(f"Error: Task '{task_id}' not found.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1

    # Update task status
    task.status = status_value
    task.completed = (status_value == 'done')

    # Save the task
    json_store.save_task(task)

    print(f"Updated task '{task_id}' status to '{status_value}'.")
    return 0


def edit_task(task_id: str, args):
    """
    Edit a task in $EDITOR.

    Opens the JSON task file.
    """
    import os
    import subprocess

    verbose = getattr(args, 'verbose', False)
    json_store = JsonStore()
    task_file = json_store.tasks_dir / f"{task_id}.json"
    if not task_file.exists():
        print(f"Error: Task '{task_id}' not found.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1
    original = task_file.read_text(encoding='utf-8')

    editor = os.environ.get('EDITOR', 'vim')
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp.write(original.encode('utf-8'))
            tmp_path = tmp.name
        subprocess.run([editor, tmp_path])
        new_block = Path(tmp_path).read_text(encoding='utf-8')
        Path(tmp_path).unlink(missing_ok=True)
        if new_block == original:
            print("No changes made.")
            return 0
        try:
            json.loads(new_block)
        except json.JSONDecodeError as exc:
            print(f"Error: Updated content is not valid JSON: {exc}")
            return 1
        task_file.write_text(new_block, encoding='utf-8')
        print(f"Updated task '{task_id}' JSON.")
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def set_task_context(task_id: str, args):
    """Set the current task context.

    Args:
        task_id: Task ID to set as current
        args: Command arguments
    """
    from maestro.config.settings import get_settings

    # Find task and set context including parent phase and track
    # For now, we'll just set the task ID directly
    # In a more complex implementation, we might want to look up the parent phase and track
    settings = get_settings()
    settings.current_task = task_id
    # We could also set the current_phase and current_track if we had access to the phase/track info
    settings.save()

    print(f"Context set to task: {task_id}")
    return 0


def handle_task_command(args):
    """
    Main handler for task commands.

    Routes to appropriate subcommand handler.
    """
    # Handle 'maestro task discuss <task_id>' (new subcommand format)
    if hasattr(args, 'task_subcommand') and args.task_subcommand in ['discuss', 'd']:
        if hasattr(args, 'task_id_arg'):
            from .discuss import handle_task_discuss
            return handle_task_discuss(args.task_id_arg, args)

    # Handle 'maestro task list [phase_id]'
    if hasattr(args, 'task_subcommand'):
        if args.task_subcommand in ['list', 'ls', 'l']:
            return list_tasks(args)
        elif args.task_subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Task name required. Usage: maestro task add <name>")
                return 1
            name = " ".join(args.name) if isinstance(args.name, list) else args.name
            return add_task(name, args)
        elif args.task_subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task remove <id>")
                return 1
            return remove_task(args.task_id, args)
        elif args.task_subcommand in ['status', 'set-status']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task status <id> <status>")
                return 1
            if not getattr(args, 'status', None):
                print("Error: Status required. Usage: maestro task status <id> <status>")
                return 1
            return set_task_status(args.task_id, args)
        elif args.task_subcommand in ['text', 'raw']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task text <id>")
                return 1
            json_store = JsonStore()
            task_file = json_store.tasks_dir / f"{args.task_id}.json"
            if not task_file.exists():
                print(f"Error: Task '{args.task_id}' not found.")
                return 1
            print(task_file.read_text(encoding='utf-8').rstrip())
            return 0
        elif args.task_subcommand in ['set-text', 'setraw']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task set-text <id> [--file path]")
                return 1
            new_block = _resolve_text_input(args)
            if not new_block.strip():
                print("Error: Replacement text is empty.")
                return 1
            try:
                json.loads(new_block)
            except json.JSONDecodeError as exc:
                print(f"Error: Updated content is not valid JSON: {exc}")
                return 1
            json_store = JsonStore()
            task_file = json_store.tasks_dir / f"{args.task_id}.json"
            if not task_file.exists():
                print(f"Error: Task '{args.task_id}' not found.")
                return 1
            task_file.write_text(new_block, encoding='utf-8')
            print(f"Updated task '{args.task_id}' JSON.")
            return 0
        elif args.task_subcommand in ['help', 'h']:
            print_task_help()
            return 0

    # Handle 'maestro task <id>' or 'maestro task <id> <subcommand>'
    if hasattr(args, 'task_id_arg') and args.task_id_arg:
        task_id = args.task_id_arg

        # Check if there's a task-specific subcommand
        subcommand = getattr(args, 'task_item_subcommand', None)
        if subcommand:
            if subcommand == 'show':
                return show_task(task_id, args)
            elif subcommand == 'edit':
                return edit_task(task_id, args)
            elif subcommand == 'complete':
                return complete_task(task_id, args)
            elif subcommand == 'discuss':
                from .discuss import handle_task_discuss
                return handle_task_discuss(task_id, args)
            elif subcommand == 'set':
                return set_task_context(task_id, args)
            elif subcommand == 'help' or subcommand == 'h':
                print_task_item_help()
                return 0
        # Default to 'show' if no subcommand
        return show_task(task_id, args)

    # No subcommand - show help or list based on context
    # Check if we have a current phase set
    from maestro.config.settings import get_settings
    settings = get_settings()
    if settings.current_phase:
        args.filters = [settings.current_phase]
        return list_tasks(args)

    print_task_help()
    return 0


def print_task_help():
    """Print help for task commands."""
    help_text = """
maestro task - Manage project tasks

USAGE:
    maestro task list [filters]           List tasks across all tracks/phases
    maestro task add <name>               Add new task
    maestro task remove <id>              Remove a task
    maestro task <id>                     Show task details
    maestro task <id> show                Show task details
    maestro task <id> edit                Edit task in $EDITOR
    maestro task <id> complete            Mark task as complete
    maestro task <id> status <status>     Update task status
    maestro task text <id>                Show raw task block
    maestro task set-text <id>            Replace task block (stdin or --file)
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

LIST FILTERS:
    plan | prop | done                    Filter by task status
    track <id|#>                          Filter by track ID or number
    phase <id>                            Filter by phase ID

ALIASES:
    list:     ls, l
    add:      a
    remove:   rm, r
    show:     sh
    edit:     e
    complete: c, done
    status:   set-status
    discuss:  d
    set:      st
    text:     raw
    set-text: setraw

EXAMPLES:
    maestro task list                     # List all tasks
    maestro task list plan                # List planned tasks
    maestro task list track umk           # List tasks in track 'umk'
    maestro task list phase umk1          # List tasks in phase 'umk1'
    maestro task list track umk phase umk1
    maestro task 12                       # Show task by list number
    maestro task cli-tpt-1-1              # Show task details
    maestro task cli-tpt-1-1 edit         # Edit task in $EDITOR
    maestro task cli-tpt-1-1 complete     # Mark task as complete
    maestro task cli-tpt-1-1 status done --summary "Finished validation"
    maestro task cli-tpt-1-1 discuss      # Discuss task with AI
    maestro task cli-tpt-1-1 set          # Set current task context
"""
    print(help_text)


def print_task_item_help():
    """Print help for task item commands."""
    help_text = """
maestro task <id> - Manage a specific task

USAGE:
    maestro task <id> show                Show task details
    maestro task <id> edit                Edit task in $EDITOR
    maestro task <id> complete            Mark task as complete
    maestro task <id> status <status>     Update task status
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

ALIASES:
    show:     sh
    edit:     e
    complete: c, done
    status:   set-status
    discuss:  d
    set:      st

EXAMPLES:
    maestro task cli-tpt-1-1 show
    maestro task cli-tpt-1-1 edit
    maestro task cli-tpt-1-1 complete
    maestro task cli-tpt-1-1 status in_progress
    maestro task cli-tpt-1-1 discuss
    maestro task cli-tpt-1-1 set
"""
    print(help_text)


def add_task_parser(subparsers):
    """
    Add task command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    if len(sys.argv) >= 3 and sys.argv[1] in ['task', 'ta']:
        arg = sys.argv[2]
        known_subcommands = [
            'list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'text', 'raw',
            'set-text', 'setraw', 'help', 'h', 'discuss', 'd', 'show', 'sh',
            'status', 'set-status'
        ]
        # Only modify the command if it's not a global argument like --help
        if not arg.startswith('-') and arg not in known_subcommands and arg not in ['--help', '-h']:
            if len(sys.argv) >= 4 and sys.argv[3] in [
                'show', 'sh', 'edit', 'e', 'complete', 'c', 'done', 'discuss', 'd',
                'set', 'st', 'help', 'h', 'status', 'set-status'
            ]:
                subcommand = sys.argv[3]
                task_id = sys.argv[2]
                if subcommand in ['status', 'set-status']:
                    sys.argv[2] = subcommand
                    sys.argv[3] = task_id
                else:
                    sys.argv[2] = 'show'
                    sys.argv[3] = task_id
                    sys.argv.insert(4, subcommand)
            else:
                sys.argv.insert(2, 'show')

    # Main task command
    task_parser = subparsers.add_parser(
        'task',
        aliases=['ta'],
        help='Manage project tasks'
    )

    # Task subcommands
    task_subparsers = task_parser.add_subparsers(
        dest='task_subcommand',
        help='Task subcommands'
    )

    # maestro task list [phase_id]
    task_list_parser = task_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all tasks (or tasks in phase)'
    )
    task_list_parser.add_argument(
        'filters',
        nargs='*',
        help='Optional filters: [plan|prop|done] [track <id|#>] [phase <id>]'
    )

    # maestro task show <id> [action]
    task_show_parser = task_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show task details'
    )
    task_show_parser.add_argument('task_id_arg', help='Task ID (or list #)')
    task_show_parser.add_argument(
        'task_item_subcommand',
        nargs='?',
        choices=['show', 'sh', 'edit', 'e', 'complete', 'c', 'done', 'discuss', 'd', 'set', 'st', 'help', 'h'],
        help='Task item subcommand (show/edit/complete/discuss/set)'
    )

    # maestro task add <name>
    task_add_parser = task_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new task'
    )
    task_add_parser.add_argument('name', nargs='+', help='Task name')
    task_add_parser.add_argument('--id', dest='task_id_opt', help='Task ID (default: <phase_id>.1)')
    task_add_parser.add_argument('--phase', dest='phase_id', help='Phase ID to add the task to')
    task_add_parser.add_argument('--after', help='Insert after task ID')
    task_add_parser.add_argument('--before', help='Insert before task ID')
    task_add_parser.add_argument('--desc', action='append', help='Description line (repeatable)')

    # maestro task remove <id>
    task_remove_parser = task_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a task'
    )
    task_remove_parser.add_argument('task_id', help='Task ID to remove')

    task_status_parser = task_subparsers.add_parser(
        'status',
        aliases=['set-status'],
        help='Update task status'
    )
    task_status_parser.add_argument('task_id', help='Task ID to update')
    task_status_parser.add_argument('status', help='Status (planned, in_progress, done, proposed)')
    task_status_parser.add_argument('--summary', help='Status change summary')

    task_text_parser = task_subparsers.add_parser(
        'text',
        aliases=['raw'],
        help='Show raw task block from phase file'
    )
    task_text_parser.add_argument('task_id', help='Task ID to show')

    task_set_text_parser = task_subparsers.add_parser(
        'set-text',
        aliases=['setraw'],
        help='Replace task block from stdin or a file'
    )
    task_set_text_parser.add_argument('task_id', help='Task ID to replace')
    task_set_text_parser.add_argument('--file', dest='text_file', help='Read replacement text from file')

    # maestro task help
    task_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for task commands'
    )

    # NOTE: task_id_arg is handled via the "show" subcommand to allow "task <id>" parsing.
    task_parser.add_argument(
        '--mode',
        choices=['editor', 'terminal'],
        help='Discussion mode (editor or terminal)'
    )
    task_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )
    task_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose errors and parsing details'
    )

    # maestro task discuss <id>
    task_discuss_parser = task_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss task with AI'
    )
    task_discuss_parser.add_argument('task_id_arg', help='Task ID to discuss')
    task_discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                                     default='editor', help='Discussion mode')
    task_discuss_parser.add_argument('--resume', help='Resume previous discussion session')

    return task_parser


def discuss_task(task_id: str, args):
    """Discuss a specific task with AI."""
    from .discuss import handle_task_discuss
    return handle_task_discuss(task_id, args)
