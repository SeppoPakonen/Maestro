#!/usr/bin/env python3
"""
Maestro - AI Task Management CLI

This is the main entry point for the Maestro AI task orchestrator.
"""

# Import all the functionality from the modules
from .modules.dataclasses import *
from .modules.utils import *
from .modules.cli_parser import *
from .modules.command_handlers import *

# Version information
__version__ = "1.2.1"

def main():
    """Main entry point for the Maestro CLI."""
    # Create the main parser
    parser = create_main_parser()

    # Parse arguments
    args = parser.parse_args()

    # Handle help command first
    if args.command == 'help' or (hasattr(args, 'help') and args.help):
        parser.print_help()
        return

    # Normalize command aliases to main command names
    args = normalize_command_aliases(args)

    # Import command handlers from the commands module
    from maestro.commands import (
        handle_track_command,
        handle_phase_command,
        handle_task_command,
        handle_discuss_command,
        handle_settings_command,
        handle_issues_command,
        handle_solutions_command,
    )

    # Handle different commands based on the parsed arguments
    if args.command == 'track':
        handle_track_command(args)

    elif args.command == 'phase':
        handle_phase_command(args)

    elif args.command == 'task':  # New task command from commands module (different from core task)
        handle_task_command(args)

    elif args.command == 'discuss':
        handle_discuss_command(args)

    elif args.command == 'settings':
        handle_settings_command(args)

    elif args.command == 'issues':
        handle_issues_command(args)

    elif args.command == 'solutions':
        handle_solutions_command(args)

    elif args.command == 'session':
        if args.session_subcommand == 'new':
            handle_session_new(args.name, args.verbose, args.root_task)
        elif args.session_subcommand == 'list':
            handle_session_list(args.verbose)
        elif args.session_subcommand == 'set':
            handle_session_set(args.name, args.number, args.verbose)
        elif args.session_subcommand == 'get':
            handle_session_get(args.verbose)
        elif args.session_subcommand == 'remove':
            handle_session_remove(args.name, args.skip_confirmation, args.verbose)
        elif args.session_subcommand == 'details':
            handle_session_details(args.name, args.list_number, args.verbose)
        else:
            parser.print_help()

    elif args.command == 'plan':
        if args.plan_subcommand == 'list':
            handle_plan_list(args.session, args.verbose)
        elif args.plan_subcommand == 'show':
            handle_plan_show(args.session, args.plan_id, args.verbose)
        elif args.plan_subcommand == 'discuss':
            handle_interactive_plan_session(
                args.session,
                args.verbose,
                args.stream_ai_output,
                args.print_ai_prompts,
                args.planner_order
            )
        elif args.plan_subcommand == 'tree':
            handle_show_plan_tree(args.session, args.verbose)
        elif args.plan_subcommand == 'set':
            handle_focus_plan(args.session, args.plan_id, args.verbose)
        elif args.plan_subcommand == 'get':
            handle_plan_get(args.session, args.verbose)
        elif args.plan_subcommand == 'kill':
            handle_kill_plan(args.session, args.plan_id, args.verbose)
        else:
            # Default to discuss mode if no subcommand specified
            handle_interactive_plan_session(
                args.session,
                args.verbose,
                args.stream_ai_output,
                args.print_ai_prompts,
                args.planner_order
            )

    elif args.command == 'rules':
        if args.rules_subcommand == 'list':
            handle_rules_list(args.session, args.verbose)
        elif args.rules_subcommand == 'edit':
            handle_rules_file(args.session, args.verbose)
        else:
            handle_rules_file(args.session, args.verbose)

    elif args.command == 'root':
        if args.root_subcommand == 'set':
            handle_root_set(args.session, args.text, args.verbose)
        elif args.root_subcommand == 'get':
            handle_root_get(args.session, args.clean, args.verbose)
        elif args.root_subcommand == 'refine':
            handle_root_refine(args.session, args.verbose, args.planner_order)
        elif args.root_subcommand == 'discuss':
            handle_root_discuss(
                args.session,
                args.verbose,
                args.stream_ai_output,
                args.print_ai_prompts,
                args.planner_order
            )
        elif args.root_subcommand == 'show':
            handle_root_show(args.session, args.verbose)
        else:
            parser.print_help()

    elif args.command == 'log':
        if args.log_subcommand == 'list':
            handle_log_list(args.session, args.verbose)
        elif args.log_subcommand == 'list-work':
            handle_log_list_work(args.session, args.verbose)
        elif args.log_subcommand == 'list-plan':
            handle_log_list_plan(args.session, args.verbose)
        else:
            parser.print_help()

    elif args.command == 'resume':
        handle_resume_session(
            args.session,
            args.verbose,
            args.dry_run,
            args.stream_ai_output,
            args.print_ai_prompts,
            args.retry_interrupted
        )

    elif args.command == 'work':
        handle_task_run(
            args.session,
            args.num_tasks,
            args.verbose,
            args.quiet,
            args.retry_interrupted,
            args.stream_ai_output,
            args.print_ai_prompts
        )

    else:
        # If no command is provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()