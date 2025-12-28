"""
CLI argument parsing for Maestro.
"""
import argparse
import sys
import os
from typing import Any
from .utils import _filter_suppressed_help, Colors, styled_print, print_subheader
from .. import __version__


class StyledArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that provides styled help output."""

    def __init__(self, *args, show_banner=False, **kwargs):
        """Initialize with optional banner flag."""
        super().__init__(*args, **kwargs)
        self.show_banner = show_banner

    def format_help(self):
        """Override format_help to return styled output."""
        # Get the original help text
        original_help = _filter_suppressed_help(super().format_help())

        # Apply styling to the help text
        lines = original_help.split('\n')
        styled_lines = []

        for line in lines:
            if line.strip() == '':
                styled_lines.append('')
            elif line.startswith('usage:') or line.startswith('options:') or line.startswith('optional arguments:'):
                # Style section headers
                styled_lines.append(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}{line}{Colors.RESET}")
            elif line.startswith('  -') or line.startswith('    -'):
                # Style argument descriptions
                if ':' in line and not line.startswith('    -'):
                    # This is a main argument line
                    styled_lines.append(f"{Colors.BRIGHT_YELLOW}{line}{Colors.RESET}")
                else:
                    # This is a sub-description line
                    styled_lines.append(f"{Colors.BRIGHT_WHITE}{line}{Colors.RESET}")
            else:
                # Style general description text
                styled_lines.append(f"{Colors.BRIGHT_GREEN}{line}{Colors.RESET}")

        return '\n'.join(styled_lines)

    def print_help(self, file=None):
        """Override print_help to use our styled formatter."""
        # Only show banner for main parser
        if self.show_banner:
            # Import pyfiglet to generate ASCII art for "MAESTRO"
            try:
                import pyfiglet

                # Generate ASCII art for "MAESTRO" using the letters font
                ascii_art = pyfiglet.figlet_format("MAESTRO", font="letters")

                # Print the ASCII art with cyan color
                for line in ascii_art.split('\n'):
                    if line.strip():  # Only print non-empty lines
                        styled_print(line, Colors.BRIGHT_CYAN, Colors.BOLD, 0)

                print()

            except ImportError:
                # If pyfiglet is not available, just print a simple header
                styled_print("MAESTRO", Colors.BRIGHT_CYAN, Colors.BOLD, 0)
                print()

        # Print the styled help using our functions
        original_help = _filter_suppressed_help(super().format_help())
        lines = original_help.split('\n')

        if self.show_banner:
            print_subheader("COMMAND OPTIONS")

        for line in lines:
            if not line.strip():
                continue
            elif line.startswith('usage:'):
                styled_print(line, Colors.BRIGHT_YELLOW, Colors.BOLD, 0)
            elif line.startswith('options:') or line.startswith('optional arguments:'):
                styled_print(line, Colors.BRIGHT_CYAN, Colors.BOLD, 0)
            elif line.startswith('  -') or line.startswith('    -'):
                if line.startswith('    -'):
                    # Sub-description
                    styled_print(line, Colors.BRIGHT_WHITE, None, 4)
                else:
                    # Main argument
                    styled_print(line, Colors.BRIGHT_YELLOW, None, 0)
            else:
                styled_print(line, Colors.BRIGHT_GREEN, None, 0)

        # Add a footer with version information only for main parser
        if self.show_banner:
            print()
            styled_print(f" maestro v{__version__} ", Colors.BRIGHT_MAGENTA, None, 0)
            styled_print(" Conductor of AI symphonies 🎼 ", Colors.BRIGHT_RED, Colors.BOLD, 0)
            styled_print(" Copyright 2025 Seppo Pakonen ", Colors.BRIGHT_YELLOW, Colors.BOLD, 0)


def _reorder_subparser_actions(subparsers, preferred_order):
    """Helper to reorder subparser actions."""
    actions = list(getattr(subparsers, "_choices_actions", []))
    if not actions:
        return
    preferred_set = set(preferred_order)
    ordered = []
    for name in preferred_order:
        for action in actions:
            if action.dest == name:
                ordered.append(action)
                break
    for action in actions:
        if action.dest not in preferred_set:
            ordered.append(action)
    subparsers._choices_actions[:] = ordered

    name_map = getattr(subparsers, "_name_parser_map", None)
    if not isinstance(name_map, dict):
        return
    new_map = {}
    seen_parsers = set()
    for name in preferred_order:
        parser = name_map.get(name)
        if not parser or parser in seen_parsers:
            continue
        seen_parsers.add(parser)
        keys_for_parser = [key for key, value in name_map.items() if value is parser]
        if name in keys_for_parser:
            keys_for_parser.remove(name)
            keys_for_parser = [name] + keys_for_parser
        for key in keys_for_parser:
            new_map[key] = parser
    for key, parser in name_map.items():
        if parser in seen_parsers:
            continue
        keys_for_parser = [alias for alias, value in name_map.items() if value is parser]
        for alias in keys_for_parser:
            new_map[alias] = parser
        seen_parsers.add(parser)
    subparsers._name_parser_map = new_map
    subparsers.choices = new_map


def create_main_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for Maestro."""
    from .. import __version__

    parser = StyledArgumentParser(
        description="Maestro - AI Task Management CLI\n\n"
                    "Short aliases are available for all commands and subcommands.\n"
                    "Examples: 'maestro b p' (build plan), 'maestro s l' (session list),\n"
                    "          'maestro p tr' (plan tree), 'maestro t l' (track list)",
        formatter_class=argparse.RawTextHelpFormatter,
        show_banner=True,
        allow_abbrev=False
    )
    parser.add_argument('--version', action='version',
                       version=f'maestro {__version__}',
                       help='Show version information')
    parser.add_argument('-s', '--session', required=False,
                       help='Path to session JSON file (required for most commands)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed debug, engine commands, and file paths')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Suppress streaming AI output and extra messages')

    # Create subparsers for command-based interface
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Add the help command first to ensure it's always available
    subparsers.add_parser('help', aliases=['h'], help='Show help for all commands')

    # Import and register all command parsers
    from ..commands import (
        add_track_parser,
        add_phase_parser,
        add_task_parser,
        add_discuss_parser,
        add_settings_parser,
        add_issues_parser,
        add_solutions_parser,
        add_ai_parser,
        add_work_parser,
        add_wsession_parser,
        add_init_parser,
        add_plan_parser,
        add_understand_parser,
        add_tu_parser,
        add_repo_parser,
        add_runbook_parser,
        add_workflow_parser,
        add_make_parser,
    )
    from ..commands.convert import add_convert_parser
    from ..commands.log import add_log_parser
    from ..commands.cache import add_cache_parser

    # Register all available command parsers
    add_init_parser(subparsers)
    add_runbook_parser(subparsers)  # Add runbook parser between init and workflow
    add_workflow_parser(subparsers)  # Add workflow parser between runbook and repo
    add_repo_parser(subparsers)  # Add repo parser after workflow
    add_plan_parser(subparsers)  # Add plan parser to position between repo and track
    add_make_parser(subparsers)  # Add make parser near repo/build commands
    add_log_parser(subparsers)  # Add log parser for observability pipeline
    add_cache_parser(subparsers)  # Add cache parser for AI cache management
    add_track_parser(subparsers)
    add_phase_parser(subparsers)
    add_task_parser(subparsers)
    add_discuss_parser(subparsers)
    add_settings_parser(subparsers)
    add_issues_parser(subparsers)
    add_solutions_parser(subparsers)
    add_ai_parser(subparsers)
    add_work_parser(subparsers)
    add_wsession_parser(subparsers)
    add_understand_parser(subparsers)
    add_tu_parser(subparsers)
    add_convert_parser(subparsers)  # Add convert parser after tu parser

    # Also add the original core commands
    add_core_subparsers(subparsers)

    return parser


def add_core_subparsers(subparsers):
    """Add the original core subparsers that were handled in main.py"""
    # Session subparsers
    session_parser = subparsers.add_parser(
        'session',
        aliases=['s'],
        help='[DEPRECATED] Use wsession instead',
        description="[DEPRECATED] Legacy session management. Use 'maestro wsession' for work sessions and breadcrumbs."
    )
    session_subparsers = session_parser.add_subparsers(dest='session_subcommand', help='Session subcommands')
    session_subparsers.add_parser('new', aliases=['n'], help='Create new session')
    session_subparsers.add_parser('list', aliases=['ls', 'l'], help='List sessions')
    session_subparsers.add_parser('set', aliases=['st'], help='Set active session')
    session_subparsers.add_parser('get', aliases=['g'], help='Get active session')
    session_subparsers.add_parser('remove', aliases=['rm'], help='Remove session')
    session_subparsers.add_parser('details', aliases=['d'], help='Show session details')
    breadcrumbs_parser = session_subparsers.add_parser('breadcrumbs', aliases=['bc'], help='Show work session breadcrumbs')
    breadcrumbs_parser.add_argument('session_id', help='Session ID (or prefix)')
    breadcrumbs_parser.add_argument('--summary', action='store_true', help='Show summary only')
    breadcrumbs_parser.add_argument('--depth', type=int, help='Depth level to include')
    breadcrumbs_parser.add_argument('--limit', type=int, help='Limit number of breadcrumbs displayed')

    timeline_parser = session_subparsers.add_parser('timeline', aliases=['tl'], help='Show work session timeline')
    timeline_parser.add_argument('session_id', help='Session ID (or prefix)')

    stats_parser = session_subparsers.add_parser('stats', aliases=['stt'], help='Show work session stats')
    stats_parser.add_argument('session_id', nargs='?', help='Session ID (or prefix)')
    stats_parser.add_argument('--tree', action='store_true', help='Include child sessions')

    # Note: Plan subparsers are now handled in the commands module
    # See maestro/commands/plan.py for the current implementation

    # Rules subparsers
    rules_parser = subparsers.add_parser('rules', aliases=['r'], help='[DEPRECATED] Use solutions instead')
    rules_subparsers = rules_parser.add_subparsers(dest='rules_subcommand', help='Rules subcommands')
    rules_subparsers.add_parser('list', aliases=['ls'], help='List rules')
    rules_subparsers.add_parser('edit', aliases=['e'], help='Edit rules file')

    # Root subparsers
    root_parser = subparsers.add_parser('root', help='[DEPRECATED] Use track/phase/task hierarchy')
    root_subparsers = root_parser.add_subparsers(dest='root_subcommand', help='Root subcommands')
    root_subparsers.add_parser('set', aliases=['s'], help='Set root task')
    root_subparsers.add_parser('get', aliases=['g'], help='Get root task')
    root_subparsers.add_parser('refine', aliases=['r'], help='Refine root task')
    root_subparsers.add_parser('discuss', aliases=['d'], help='Discuss root task')
    root_subparsers.add_parser('show', aliases=['sh'], help='Show root task details')

    # Note: Log parser is now handled in maestro/commands/log.py (observability pipeline)
    # Old log management has been replaced with new log scan functionality

    # Resume command (no subcommands)
    subparsers.add_parser('resume', aliases=['rs'], help='[DEPRECATED] Use work resume or discuss resume')

    # Project ops command
    ops_parser = subparsers.add_parser('ops', help='Project operations automation')
    ops_subparsers = ops_parser.add_subparsers(dest='ops_subcommand', help='Project ops subcommands')
    validate_parser = ops_subparsers.add_parser('validate', help='Validate project operations JSON file')
    validate_parser.add_argument('json_file', help='JSON file containing project operations')
    preview_parser = ops_subparsers.add_parser('preview', help='Preview changes from project operations')
    preview_parser.add_argument('json_file', help='JSON file containing project operations')
    apply_parser = ops_subparsers.add_parser('apply', help='Apply project operations')
    apply_parser.add_argument('json_file', help='JSON file containing project operations')

    # Work command is registered in maestro.commands.work


def normalize_command_aliases(args: argparse.Namespace) -> argparse.Namespace:
    """Normalize command aliases to main command names."""
    # Normalize command aliases to main command names
    # This ensures aliases like 's' are mapped to 'session', etc.
    command_alias_map = {
        's': 'session',
        'r': 'rules',
        'p': 'phase',
        't': 'track',
        'l': 'log',
        'c': 'convert',
        'b': 'make',
        'build': 'make',
        'wk': 'work',
        'ws': 'wsession',
        'runba': 'runbook',
        'rb': 'runbook'
    }
    if args.command in ('build', 'b'):
        setattr(args, "_deprecated_build_alias", True)
    # Map alias to main command name if present
    args.command = command_alias_map.get(args.command, args.command)

    # Normalize subcommand aliases based on the main command
    if args.command and hasattr(args, 'session_subcommand') and args.session_subcommand:
        if args.command == 'session':
            session_subcommand_alias_map = {
                'n': 'new',
                'ls': 'list',
                'l': 'list',
                'st': 'set',
                'g': 'get',
                'rm': 'remove',
                'd': 'details',
                'bc': 'breadcrumbs',
                'tl': 'timeline',
                'stt': 'stats',
                'h': 'help'
            }
            args.session_subcommand = session_subcommand_alias_map.get(args.session_subcommand, args.session_subcommand)
    elif args.command and hasattr(args, 'plan_subcommand') and args.plan_subcommand:
        if args.command == 'plan':
            plan_subcommand_alias_map = {
                'a': 'add',
                'ls': 'list',
                'tr': 'tree',
                'rm': 'remove',
                'sh': 'show',
                'ai': 'add-item',
                'ri': 'remove-item',
                'o': 'ops',
                'd': 'discuss',
                'e': 'explore',
                'st': 'set',
                'g': 'get',
                'k': 'kill',
                'h': 'help'
            }
            args.plan_subcommand = plan_subcommand_alias_map.get(args.plan_subcommand, args.plan_subcommand)
    elif args.command and hasattr(args, 'rules_subcommand') and args.rules_subcommand:
        if args.command == 'rules':
            rules_subcommand_alias_map = {
                'ls': 'list',
                'e': 'enable',
                'd': 'disable',
                'h': 'help'
            }
            args.rules_subcommand = rules_subcommand_alias_map.get(args.rules_subcommand, args.rules_subcommand)
    elif args.command and hasattr(args, 'task_subcommand') and args.task_subcommand:
        if args.command == 'task':
            task_subcommand_alias_map = {
                'ls': 'list',
                'l': 'list',
                'a': 'add',
                'rm': 'remove',
                'r': 'remove',
                'h': 'help'
            }
            args.task_subcommand = task_subcommand_alias_map.get(args.task_subcommand, args.task_subcommand)
    elif args.command and hasattr(args, 'log_subcommand') and args.log_subcommand:
        if args.command == 'log':
            log_subcommand_alias_map = {
                'ls': 'list',
                'lw': 'list-work',
                'lp': 'list-plan',
                'h': 'help'
            }
            args.log_subcommand = log_subcommand_alias_map.get(args.log_subcommand, args.log_subcommand)
    elif args.command and hasattr(args, 'root_subcommand') and args.root_subcommand:
        if args.command == 'root':
            root_subcommand_alias_map = {
                's': 'set',
                'g': 'get',
                'r': 'refine',
                'd': 'discuss',
                'sh': 'show',
                'h': 'help'
            }
            args.root_subcommand = root_subcommand_alias_map.get(args.root_subcommand, args.root_subcommand)
    elif args.command and hasattr(args, 'convert_subcommand') and args.convert_subcommand:
        if args.command == 'convert':
            # Track if 'new' was used (deprecated)
            if args.convert_subcommand == 'new':
                setattr(args, "_deprecated_convert_new_alias", True)

            convert_subcommand_alias_map = {
                'n': 'add',      # Map short alias to canonical 'add'
                'new': 'add',    # Map deprecated 'new' to canonical 'add'
                'p': 'plan',
                'r': 'run',
                's': 'status',
                'sh': 'show',
                'rst': 'reset',
                'b': 'batch',
                'h': 'help'
            }
            args.convert_subcommand = convert_subcommand_alias_map.get(args.convert_subcommand, args.convert_subcommand)
    elif args.command and hasattr(args, 'batch_subcommand') and args.batch_subcommand:
        if args.command == 'convert' and hasattr(args, 'convert_subcommand') and args.convert_subcommand == 'batch':
            batch_subcommand_alias_map = {
                'r': 'run',
                's': 'status',
                'sh': 'show',
                'rep': 'report',
                'h': 'help'
            }
            args.batch_subcommand = batch_subcommand_alias_map.get(args.batch_subcommand, args.batch_subcommand)
    elif args.command and hasattr(args, 'builder_subcommand') and args.builder_subcommand:
        if args.command == 'build':
            build_subcommand_alias_map = {
                'ru': 'run',
                'f': 'fix',
                'stat': 'status',
                'r': 'rules',
                'n': 'new',
                'ls': 'list',
                'se': 'set',
                'g': 'get',
                'p': 'plan',
                'sh': 'show',
                'str': 'structure',
                'h': 'help'
            }
            args.builder_subcommand = build_subcommand_alias_map.get(args.builder_subcommand, args.builder_subcommand)
    elif args.command and hasattr(args, 'fix_subcommand') and args.fix_subcommand:
        if args.command == 'build' and hasattr(args, 'builder_subcommand') and args.builder_subcommand == 'fix':
            fix_subcommand_alias_map = {
                'r': 'run',
                'a': 'add',
                'n': 'new',
                'ls': 'list',
                'rm': 'remove',
                'p': 'plan',
                'sh': 'show',
                'h': 'help'
            }
            args.fix_subcommand = fix_subcommand_alias_map.get(args.fix_subcommand, args.fix_subcommand)
    elif args.command and hasattr(args, 'structure_subcommand') and args.structure_subcommand:
        if args.command == 'build' and hasattr(args, 'builder_subcommand') and args.builder_subcommand == 'structure':
            structure_subcommand_alias_map = {
                'sc': 'scan',
                'sh': 'show',
                'f': 'fix',
                'a': 'apply',
                'l': 'lint',
                'h': 'help'
            }
            args.structure_subcommand = structure_subcommand_alias_map.get(args.structure_subcommand, args.structure_subcommand)

    return args
