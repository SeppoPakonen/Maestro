#!/usr/bin/env python3
"""
Maestro - AI Task Management CLI

This is the main entry point for the Maestro AI task orchestrator.
"""

# Import all the functionality from the modules
import asyncio
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
        handle_init_command,
        handle_plan_add,
        handle_plan_list,
        handle_plan_remove,
        handle_plan_show,
        handle_plan_add_item,
        handle_plan_remove_item,
        handle_track_command,
        handle_phase_command,
        handle_task_command,
        handle_discuss_command,
        handle_settings_command,
        handle_issues_command,
        handle_solutions_command,
        handle_understand_dump,
    )
    from maestro.commands.ai import handle_ai_qwen, handle_ai_sync, handle_ai_gemini, handle_ai_codex, handle_ai_claude
    from maestro.commands.work import (
        handle_work_any,
        handle_work_any_pick,
        handle_work_track,
        handle_work_phase,
        handle_work_issue,
        handle_work_task,
        handle_work_discuss,
        handle_work_analyze,
        handle_work_fix,
    )
    from maestro.commands.work_session import (
        handle_wsession_list,
        handle_wsession_show,
        handle_wsession_tree,
        handle_wsession_breadcrumbs,
        handle_wsession_timeline,
        handle_wsession_stats,
    )

    # Handle different commands based on the parsed arguments
    if args.command == 'init':
        handle_init_command(args)

    elif args.command == 'track':
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
        elif args.session_subcommand == 'breadcrumbs':
            handle_wsession_breadcrumbs(args)
        elif args.session_subcommand == 'timeline':
            handle_wsession_timeline(args)
        elif args.session_subcommand == 'stats':
            handle_wsession_stats(args)
        else:
            parser.print_help()

    elif args.command == 'plan':
        # Check if a subcommand was explicitly provided
        if hasattr(args, 'plan_subcommand') and args.plan_subcommand:
            if args.plan_subcommand == 'add':
                # Check if the 'title' argument was provided for add command
                if hasattr(args, 'title') and args.title:
                    handle_plan_add(args.title, args.session, args.verbose)
                else:
                    # Missing required 'title' argument for add command
                    parser.print_help()
                    import sys
                    sys.exit(1)
            elif args.plan_subcommand == 'list':
                handle_plan_list(args.session, args.verbose)
            elif args.plan_subcommand == 'remove':
                # Check if the 'title_or_number' argument was provided
                if hasattr(args, 'title_or_number') and args.title_or_number:
                    handle_plan_remove(args.title_or_number, args.session, args.verbose)
                else:
                    parser.print_help()
                    import sys
                    sys.exit(1)
            elif args.plan_subcommand == 'show':
                # Check if the 'title_or_number' argument was provided
                if hasattr(args, 'title_or_number') and args.title_or_number:
                    handle_plan_show(args.title_or_number, args.session, args.verbose)
                else:
                    parser.print_help()
                    import sys
                    sys.exit(1)
            elif args.plan_subcommand == 'add-item':
                # Check if both required arguments were provided
                if (hasattr(args, 'title_or_number') and args.title_or_number and
                    hasattr(args, 'item_text') and args.item_text):
                    handle_plan_add_item(args.title_or_number, args.item_text, args.session, args.verbose)
                else:
                    parser.print_help()
                    import sys
                    sys.exit(1)
            elif args.plan_subcommand == 'remove-item':
                # Check if both required arguments were provided
                if (hasattr(args, 'title_or_number') and args.title_or_number and
                    hasattr(args, 'item_number') and args.item_number):
                    handle_plan_remove_item(args.title_or_number, args.item_number, args.session, args.verbose)
                else:
                    parser.print_help()
                    import sys
                    sys.exit(1)
            elif args.plan_subcommand == 'ops':
                # Handle plan ops subcommands
                if hasattr(args, 'ops_subcommand') and args.ops_subcommand:
                    from maestro.plan_ops.commands import handle_plan_ops_validate, handle_plan_ops_preview, handle_plan_ops_apply
                    if args.ops_subcommand == 'validate':
                        handle_plan_ops_validate(args.json_file, args.session, args.verbose)
                    elif args.ops_subcommand == 'preview':
                        handle_plan_ops_preview(args.json_file, args.session, args.verbose)
                    elif args.ops_subcommand == 'apply':
                        handle_plan_ops_apply(args.json_file, args.session, args.verbose)
            elif args.plan_subcommand == 'discuss':
                # Handle plan discuss command
                from .commands.plan import handle_plan_discuss
                handle_plan_discuss(args.title_or_number, args.session, args.verbose, prompt=getattr(args, 'prompt', None))
            elif args.plan_subcommand == 'explore':
                # Handle plan explore command
                from .commands.plan import handle_plan_explore
                handle_plan_explore(
                    args.title_or_number,
                    args.session,
                    args.verbose,
                    dry_run=args.dry_run,
                    apply=args.apply,
                    max_iterations=args.max_iterations,
                    engine=args.engine,
                    save_session=getattr(args, 'save_session', False),
                    auto_apply=getattr(args, 'auto_apply', False),
                    stop_after_apply=getattr(args, 'stop_after_apply', False)
                )
        else:
            # No subcommand provided - show help
            parser.print_help()
            import sys
            sys.exit(0)

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

    elif args.command == 'ops':
        if hasattr(args, 'ops_subcommand') and args.ops_subcommand:
            from maestro.project_ops.commands import handle_project_ops_validate, handle_project_ops_preview, handle_project_ops_apply
            if args.ops_subcommand == 'validate':
                handle_project_ops_validate(args.json_file, args.session, args.verbose)
            elif args.ops_subcommand == 'preview':
                handle_project_ops_preview(args.json_file, args.session, args.verbose)
            elif args.ops_subcommand == 'apply':
                handle_project_ops_apply(args.json_file, args.session, args.verbose)

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
        work_subcommand = getattr(args, 'work_subcommand', None)
        if work_subcommand is None:
            asyncio.run(handle_work_any(args))
        elif work_subcommand == 'any':
            if getattr(args, 'any_subcommand', None) == 'pick':
                asyncio.run(handle_work_any_pick(args))
            else:
                asyncio.run(handle_work_any(args))
        elif work_subcommand == 'track':
            asyncio.run(handle_work_track(args))
        elif work_subcommand == 'phase':
            asyncio.run(handle_work_phase(args))
        elif work_subcommand == 'issue':
            asyncio.run(handle_work_issue(args))
        elif work_subcommand == 'task':
            asyncio.run(handle_work_task(args))
        elif work_subcommand == 'discuss':
            handle_work_discuss(args)
        elif work_subcommand == 'analyze':
            asyncio.run(handle_work_analyze(args))
        elif work_subcommand == 'fix':
            asyncio.run(handle_work_fix(args))
        else:
            parser.print_help()

    elif args.command == 'ai':
        if args.ai_subcommand == 'sync':
            exit_code = handle_ai_sync(args)
            if exit_code:
                raise SystemExit(exit_code)
        elif args.ai_subcommand == 'qwen':
            exit_code = handle_ai_qwen(args)
            if exit_code:
                raise SystemExit(exit_code)
        elif args.ai_subcommand == 'gemini':
            exit_code = handle_ai_gemini(args)
            if exit_code:
                raise SystemExit(exit_code)
        elif args.ai_subcommand == 'codex':
            exit_code = handle_ai_codex(args)
            if exit_code:
                raise SystemExit(exit_code)
        elif args.ai_subcommand == 'claude':
            exit_code = handle_ai_claude(args)
            if exit_code:
                raise SystemExit(exit_code)
        else:
            parser.print_help()

    elif args.command == 'wsession':
        if args.wsession_subcommand == 'list':
            handle_wsession_list(args)
        elif args.wsession_subcommand == 'show':
            handle_wsession_show(args)
        elif args.wsession_subcommand == 'tree':
            handle_wsession_tree(args)
        elif args.wsession_subcommand == 'breadcrumbs':
            handle_wsession_breadcrumbs(args)
        elif args.wsession_subcommand == 'timeline':
            handle_wsession_timeline(args)
        elif args.wsession_subcommand == 'stats':
            handle_wsession_stats(args)
        else:
            parser.print_help()

    elif args.command == 'understand':
        if args.understand_subcommand == 'dump':
            handle_understand_dump(
                output_path=args.output_path,
                check=args.check
            )
        else:
            parser.print_help()

    else:
        # If no command is provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()
