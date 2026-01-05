"""
Phase command implementation for Maestro CLI.

Commands:
- maestro phase list [track_id] - List all phases (or phases in track)
- maestro phase add <name> - Add new phase
- maestro phase remove <id> - Remove phase
- maestro phase <id> - Show phase details
- maestro phase <id> show - Show phase details
- maestro phase <id> edit - Edit phase in $EDITOR
- maestro phase <id> set - Set current phase context
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from maestro.tracks.json_store import JsonStore
from maestro.display.table_renderer import render_phase_table
from maestro.data.common_utils import (
    get_all_tracks_with_phases_and_tasks,
    resolve_identifier_by_type,
    filter_items_by_track,
    print_error,
    print_warning,
    print_info,
)
from .status_utils import allowed_statuses, normalize_status, status_badge, status_timestamp


def _looks_like_phase_id(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", value))


def _available_track_ids(verbose: bool = False) -> List[str]:
    json_store = JsonStore()
    return json_store.list_all_tracks()


def _available_phase_ids(verbose: bool = False) -> List[str]:
    json_store = JsonStore()
    return json_store.list_all_phases()


def list_phases(args):
    """
    List all phases from the JSON store.

    If track_id is provided, list only phases in that track.
    Otherwise, list all phases across all tracks.
    """
    from maestro.config.settings import get_settings

    tracks = get_all_tracks_with_phases_and_tasks(verbose=getattr(args, 'verbose', False))

    # If no track_id provided and context is set, use context
    track_filter = getattr(args, 'track_id', None)
    status_filter = None
    if track_filter:
        status_aliases = {
            'plan': 'planned',
            'planned': 'planned',
            'done': 'done',
            'prop': 'proposed',
            'proposed': 'proposed',
        }
        normalized = track_filter.strip().lower()
        if normalized in status_aliases:
            status_filter = status_aliases[normalized]
            track_filter = None
    if not track_filter:
        settings = get_settings()
        if settings.current_track:
            track_filter = settings.current_track
            print(f"Using current track context: {track_filter}")
            print()

    phases_to_show = []

    if track_filter:
        # Find the specific track
        for track in tracks:
            if track.get('track_id') == track_filter:
                phases_to_show = track.get('phases', [])
                track_name = track.get('name', 'Unnamed Track')
                print()
                print(f"Phases in track '{track_name}' ({track_filter}):")
                break

        if not phases_to_show:
            print(f"Error: Track '{track_filter}' not found or has no phases.")
            return 1
    else:
        # Collect all phases from all tracks
        for track in tracks:
            for phase in track.get('phases', []):
                # Add track info to phase
                phase['_track_id'] = track.get('track_id', 'N/A')
                phase['_track_name'] = track.get('name', 'Unnamed')
                phases_to_show.append(phase)

    if status_filter:
        phases_to_show = [
            phase for phase in phases_to_show
            if phase.get('status') == status_filter
        ]

    if not phases_to_show:
        print("No phases found.")
        return 0

    # Format the data with index values for the table renderer
    formatted_phases = []
    for i, phase in enumerate(phases_to_show, 1):
        formatted_phase = {
            'idx': str(i),
            'phase_id': phase.get('phase_id', 'N/A'),
            'name': phase.get('name', 'Unnamed Phase'),
            'status': phase.get('status', 'unknown'),
            'track': phase.get('_track_id', 'N/A')
        }
        formatted_phases.append(formatted_phase)

    # Render the table using unified renderer
    table_lines = render_phase_table(formatted_phases, track_filter)
    for line in table_lines:
        print(line)

    return 0


def show_phase(phase_id: str, args):
    """
    Show detailed information about a specific phase.

    Loads from JSON storage.
    """
    verbose = getattr(args, 'verbose', False)
    json_store = JsonStore()
    phase_obj = json_store.load_phase(phase_id, load_tasks=True)
    phase = None
    if phase_obj:
        phase = {
            "phase_id": phase_obj.phase_id,
            "name": phase_obj.name,
            "status": phase_obj.status,
            "completion": phase_obj.completion,
            "description": phase_obj.description,
            "track": phase_obj.track_id,
            "priority": phase_obj.priority,
            "tasks": [],
        }
        track = json_store.load_track(phase_obj.track_id, load_phases=False, load_tasks=False)
        if track:
            phase["_track_name"] = track.name
        for task in phase_obj.tasks:
            if hasattr(task, "task_id"):
                phase["tasks"].append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": task.status,
                    "completed": task.completed,
                    "description": task.description,
                })
            else:
                phase["tasks"].append({"task_id": task})

    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        if verbose:
            phase_ids = json_store.list_all_phases()
            if phase_ids:
                print(f"Verbose: Available phases: {', '.join(phase_ids)}")
        return 1

    # Display phase details
    print()
    print("=" * 80)
    print(f"PHASE: {phase.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    # Metadata
    print(f"ID:          {phase.get('phase_id', 'N/A')}")
    print(f"Track:       {phase.get('track', phase.get('_track_name', 'N/A'))}")
    print(f"Priority:    {phase.get('priority', 'N/A')}")
    print(f"Status:      {phase.get('status', 'N/A')}")
    print(f"Completion:  {phase.get('completion', 0)}%")
    print(f"Duration:    {phase.get('duration', 'N/A')}")

    dependencies = phase.get('dependencies', [])
    if dependencies:
        print(f"Dependencies: {', '.join(dependencies)}")

    print()

    # Description
    description = phase.get('description', [])
    if description:
        print("Description:")
        for line in description:
            if line.strip():
                print(f"  {line}")
        print()

    # Tasks
    tasks = phase.get('tasks', [])
    if tasks:
        print(f"Tasks ({len(tasks)}):")
        for i, task in enumerate(tasks, 1):
            task_id = task.get('task_id', task.get('task_number', 'N/A'))
            task_name = task.get('name', 'Unnamed')
            task_status = task.get('status', 'todo')
            task_completed = task.get('completed', False)

            # Determine emoji based on status
            status_emoji = "✅" if task_completed else "⬜"

            print(f"  {status_emoji} [{task_id}] {task_name}")

            # Print description if available
            task_description = task.get('description', [])
            if task_description:
                for desc_line in task_description:
                    if desc_line.strip() and not desc_line.startswith('- [') and not desc_line.startswith('  - '):
                        # Clean up the description line
                        cleaned_desc = desc_line.replace(f"**{task_id}**", "").strip()
                        if cleaned_desc.startswith('-'):
                            cleaned_desc = cleaned_desc[1:].strip()
                        if cleaned_desc:
                            print(f"      - {cleaned_desc}")
        print()

    # Link to detailed file
    if phase_file.exists():
        print(f"Detailed documentation: {phase_file}")
        print()

    return 0


def _resolve_text_input(args) -> str:
    if getattr(args, 'text_file', None):
        return Path(args.text_file).read_text(encoding='utf-8')
    return sys.stdin.read()


def add_phase(name: str, args):
    """
    Add a new phase to a track.

    Args:
        name: Name of the new phase
        args: Command arguments
    """
    from maestro.config.settings import get_settings
    from maestro.tracks.json_store import JsonStore
    from maestro.tracks.models import Phase

    track_id = getattr(args, 'track_id', None)
    if not track_id:
        settings = get_settings()
        track_id = settings.current_track
    if not track_id:
        print("Error: Track ID required. Usage: maestro phase add --track <track_id> <name>")
        return 1

    verbose = getattr(args, 'verbose', False)
    json_store = JsonStore()

    # Load the track
    track = json_store.load_track(track_id, load_phases=True, load_tasks=False)
    if not track:
        print(f"Error: Track '{track_id}' not found.")
        if verbose:
            available = json_store.list_all_tracks()
            if available:
                print(f"Verbose: Available tracks: {', '.join(available)}")
        return 1

    # Generate phase ID
    phase_id = getattr(args, 'phase_id', None)
    if not phase_id:
        phase_id = name.strip().split()[0].lower().replace(' ', '-')
    if phase_id.isdigit():
        print("Error: Phase ID cannot be purely numeric.")
        return 1

    # Check if phase already exists
    if json_store.load_phase(phase_id, load_tasks=False):
        print(f"Error: Phase ID '{phase_id}' already exists.")
        return 1

    # Get description
    desc_lines = getattr(args, 'desc', None) or []

    # Create new phase
    phase = Phase(
        phase_id=phase_id,
        name=name,
        status='planned',
        completion=0,
        description=desc_lines,
        tasks=[],
        track_id=track_id,
        priority='P2',
        tags=[],
        owner=None,
        dependencies=[],
        order=None
    )

    # Save phase
    json_store.save_phase(phase)

    # Add phase to track's phase list
    if not track.phases:
        track.phases = []

    # Handle phase IDs vs Phase objects
    if track.phases and isinstance(track.phases[0], str):
        track.phases.append(phase_id)
    else:
        track.phases.append(phase)

    json_store.save_track(track)

    print(f"Added phase '{phase_id}' ({name}) to track '{track_id}'.")
    return 0


def remove_phase(phase_id: str, args):
    """
    Remove a phase from JSON storage.

    Args:
        phase_id: Phase ID to remove
        args: Command arguments
    """
    from maestro.tracks.json_store import JsonStore

    json_store = JsonStore()
    verbose = getattr(args, 'verbose', False)

    # Load the phase to get its track_id
    phase = json_store.load_phase(phase_id, load_tasks=False)
    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        if verbose:
            available = json_store.list_all_phases()
            if available:
                print(f"Verbose: Available phases: {', '.join(available[:10])}")
        return 1

    track_id = phase.track_id

    # Load the track and remove phase reference
    if track_id:
        track = json_store.load_track(track_id, load_phases=True, load_tasks=False)
        if track and track.phases:
            # Handle both phase IDs and Phase objects
            if isinstance(track.phases[0], str):
                track.phases = [p for p in track.phases if p != phase_id]
            else:
                track.phases = [p for p in track.phases if p.phase_id != phase_id]
            json_store.save_track(track)

    # Delete the phase file
    phase_file = json_store.phases_dir / f"{phase_id}.json"
    if phase_file.exists():
        phase_file.unlink()

    print(f"Removed phase: {phase_id}")
    return 0


def edit_phase(phase_id: str, args):
    """
    Edit a phase in $EDITOR.

    Opens the JSON phase file.
    """
    import os
    import subprocess

    json_store = JsonStore()
    phase_file = json_store.phases_dir / f"{phase_id}.json"
    editor = os.environ.get('EDITOR', 'vim')
    if not phase_file.exists():
        print(f"Error: Phase '{phase_id}' not found.")
        if getattr(args, 'verbose', False):
            available = _available_phase_ids(verbose=True)
            if available:
                print(f"Verbose: Available phases: {', '.join(available)}")
        return 1

    try:
        original = phase_file.read_text(encoding='utf-8')
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
        phase_file.write_text(new_block, encoding='utf-8')
        print(f"Updated phase '{phase_id}' JSON.")
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def set_phase_status(phase_id: str, args) -> int:
    """
    Update a phase status in JSON storage.
    """
    from maestro.tracks.json_store import JsonStore

    status_value = normalize_status(getattr(args, 'status', None))
    if not status_value:
        print(f"Error: Unknown status. Allowed: {allowed_statuses()}.")
        return 1

    json_store = JsonStore()

    # Load the phase
    phase = json_store.load_phase(phase_id, load_tasks=False)
    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        verbose = getattr(args, 'verbose', False)
        if verbose:
            available = json_store.list_all_phases()
            if available:
                print(f"Available phases: {', '.join(available[:10])}")
        return 1

    # Update phase status
    phase.status = status_value

    # Save the phase
    json_store.save_phase(phase)

    print(f"Updated phase '{phase_id}' status to '{status_value}'.")
    return 0


def set_phase_context(phase_id: str, args):
    """Set the current phase context.

    Args:
        phase_id: Phase ID to set as current
        args: Command arguments
    """
    from maestro.config.settings import get_settings
    from pathlib import Path

    json_store = JsonStore()
    phase_obj = json_store.load_phase(phase_id, load_tasks=False)
    if not phase_obj:
        print(f"Error: Phase '{phase_id}' not found.")
        verbose = getattr(args, 'verbose', False)
        if verbose:
            phase_ids = json_store.list_all_phases()
            if phase_ids:
                print(f"Verbose: Available phases: {', '.join(phase_ids)}")
        return 1

    # Set context
    settings = get_settings()
    settings.current_phase = phase_id
    # Also set current_track to phase's parent track
    if phase_obj.track_id:
        settings.current_track = phase_obj.track_id
    # Clear current_task
    settings.current_task = None
    settings.save()

    print(f"Context set to phase: {phase_id}")
    print(f"Use 'maestro task list' to see tasks in this phase.")
    return 0


def handle_phase_command(args):
    """
    Main handler for phase commands.

    Routes to appropriate subcommand handler.
    """
    # Handle 'maestro phase list [track_id]'
    if hasattr(args, 'phase_subcommand') and args.phase_subcommand:
        subcommand = args.phase_subcommand

        # For 'show' subcommand, handle the phase_id argument
        if subcommand in ['show', 'sh']:
            if hasattr(args, 'phase_id') and args.phase_id:
                phase_id = args.phase_id
                # Check if there's a phase-specific subcommand
                item_subcommand = getattr(args, 'phase_item_subcommand', None)
                if item_subcommand in ['help', 'h']:
                    print_phase_item_help()
                    return 0
                return show_phase(phase_id, args)

        # Handle other subcommands
        if subcommand in ['list', 'ls', 'l']:
            return list_phases(args)
        elif subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Phase name required. Usage: maestro phase add <name>")
                return 1
            name_parts = args.name if isinstance(args.name, list) else [args.name]
            track_id = getattr(args, 'track_id', None)
            phase_id = getattr(args, 'phase_id', None)
            if not track_id and name_parts:
                track_ids = _available_track_ids(verbose=getattr(args, 'verbose', False))
                if track_ids and name_parts[0] in track_ids:
                    track_id = name_parts[0]
                    name_parts = name_parts[1:]
            if not phase_id and len(name_parts) >= 2:
                candidate_phase_id = name_parts[0]
                if _looks_like_phase_id(candidate_phase_id):
                    phase_id = candidate_phase_id
                    name_parts = name_parts[1:]
            if not name_parts:
                print("Error: Phase name required. Usage: maestro phase add <name>")
                return 1
            if track_id:
                args.track_id = track_id
            if phase_id:
                args.phase_id = phase_id
            name = " ".join(name_parts)
            return add_phase(name, args)
        elif subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase remove <id>")
                return 1
            return remove_phase(args.phase_id, args)
        elif subcommand in ['edit', 'e']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase edit <id>")
                return 1
            return edit_phase(args.phase_id, args)
        elif subcommand in ['status', 'set-status']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase status <id> <status>")
                return 1
            if not getattr(args, 'status', None):
                print("Error: Status required. Usage: maestro phase status <id> <status>")
                return 1
            return set_phase_status(args.phase_id, args)
        elif subcommand in ['text', 'raw']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase text <id>")
                return 1
            json_store = JsonStore()
            phase_file = json_store.phases_dir / f"{args.phase_id}.json"
            if not phase_file.exists():
                print(f"Error: Phase '{args.phase_id}' not found.")
                return 1
            print(phase_file.read_text(encoding='utf-8').rstrip())
            return 0
        elif subcommand in ['set-text', 'setraw']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase set-text <id> [--file path]")
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
            phase_file = json_store.phases_dir / f"{args.phase_id}.json"
            if not phase_file.exists():
                print(f"Error: Phase '{args.phase_id}' not found.")
                return 1
            phase_file.write_text(new_block, encoding='utf-8')
            print(f"Updated phase '{args.phase_id}' JSON.")
            return 0
        elif subcommand in ['discuss', 'd']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase discuss <id>")
                return 1
            from .discuss import handle_phase_discuss
            return handle_phase_discuss(args.phase_id, args)
        elif subcommand in ['set', 'st']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase set <id>")
                return 1
            return set_phase_context(args.phase_id, args)
        elif subcommand in ['help', 'h']:
            print_phase_help()
            return 0

    # Handle 'maestro phase <id>' or 'maestro phase <id> <subcommand>' (for backward compatibility)
    # This is for when no phase_subcommand is set but we have a positional phase_id arg
    # But we had to modify this logic to work with our new parser approach
    if hasattr(args, 'phase_subcommand') and args.phase_subcommand is None:
        # If no subcommand but we have phase_id, default to show
        if hasattr(args, 'phase_id') and args.phase_id:
            return show_phase(args.phase_id, args)

    # No subcommand - show help or list based on context
    # Check if we have a current phase set
    from maestro.config.settings import get_settings
    settings = get_settings()
    if settings.current_track:
        from types import SimpleNamespace
        list_args = SimpleNamespace(track_id=settings.current_track)
        return list_phases(list_args)

    print_phase_help()
    return 0


def print_phase_help():
    """Print help for phase commands."""
    help_text = """
maestro phase - Manage project phases

USAGE:
    maestro phase list [track_id]         List all phases (or phases in track)
    maestro phase add <name>              Add new phase
    maestro phase remove <id>             Remove a phase
    maestro phase <id>                    Show phase details
    maestro phase <id> show               Show phase details
    maestro phase <id> edit               Edit phase in $EDITOR
    maestro phase <id> status <status>    Update phase status
    maestro phase text <id>               Show raw phase block
    maestro phase set-text <id>           Replace phase block (stdin or --file)
    maestro phase <id> discuss            Discuss phase with AI
    maestro phase <id> set                Set current phase context

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    show:   sh
    edit:   e
    status: set-status
    discuss: d
    set:    st
    text:   raw
    set-text: setraw

EXAMPLES:
    maestro phase list                    # List all phases
    maestro phase list cli-tpt            # List phases in track 'cli-tpt'
    maestro phase list plan               # List planned phases
    maestro phase list done               # List done phases
    maestro phase list prop               # List proposed phases
    maestro phase cli-tpt-1               # Show phase details
    maestro phase cli-tpt-1 edit          # Edit phase in $EDITOR
    maestro phase cli-tpt-1 status done --summary "Completed core work"
    maestro phase cli-tpt-1 discuss       # Discuss phase with AI
    maestro phase cli-tpt-1 set           # Set current phase context
"""
    print(help_text)


def print_phase_item_help():
    """Print help for phase item commands."""
    help_text = """
maestro phase <id> - Manage a specific phase

USAGE:
    maestro phase <id> show               Show phase details
    maestro phase <id> edit               Edit phase in $EDITOR
    maestro phase <id> status <status>    Update phase status
    maestro phase <id> discuss            Discuss phase with AI
    maestro phase <id> set                Set current phase context

ALIASES:
    show: sh
    edit: e
    status: set-status
    discuss: d
    set: st

EXAMPLES:
    maestro phase cli-tpt-1 show
    maestro phase cli-tpt-1 edit
    maestro phase cli-tpt-1 status in_progress
    maestro phase cli-tpt-1 discuss
    maestro phase cli-tpt-1 set
"""
    print(help_text)


def add_phase_parser(subparsers):
    """
    Add phase command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    # Main phase command - use parse_known_args workaround for flexible syntax
    import sys

    # Check if we need to inject 'show' subcommand for backwards compatibility
    # This handles: maestro phase <id> [show|edit|discuss|set]
    # By transforming to: maestro phase show <id> [subcommand]
    if len(sys.argv) >= 3 and sys.argv[1] in ['phase', 'ph', 'p']:
        arg = sys.argv[2]

        # If arg is numeric, resolve it to a phase_id from the list
        if arg.isdigit():
            try:
                from maestro.tracks.json_store import JsonStore
                json_store = JsonStore()
                all_phases = sorted(json_store.list_all_phases())
                idx = int(arg) - 1  # Convert to 0-based index
                if 0 <= idx < len(all_phases):
                    sys.argv[2] = all_phases[idx]
                    arg = sys.argv[2]
            except:
                pass  # If resolution fails, continue with original arg

        # If arg is not a known subcommand, treat it as phase_id and inject 'show'
        known_subcommands = [
            'list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'help', 'h',
            'show', 'sh', 'edit', 'e', 'discuss', 'd', 'set', 'st',
            'text', 'raw', 'set-text', 'setraw', 'status', 'set-status'
        ]
        # Only modify the command if it's not a global argument like --help
        if arg not in known_subcommands and arg not in ['--help', '-h']:
            # Check if there's a third argument that's a subcommand
            if len(sys.argv) >= 4 and sys.argv[3] in ['show', 'sh', 'edit', 'e', 'discuss', 'd', 'set', 'st', 'text', 'raw', 'set-text', 'setraw', 'status', 'set-status']:
                # maestro phase <id> <subcommand> - already has subcommand, just move id after 'show'
                subcommand = sys.argv[3]
                phase_id = sys.argv[2]
                sys.argv[2] = subcommand
                sys.argv[3] = phase_id
            else:
                # maestro phase <id> - inject 'show'
                sys.argv.insert(2, 'show')

    # Main phase command
    phase_parser = subparsers.add_parser(
        'phase',
        aliases=['ph', 'p'],
        help='Manage project phases'
    )

    # Phase subcommands
    phase_subparsers = phase_parser.add_subparsers(
        dest='phase_subcommand',
        help='Phase subcommands'
    )

    # maestro phase list [track_id]
    phase_list_parser = phase_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all phases (or phases in track)'
    )
    phase_list_parser.add_argument(
        'track_id',
        nargs='?',
        help='Track ID to filter phases (optional)'
    )
    phase_list_parser.add_argument('-v', '--verbose', action='store_true',
                                  help='Show detailed debug information including parsing failures')

    # maestro phase add <name>
    phase_add_parser = phase_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new phase'
    )
    phase_add_parser.add_argument('name', nargs='+', help='Phase name')
    phase_add_parser.add_argument('--id', dest='phase_id', help='Phase ID (default: first word of name)')
    phase_add_parser.add_argument('--track', dest='track_id', help='Track ID to add the phase to')
    phase_add_parser.add_argument('--after', help='Insert after phase ID')
    phase_add_parser.add_argument('--before', help='Insert before phase ID')
    phase_add_parser.add_argument('--desc', action='append', help='Description line (repeatable)')

    # maestro phase remove <id>
    phase_remove_parser = phase_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a phase'
    )
    phase_remove_parser.add_argument('phase_id', help='Phase ID to remove')

    # maestro phase help
    phase_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for phase commands'
    )

    # maestro phase show <id>
    phase_show_parser = phase_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show phase details'
    )
    phase_show_parser.add_argument('phase_id', help='Phase ID to show')
    phase_show_parser.add_argument(
        'phase_item_subcommand',
        nargs='?',
        choices=['help', 'h'],
        help='Show help for phase item'
    )

    # maestro phase edit <id>
    phase_edit_parser = phase_subparsers.add_parser(
        'edit',
        aliases=['e'],
        help='Edit phase in $EDITOR'
    )
    phase_edit_parser.add_argument('phase_id', help='Phase ID to edit')

    phase_status_parser = phase_subparsers.add_parser(
        'status',
        aliases=['set-status'],
        help='Update phase status'
    )
    phase_status_parser.add_argument('phase_id', help='Phase ID to update')
    phase_status_parser.add_argument('status', help='Status (planned, in_progress, done, proposed)')
    phase_status_parser.add_argument('--summary', help='Status change summary')

    phase_text_parser = phase_subparsers.add_parser(
        'text',
        aliases=['raw'],
        help='Show raw phase JSON payload'
    )
    phase_text_parser.add_argument('phase_id', help='Phase ID to show')

    phase_set_text_parser = phase_subparsers.add_parser(
        'set-text',
        aliases=['setraw'],
        help='Replace phase block from stdin or a file'
    )
    phase_set_text_parser.add_argument('phase_id', help='Phase ID to replace')
    phase_set_text_parser.add_argument('--file', dest='text_file', help='Read replacement text from file')

    # maestro phase discuss <id>
    phase_discuss_parser = phase_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss phase with AI'
    )
    phase_discuss_parser.add_argument('phase_id', help='Phase ID to discuss')
    phase_discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                                     default='editor', help='Discussion mode')
    phase_discuss_parser.add_argument('--resume', help='Resume previous discussion session')

    # maestro phase set <id>
    phase_set_parser = phase_subparsers.add_parser(
        'set',
        aliases=['st'],
        help='Set current phase context'
    )
    phase_set_parser.add_argument('phase_id', help='Phase ID to set as current')

    # Add optional arguments to main parser
    phase_parser.add_argument(
        '--mode',
        choices=['editor', 'terminal'],
        help='Discussion mode (editor or terminal)'
    )
    phase_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )
    phase_parser.add_argument('-v', '--verbose', action='store_true',
                              help='Show detailed debug information including parsing failures')

    return phase_parser


def discuss_phase(phase_id: str, args):
    """Discuss a specific phase with AI."""
    from .discuss import handle_phase_discuss
    return handle_phase_discuss(phase_id, args)
