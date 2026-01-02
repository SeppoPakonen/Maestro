"""
Ops command handlers for Maestro CLI.

Operations automation layer for health checks and deterministic runbook execution.
"""

import argparse
import sys
from pathlib import Path


def add_ops_parser(subparsers) -> argparse.ArgumentParser:
    """Add ops command parser."""
    ops_parser = subparsers.add_parser(
        'ops',
        help='Operations automation (health checks, runbook execution)'
    )
    ops_subparsers = ops_parser.add_subparsers(
        dest='ops_subcommand',
        help='Ops subcommands'
    )

    # ops doctor
    doctor_parser = ops_subparsers.add_parser(
        'doctor',
        help='Run health checks and report gates/blockers'
    )
    doctor_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    doctor_parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors (non-zero exit)'
    )
    doctor_parser.add_argument(
        '--ignore-gates',
        action='store_true',
        help='Report gates but do not enforce them'
    )
    doctor_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show recommendations and additional details'
    )

    # ops run
    run_parser = ops_subparsers.add_parser(
        'run',
        help='Execute an ops plan (deterministic runbook)'
    )
    run_parser.add_argument(
        'plan',
        help='Path to ops plan YAML file'
    )
    run_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without running'
    )
    run_parser.add_argument(
        '--execute',
        action='store_true',
        help='Allow write steps to execute (default: dry-run for write steps)'
    )
    run_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    run_parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue executing steps even if one fails'
    )

    # ops list
    list_parser = ops_subparsers.add_parser(
        'list',
        aliases=['ls'],
        help='List ops run records'
    )

    # ops show
    show_parser = ops_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show ops run details'
    )
    show_parser.add_argument(
        'run_id',
        help='Run ID to show'
    )

    return ops_parser


def handle_ops_command(args: argparse.Namespace) -> int:
    """Handle ops commands."""
    subcommand = getattr(args, 'ops_subcommand', None)

    if subcommand == 'doctor':
        return handle_ops_doctor(args)
    elif subcommand == 'run':
        return handle_ops_run(args)
    elif subcommand in (None, 'list', 'ls'):
        return handle_ops_list(args)
    elif subcommand in ('show', 'sh'):
        return handle_ops_show(args)
    else:
        print(f"Unknown ops subcommand: {subcommand}")
        return 1


def handle_ops_doctor(args: argparse.Namespace) -> int:
    """Handle ops doctor command."""
    import json
    from maestro.ops.doctor import run_doctor, format_text_output

    try:
        # Run doctor checks
        result = run_doctor(
            strict=args.strict,
            ignore_gates=args.ignore_gates,
            verbose=getattr(args, 'verbose', False)
        )
    except Exception as exc:
        print(f"Internal error: {exc}", file=sys.stderr)
        return 3

    # Output results
    if args.format == 'json':
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_text_output(result, verbose=getattr(args, 'verbose', False)))

    return result.exit_code


def handle_ops_run(args: argparse.Namespace) -> int:
    """Handle ops run command."""
    import json
    from pathlib import Path
    from maestro.ops.runner import run_ops_plan

    plan_path = Path(args.plan)

    try:
        result = run_ops_plan(
            plan_path=plan_path,
            dry_run=args.dry_run,
            continue_on_error=args.continue_on_error,
            execute_writes=getattr(args, 'execute', False)
        )

        if args.format == 'json':
            output = {
                "run_id": result.run_id,
                "plan_name": result.plan_name,
                "dry_run": result.dry_run,
                "exit_code": result.exit_code,
                "total_steps": len(result.step_results),
                "successful_steps": sum(1 for r in result.step_results if r.exit_code == 0),
            }
            print(json.dumps(output, indent=2))
        else:
            # Text output
            print(f"Ops Run: {result.run_id}")
            print(f"Plan: {result.plan_name}")
            print(f"Dry run: {result.dry_run}")
            print()
            print(f"Executed {len(result.step_results)} steps:")
            for step in result.step_results:
                status = "✓" if step.exit_code == 0 else "✗"
                print(f"  {status} Step {step.step_index}: {step.command} ({step.duration_ms}ms)")
            print()
            print(f"Run record: docs/maestro/ops/runs/{result.run_id}/")
            print(f"Exit code: {result.exit_code}")

        return result.exit_code

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Internal error: {e}", file=sys.stderr)
        return 3


def handle_ops_list(args: argparse.Namespace) -> int:
    """Handle ops list command."""
    from maestro.ops.runner import list_ops_runs

    runs = list_ops_runs()

    if not runs:
        print("No ops runs recorded yet")
        return 0

    print(f"Ops Runs ({len(runs)} total):")
    print()
    for run in runs:
        status = "✓" if run["exit_code"] == 0 else "✗"
        print(f"  {status} {run['run_id']}")
        print(f"     Plan: {run['plan_name']}")
        print(f"     Started: {run['started_at']}")
        print(f"     Exit code: {run['exit_code']}")
        print()

    return 0


def handle_ops_show(args: argparse.Namespace) -> int:
    """Handle ops show command."""
    from maestro.ops.runner import show_ops_run

    details = show_ops_run(args.run_id)

    if not details:
        print(f"Run {args.run_id}: not found")
        return 1

    # Show run details
    meta = details["meta"]
    summary = details["summary"]
    steps = details["steps"]

    print(f"Ops Run: {meta['run_id']}")
    print(f"Plan: {meta['plan_name']}")
    print(f"Path: {meta['plan_path']}")
    print(f"Started: {meta['started_at']}")
    print(f"Completed: {meta['completed_at']}")
    print(f"Dry run: {meta['dry_run']}")
    print()
    print(f"Summary:")
    print(f"  Total steps: {summary['total_steps']}")
    print(f"  Successful: {summary['successful_steps']}")
    print(f"  Failed: {summary['failed_steps']}")
    print(f"  Total duration: {summary['total_duration_ms']}ms")
    print()
    print(f"Steps:")
    for step in steps:
        status = "✓" if step["exit_code"] == 0 else "✗"
        print(f"  {status} Step {step['step_index']}: {step['command']}")
        print(f"     Exit code: {step['exit_code']}, Duration: {step['duration_ms']}ms")
    print()
    print(f"Exit code: {meta['exit_code']}")

    return 0
