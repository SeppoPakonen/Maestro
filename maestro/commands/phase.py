"""
Phase command implementation for Maestro CLI.

Commands:
- maestro phase list [track_id] - List all phases (or phases in track)
- maestro phase add <name> - Add new phase
- maestro phase remove <id> - Remove phase
- maestro phase <id> - Show phase details
- maestro phase <id> show - Show phase details
- maestro phase <id> edit - Edit phase in $EDITOR
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from maestro.data import parse_todo_md, parse_phase_md, parse_config_md


def list_phases(args):
    """
    List all phases from docs/todo.md.

    If track_id is provided, list only phases in that track.
    Otherwise, list all phases across all tracks.
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found. Run 'maestro init' first.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    # Filter by track if specified
    track_filter = getattr(args, 'track_id', None)

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

    if not phases_to_show:
        print("No phases found.")
        return 0

    # Table format
    print()
    print("=" * 80)

    # Header
    if not track_filter:
        print(f"{'Phase ID':<15} {'Name':<30} {'Track':<15} {'Status':<12}")
    else:
        print(f"{'Phase ID':<15} {'Name':<40} {'Status':<12}")
    print("-" * 80)

    # Rows
    for phase in phases_to_show:
        phase_id = phase.get('phase_id', 'N/A')
        name = phase.get('name', 'Unnamed Phase')
        status = phase.get('status', 'unknown')

        # Truncate long names
        max_name_len = 30 if not track_filter else 40
        if len(name) > max_name_len:
            name = name[:max_name_len - 3] + '...'

        # Format status with emoji
        status_display = status
        if status == 'done':
            status_display = '✅ Done'
        elif status == 'in_progress':
            status_display = '🚧 Active'
        elif status == 'planned':
            status_display = '📋 Planned'
        elif status == 'proposed':
            status_display = '💡 Proposed'

        if not track_filter:
            track_id = phase.get('_track_id', 'N/A')
            print(f"{phase_id:<15} {name:<30} {track_id:<15} {status_display:<12}")
        else:
            print(f"{phase_id:<15} {name:<40} {status_display:<12}")

    print()
    print(f"Total: {len(phases_to_show)} phases")
    print()

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

    if phase_file.exists():
        # Parse from dedicated phase file
        phase = parse_phase_md(str(phase_file))
    else:
        # Search in todo.md
        todo_path = Path('docs/todo.md')
        if todo_path.exists():
            data = parse_todo_md(str(todo_path))
            tracks = data.get('tracks', [])

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
            task_priority = task.get('priority', 'N/A')
            task_hours = task.get('estimated_hours', '?')
            print(f"  {i}. [{task_id}] {task_name}")
            print(f"      Priority: {task_priority}, Estimated: {task_hours}h")
        print()

    # Link to detailed file
    if phase_file.exists():
        print(f"Detailed documentation: {phase_file}")
        print()

    return 0


def add_phase(name: str, args):
    """
    Add a new phase to a track.

    Args:
        name: Name of the new phase
        args: Command arguments
    """
    print(f"Adding phase: {name}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


def remove_phase(phase_id: str, args):
    """
    Remove a phase from docs/todo.md.

    Args:
        phase_id: Phase ID to remove
        args: Command arguments
    """
    print(f"Removing phase: {phase_id}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


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

    if phase_file.exists():
        file_to_edit = phase_file
    else:
        # Edit todo.md
        file_to_edit = Path('docs/todo.md')
        if not file_to_edit.exists():
            print(f"Error: Neither docs/phases/{phase_id}.md nor docs/todo.md found.")
            return 1

    editor = os.environ.get('EDITOR', 'vim')

    try:
        subprocess.run([editor, str(file_to_edit)])
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def handle_phase_command(args):
    """
    Main handler for phase commands.

    Routes to appropriate subcommand handler.
    """
    # Handle 'maestro phase list [track_id]'
    if hasattr(args, 'phase_subcommand'):
        if args.phase_subcommand == 'list' or args.phase_subcommand == 'ls':
            return list_phases(args)
        elif args.phase_subcommand == 'add':
            if not hasattr(args, 'name') or not args.name:
                print("Error: Phase name required. Usage: maestro phase add <name>")
                return 1
            return add_phase(args.name, args)
        elif args.phase_subcommand == 'remove' or args.phase_subcommand == 'rm':
            if not hasattr(args, 'phase_id') or not args.phase_id:
                print("Error: Phase ID required. Usage: maestro phase remove <id>")
                return 1
            return remove_phase(args.phase_id, args)
        elif args.phase_subcommand == 'help' or args.phase_subcommand == 'h':
            print_phase_help()
            return 0

    # Handle 'maestro phase <id>' or 'maestro phase <id> <subcommand>'
    if hasattr(args, 'phase_id') and args.phase_id:
        phase_id = args.phase_id

        # Check if there's a phase-specific subcommand
        subcommand = getattr(args, 'phase_item_subcommand', None)
        if subcommand:
            if subcommand == 'show':
                return show_phase(phase_id, args)
            elif subcommand == 'edit':
                return edit_phase(phase_id, args)
            elif subcommand == 'discuss':
                from .discuss import handle_phase_discuss
                return handle_phase_discuss(phase_id, args)
            elif subcommand == 'help' or subcommand == 'h':
                print_phase_item_help()
                return 0
        # Default to 'show' if no subcommand
        return show_phase(phase_id, args)

    # No subcommand - show help or list based on context
    # Check if we have a current phase set
    config_path = Path('docs/config.md')
    if config_path.exists():
        config = parse_config_md(str(config_path))
        current_track = config.get('current_track')
        if current_track:
            # List phases in current track
            args.track_id = current_track
            return list_phases(args)

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
    maestro phase <id> discuss            Discuss phase with AI

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    show:   sh
    edit:   e
    discuss: d

EXAMPLES:
    maestro phase list                    # List all phases
    maestro phase list cli-tpt            # List phases in track 'cli-tpt'
    maestro phase cli-tpt-1               # Show phase details
    maestro phase cli-tpt-1 edit          # Edit phase in $EDITOR
    maestro phase cli-tpt-1 discuss       # Discuss phase with AI
"""
    print(help_text)


def print_phase_item_help():
    """Print help for phase item commands."""
    help_text = """
maestro phase <id> - Manage a specific phase

USAGE:
    maestro phase <id> show               Show phase details
    maestro phase <id> edit               Edit phase in $EDITOR
    maestro phase <id> discuss            Discuss phase with AI

ALIASES:
    show: sh
    edit: e
    discuss: d

EXAMPLES:
    maestro phase cli-tpt-1 show
    maestro phase cli-tpt-1 edit
    maestro phase cli-tpt-1 discuss
"""
    print(help_text)


def add_phase_parser(subparsers):
    """
    Add phase command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    # Main phase command
    phase_parser = subparsers.add_parser(
        'phase',
        aliases=['ph'],
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

    # maestro phase add <name>
    phase_add_parser = phase_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new phase'
    )
    phase_add_parser.add_argument('name', help='Phase name')

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

    # Add phase_id argument for 'maestro phase <id>' commands
    phase_parser.add_argument(
        'phase_id',
        nargs='?',
        help='Phase ID (for show/edit commands)'
    )
    phase_parser.add_argument(
        'phase_item_subcommand',
        nargs='?',
        help='Phase item subcommand (show/edit/discuss)'
    )
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

    return phase_parser


def discuss_phase(phase_id: str, args):
    """Discuss a specific phase with AI."""
    from .discuss import handle_phase_discuss
    return handle_phase_discuss(phase_id, args)
