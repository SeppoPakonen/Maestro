#!/usr/bin/env python3
"""
Maestro - AI Task Management CLI

This is the main entry point for the Maestro AI task orchestrator.
"""

# Import all the functionality from the modules
import asyncio
import os
import sys
from .modules.dataclasses import *
from .modules.utils import *
from .modules.cli_parser import *
from .modules.command_handlers import *
from maestro.structure_fix import (
    apply_fix_plan_operations,
    check_verification_improvement,
    create_git_backup,
    is_git_repo,
    report_revert_action,
    restore_from_git,
)
from maestro.structure_tools import (
    apply_structure_fix_rules,
    execute_structure_fix_action,
    fix_header_guards,
    get_fix_rulebooks_dir,
    get_registry_file_path,
    handle_structure_apply,
    handle_structure_fix,
    handle_structure_lint,
    handle_structure_scan,
    handle_structure_show,
    load_registry,
    load_rulebook,
    normalize_cpp_includes,
    reduce_secondary_header_includes,
    resolve_upp_dependencies,
    run_structure_fixes_from_rulebooks,
    save_rulebook,
    scan_upp_repo,
    ensure_main_header_content,
)

# Version information
__version__ = "1.2.1"

# Legacy re-exports for TUI facade imports
from maestro.repo import (  # noqa: E402
    scan_upp_repo_v2,
    AssemblyInfo,
    RepoScanResult,
    UnknownPath,
    InternalPackage,
)
from maestro.repo.package import PackageInfo  # noqa: E402
from maestro.commands.repo import load_repo_index, find_repo_root  # noqa: E402
from maestro.commands.convert import handle_convert_run, handle_convert_show  # noqa: E402
from maestro.convert.pipeline_runtime import (  # noqa: E402
    create_conversion_pipeline,
    load_conversion_pipeline,
    save_conversion_pipeline,
    run_overview_stage,
    run_core_builds_stage,
    run_grow_from_main_stage,
    run_full_tree_check_stage,
    run_refactor_stage,
    get_decisions,
    get_decision_by_id,
)
from maestro.data.track_cache import set_cache_validation


def init_maestro_dir(target_dir: str, verbose: bool = True) -> str:
    """Ensure a .maestro directory exists in the target path."""
    from pathlib import Path

    maestro_dir = Path(target_dir) / ".maestro"
    maestro_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Initialized Maestro directory at {maestro_dir}")

    return str(maestro_dir)


def _print_legacy_warning(command_name: str, replacement: str):
    """Print a prominent warning banner for deprecated commands.

    This warning is displayed when MAESTRO_ENABLE_LEGACY=1 and a user
    invokes a legacy command (session, understand, resume, rules, root).

    Args:
        command_name: The deprecated command name (e.g., 'session')
        replacement: The canonical replacement command (e.g., 'maestro wsession')
    """
    warning_text = f"""
╔════════════════════════════════════════════════════════════════╗
║  DEPRECATED COMMAND: maestro {command_name:<30}║
╠════════════════════════════════════════════════════════════════╣
║  This command is deprecated and will be removed in a future   ║
║  release. Please use the replacement command instead:         ║
║                                                                ║
║  → {replacement:<60}║
║                                                                ║
║  See: docs/workflows/v3/cli/DEPRECATION.md                    ║
╚════════════════════════════════════════════════════════════════╝
"""
    print(warning_text, file=sys.stderr)


def _has_help_flag(argv):
    return "-h" in argv or "--help" in argv


def _resolve_help_command(argv):
    if not argv:
        return None
    raw = argv[0]
    if raw.startswith("-"):
        return None
    alias_map = {
        "b": "make",
        "build": "make",
        "m": "make",
        "s": "session",
        "u": "understand",
        "r": "rules",
        "p": "phase",
        "t": "track",
        "l": "log",
        "c": "convert",
        "wk": "work",
        "ws": "wsession",
        "runba": "runbook",
        "rb": "runbook",
        "tut": "tutorial",
    }
    return alias_map.get(raw, raw)


def _legacy_enabled():
    value = os.environ.get("MAESTRO_ENABLE_LEGACY", "0").lower()
    return value in ("1", "true", "yes")


def _print_legacy_disabled(command_name: str, replacement: str) -> None:
    print(f"[DEPRECATED] '{command_name}' command is not available.", file=sys.stderr)
    print(f"Use: maestro {replacement} instead.", file=sys.stderr)
    print("", file=sys.stderr)
    print("To enable legacy commands (for backward compatibility):", file=sys.stderr)
    print("  export MAESTRO_ENABLE_LEGACY=1", file=sys.stderr)
    print("", file=sys.stderr)
    print("See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md", file=sys.stderr)


def main():
    """Main entry point for the Maestro CLI."""
    if os.environ.get("MAESTRO_DEBUG_HANG") == "1":
        import faulthandler

        faulthandler.dump_traceback_later(4, repeat=True, file=sys.stderr)

    argv = sys.argv[1:]
    if _has_help_flag(argv):
        raw_command = argv[0] if argv else None
        help_command = _resolve_help_command(argv)
        legacy_commands = {"session", "resume", "rules", "root", "understand"}
        include_legacy = None
        if help_command in legacy_commands:
            if not _legacy_enabled():
                legacy_map = {
                    "session": "wsession",
                    "understand": "repo resolve / runbook export",
                    "resume": "discuss resume / work resume",
                    "rules": "repo conventions / solutions",
                    "root": "track / phase / task",
                }
                replacement = legacy_map.get(help_command, "canonical commands")
                _print_legacy_disabled(help_command, replacement)
                sys.exit(1)
            include_legacy = True

        help_argv = list(argv)
        if raw_command in ("build", "b"):
            print(
                "Warning: 'maestro build' is deprecated; use 'maestro make' instead. "
                "This alias will be removed after two minor releases.",
                file=sys.stderr,
            )
            if help_argv:
                help_argv[0] = "make"
            help_command = "make"
        elif help_command in legacy_commands:
            legacy_map = {
                "session": "wsession",
                "understand": "repo resolve / runbook export",
                "resume": "discuss resume / work resume",
                "rules": "repo conventions / solutions",
                "root": "track / phase / task",
            }
            replacement = legacy_map.get(help_command, "canonical commands")
            print(f"Warning: '{help_command}' is deprecated; use '{replacement}' instead.", file=sys.stderr)

        commands_to_load = [help_command] if help_command else None
        parser = create_main_parser(
            commands_to_load=commands_to_load,
            include_legacy=include_legacy,
            show_banner=False,
        )
        parser.parse_args(help_argv)
        return

    # Create the main parser
    parser = create_main_parser()

    # Parse arguments
    raw_command = sys.argv[1] if len(sys.argv) > 1 else None
    raw_command_orig = raw_command
    enable_legacy = os.environ.get('MAESTRO_ENABLE_LEGACY', '0').lower() in ('1', 'true', 'yes')
    legacy_aliases = {'s': 'session', 'u': 'understand'}
    legacy_command = legacy_aliases.get(raw_command, raw_command)
    if legacy_command in ('session', 'understand', 'resume', 'rules', 'root'):
        if not enable_legacy:
            legacy_map = {
                'session': 'wsession',
                'understand': 'repo resolve / runbook export',
                'resume': 'discuss resume / work resume',
                'rules': 'repo conventions / solutions',
                'root': 'track / phase / task'
            }
            replacement = legacy_map.get(legacy_command, 'canonical commands')
            print(f"[DEPRECATED] '{legacy_command}' command is not available.", file=sys.stderr)
            print(f"Use: maestro {replacement} instead.", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"To enable legacy commands (for backward compatibility):", file=sys.stderr)
            print(f"  export MAESTRO_ENABLE_LEGACY=1", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md", file=sys.stderr)
            sys.exit(1)
        if legacy_command == 'session' and raw_command in ('session', 's'):
            print("Warning: 'session' is deprecated; use 'wsession' instead.")
            sys.argv[1] = 'wsession'

    args = parser.parse_args()

    set_cache_validation(getattr(args, 'validate_cache', False))

    # Handle help command first
    if args.command == 'help' or (hasattr(args, 'help') and args.help):
        parser.print_help()
        return

    # Normalize command aliases to main command names
    args = normalize_command_aliases(args)
    if raw_command_orig in ("build", "b"):
        setattr(args, "_deprecated_build_alias", True)

    # Check if user tried to invoke a disabled legacy command
    # Legacy commands (session, understand, resume, rules, root) require MAESTRO_ENABLE_LEGACY=1
    enable_legacy = os.environ.get('MAESTRO_ENABLE_LEGACY', '0').lower() in ('1', 'true', 'yes')
    if not enable_legacy and hasattr(args, 'command') and args.command in ('session', 'understand', 'resume', 'rules', 'root'):
        legacy_map = {
            'session': 'wsession',
            'understand': 'repo resolve / runbook export',
            'resume': 'discuss resume / work resume',
            'rules': 'repo conventions / solutions',
            'root': 'track / phase / task'
        }
        replacement = legacy_map.get(args.command, 'canonical commands')
        print(f"Error: '{args.command}' command is not available.", file=sys.stderr)
        print(f"Use: maestro {replacement} instead.", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"To enable legacy commands (for backward compatibility):", file=sys.stderr)
        print(f"  export MAESTRO_ENABLE_LEGACY=1", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md", file=sys.stderr)
        sys.exit(1)

    # Import command handlers from the commands module
    from maestro.commands import (
        handle_init_command,
        handle_repo_command,
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
        handle_runbook_command,
        handle_workflow_command,
        handle_make_command,
    )
    from maestro.commands.cache import handle_cache_command
    from maestro.commands.track_cache import handle_track_cache_command
    from maestro.commands.convert import (
        handle_convert_new,
        handle_convert_plan,
        handle_convert_run,
        handle_convert_status,
        handle_convert_show,
        handle_convert_reset,
        handle_convert_batch,
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
        handle_work_subwork_start,
        handle_work_subwork_list,
        handle_work_subwork_show,
        handle_work_subwork_close,
        handle_work_subwork_resume_parent,
    )
    from maestro.commands.work_session import (
        handle_wsession_list,
        handle_wsession_show,
        handle_wsession_tree,
        handle_wsession_breadcrumbs,
        handle_wsession_breadcrumb_add,
        handle_wsession_timeline,
        handle_wsession_stats,
        handle_wsession_close,
    )

    # Handle different commands based on the parsed arguments
    if args.command == 'init':
        handle_init_command(args)

    elif args.command == 'runbook':
        handle_runbook_command(args)

    elif args.command == 'workflow':
        handle_workflow_command(args)

    elif args.command == 'repo':
        handle_repo_command(args)

    elif args.command == 'make':
        if getattr(args, "_deprecated_build_alias", False):
            print("Warning: 'maestro build' is deprecated; use 'maestro make' instead. "
                  "This alias will be removed after two minor releases.")
            if not getattr(args, "make_subcommand", None):
                args.make_subcommand = "build"
        handle_make_command(args)

    elif args.command == 'track':
        handle_track_command(args)

    elif args.command == 'phase':
        handle_phase_command(args)

    elif args.command == 'task':  # New task command from commands module (different from core task)
        handle_task_command(args)

    elif args.command == 'discuss':
        sys.exit(handle_discuss_command(args))

    elif args.command == 'settings':
        handle_settings_command(args)

    elif args.command == 'issues':
        handle_issues_command(args)

    elif args.command == 'solutions':
        handle_solutions_command(args)

    elif args.command == 'session':
        _print_legacy_warning('session', 'maestro wsession')
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
                    sys.exit(1)
            elif args.plan_subcommand == 'list':
                handle_plan_list(args.session, args.verbose)
            elif args.plan_subcommand == 'remove':
                # Check if the 'title_or_number' argument was provided
                if hasattr(args, 'title_or_number') and args.title_or_number:
                    handle_plan_remove(args.title_or_number, args.session, args.verbose)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.plan_subcommand == 'show':
                # Check if the 'title_or_number' argument was provided
                if hasattr(args, 'title_or_number') and args.title_or_number:
                    handle_plan_show(args.title_or_number, args.session, args.verbose)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.plan_subcommand == 'add-item':
                # Check if both required arguments were provided
                if (hasattr(args, 'title_or_number') and args.title_or_number and
                    hasattr(args, 'item_text') and args.item_text):
                    handle_plan_add_item(args.title_or_number, args.item_text, args.session, args.verbose)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.plan_subcommand == 'remove-item':
                # Check if both required arguments were provided
                if (hasattr(args, 'title_or_number') and args.title_or_number and
                    hasattr(args, 'item_number') and args.item_number):
                    handle_plan_remove_item(args.title_or_number, args.item_number, args.session, args.verbose)
                else:
                    parser.print_help()
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
            elif args.plan_subcommand == 'decompose':
                # Handle plan decompose command
                from .commands.plan import handle_plan_decompose
                handle_plan_decompose(args)
            elif args.plan_subcommand == 'enact':
                # Handle plan enact command
                from .commands.plan import handle_plan_enact
                handle_plan_enact(args)
            elif args.plan_subcommand == 'run':
                # Handle plan run command
                from .commands.plan import handle_plan_run
                handle_plan_run(args)
            elif args.plan_subcommand == 'score':
                # Handle plan score command
                from .commands.plan import handle_plan_score
                handle_plan_score(args)
            elif args.plan_subcommand == 'recommend':
                # Handle plan recommend command
                from .commands.plan import handle_plan_recommend
                handle_plan_recommend(args)
            elif args.plan_subcommand == 'sprint':
                # Handle plan sprint command
                from .commands.plan import handle_plan_sprint
                handle_plan_sprint(args)
            elif args.plan_subcommand == 'postmortem':
                # Handle plan postmortem command
                from .commands.plan import handle_plan_postmortem
                handle_plan_postmortem(args)
        else:
            # No subcommand provided - show help
            if hasattr(args, "func") and callable(args.func):
                args.func(args)
            else:
                parser.print_help()
            sys.exit(0)

    elif args.command == 'rules':
        _print_legacy_warning('rules', 'maestro repo conventions / maestro solutions')
        if args.rules_subcommand == 'list':
            handle_rules_list(args.session, args.verbose)
        elif args.rules_subcommand == 'edit':
            handle_rules_file(args.session, args.verbose)
        else:
            handle_rules_file(args.session, args.verbose)

    elif args.command == 'root':
        _print_legacy_warning('root', 'maestro track / maestro phase / maestro task')
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
        from maestro.commands.log import handle_log_command
        exit_code = handle_log_command(args)
        if exit_code:
            raise SystemExit(exit_code)

    elif args.command == 'cache':
        exit_code = handle_cache_command(args)
        if exit_code:
            raise SystemExit(exit_code)

    elif args.command == 'track-cache':
        exit_code = handle_track_cache_command(args)
        if exit_code:
            raise SystemExit(exit_code)

    elif args.command == 'ops':
        from maestro.commands.ops import handle_ops_command
        exit_code = handle_ops_command(args)
        if exit_code:
            raise SystemExit(exit_code)

    elif args.command == 'ux':
        from maestro.commands.ux import handle_ux_command
        exit_code = handle_ux_command(args)
        if exit_code:
            raise SystemExit(exit_code)

    elif args.command == 'resume':
        _print_legacy_warning('resume', 'maestro discuss resume / maestro work resume')
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
        elif work_subcommand == 'subwork':
            subcommand = getattr(args, 'subwork_subcommand', None)
            if subcommand == 'start':
                exit_code = handle_work_subwork_start(args)
            elif subcommand == 'list':
                exit_code = handle_work_subwork_list(args)
            elif subcommand == 'show':
                exit_code = handle_work_subwork_show(args)
            elif subcommand == 'close':
                exit_code = handle_work_subwork_close(args)
            elif subcommand == 'resume-parent':
                exit_code = handle_work_subwork_resume_parent(args)
            else:
                parser.print_help()
                return
            if exit_code:
                raise SystemExit(exit_code)
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
        elif args.wsession_subcommand == 'breadcrumb':
            if args.breadcrumb_subcommand == 'add':
                handle_wsession_breadcrumb_add(args)
            else:
                parser.print_help()
        elif args.wsession_subcommand == 'timeline':
            handle_wsession_timeline(args)
        elif args.wsession_subcommand == 'stats':
            handle_wsession_stats(args)
        elif args.wsession_subcommand == 'close':
            handle_wsession_close(args)
        else:
            parser.print_help()

    elif args.command == 'understand':
        _print_legacy_warning('understand', 'maestro repo resolve / maestro runbook export')
        if args.understand_subcommand == 'dump':
            handle_understand_dump(
                output_path=args.output_path,
                check=args.check
            )
        else:
            parser.print_help()

    elif args.command == 'tu':
        from .commands.tu import handle_tu_command
        handle_tu_command(args)

    elif args.command == 'convert':
        # Handle different convert subcommands based on the parsed arguments
        if hasattr(args, 'convert_subcommand') and args.convert_subcommand:
            if args.convert_subcommand == 'add':
                # Emit deprecation warning if 'new' was used
                if getattr(args, "_deprecated_convert_new_alias", False):
                    print("Warning: 'maestro convert new' is deprecated; use 'maestro convert add' instead.")

                if hasattr(args, 'pipeline_name') and args.pipeline_name:
                    exit_code = handle_convert_new(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'plan':
                if getattr(args, "action_or_pipeline", None):
                    exit_code = handle_convert_plan(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'run':
                if hasattr(args, 'pipeline_id') and args.pipeline_id:
                    exit_code = handle_convert_run(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'status':
                if hasattr(args, 'pipeline_id') and args.pipeline_id:
                    exit_code = handle_convert_status(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'show':
                if hasattr(args, 'pipeline_id') and args.pipeline_id:
                    exit_code = handle_convert_show(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'reset':
                if hasattr(args, 'pipeline_id') and args.pipeline_id:
                    exit_code = handle_convert_reset(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            elif args.convert_subcommand == 'batch':
                # Handle batch subcommands
                if hasattr(args, 'batch_subcommand') and args.batch_subcommand:
                    exit_code = handle_convert_batch(args)
                    if exit_code:
                        raise SystemExit(exit_code)
                else:
                    parser.print_help()
                    sys.exit(1)
            else:
                parser.print_help()
                sys.exit(1)
        else:
            # No subcommand provided - show help
            parser.print_help()
            sys.exit(0)

    elif args.command == 'tutorial':
        from maestro.commands.tutorial import handle_tutorial_command
        handle_tutorial_command(args)

    else:
        # If no command is provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()
