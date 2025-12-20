"""
Context command implementation for Maestro CLI.

Commands:
- maestro context show or maestro context (default) - Show current context
- maestro context clear - Clear all context
"""

import argparse

from maestro.config.settings import get_settings
from maestro.data import parse_todo_md
from pathlib import Path


def show_context(args):
    """
    Show the current context: track, phase, and task.

    Args:
        args: Command arguments
    """
    settings = get_settings()

    if not settings.current_track and not settings.current_phase and not settings.current_task:
        print()
        print("No context set.")
        print("Use 'maestro track <id> set' to set a track context.")
        print()
        return 0

    print()
    print("Current context:")

    # Show track
    if settings.current_track:
        # Look up track name from docs/todo.md
        todo_path = Path('docs/todo.md')
        if todo_path.exists():
            data = parse_todo_md(str(todo_path))
            tracks = data.get('tracks', [])
            track = next((t for t in tracks if t.get('track_id') == settings.current_track), None)
            if track:
                print(f"  Track: {settings.current_track} ({track.get('name', 'Unnamed')})")
            else:
                print(f"  Track: {settings.current_track}")
        else:
            print(f"  Track: {settings.current_track}")

    # Show phase
    if settings.current_phase:
        # Look up phase name from docs/todo.md or phase files
        print(f"  Phase: {settings.current_phase}")

    # Show task
    if settings.current_task:
        print(f"  Task: {settings.current_task}")

    print()
    return 0


def clear_context(args):
    """
    Clear all context settings.

    Args:
        args: Command arguments
    """
    settings = get_settings()
    settings.current_track = None
    settings.current_phase = None
    settings.current_task = None
    settings.save()

    print("Context cleared.")
    return 0


def handle_context_command(args):
    """
    Main handler for context commands.

    Routes to appropriate subcommand handler.

    Args:
        args: Command arguments
    """
    if hasattr(args, 'context_subcommand'):
        if args.context_subcommand == 'show':
            return show_context(args)
        elif args.context_subcommand == 'clear':
            return clear_context(args)
        elif args.context_subcommand == 'help' or args.context_subcommand == 'h':
            print_context_help()
            return 0

    # Default: show context
    return show_context(args)


def print_context_help():
    """
    Print help for context commands.
    """
    help_text = """
maestro context - Manage current track/phase/task context

USAGE:
    maestro context                   Show current context
    maestro context show              Show current context
    maestro context clear             Clear current context

DESCRIPTION:
    The context system allows you to set a current track, phase, or task
    so that you don't have to repeatedly specify IDs in commands.

    When a context is set:
    - 'maestro phase list' lists phases in the current track
    - 'maestro task list' lists tasks in the current phase
    - 'maestro discuss' discusses the current phase/track

SETTING CONTEXT:
    maestro track <id> set            Set current track
    maestro phase <id> set            Set current phase
    maestro task <id> set             Set current task

EXAMPLES:
    maestro track cli-tpt set         # Set current track
    maestro phase list                # List phases in current track
    maestro phase cli-tpt-4 set       # Set current phase
    maestro task list                 # List tasks in current phase
    maestro context show              # Show what's currently set
    maestro context clear             # Clear all context
"""
    print(help_text)


def add_context_parser(subparsers):
    """
    Add context command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    # Main context command
    context_parser = subparsers.add_parser(
        'context',
        aliases=['ctx'],
        help=argparse.SUPPRESS
    )

    # Context subcommands
    context_subparsers = context_parser.add_subparsers(
        dest='context_subcommand',
        help='Context subcommands'
    )

    # maestro context show
    context_subparsers.add_parser('show', aliases=['s'])

    # maestro context clear
    context_subparsers.add_parser('clear', aliases=['c'])

    # maestro context help
    context_subparsers.add_parser('help', aliases=['h'])

    return context_parser
