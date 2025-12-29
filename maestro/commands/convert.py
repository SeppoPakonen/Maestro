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
    """Handle maestro convert add [PIPELINE_NAME]"""
    try:
        from maestro.convert.plan_approval import create_pipeline

        pipeline_name = args.pipeline_name or "default"
        print(f"Creating new conversion pipeline: {pipeline_name}")

        try:
            repo_root = find_repo_root_v3()
            meta = create_pipeline(
                pipeline_name,
                source_repo=repo_root,
                target_repo=repo_root,
                repo_root=repo_root,
            )
            print(f"Successfully created conversion pipeline: {meta.get('pipeline_id', pipeline_name)}")
            print(f"Pipeline file: {Path(repo_root) / 'docs' / 'maestro' / 'convert' / 'pipelines' / pipeline_name / 'meta.json'}")
            print()
            print("Next steps:")
            print(f"  1. Plan conversion: maestro convert plan {pipeline_name}")
            print(f"  2. Approve plan: maestro convert plan approve {pipeline_name} --reason \"...\"")
            print(f"  3. Run conversion: maestro convert run {pipeline_name}")
            return 0
        except Exception as e:
            print(f"Error creating conversion pipeline: {e}")
            return 1
    except ImportError as e:
        print(f"Conversion functionality not fully available: {e}")
        print("This may be due to missing dependencies or incomplete conversion module setup.")
        return 1


def handle_convert_plan(args):
    """Handle maestro convert plan [PIPELINE_ID] [ACTION] or [ACTION] [PIPELINE_ID]."""
    try:
        from maestro.convert.plan_approval import (
            approve_plan,
            reject_plan,
            plan_conversion,
            load_meta,
            load_plan,
        )

        repo_root = find_repo_root_v3()
        action_or_pipeline = args.action_or_pipeline
        pipeline_or_action = args.pipeline_id
        actions = {"show", "approve", "reject", "status", "history"}
        plan_subcommand = None
        pipeline_id = None

        if action_or_pipeline in actions:
            plan_subcommand = action_or_pipeline
            pipeline_id = pipeline_or_action
            if not pipeline_id:
                print("Error: PIPELINE_ID is required for this command.")
                return 1
        else:
            pipeline_id = action_or_pipeline
            if pipeline_or_action:
                if pipeline_or_action not in actions:
                    print(f"Error: unknown action '{pipeline_or_action}'.")
                    return 1
                plan_subcommand = pipeline_or_action

        if plan_subcommand == "show":
            meta = load_meta(pipeline_id, repo_root=repo_root)
            plan = load_plan(pipeline_id, repo_root=repo_root)
            print(f"Pipeline ID: {pipeline_id}")
            print(f"Status: {meta.get('status')}")
            print(f"Plan path: {Path(repo_root) / 'docs' / 'maestro' / 'convert' / 'pipelines' / pipeline_id / 'plan.json'}")
            steps = plan.get("steps", [])
            print(f"Plan steps: {len(steps)}")
            return 0

        if plan_subcommand == "status":
            meta = load_meta(pipeline_id, repo_root=repo_root)
            print(f"Pipeline ID: {pipeline_id}")
            print(f"Status: {meta.get('status')}")
            return 0

        if plan_subcommand == "history":
            pipeline_dir = Path(repo_root) / "docs" / "maestro" / "convert" / "pipelines" / pipeline_id
            decision_path = pipeline_dir / "decision.json"
            runs_dir = pipeline_dir / "runs"
            print(f"Pipeline ID: {pipeline_id}")
            if decision_path.exists():
                print(f"Decision: {decision_path}")
            else:
                print("Decision: none")
            if runs_dir.exists():
                runs = sorted(p.name for p in runs_dir.iterdir() if p.is_dir())
            else:
                runs = []
            print(f"Runs: {len(runs)}")
            for run_id in runs:
                print(f"  - {run_id}")
            return 0

        if plan_subcommand == "approve":
            meta, decision = approve_plan(
                pipeline_id,
                reason=getattr(args, "reason", None),
                decided_by="user",
                repo_root=repo_root,
            )
            if decision is None:
                print(f"Pipeline {pipeline_id} is already approved; no changes.")
            print(f"Pipeline ID: {pipeline_id}")
            print(f"Status: {meta.get('status')}")
            print(f"Next: maestro convert run {pipeline_id}")
            return 0

        if plan_subcommand == "reject":
            meta, decision = reject_plan(
                pipeline_id,
                reason=getattr(args, "reason", None),
                decided_by="user",
                repo_root=repo_root,
            )
            if decision is None:
                print(f"Pipeline {pipeline_id} is already rejected; no changes.")
            print(f"Pipeline ID: {pipeline_id}")
            print(f"Status: {meta.get('status')}")
            print(f"Next: maestro convert plan show {pipeline_id}")
            return 0

        print(f"Planning conversion for pipeline: {pipeline_id}")
        try:
            plan = plan_conversion(pipeline_id, repo_root=repo_root)
            print(f"Successfully planned conversion for pipeline: {pipeline_id}")
            print(f"Plan steps: {len(plan.get('steps', []))}")
            return 0
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
        from maestro.convert.plan_approval import run_conversion_pipeline, load_meta

        repo_root = find_repo_root_v3()
        pipeline_id = args.pipeline_id
        ignore_gates = getattr(args, "ignore_gates", False)

        # Check plan approval gate FIRST before any other gates
        # This allows user to see "plan not approved" rather than "repoconf missing"
        if not ignore_gates:
            try:
                meta = load_meta(pipeline_id, repo_root)
                status = meta.get("status", "draft")
                if status != "approved":
                    print(f"\n  [Gate] CONVERT_PLAN_NOT_APPROVED")
                    print(f"  Pipeline '{pipeline_id}' status is '{status}', not 'approved'.")
                    print(f"  Run 'maestro convert plan approve {pipeline_id} --reason \"...\"' first.\n")
                    return 1
            except Exception as e:
                print(f"Error loading pipeline metadata: {e}")
                return 1

        # Only check repo/branch requirements if plan is approved (or gates bypassed)
        # Note: convert pipelines specify target in pipeline metadata, not repoconf
        require_repo_model(repo_root)
        branch_guard_error = check_branch_guard(repo_root)
        if branch_guard_error:
            print(f"Error: {branch_guard_error}")
            return 1

        print(f"Running conversion pipeline: {pipeline_id}")

        try:
            result = run_conversion_pipeline(
                pipeline_id,
                repo_root=repo_root,
                ignore_gates=ignore_gates,
            )
            if result.success:
                print(f"Successfully ran conversion pipeline: {pipeline_id}")
                if result.run_id:
                    print(f"Run ID: {result.run_id}")
                return 0
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

    # convert plan (show/approve/reject or default planning)
    plan_parser = convert_subparsers.add_parser('plan', aliases=['p'], help='Plan conversion approach')
    plan_parser.add_argument(
        'action_or_pipeline',
        help='ACTION (show/approve/reject/status/history) or PIPELINE_ID'
    )
    plan_parser.add_argument(
        'pipeline_id',
        nargs='?',
        help='PIPELINE_ID when ACTION first, or ACTION when PIPELINE_ID first'
    )
    plan_parser.add_argument('--reason', help='Reason for approval or rejection')
    plan_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')

    # convert run
    run_parser = convert_subparsers.add_parser('run', aliases=['r'], help='Run conversion pipeline')
    run_parser.add_argument('pipeline_id', help='ID of the pipeline to run')
    run_parser.add_argument('--ignore-gates', action='store_true', help='Bypass convert plan gates')
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
