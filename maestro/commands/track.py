"""
Track command implementation for Maestro CLI.

Commands:
- maestro track list - List all tracks
- maestro track add <name> - Add new track
- maestro track remove <id> - Remove track
- maestro track <id> - Show track details
- maestro track <id> show - Show track details
- maestro track <id> list - List phases in track
- maestro track <id> details - Show track details with phases/tasks
- maestro track <id> edit - Edit track in $EDITOR
- maestro track <id> set - Set current track context
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from maestro.data import parse_todo_md, parse_done_md
from .discuss import handle_track_discuss


def resolve_track_identifier(identifier: str) -> Optional[str]:
    """
    Resolve a track identifier (number or ID) to a track ID.

    Args:
        identifier: Either a track number (1, 2, 3) or track ID (umk, cli-tpt)

    Returns:
        Track ID if found, None otherwise
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return None

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])
    if identifier.isdigit():
        index = int(identifier) - 1
        if 0 <= index < len(tracks):
            return tracks[index].get('track_id')
        return None

    for track in tracks:
        if track.get('track_id') == identifier:
            return identifier

    return None


def list_tracks(args) -> int:
    """
    List all tracks from docs/todo.md.
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found. Run 'maestro init' first.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])
    done_path = Path('docs/done.md')
    done_tracks = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])

    if not tracks:
        print("No tracks found.")
        return 0

    print()
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    term_width = max(term_width, 80)
    print("=" * term_width)
    print("TRACKS")
    print("=" * term_width)
    print()

    max_name_len = max(
        (len(track.get('name', '')) for track in tracks),
        default=len('Name'),
    )
    name_width = min(max(max_name_len, len('Name')), term_width - 3 - 1 - 22 - 1 - 4 - 1 - 6 - 1 - 6)
    name_width = max(name_width, len('Name'))
    print(f"{'#':<3} {'Track ID':<22} {'Name':<{name_width}} {'St':<4} {'Ph':<6} {'Todo':<6}")
    print("-" * term_width)

    done_phase_counts = {
        track.get('track_id', ''): len(track.get('phases', []))
        for track in done_tracks
    }

    for i, track in enumerate(tracks, 1):
        track_id = track.get('track_id', 'N/A')
        name = track.get('name', 'Unnamed Track')
        status = track.get('status', 'unknown')
        phases = track.get('phases', [])
        todo_count = sum(
            1
            for phase in phases
            if phase.get('status') in ('planned', 'proposed', 'in_progress')
        )
        done_in_todo_count = sum(
            1
            for phase in phases
            if phase.get('status') == 'done'
        )
        done_phase_count = done_phase_counts.get(track_id, 0)
        phase_count = todo_count + done_in_todo_count + done_phase_count

        if len(name) > name_width:
            if name_width >= 4:
                name = name[:name_width - 3] + '...'
            else:
                name = name[:name_width]

        status_display = status
        if status == 'done':
            status_display = '✅'
        elif status == 'in_progress':
            status_display = '🚧'
        elif status in ('planned', 'todo'):
            status_display = '📋'
        elif status == 'proposed':
            status_display = '💡'

        print(f"{i:<3} {track_id:<22} {name:<{name_width}} {status_display:<4} {phase_count:<6} {todo_count:<6}")

    print()
    print(f"Total: {len(tracks)} tracks")
    print("Use 'maestro track <#>' or 'maestro track <id>' to view details")
    print()

    return 0


def show_track(track_identifier: str, args) -> int:
    """
    Show detailed information about a specific track.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    done_path = Path('docs/done.md')
    done_phases = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])
        for done_track in done_tracks:
            if done_track.get('track_id') == track_id:
                done_phases = done_track.get('phases', [])
                break

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    print()
    print("=" * 80)
    print(f"TRACK: {track.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    print(f"ID:          {track.get('track_id', 'N/A')}")
    print(f"Priority:    {track.get('priority', 'N/A')}")
    print(f"Status:      {track.get('status', 'N/A')}")
    print(f"Completion:  {track.get('completion', 0)}%")
    print()

    description = track.get('description', [])
    if description:
        print("Description:")
        for line in description:
            print(f"  {line}")
        print()

    phases = track.get('phases', [])
    todo_phases = [phase for phase in phases if phase.get('status') != 'done']

    print(f"Todo phases ({len(todo_phases)}):")
    if todo_phases:
        for i, phase in enumerate(todo_phases, 1):
            phase_id = phase.get('phase_id', 'N/A')
            phase_name = phase.get('name', 'Unnamed')
            phase_status = phase.get('status', 'unknown')
            print(f"  {i}. [{phase_id}] {phase_name} - {phase_status}")
    else:
        print("  (none)")
    print()

    if done_phases:
        total_done = len(done_phases)
        visible_done = done_phases[-10:]
        if total_done > len(visible_done):
            done_label = f"Done phases ({len(visible_done)} of {total_done}):"
        else:
            done_label = f"Done phases ({len(visible_done)}):"
        print(done_label)
        for i, phase in enumerate(visible_done, 1):
            phase_id = phase.get('phase_id', 'N/A')
            phase_name = phase.get('name', 'Unnamed')
            phase_status = phase.get('status', 'done')
            print(f"  {i}. [{phase_id}] {phase_name} - {phase_status}")
        print()

    return 0


def show_track_details(track_identifier: str, args) -> int:
    """
    Show detailed information about a specific track with all phases and their sub-tasks.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    done_path = Path('docs/done.md')
    done_phases = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])
        for done_track in done_tracks:
            if done_track.get('track_id') == track_id:
                done_phases = done_track.get('phases', [])
                break

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    print()
    print("=" * 80)
    print(f"TRACK: {track.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    print(f"ID:          {track.get('track_id', 'N/A')}")
    print(f"Priority:    {track.get('priority', 'N/A')}")
    print(f"Status:      {track.get('status', 'N/A')}")
    print(f"Completion:  {track.get('completion', 0)}%")
    print()

    description = track.get('description', [])
    if description:
        print("Description:")
        for line in description:
            print(f"  {line}")
        print()

    all_phases = track.get('phases', []) + done_phases

    print("=" * 80)
    print("PHASES")
    print("=" * 80)
    print()

    sorted_phases = sorted(
        all_phases,
        key=lambda p: (p.get('status', 'planned') != 'done', p.get('phase_id', '')),
    )

    for phase in sorted_phases:
        phase_id = phase.get('phase_id', 'N/A')
        phase_name = phase.get('name', 'Unnamed')
        phase_status = phase.get('status', 'unknown')
        phase_completion = phase.get('completion', 0)

        if phase_status == 'done':
            status_emoji = "✅"
        elif phase_status == 'planned':
            status_emoji = "📋"
        elif phase_status == 'in_progress':
            status_emoji = "🚧"
        else:
            status_emoji = "💡"

        print(f"{status_emoji} Phase {phase_id}: {phase_name} [{phase_status.title()}]")
        print(f"   Completion: {phase_completion}%")
        print()

        tasks = phase.get('tasks', [])
        if tasks:
            print(f"   Tasks ({len(tasks)}):")
            for task in tasks:
                task_id = task.get('task_id', task.get('task_number', 'N/A'))
                task_name = task.get('name', 'Unnamed')
                task_completed = task.get('completed', False)

                task_status_emoji = "✅" if task_completed else "⬜"
                print(f"     {task_status_emoji} [{task_id}] {task_name}")

                task_description = task.get('description', [])
                if task_description:
                    for desc_line in task_description:
                        if desc_line.strip() and not desc_line.startswith('- [') and not desc_line.startswith('  - '):
                            cleaned_desc = desc_line.replace(f"**{task_id}**", "").strip()
                            if cleaned_desc.startswith('-'):
                                cleaned_desc = cleaned_desc[1:].strip()
                            if cleaned_desc:
                                print(f"         - {cleaned_desc}")
            print()
        else:
            print("   Tasks: (none)")
            print()

    print()
    return 0


def add_track(name: str, args) -> int:
    """
    Add a new track to docs/todo.md.
    """
    print(f"Adding track: {name}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


def remove_track(track_identifier: str, args) -> int:
    """
    Remove a track from docs/todo.md.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    print(f"Removing track: {track_id}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


def edit_track(track_identifier: str, args) -> int:
    """
    Edit a track in $EDITOR.
    """
    import os
    import subprocess

    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    editor = os.environ.get('EDITOR', 'vim')
    try:
        subprocess.run([editor, str(todo_path)])
        return 0
    except Exception as exc:
        print(f"Error opening editor: {exc}")
        return 1


def set_track_context(track_identifier: str, args) -> int:
    """
    Set the current track context.
    """
    from maestro.config.settings import get_settings

    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    settings = get_settings()
    settings.current_track = track_id
    settings.current_phase = None
    settings.current_task = None
    settings.save()

    print(f"Context set to track: {track_id} ({track.get('name', 'Unnamed')})")
    print("Use 'maestro phase list' to see phases in this track.")
    return 0


def handle_track_command(args) -> int:
    """
    Main handler for track commands.
    """
    if hasattr(args, 'track_subcommand') and args.track_subcommand:
        subcommand = args.track_subcommand

        if subcommand in ['list', 'ls', 'l']:
            return list_tracks(args)

        if subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Track name required. Usage: maestro track add <name>")
                return 1
            return add_track(args.name, args)

        if subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track remove <id>")
                return 1
            return remove_track(args.track_id, args)

        if subcommand in ['discuss', 'd']:
            return handle_track_discuss(getattr(args, 'track_id', None), args)

        if subcommand in ['show', 'sh', 's']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track show <id>")
                return 1
            if getattr(args, 'track_item_action', None) in ['help', 'h']:
                print_track_item_help()
                return 0
            if getattr(args, 'track_item_action', None) in ['list', 'ls', 'l']:
                track_id = resolve_track_identifier(args.track_id)
                if not track_id:
                    print(f"Error: Track '{args.track_id}' not found.")
                    print("Use 'maestro track list' to see available tracks.")
                    return 1
                from .phase import list_phases
                return list_phases(SimpleNamespace(track_id=track_id))
            return show_track(args.track_id, args)

        if subcommand in ['details', 'dt']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track details <id>")
                return 1
            return show_track_details(args.track_id, args)

        if subcommand in ['edit', 'e']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track edit <id>")
                return 1
            return edit_track(args.track_id, args)

        if subcommand in ['set', 'st']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track set <id>")
                return 1
            return set_track_context(args.track_id, args)

        if subcommand in ['help', 'h']:
            print_track_help()
            return 0

    print_track_help()
    return 0


def print_track_help() -> None:
    """Print help for track commands."""
    help_text = """
maestro track - Manage project tracks

USAGE:
    maestro track list                    List all tracks
    maestro track add <name>              Add new track
    maestro track remove <id|#>           Remove a track
    maestro track discuss [id|#]          Discuss tracks with AI
    maestro track <id|#>                  Show track details
    maestro track <id|#> show             Show track details
    maestro track <id|#> list             List phases in this track
    maestro track <id|#> details          Show track details with phases/tasks
    maestro track <id|#> edit             Edit track in $EDITOR
    maestro track <id|#> set              Set current track context

TRACK IDENTIFIERS:
    You can use either the track ID (e.g., 'umk') or the track number (e.g., '2')
    from the track list. Both work identically.

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    discuss: d
    show:   s, sh
    details: dt
    edit:   e
    set:    st

EXAMPLES:
    maestro track list
    maestro track 2
    maestro track umk
    maestro track 2 list
    maestro track umk details
    maestro track umk set
    maestro track discuss
    maestro track umk discuss
"""
    print(help_text)


def print_track_item_help() -> None:
    """Print help for track item commands."""
    help_text = """
maestro track <id> - Manage a specific track

USAGE:
    maestro track <id> show               Show track details
    maestro track <id> list               List phases in this track
    maestro track <id> details            Show track details with phases/tasks
    maestro track <id> edit               Edit track in $EDITOR
    maestro track <id> discuss            Discuss track with AI
    maestro track <id> set                Set current track context

ALIASES:
    show: s, sh
    list: l, ls
    details: dt
    edit: e
    discuss: d
    set: st

EXAMPLES:
    maestro track cli-tpt show
    maestro track cli-tpt list
    maestro track cli-tpt details
    maestro track cli-tpt edit
    maestro track cli-tpt discuss
    maestro track cli-tpt set
"""
    print(help_text)


def add_track_parsers(subparsers):
    """
    Add track command parser to the main argument parser.
    """
    if len(sys.argv) >= 3 and sys.argv[1] in ['track', 'tr', 't']:
        arg = sys.argv[2]
        known_subcommands = [
            'list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'discuss', 'd',
            'help', 'h', 'show', 'sh', 's', 'details', 'dt', 'edit', 'e', 'set', 'st'
        ]
        if arg not in known_subcommands:
            if len(sys.argv) >= 4 and sys.argv[3] in ['show', 'sh', 's', 'details', 'dt', 'edit', 'e', 'discuss', 'd', 'set', 'st']:
                subcommand = sys.argv[3]
                track_id = sys.argv[2]
                sys.argv[2] = subcommand
                sys.argv[3] = track_id
            else:
                sys.argv.insert(2, 'show')

    track_parser = subparsers.add_parser(
        'track',
        aliases=['tr', 't'],
        help='Manage project tracks'
    )

    track_subparsers = track_parser.add_subparsers(
        dest='track_subcommand',
        help='Track subcommands'
    )

    track_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all tracks'
    )

    track_add_parser = track_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new track'
    )
    track_add_parser.add_argument('name', help='Track name')

    track_remove_parser = track_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a track'
    )
    track_remove_parser.add_argument('track_id', help='Track ID to remove')

    track_discuss_parser = track_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss tracks with AI'
    )
    track_discuss_parser.add_argument('track_id', nargs='?', help='Track ID to discuss')

    track_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for track commands'
    )

    track_show_parser = track_subparsers.add_parser(
        'show',
        aliases=['s', 'sh'],
        help='Show track details'
    )
    track_show_parser.add_argument('track_id', help='Track ID to show')
    track_show_parser.add_argument(
        'track_item_action',
        nargs='?',
        choices=['help', 'h', 'list', 'ls', 'l'],
        help='Show help or list phases for a track'
    )

    track_details_parser = track_subparsers.add_parser(
        'details',
        aliases=['dt'],
        help='Show track details with all phases and tasks'
    )
    track_details_parser.add_argument('track_id', help='Track ID to show details for')

    track_edit_parser = track_subparsers.add_parser(
        'edit',
        aliases=['e'],
        help='Edit track in $EDITOR'
    )
    track_edit_parser.add_argument('track_id', help='Track ID to edit')

    track_set_parser = track_subparsers.add_parser(
        'set',
        aliases=['st'],
        help='Set current track context'
    )
    track_set_parser.add_argument('track_id', help='Track ID to set as current')

    track_parser.add_argument(
        '--mode',
        choices=['editor', 'terminal'],
        help='Discussion mode (editor or terminal)'
    )
    track_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )

    return track_parser
