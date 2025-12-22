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

import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from maestro.data import parse_todo_md, parse_done_md, parse_phase_md, parse_config_md
from maestro.data.markdown_writer import (
    escape_asterisk_text,
    extract_phase_block,
    insert_phase_block,
    remove_phase_block,
    replace_phase_block,
    update_phase_metadata,
    update_phase_heading_status,
)
from maestro.display.table_renderer import render_phase_table
from maestro.data.common_utils import (
    parse_todo_safe,
    parse_done_safe,
    get_all_tracks_with_phases_and_tasks,
    resolve_identifier_by_type,
    filter_items_by_track,
    print_error,
    print_warning,
    print_info
)
from .status_utils import allowed_statuses, normalize_status, status_badge, status_timestamp


def _available_track_ids(verbose: bool = False) -> List[str]:
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return []
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return []
    return [track.get('track_id') for track in data.get('tracks', []) if track.get('track_id')]


def _available_phase_ids(verbose: bool = False) -> List[str]:
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return []
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return []
    phase_ids = []
    for track in data.get('tracks', []):
        for phase in track.get('phases', []):
            phase_id = phase.get('phase_id')
            if phase_id:
                phase_ids.append(phase_id)
    return phase_ids


def list_phases(args):
    """
    List all phases from docs/todo.md and docs/done.md.

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

    Reads from docs/phases/<phase_id>.md if it exists,
    otherwise searches in docs/todo.md.
    """
    # Try to find phase file
    phase_file = Path(f'docs/phases/{phase_id}.md')

    phase = None
    verbose = getattr(args, 'verbose', False)

    if phase_file.exists():
        # Parse from dedicated phase file
        phase = parse_phase_md(str(phase_file))
    else:
        # Search in todo.md
        todo_path = Path('docs/todo.md')
        if todo_path.exists():
            data = _parse_todo_safe(todo_path, verbose=verbose)
            tracks = data.get('tracks', []) if data else []

            for track in tracks:
                for p in track.get('phases', []):
                    if p.get('phase_id') == phase_id:
                        phase = p
                        phase['_track_name'] = track.get('name', 'Unnamed')
                        break
                if phase:
                    break

    if not phase:
        print(f"Error: Phase '{phase_id}' not found.")
        if verbose:
            phase_ids = []
            if Path('docs/todo.md').exists():
                data = _parse_todo_safe(Path('docs/todo.md'), verbose=verbose)
                if data:
                    for track in data.get('tracks', []):
                        for p in track.get('phases', []):
                            pid = p.get('phase_id')
                            if pid:
                                phase_ids.append(pid)
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

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        print("Use 'maestro track add' to create a track first or run 'maestro init'.")
        return 1

    track_id = getattr(args, 'track_id', None)
    if not track_id:
        settings = get_settings()
        track_id = settings.current_track
    if not track_id:
        print("Error: Track ID required. Usage: maestro phase add --track <track_id> <name>")
        return 1

    verbose = getattr(args, 'verbose', False)
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if data is None:
        return 1
    track = next((t for t in data.get('tracks', []) if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_id}' not found in docs/todo.md.")
        if verbose:
            available = _available_track_ids(verbose=verbose)
            if available:
                print(f"Verbose: Available tracks: {', '.join(available)}")
        return 1

    phase_id = getattr(args, 'phase_id', None)
    if not phase_id:
        phase_id = name.strip().split()[0].lower()
    if phase_id.isdigit():
        print("Error: Phase ID cannot be purely numeric.")
        return 1

    if any(p.get('phase_id') == phase_id for p in track.get('phases', [])):
        print(f"Error: Phase ID '{phase_id}' already exists in track '{track_id}'.")
        return 1

    desc_lines = getattr(args, 'desc', None) or []
    escaped_phase_id = escape_asterisk_text(phase_id)
    block_lines = [
        f"### Phase {phase_id}: {name}\n",
        "\n",
        f"- *phase_id*: *{escaped_phase_id}*\n",
        "- *status*: *planned*\n",
        "- *completion*: 0\n",
        "\n",
    ]
    for line in desc_lines:
        if line.strip():
            block_lines.append(f"{line.strip()}\n")
    block_lines.append("\n")

    inserted = insert_phase_block(
        todo_path,
        track_id,
        "".join(block_lines),
        after_phase_id=getattr(args, 'after', None),
        before_phase_id=getattr(args, 'before', None),
    )
    if not inserted:
        print("Error: Unable to insert phase block.")
        return 1

    phases_dir = Path('docs/phases')
    phases_dir.mkdir(parents=True, exist_ok=True)
    phase_path = phases_dir / f"{phase_id}.md"
    if not phase_path.exists():
        track_name = track.get('name', 'Unknown Track')
        escaped_track_name = escape_asterisk_text(track_name)
        escaped_track_id = escape_asterisk_text(track_id)
        header = [
            f"# Phase {phase_id}: {name} 📋 **[Planned]**\n",
            "\n",
            f"- *phase_id*: *{escaped_phase_id}*\n",
            f"- *track*: *{escaped_track_name}*\n",
            f"- *track_id*: *{escaped_track_id}*\n",
            "- *status*: *planned*\n",
            "- *completion*: 0\n",
            "\n",
            "## Tasks\n",
            "\n",
        ]
        phase_path.write_text("".join(header), encoding='utf-8')

    print(f"Added phase '{phase_id}' ({name}) to track '{track_id}'.")
    return 0


def remove_phase(phase_id: str, args):
    """
    Remove a phase from docs/todo.md.

    Args:
        phase_id: Phase ID to remove
        args: Command arguments
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    if not remove_phase_block(todo_path, phase_id):
        print(f"Error: Phase '{phase_id}' not found in docs/todo.md.")
        if getattr(args, 'verbose', False):
            available = _available_phase_ids(verbose=True)
            if available:
                print(f"Verbose: Available phases: {', '.join(available)}")
        return 1

    phase_file = Path(f'docs/phases/{phase_id}.md')
    if phase_file.exists():
        phase_file.unlink()

    print(f"Removed phase: {phase_id}")
    return 0


def edit_phase(phase_id: str, args):
    """
    Edit a phase in $EDITOR.

    Opens docs/phases/<phase_id>.md if it exists,
    otherwise opens docs/todo.md.
    """
    import os
    import subprocess

    # Check for dedicated phase file first
    phase_file = Path(f'docs/phases/{phase_id}.md')

    editor = os.environ.get('EDITOR', 'vim')
    if phase_file.exists():
        try:
            subprocess.run([editor, str(phase_file)])
            return 0
        except Exception as e:
            print(f"Error opening editor: {e}")
            return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: Neither docs/phases/{phase_id}.md nor docs/todo.md found.")
        return 1

    block = extract_phase_block(todo_path, phase_id)
    if not block:
        print(f"Error: Phase '{phase_id}' not found in docs/todo.md.")
        if getattr(args, 'verbose', False):
            available = _available_phase_ids(verbose=True)
            if available:
                print(f"Verbose: Available phases: {', '.join(available)}")
        return 1

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
            tmp.write(block.encode('utf-8'))
            tmp_path = tmp.name
        subprocess.run([editor, tmp_path])
        new_block = Path(tmp_path).read_text(encoding='utf-8')
        Path(tmp_path).unlink(missing_ok=True)
        if new_block == block:
            print("No changes made.")
            return 0
        if not replace_phase_block(todo_path, phase_id, new_block):
            print("Error: Failed to update phase block.")
            return 1
        print(f"Updated phase '{phase_id}'.")
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def set_phase_status(phase_id: str, args) -> int:
    """
    Update a phase status in docs/todo.md and phase file.
    """
    status_value = normalize_status(getattr(args, 'status', None))
    if not status_value:
        print(f"Error: Unknown status. Allowed: {allowed_statuses()}.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    available = _available_phase_ids(verbose=getattr(args, 'verbose', False))
    if phase_id not in available:
        print(f"Error: Phase '{phase_id}' not found in docs/todo.md.")
        if available:
            print(f"Available phases: {', '.join(available)}")
        return 1

    if not update_phase_metadata(todo_path, phase_id, 'status', status_value):
        print(f"Error: Phase '{phase_id}' not found in docs/todo.md.")
        return 1

    update_phase_heading_status(todo_path, phase_id, status_badge(status_value))

    summary = getattr(args, 'summary', None)
    if summary:
        update_phase_metadata(todo_path, phase_id, 'status_summary', summary)
    else:
        print("Note: consider adding --summary to capture the status change context.")

    changed_at = status_timestamp()
    update_phase_metadata(todo_path, phase_id, 'status_changed', changed_at)

    phase_path = Path('docs/phases') / f"{phase_id}.md"
    if phase_path.exists():
        update_phase_metadata(phase_path, phase_id, 'status', status_value)
        update_phase_heading_status(phase_path, phase_id, status_badge(status_value))
        if summary:
            update_phase_metadata(phase_path, phase_id, 'status_summary', summary)
        update_phase_metadata(phase_path, phase_id, 'status_changed', changed_at)
    else:
        print(f"Warning: phase file not found at {phase_path}.")

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

    # Find phase in docs/todo.md or docs/phases/*.md
    # Set current_phase and parent current_track
    # Clear current_task

    # Look in todo.md for the phase
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: docs/todo.md not found.")
        return 1

    verbose = getattr(args, 'verbose', False)
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if data is None:
        return 1
    tracks = data.get('tracks', [])

    phase = None
    parent_track = None

    # Search for the phase in all tracks
    for track in tracks:
        for p in track.get('phases', []):
            if p.get('phase_id') == phase_id:
                phase = p
                parent_track = track.get('track_id')
                break
        if phase:
            break

    if not phase:
        # If not found in todo.md, check phase files
        phase_file = Path(f'docs/phases/{phase_id}.md')
        if phase_file.exists():
            from maestro.data import parse_phase_md
            phase_data = parse_phase_md(str(phase_file))
            phase = phase_data
        else:
            print(f"Error: Phase '{phase_id}' not found.")
            if verbose:
                phase_ids = []
                for track in tracks:
                    for p in track.get('phases', []):
                        pid = p.get('phase_id')
                        if pid:
                            phase_ids.append(pid)
                if phase_ids:
                    print(f"Verbose: Available phases: {', '.join(phase_ids)}")
            return 1

    # Set context
    settings = get_settings()
    settings.current_phase = phase_id
    # Also set current_track to phase's parent track
    if parent_track:
        settings.current_track = parent_track
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
            name = " ".join(args.name) if isinstance(args.name, list) else args.name
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
            todo_path = Path('docs/todo.md')
            block = extract_phase_block(todo_path, args.phase_id)
            if not block:
                print(f"Error: Phase '{args.phase_id}' not found in docs/todo.md.")
                return 1
            print(block.rstrip())
            return 0
        elif subcommand in ['set-text', 'setraw']:
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase set-text <id> [--file path]")
                return 1
            todo_path = Path('docs/todo.md')
            new_block = _resolve_text_input(args)
            if not new_block.strip():
                print("Error: Replacement text is empty.")
                return 1
            if not replace_phase_block(todo_path, args.phase_id, new_block):
                print(f"Error: Phase '{args.phase_id}' not found in docs/todo.md.")
                return 1
            print(f"Updated phase '{args.phase_id}'.")
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
    config_path = Path('docs/config.md')
    if config_path.exists():
        config = parse_config_md(str(config_path))
        current_track = config.get('current_track')
        if current_track:
            # List phases in current track
            from types import SimpleNamespace
            list_args = SimpleNamespace(track_id=current_track)
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
                from pathlib import Path
                todo_path = Path('docs/todo.md')
                if todo_path.exists():
                    data = parse_todo_md(str(todo_path))
                    tracks = data.get('tracks', [])
                    all_phases = []
                    for track in tracks:
                        for phase in track.get('phases', []):
                            all_phases.append(phase)

                    idx = int(arg) - 1  # Convert to 0-based index
                    if 0 <= idx < len(all_phases):
                        # Replace numeric arg with actual phase_id
                        sys.argv[2] = all_phases[idx].get('phase_id', arg)
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
        help='Show raw phase block from docs/todo.md'
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
