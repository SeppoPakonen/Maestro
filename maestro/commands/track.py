"""
Track command implementation for Maestro CLI.

Commands:
- maestro track list - List all tracks
- maestro track add <name> - Add new track
- maestro track remove <id> - Remove track
- maestro track <id> - Show track details
- maestro track <id> show - Show track details
- maestro track <id> edit - Edit track in $EDITOR
- maestro track <id> set - Set current track context
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from maestro.data import parse_todo_md


def resolve_track_identifier(identifier: str) -> Optional[str]:
    """
    Resolve a track identifier (number or ID) to a track ID.

    Args:
        identifier: Either a track number (1, 2, 3) or track ID (umk, cli-tpt)

    Returns:
        Track ID if found, None otherwise

    Examples:
        >>> resolve_track_identifier('1')  # Returns first track's ID
        'cli-tpt'
        >>> resolve_track_identifier('umk')  # Returns as-is if valid
        'umk'
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return None

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    # Try as numeric index first
    if identifier.isdigit():
        index = int(identifier) - 1  # Convert to 0-based
        if 0 <= index < len(tracks):
            return tracks[index].get('track_id')
        return None

    # Otherwise, treat as track_id and verify it exists
    for track in tracks:
        if track.get('track_id') == identifier:
            return identifier

    return None


def list_tracks(args):
    """
    List all tracks from docs/todo.md.

    Format:
    +----+-----------+--------------------+----------+------------+
    | #  | Track ID  | Name               | Status   | Completion |
    +----+-----------+--------------------+----------+------------+
    | 1  | cli-tpt   | CLI and AI System  | Planned  | 20%        |
    | 2  | umk       | UMK Integration    | Planned  | 0%         |
    +----+-----------+--------------------+----------+------------+
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found. Run 'maestro init' first.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    if not tracks:
        print("No tracks found.")
        return 0

    # Table format
    print()
    print("=" * 80)
    print("TRACKS")
    print("=" * 80)
    print()

    # Header
    print(f"{'#':<3} {'Track ID':<15} {'Name':<32} {'Status':<12} {'Phases':<8}")
    print("-" * 80)

    # Rows
    for i, track in enumerate(tracks, 1):
        track_id = track.get('track_id', 'N/A')
        name = track.get('name', 'Unnamed Track')
        status = track.get('status', 'unknown')
        phase_count = len(track.get('phases', []))

        # Truncate long names
        if len(name) > 32:
            name = name[:29] + '...'

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

        print(f"{i:<3} {track_id:<15} {name:<32} {status_display:<12} {phase_count:<8}")

    print()
    print(f"Total: {len(tracks)} tracks")
    print(f"Use 'maestro track <#>' or 'maestro track <id>' to view details")
    print()

    return 0


def show_track(track_identifier: str, args):
    """
    Show detailed information about a specific track.

    Args:
        track_identifier: Track ID or number (e.g., 'umk' or '2')
        args: Command arguments
    """
    # Resolve identifier to track_id
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    # Find the track
    track = None
    for t in tracks:
        if t.get('track_id') == track_id:
            track = t
            break

    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    # Display track details
    print()
    print("=" * 80)
    print(f"TRACK: {track.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    # Metadata
    print(f"ID:          {track.get('track_id', 'N/A')}")
    print(f"Priority:    {track.get('priority', 'N/A')}")
    print(f"Status:      {track.get('status', 'N/A')}")
    print(f"Completion:  {track.get('completion', 0)}%")
    print()

    # Description
    description = track.get('description', [])
    if description:
        print("Description:")
        for line in description:
            print(f"  {line}")
        print()

    # Phases
    phases = track.get('phases', [])
    if phases:
        print(f"Phases ({len(phases)}):")
        for i, phase in enumerate(phases, 1):
            phase_id = phase.get('phase_id', 'N/A')
            phase_name = phase.get('name', 'Unnamed')
            phase_status = phase.get('status', 'unknown')
            print(f"  {i}. [{phase_id}] {phase_name} - {phase_status}")
        print()

    return 0


def add_track(name: str, args):
    """
    Add a new track to docs/todo.md.

    Args:
        name: Name of the new track
        args: Command arguments
    """
    print(f"Adding track: {name}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


def remove_track(track_identifier: str, args):
    """
    Remove a track from docs/todo.md.

    Args:
        track_identifier: Track ID or number to remove
        args: Command arguments
    """
    # Resolve identifier to track_id
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    print(f"Removing track: {track_id}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/todo.md manually.")
    return 1


def edit_track(track_identifier: str, args):
    """
    Edit a track in $EDITOR.

    Args:
        track_identifier: Track ID or number to edit
        args: Command arguments
    """
    import os
    import subprocess

    # Resolve identifier to track_id
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    # Find the track in todo.md to get line number
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: docs/todo.md not found.")
        return 1

    editor = os.environ.get('EDITOR', 'vim')

    # For now, just open the file
    # In the future, we could jump to the specific track
    try:
        subprocess.run([editor, str(todo_path)])
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def set_track_context(track_identifier: str, args):
    """
    Set the current track context.

    Args:
        track_identifier: Track ID or number to set as current
        args: Command arguments
    """
    from maestro.config.settings import get_settings
    from maestro.data import parse_todo_md
    from pathlib import Path

    # Resolve identifier to track_id
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    # Verify track exists
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print(f"Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    track = None
    for t in tracks:
        if t.get('track_id') == track_id:
            track = t
            break

    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    # Set context
    settings = get_settings()
    settings.current_track = track_id
    settings.current_phase = None  # Clear phase and task
    settings.current_task = None
    settings.save()

    print(f"Context set to track: {track_id} ({track.get('name', 'Unnamed')})")
    print(f"Use 'maestro phase list' to see phases in this track.")
    return 0


def handle_track_command(args):
    """
    Main handler for track commands.

    Routes to appropriate subcommand handler.
    """
    # Handle track subcommands
    if hasattr(args, 'track_subcommand') and args.track_subcommand:
        subcommand = args.track_subcommand

        # List tracks
        if subcommand in ['list', 'ls', 'l']:
            return list_tracks(args)

        # Add track
        elif subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Track name required. Usage: maestro track add <name>")
                return 1
            return add_track(args.name, args)

        # Remove track
        elif subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track remove <id>")
                return 1
            return remove_track(args.track_id, args)

        # Discuss (general)
        elif subcommand in ['discuss', 'd']:
            from .discuss import handle_track_discuss
            return handle_track_discuss(None, args)

        # Show track
        elif subcommand in ['show', 'sh']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track show <id>")
                return 1
            return show_track(args.track_id, args)

        # Edit track
        elif subcommand in ['edit', 'e']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track edit <id>")
                return 1
            return edit_track(args.track_id, args)

        # Set track context
        elif subcommand in ['set', 'st']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track set <id>")
                return 1
            return set_track_context(args.track_id, args)

        # Help
        elif subcommand in ['help', 'h']:
            print_track_help()
            return 0

    # No subcommand - show help
    print_track_help()
    return 0


def print_track_help():
    """Print help for track commands."""
    help_text = """
maestro track - Manage project tracks

USAGE:
    maestro track list                    List all tracks
    maestro track add <name>              Add new track
    maestro track remove <id|#>           Remove a track
    maestro track discuss                 Discuss tracks with AI
    maestro track <id|#>                  Show track details
    maestro track <id|#> show             Show track details
    maestro track <id|#> edit             Edit track in $EDITOR
    maestro track <id|#> discuss          Discuss track with AI
    maestro track <id|#> set              Set current track context

TRACK IDENTIFIERS:
    You can use either the track ID (e.g., 'umk') or the track number (e.g., '2')
    from the track list. Both work identically.

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    discuss: d
    show:   sh
    edit:   e
    set:    st

EXAMPLES:
    maestro track list
    maestro track 2                       # Show track #2
    maestro track umk                     # Show track by ID
    maestro track 2 edit                  # Edit track #2
    maestro track umk set                 # Set track by ID
    maestro track discuss
    maestro track add "New Feature Track"
"""
    print(help_text)


def print_track_item_help():
    """Print help for track item commands."""
    help_text = """
maestro track <id> - Manage a specific track

USAGE:
    maestro track <id> show               Show track details
    maestro track <id> edit               Edit track in $EDITOR
    maestro track <id> discuss            Discuss track with AI
    maestro track <id> set                Set current track context

ALIASES:
    show: sh
    edit: e
    discuss: d
    set: st

EXAMPLES:
    maestro track cli-tpt show
    maestro track cli-tpt edit
    maestro track cli-tpt discuss
    maestro track cli-tpt set
"""
    print(help_text)


def add_track_parser(subparsers):
    """
    Add track command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    # Main track command - use parse_known_args workaround for flexible syntax
    import sys

    # Check if we need to inject 'show' subcommand for backwards compatibility
    # This handles: maestro track <id> [show|edit|discuss|set]
    # By transforming to: maestro track show <id> [subcommand]
    if len(sys.argv) >= 3 and sys.argv[1] in ['track', 'tr']:
        arg = sys.argv[2]
        # If arg is not a known subcommand, treat it as track_id and inject 'show'
        if arg not in ['list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'discuss', 'd', 'help', 'h', 'show', 'sh', 'edit', 'e', 'set', 'st']:
            # Check if there's a third argument that's a subcommand
            if len(sys.argv) >= 4 and sys.argv[3] in ['show', 'sh', 'edit', 'e', 'discuss', 'd', 'set', 'st']:
                # maestro track <id> <subcommand> - already has subcommand, just move id after 'show'
                subcommand = sys.argv[3]
                track_id = sys.argv[2]
                sys.argv[2] = subcommand
                sys.argv[3] = track_id
            else:
                # maestro track <id> - inject 'show'
                sys.argv.insert(2, 'show')

    # Main track command
    track_parser = subparsers.add_parser(
        'track',
        aliases=['tr'],
        help='Manage project tracks'
    )

    # Track subcommands
    track_subparsers = track_parser.add_subparsers(
        dest='track_subcommand',
        help='Track subcommands'
    )

    # maestro track list
    track_list_parser = track_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all tracks'
    )

    # maestro track add <name>
    track_add_parser = track_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new track'
    )
    track_add_parser.add_argument('name', help='Track name')

    # maestro track remove <id>
    track_remove_parser = track_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a track'
    )
    track_remove_parser.add_argument('track_id', help='Track ID to remove')

    # maestro track discuss
    track_discuss_parser = track_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss tracks with AI'
    )

    # maestro track help
    track_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for track commands'
    )

    # maestro track show <id>
    track_show_parser = track_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show track details'
    )
    track_show_parser.add_argument('track_id', help='Track ID to show')

    # maestro track edit <id>
    track_edit_parser = track_subparsers.add_parser(
        'edit',
        aliases=['e'],
        help='Edit track in $EDITOR'
    )
    track_edit_parser.add_argument('track_id', help='Track ID to edit')

    # maestro track set <id>
    track_set_parser = track_subparsers.add_parser(
        'set',
        aliases=['st'],
        help='Set current track context'
    )
    track_set_parser.add_argument('track_id', help='Track ID to set as current')

    # Add optional arguments to main parser
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
