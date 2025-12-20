"""Discussion command implementation with work session integration."""

from __future__ import annotations

import os
from typing import Optional

from maestro.ai import (
    ActionProcessor,
    DiscussionMode,
    ExternalCommandClient,
    build_phase_context,
    build_task_context,
    build_track_context,
)
from maestro.data import parse_config_md
from maestro.discussion import DiscussionSession, create_discussion_session, resume_discussion
from maestro.work_session import SessionType
from maestro.breadcrumb import list_breadcrumbs, get_breadcrumb_summary


def choose_mode(mode_arg: Optional[str]) -> DiscussionMode:
    if mode_arg:
        return DiscussionMode(mode_arg.lower())
    config = parse_config_md("docs/config.md")
    # Use the flat keys from parse_config_md
    discussion_mode = config.get("discussion_mode") if config else None
    if discussion_mode in ("editor", "terminal"):
        return DiscussionMode(discussion_mode)
    if os.environ.get("VISUAL") or os.environ.get("EDITOR"):
        return DiscussionMode.EDITOR
    return DiscussionMode.TERMINAL


def run_discussion_with_session(discussion_session: DiscussionSession, dry_run: bool = False) -> int:
    # Run the discussion based on the mode
    if discussion_session.mode == "editor":
        result = discussion_session.run_editor_mode()
    else:
        result = discussion_session.run_terminal_mode()

    # Process actions if any were generated
    if hasattr(result, 'actions') and result.actions:
        # Get context to determine allowed actions
        context = discussion_session._get_context_for_session()
        processor = ActionProcessor(dry_run=dry_run)
        errors = processor.validate_actions(result.actions, context.allowed_actions)

        if errors:
            print("[System] Action validation errors:")
            for err in errors:
                print(f"- {err}")
        else:
            action_result = processor.execute_actions(result.actions)
            if action_result.summary:
                print("[System] Action summary:")
                for line in action_result.summary:
                    print(f"- {line}")
            if action_result.errors:
                print("[System] Action execution errors:")
                for err in action_result.errors:
                    print(f"- {err}")

    # Print session summary
    summary = get_breadcrumb_summary(discussion_session.work_session.session_id)
    print(f"[System] Discussion session completed. Session ID: {discussion_session.work_session.session_id}")
    print(f"[System] Total interactions: {summary['total_breadcrumbs']}")
    print(f"[System] Total tokens: {summary['total_tokens']['input'] + summary['total_tokens']['output']:,}")
    print(f"[System] Estimated cost: ${summary['total_cost']:.2f}")

    return 0


def handle_discuss_command(args) -> int:
    config = parse_config_md("docs/config.md")

    # Check if we should resume an existing session
    if hasattr(args, 'resume') and args.resume:
        discussion_session = resume_discussion(args.resume)
    else:
        # Create a new session based on the provided context
        related_entity = {}

        # Check if specific IDs were provided via new arguments
        if hasattr(args, 'track_id') and args.track_id:
            related_entity = {'track_id': args.track_id}
        elif hasattr(args, 'phase_id') and args.phase_id:
            related_entity = {'phase_id': args.phase_id}
        elif hasattr(args, 'task_id') and args.task_id:
            related_entity = {'task_id': args.task_id}
        else:
            # Use current context
            current_phase = None
            if config:
                current_phase = config.get("current_phase")
            if current_phase:
                related_entity = {'phase_id': current_phase}
            else:
                related_entity = {}

        mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string
        discussion_session = create_discussion_session(
            session_type=SessionType.DISCUSSION.value,
            related_entity=related_entity,
            mode=mode
        )

    dry_run = getattr(args, "dry_run", False)
    return run_discussion_with_session(discussion_session, dry_run=dry_run)


def handle_track_discuss(track_id: Optional[str], args) -> int:
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'track_id': track_id},
        mode=mode
    )
    dry_run = getattr(args, "dry_run", False)
    return run_discussion_with_session(discussion_session, dry_run=dry_run)


def handle_phase_discuss(phase_id: str, args) -> int:
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'phase_id': phase_id},
        mode=mode
    )
    dry_run = getattr(args, "dry_run", False)
    return run_discussion_with_session(discussion_session, dry_run=dry_run)


def handle_task_discuss(task_id: str, args) -> int:
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string
    discussion_session = create_discussion_session(
        session_type=SessionType.DISCUSSION.value,
        related_entity={'task_id': task_id},
        mode=mode
    )
    dry_run = getattr(args, "dry_run", False)
    return run_discussion_with_session(discussion_session, dry_run=dry_run)


def add_discuss_parser(subparsers):
    discuss_parser = subparsers.add_parser(
        "discuss",
        help="Start an AI discussion using the current context",
    )
    # Add mutually exclusive group for selecting context
    context_group = discuss_parser.add_mutually_exclusive_group()
    context_group.add_argument("--track", "--track-id", dest="track_id", help="Select track by ID")
    context_group.add_argument("--phase", "--phase-id", dest="phase_id", help="Select phase by ID")
    context_group.add_argument("--task", "--task-id", dest="task_id", help="Select task by ID")

    discuss_parser.add_argument(
        "--mode",
        choices=["editor", "terminal"],
        help="Discussion mode (editor or terminal)",
    )
    discuss_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing them",
    )
    discuss_parser.add_argument(
        "--resume",
        help="Resume previous discussion session"
    )
    return discuss_parser
