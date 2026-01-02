"""
UX evaluation command handlers.

Provides blindfold UX evaluation tools for Maestro CLI.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def add_ux_parser(subparsers) -> argparse.ArgumentParser:
    """Add UX command parser."""
    ux_parser = subparsers.add_parser(
        'ux',
        help='UX evaluation and telemetry tools'
    )
    ux_subparsers = ux_parser.add_subparsers(
        dest='ux_subcommand',
        help='UX subcommands'
    )

    # ux eval
    eval_parser = ux_subparsers.add_parser(
        'eval',
        help='Run blindfold UX evaluation for a goal'
    )
    eval_parser.add_argument(
        'goal',
        help='Goal string to evaluate (e.g., "Create an actionable runbook")'
    )
    eval_parser.add_argument(
        '--repo',
        help='Repository root path (default: current directory)'
    )
    eval_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute commands (default: dry-run preview only)'
    )
    eval_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show decision summary and discovered commands count'
    )
    eval_parser.add_argument(
        '-vv', '--very-verbose',
        dest='very_verbose',
        action='store_true',
        help='Additionally show bounded help excerpts and reasoning trace'
    )
    eval_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )
    eval_parser.add_argument(
        '--out',
        help='Output directory for report (default: docs/maestro/ux_eval/<eval_id>)'
    )

    # ux postmortem
    postmortem_parser = ux_subparsers.add_parser(
        'postmortem',
        help='Turn UX eval findings into issues and WorkGraph'
    )
    postmortem_parser.add_argument(
        'eval_id',
        help='UX eval ID to process (e.g., ux_eval_20260102_143052)'
    )
    postmortem_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually run pipeline (default: preview only)'
    )
    postmortem_parser.add_argument(
        '--issues',
        action='store_true',
        help='Create issues from findings (requires --execute)'
    )
    postmortem_parser.add_argument(
        '--decompose',
        action='store_true',
        help='Create WorkGraph for fixes (requires --execute and --issues)'
    )
    postmortem_parser.add_argument(
        '--profile',
        choices=['investor', 'purpose', 'default'],
        default='default',
        help='WorkGraph profile for decompose (default: default)'
    )
    postmortem_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    postmortem_parser.add_argument(
        '-vv', '--very-verbose',
        dest='very_verbose',
        action='store_true',
        help='Show all pipeline commands and outputs'
    )
    postmortem_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )

    # ux list
    list_parser = ux_subparsers.add_parser(
        'list',
        help='List all UX evaluation runs'
    )
    list_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    # ux show
    show_parser = ux_subparsers.add_parser(
        'show',
        help='Show UX evaluation summary'
    )
    show_parser.add_argument(
        'eval_id',
        help='UX eval ID to show'
    )
    show_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    return ux_parser


def handle_ux_command(args: argparse.Namespace) -> int:
    """Handle UX commands."""
    subcommand = getattr(args, 'ux_subcommand', None)

    if subcommand == 'eval':
        return handle_ux_eval(args)
    elif subcommand == 'postmortem':
        return handle_ux_postmortem(args)
    elif subcommand == 'list':
        return handle_ux_list(args)
    elif subcommand == 'show':
        return handle_ux_show(args)
    else:
        print(f"Unknown ux subcommand: {subcommand}")
        print("Available: eval, postmortem, list, show")
        return 1


def handle_ux_eval(args: argparse.Namespace) -> int:
    """
    Handle UX eval command.

    Runs blindfold UX evaluation:
    1. Discover CLI surface via help text
    2. Generate attempt plan from goal
    3. Execute attempts (or dry-run)
    4. Generate UX report with improvements
    """
    from ..config.paths import get_docs_root
    from ..ux.help_surface import HelpSurface, DiscoveryBudget
    from ..ux.evaluator import GoalEvaluator
    from ..ux.telemetry import TelemetryRecorder
    from ..ux.report import UXReportGenerator

    # Verbose flags
    verbose = getattr(args, 'verbose', False)
    very_verbose = getattr(args, 'very_verbose', False)
    if very_verbose:
        verbose = True

    # Get MAESTRO_BIN path
    maestro_bin = os.environ.get('MAESTRO_BIN')
    if not maestro_bin:
        # Try to infer from current script
        maestro_bin = sys.argv[0]
        if verbose:
            print(f"MAESTRO_BIN not set, using: {maestro_bin}")

    # Repo root
    repo_root = Path(args.repo) if args.repo else Path.cwd()
    if verbose:
        print(f"Repo root: {repo_root}")

    # Generate eval ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    eval_id = f"ux_eval_{timestamp}"

    # Output directory (new storage contract: docs/maestro/ux_eval/<EVAL_ID>/)
    if args.out:
        output_dir = Path(args.out)
    else:
        docs_root = get_docs_root()
        output_dir = docs_root / "docs" / "maestro" / "ux_eval" / eval_id

    if verbose:
        print(f"Output directory: {output_dir}")
        print()

    # Step 1: Discover help surface
    if verbose:
        print("Step 1: Discovering CLI surface via help text...")

    budget = DiscoveryBudget()
    help_surface = HelpSurface(
        maestro_bin=maestro_bin,
        budget=budget,
        verbose=very_verbose  # Show help discovery details only in -vv mode
    )

    try:
        discovered_surface = help_surface.discover()
    except Exception as e:
        print(f"Error discovering help surface: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Save surface
    try:
        help_surface.save_surface(output_dir)
    except Exception as e:
        print(f"Error saving help surface: {e}", file=sys.stderr)
        return 1

    if verbose:
        print(f"Discovered {len(discovered_surface)} commands")
        print(f"Help calls: {help_surface.help_call_count}")
        if help_surface.warnings:
            print(f"Warnings: {len(help_surface.warnings)}")
            if very_verbose:
                for warning in help_surface.warnings[:5]:
                    print(f"  - {warning}")
        print()

    # Step 2: Generate attempt plan from goal
    if verbose:
        print("Step 2: Generating attempt plan from goal...")

    evaluator = GoalEvaluator(
        help_surface=discovered_surface,
        verbose=very_verbose
    )

    try:
        attempt_plan = evaluator.generate_attempt_plan(goal=args.goal)
    except Exception as e:
        print(f"Error generating attempt plan: {e}", file=sys.stderr)
        return 1

    if verbose:
        print(f"Generated {len(attempt_plan.attempts)} candidate attempts")
        if very_verbose and attempt_plan.reasoning:
            print("Reasoning:")
            print(attempt_plan.reasoning)
        print()

    # Step 3: Execute attempts (or dry-run)
    dry_run = not args.execute

    if verbose:
        mode = "DRY RUN" if dry_run else "EXECUTE"
        print(f"Step 3: Running attempts ({mode})...")

    telemetry = TelemetryRecorder(
        eval_id=eval_id,
        goal=args.goal,
        output_dir=output_dir,
        verbose=verbose
    )

    # Record help call count from discovery
    telemetry.increment_help_calls(help_surface.help_call_count)

    # Execute each attempt
    for attempt_cmd_path in attempt_plan.attempts[:10]:  # Limit to 10 attempts
        # Convert command path to argv
        # Replace 'maestro' with actual bin path
        command_argv = [maestro_bin] + attempt_cmd_path[1:]

        try:
            telemetry.record_attempt(
                command_argv=command_argv,
                timeout=30.0,
                dry_run=dry_run
            )
        except Exception as e:
            if verbose:
                print(f"  Error recording attempt: {e}")

    # Save telemetry
    try:
        telemetry.save_telemetry()
    except Exception as e:
        print(f"Error saving telemetry: {e}", file=sys.stderr)
        return 1

    if verbose:
        print()
        print(f"Telemetry saved: {output_dir}/telemetry.json")
        print()

    # Step 4: Generate UX report
    if verbose:
        print("Step 4: Generating UX report...")

    report_generator = UXReportGenerator(
        eval_id=eval_id,
        goal=args.goal,
        help_surface=discovered_surface,
        attempts=telemetry.attempts,
        telemetry_summary=telemetry.get_summary(),
        verbose=verbose
    )

    report_path = output_dir / f"{eval_id}.md"

    try:
        report_generator.generate_report(report_path)
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        return 1

    # Output results
    if args.json:
        # JSON mode: print machine-readable summary
        summary = {
            'eval_id': eval_id,
            'goal': args.goal,
            'output_dir': str(output_dir),
            'report_path': str(report_path),
            'discovered_commands': len(discovered_surface),
            'help_calls': help_surface.help_call_count,
            'total_attempts': len(telemetry.attempts),
            'successful_attempts': telemetry.get_summary()['successful_attempts'],
            'failed_attempts': telemetry.get_summary()['failed_attempts'],
            'dry_run': dry_run
        }
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable mode
        print()
        print("="*60)
        print(f"UX EVALUATION COMPLETE: {eval_id}")
        print("="*60)
        print()
        print(f"Goal: {args.goal}")
        print()
        print(f"Discovered Commands: {len(discovered_surface)}")
        print(f"Help Calls: {help_surface.help_call_count}")
        print(f"Total Attempts: {len(telemetry.attempts)}")
        print(f"Successful Attempts: {telemetry.get_summary()['successful_attempts']}")
        print(f"Failed Attempts: {telemetry.get_summary()['failed_attempts']}")
        print()
        print(f"Mode: {'DRY RUN (no commands executed)' if dry_run else 'EXECUTE'}")
        print()
        print(f"Report: {report_path}")
        print(f"Telemetry: {output_dir}/telemetry.json")
        print(f"Surface: {output_dir}/surface.json")
        print()

        if not args.execute:
            print("To execute commands, run with --execute flag.")
            print()

    return 0


def handle_ux_postmortem(args: argparse.Namespace) -> int:
    """
    Handle UX postmortem command.

    Converts UX eval findings into issues and optionally a WorkGraph:
    1. Load UX eval artifacts (telemetry, attempts, surface, report)
    2. Build synthetic log from attempts
    3. Run log scan on synthetic log
    4. Create issues from scan findings
    5. Optionally decompose into WorkGraph
    """
    from ..config.paths import get_docs_root
    from ..ux.postmortem import UXPostmortem

    verbose = getattr(args, 'verbose', False)
    very_verbose = getattr(args, 'very_verbose', False)
    if very_verbose:
        verbose = True

    # Get eval directory
    docs_root = get_docs_root()
    eval_dir = docs_root / "docs" / "maestro" / "ux_eval" / args.eval_id

    if not eval_dir.exists():
        print(f"Error: UX eval not found: {args.eval_id}", file=sys.stderr)
        print(f"Expected path: {eval_dir}", file=sys.stderr)
        return 1

    # Create postmortem runner
    postmortem = UXPostmortem(
        eval_id=args.eval_id,
        eval_dir=eval_dir,
        verbose=verbose,
        very_verbose=very_verbose
    )

    # Run postmortem
    try:
        result = postmortem.run(
            execute=args.execute,
            create_issues=args.issues,
            decompose=args.decompose,
            profile=args.profile
        )
    except Exception as e:
        print(f"Error running postmortem: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output handled by UXPostmortem
        pass

    return 0


def handle_ux_list(args: argparse.Namespace) -> int:
    """
    Handle UX list command.

    Lists all UX eval runs stored under docs/maestro/ux_eval/, newest first.
    """
    from ..config.paths import get_docs_root

    docs_root = get_docs_root()
    ux_eval_dir = docs_root / "docs" / "maestro" / "ux_eval"

    if not ux_eval_dir.exists():
        if args.json:
            print(json.dumps({"evals": []}, indent=2))
        else:
            print("No UX evaluations found.")
        return 0

    # List all eval directories
    eval_dirs = [d for d in ux_eval_dir.iterdir() if d.is_dir() and d.name.startswith('ux_eval_')]

    # Sort by modification time (newest first)
    eval_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

    if args.json:
        evals = []
        for eval_dir in eval_dirs:
            eval_id = eval_dir.name
            telemetry_file = eval_dir / "telemetry.json"
            if telemetry_file.exists():
                try:
                    with open(telemetry_file, 'r') as f:
                        telemetry = json.load(f)
                    evals.append({
                        'eval_id': eval_id,
                        'goal': telemetry.get('goal', ''),
                        'total_attempts': telemetry.get('total_attempts', 0),
                        'successful_attempts': telemetry.get('successful_attempts', 0),
                        'failed_attempts': telemetry.get('failed_attempts', 0)
                    })
                except Exception:
                    evals.append({'eval_id': eval_id})
            else:
                evals.append({'eval_id': eval_id})
        print(json.dumps({"evals": evals}, indent=2))
    else:
        if not eval_dirs:
            print("No UX evaluations found.")
        else:
            print(f"Found {len(eval_dirs)} UX evaluation(s):\n")
            for eval_dir in eval_dirs:
                eval_id = eval_dir.name
                telemetry_file = eval_dir / "telemetry.json"
                if telemetry_file.exists():
                    try:
                        with open(telemetry_file, 'r') as f:
                            telemetry = json.load(f)
                        goal = telemetry.get('goal', 'N/A')
                        total = telemetry.get('total_attempts', 0)
                        success = telemetry.get('successful_attempts', 0)
                        print(f"  {eval_id}")
                        print(f"    Goal: {goal[:60]}{'...' if len(goal) > 60 else ''}")
                        print(f"    Attempts: {total} ({success} successful)")
                        print()
                    except Exception:
                        print(f"  {eval_id}")
                        print()
                else:
                    print(f"  {eval_id}")
                    print()

    return 0


def handle_ux_show(args: argparse.Namespace) -> int:
    """
    Handle UX show command.

    Shows summary and artifacts for a specific UX eval.
    """
    from ..config.paths import get_docs_root

    docs_root = get_docs_root()
    eval_dir = docs_root / "docs" / "maestro" / "ux_eval" / args.eval_id

    if not eval_dir.exists():
        print(f"Error: UX eval not found: {args.eval_id}", file=sys.stderr)
        return 1

    # Load telemetry
    telemetry_file = eval_dir / "telemetry.json"
    if not telemetry_file.exists():
        print(f"Error: telemetry.json not found for {args.eval_id}", file=sys.stderr)
        return 1

    try:
        with open(telemetry_file, 'r') as f:
            telemetry = json.load(f)
    except Exception as e:
        print(f"Error loading telemetry: {e}", file=sys.stderr)
        return 1

    # Check for artifacts
    report_file = eval_dir / f"{args.eval_id}.md"
    surface_file = eval_dir / "surface.json"
    attempts_file = eval_dir / "attempts.jsonl"
    postmortem_dir = eval_dir / "ux_postmortem"

    if args.json:
        result = {
            'eval_id': args.eval_id,
            'eval_dir': str(eval_dir),
            'telemetry': telemetry,
            'artifacts': {
                'report': str(report_file) if report_file.exists() else None,
                'surface': str(surface_file) if surface_file.exists() else None,
                'attempts': str(attempts_file) if attempts_file.exists() else None,
                'postmortem': str(postmortem_dir) if postmortem_dir.exists() else None
            }
        }
        print(json.dumps(result, indent=2))
    else:
        print()
        print("="*60)
        print(f"UX EVALUATION: {args.eval_id}")
        print("="*60)
        print()
        print(f"Goal: {telemetry.get('goal', 'N/A')}")
        print()
        print(f"Total Attempts: {telemetry.get('total_attempts', 0)}")
        print(f"Successful Attempts: {telemetry.get('successful_attempts', 0)}")
        print(f"Failed Attempts: {telemetry.get('failed_attempts', 0)}")
        print(f"Help Calls: {telemetry.get('help_call_count', 0)}")
        print(f"Timeouts: {telemetry.get('timeout_count', 0)}")
        print(f"Unknown Commands: {telemetry.get('unknown_command_count', 0)}")
        print()
        print("Artifacts:")
        print(f"  Eval Dir: {eval_dir}")
        print(f"  Report: {report_file if report_file.exists() else 'Not found'}")
        print(f"  Surface: {surface_file if surface_file.exists() else 'Not found'}")
        print(f"  Attempts: {attempts_file if attempts_file.exists() else 'Not found'}")
        print(f"  Postmortem: {postmortem_dir if postmortem_dir.exists() else 'Not run'}")
        print()

    return 0
