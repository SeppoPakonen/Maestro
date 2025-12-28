"""
Convert command handlers for Maestro CLI.
Provides conversion pipeline functionality.
"""
import argparse
from typing import Optional
import os
from pathlib import Path
from maestro.repo.storage import (
    find_repo_root as find_repo_root_v3,
    ensure_repoconf_target,
    require_repo_model,
)
from maestro.git_guard import check_branch_guard


def handle_convert_new(args):
    """Handle maestro convert new [PIPELINE_NAME]"""
    try:
        from maestro.convert.convert_orchestrator import create_new_pipeline

        pipeline_name = args.pipeline_name or "default"
        print(f"Creating new conversion pipeline: {pipeline_name}")

        try:
            pipeline = create_new_pipeline(pipeline_name)
            print(f"Successfully created conversion pipeline: {pipeline.id}")
            return 0
        except Exception as e:
            print(f"Error creating conversion pipeline: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_plan(args):
    """Handle maestro convert plan [PIPELINE_ID]"""
    try:
        from maestro.convert.planner import plan_conversion

        pipeline_id = args.pipeline_id
        print(f"Planning conversion for pipeline: {pipeline_id}")

        try:
            result = plan_conversion(pipeline_id, verbose=args.verbose)
            if result:
                print(f"Successfully planned conversion for pipeline: {pipeline_id}")
                return 0
            else:
                print(f"Failed to plan conversion for pipeline: {pipeline_id}")
                return 1
        except Exception as e:
            print(f"Error planning conversion: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_run(args):
    """Handle maestro convert run [PIPELINE_ID]"""
    try:
        repo_root = find_repo_root_v3()
        require_repo_model(repo_root)
        ensure_repoconf_target(repo_root)
        branch_guard_error = check_branch_guard(repo_root)
        if branch_guard_error:
            print(f"Error: {branch_guard_error}")
            return 1

        from maestro.convert.execution_engine import run_conversion_pipeline

        pipeline_id = args.pipeline_id
        print(f"Running conversion pipeline: {pipeline_id}")

        try:
            success = run_conversion_pipeline(pipeline_id, verbose=args.verbose)
            if success:
                print(f"Successfully ran conversion pipeline: {pipeline_id}")
                return 0
            else:
                print(f"Failed to run conversion pipeline: {pipeline_id}")
                return 1
        except Exception as e:
            print(f"Error running conversion: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_status(args):
    """Handle maestro convert status [PIPELINE_ID]"""
    try:
        from maestro.ui_facade.convert import get_pipeline_status

        pipeline_id = args.pipeline_id
        print(f"Getting status for conversion pipeline: {pipeline_id}")

        try:
            status = get_pipeline_status(pipeline_id)
            print(f"Pipeline ID: {status.id}")
            print(f"Name: {status.name}")
            print(f"Status: {status.status}")
            if status.active_stage:
                print(f"Active Stage: {status.active_stage}")

            # Print stages if available
            if status.stages:
                print("\nStages:")
                for stage in status.stages:
                    print(f"  {stage.icon} {stage.name}: {stage.status}")
                    if stage.description:
                        print(f"      {stage.description}")
                    if stage.reason:
                        print(f"      Reason: {stage.reason}")

            return 0
        except Exception as e:
            print(f"Error getting status: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_show(args):
    """Handle maestro convert show [PIPELINE_ID]"""
    try:
        from maestro.ui_facade.convert import get_pipeline_status

        pipeline_id = args.pipeline_id
        print(f"Showing details for conversion pipeline: {pipeline_id}")

        try:
            status = get_pipeline_status(pipeline_id)
            print(f"Pipeline ID: {status.id}")
            print(f"Name: {status.name}")
            print(f"Status: {status.status}")
            if status.active_stage:
                print(f"Active Stage: {status.active_stage}")

            # Print detailed stage information
            if status.stages:
                print("\nDetailed Stage Information:")
                for stage in status.stages:
                    print(f"\nStage: {stage.name}")
                    print(f"  Status: {stage.status}")
                    print(f"  Icon: {stage.icon}")
                    print(f"  Color: {stage.color}")
                    print(f"  Description: {stage.description}")
                    if stage.start_time:
                        print(f"  Start Time: {stage.start_time}")
                    if stage.end_time:
                        print(f"  End Time: {stage.end_time}")
                    if stage.reason:
                        print(f"  Reason: {stage.reason}")
                    if stage.artifacts:
                        print(f"  Artifacts: {', '.join(stage.artifacts)}")

            return 0
        except Exception as e:
            print(f"Error showing pipeline details: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_reset(args):
    """Handle maestro convert reset [PIPELINE_ID]"""
    try:
        from maestro.convert.convert_orchestrator import reset_pipeline

        pipeline_id = args.pipeline_id
        print(f"Resetting conversion pipeline: {pipeline_id}")

        try:
            success = reset_pipeline(pipeline_id)
            if success:
                print(f"Successfully reset conversion pipeline: {pipeline_id}")
                return 0
            else:
                print(f"Failed to reset conversion pipeline: {pipeline_id}")
                return 1
        except Exception as e:
            print(f"Error resetting pipeline: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_batch(args):
    """Handle maestro convert batch [SUBCOMMAND]"""
    print(f"Batch convert command with subcommand: {args.batch_subcommand}")

    # This would handle batch operations for multiple pipelines
    if args.batch_subcommand == 'run':
        print("Running batch conversion")
        # Implementation would go here
    elif args.batch_subcommand == 'status':
        print("Getting batch status")
        # Implementation would go here
    elif args.batch_subcommand == 'show':
        print("Showing batch details")
        # Implementation would go here
    elif args.batch_subcommand == 'report':
        print("Generating batch report")
        # Implementation would go here
    else:
        print(f"Unknown batch subcommand: {args.batch_subcommand}")
        return 1

    return 0


def add_convert_parser(subparsers):
    """Add convert command subparsers."""
    convert_parser = subparsers.add_parser('convert', aliases=['c'], help='Format conversion tools and pipelines')
    convert_subparsers = convert_parser.add_subparsers(dest='convert_subcommand', help='Convert subcommands')

    # convert add (canonical, with 'new' as deprecated alias)
    add_parser = convert_subparsers.add_parser('add', aliases=['new', 'n'], help='Add new conversion pipeline')
    add_parser.add_argument('pipeline_name', help='Name for the new pipeline', nargs='?')
    add_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')

    # convert plan
    plan_parser = convert_subparsers.add_parser('plan', aliases=['p'], help='Plan conversion approach')
    plan_parser.add_argument('pipeline_id', help='ID of the pipeline to plan')
    plan_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')

    # convert run
    run_parser = convert_subparsers.add_parser('run', aliases=['r'], help='Run conversion pipeline')
    run_parser.add_argument('pipeline_id', help='ID of the pipeline to run')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')

    # convert status
    status_parser = convert_subparsers.add_parser('status', aliases=['s'], help='Get pipeline status')
    status_parser.add_argument('pipeline_id', help='ID of the pipeline to check')

    # convert show
    show_parser = convert_subparsers.add_parser('show', aliases=['sh'], help='Show pipeline details')
    show_parser.add_argument('pipeline_id', help='ID of the pipeline to show')

    # convert reset
    reset_parser = convert_subparsers.add_parser('reset', aliases=['rst'], help='Reset pipeline state')
    reset_parser.add_argument('pipeline_id', help='ID of the pipeline to reset')

    # convert batch
    batch_parser = convert_subparsers.add_parser('batch', aliases=['b'], help='Batch operations')
    batch_subparsers = batch_parser.add_subparsers(dest='batch_subcommand', help='Batch subcommands')
    
    batch_subparsers.add_parser('run', aliases=['r'], help='Run batch conversion')
    batch_subparsers.add_parser('status', aliases=['s'], help='Get batch status')
    batch_subparsers.add_parser('show', aliases=['sh'], help='Show batch details')
    batch_subparsers.add_parser('report', aliases=['rep'], help='Generate batch report')
