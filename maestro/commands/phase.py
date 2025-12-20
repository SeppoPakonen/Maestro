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
from pathlib import Path
from typing import Optional, Dict, List
from maestro.data import parse_todo_md, parse_phase_md, parse_config_md


def list_phases(args):
    """
    List all phases from docs/todo.md.

    If track_id is provided, list only phases in that track.
    Otherwise, list all phases across all tracks.
    """
    from maestro.config.settings import get_settings

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found. Run 'maestro init' first.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    # If no track_id provided and context is set, use context
    track_filter = getattr(args, 'track_id', None)
    if not track_filter:
        settings = get_settings()
        if settings.current_track:
            track_filter = settings.current_track
            print(f"Using current track context: {track_filter}")
            print()

    phases_to_show = []

    # TODO: Add support for numeric track identifiers
    # if track_filter and track_filter.isdigit():
    #     resolved_track_id = resolve_track_identifier(track_filter)
    #     if not resolved_track_id:
    #         print(f"Error: Track '{track_filter}' not found.")
    #         return 1
    #     track_filter = resolved_track_id

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
    print("=" * 120)

    # Header
    if not track_filter:
        print(f"{'#':<4} {'Phase ID':<15} {'Name':<45} {'Track':<20} {'Status':<15}")
    else:
        print(f"{'#':<4} {'Phase ID':<15} {'Name':<60} {'Status':<15}")
    print("-" * 120)

    # Rows
    for idx, phase in enumerate(phases_to_show, 1):
        phase_id = phase.get('phase_id', 'N/A')
        name = phase.get('name', 'Unnamed Phase')
        status = phase.get('status', 'unknown')

        # Truncate long names
        max_name_len = 45 if not track_filter else 60
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
            print(f"{idx:<4} {phase_id:<15} {name:<45} {track_id:<20} {status_display:<15}")
        else:
            print(f"{idx:<4} {phase_id:<15} {name:<60} {status_display:<15}")

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


def set_phase_context(phase_id: str, args):
    """Set the current phase context.

    Args:
        phase_id: Phase ID to set as current
        args: Command arguments
    """
    from maestro.config.settings import get_settings
    from maestro.data import parse_todo_md
    from pathlib import Path

    # Find phase in docs/todo.md or docs/phases/*.md
    # Set current_phase and parent current_track
    # Clear current_task

    # Look in todo.md for the phase
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
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
            return add_phase(args.name, args)
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
    maestro phase <id> discuss            Discuss phase with AI
    maestro phase <id> set                Set current phase context

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    show:   sh
    edit:   e
    discuss: d
    set:    st

EXAMPLES:
    maestro phase list                    # List all phases
    maestro phase list cli-tpt            # List phases in track 'cli-tpt'
    maestro phase cli-tpt-1               # Show phase details
    maestro phase cli-tpt-1 edit          # Edit phase in $EDITOR
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
    maestro phase <id> discuss            Discuss phase with AI
    maestro phase <id> set                Set current phase context

ALIASES:
    show: sh
    edit: e
    discuss: d
    set: st

EXAMPLES:
    maestro phase cli-tpt-1 show
    maestro phase cli-tpt-1 edit
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
        known_subcommands = ['list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'help', 'h', 'show', 'sh', 'edit', 'e', 'discuss', 'd', 'set', 'st']
        if arg not in known_subcommands:
            # Check if there's a third argument that's a subcommand
            if len(sys.argv) >= 4 and sys.argv[3] in ['show', 'sh', 'edit', 'e', 'discuss', 'd', 'set', 'st']:
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

    return phase_parser


def discuss_phase(phase_id: str, args):
    """Discuss a specific phase with AI."""
    from .discuss import handle_phase_discuss
    return handle_phase_discuss(phase_id, args)
