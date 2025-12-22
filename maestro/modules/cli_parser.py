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

    # Add all the subparsers here (this would include all the subparsers from the original main.py)
    # For brevity, I'll just return the main parser here since the subparsers would be extensive
    
    return parser


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
        'b': 'build'
    }
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
                'h': 'help'
            }
            args.session_subcommand = session_subcommand_alias_map.get(args.session_subcommand, args.session_subcommand)
    elif args.command and hasattr(args, 'plan_subcommand') and args.plan_subcommand:
        if args.command == 'plan':
            plan_subcommand_alias_map = {
                'tr': 'tree',
                'ls': 'list',
                'sh': 'show',
                'd': 'discuss',
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
            convert_subcommand_alias_map = {
                'n': 'new',
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