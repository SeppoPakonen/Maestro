"""Discussion command implementation."""

from __future__ import annotations

import os
from typing import Optional

from maestro.ai import (
    ActionProcessor,
    DiscussionMode,
    EditorDiscussion,
    ExternalCommandClient,
    TerminalDiscussion,
    build_phase_context,
    build_task_context,
    build_track_context,
)
from maestro.data import parse_config_md


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


def run_discussion(context, mode: DiscussionMode, dry_run: bool = False) -> int:
    ai_client = ExternalCommandClient()
    if mode == DiscussionMode.EDITOR:
        discussion = EditorDiscussion(context, mode, ai_client)
    else:
        discussion = TerminalDiscussion(context, mode, ai_client)

    result = discussion.start()
    processor = ActionProcessor(dry_run=dry_run)
    errors = processor.validate_actions(result.actions, context.allowed_actions)

    if errors:
        print("[System] Action validation errors:")
        for err in errors:
            print(f"- {err}")
    elif result.actions:
        action_result = processor.execute_actions(result.actions)
        if action_result.summary:
            print("[System] Action summary:")
            for line in action_result.summary:
                print(f"- {line}")
        if action_result.errors:
            print("[System] Action execution errors:")
            for err in action_result.errors:
                print(f"- {err}")

    path = discussion.serialize_result()
    print(f"[System] Discussion saved to {path}")
    return 0


def handle_discuss_command(args) -> int:
    config = parse_config_md("docs/config.md")

    # Check if specific IDs were provided via new arguments
    if hasattr(args, 'track_id') and args.track_id:
        context = build_track_context(args.track_id)
    elif hasattr(args, 'phase_id') and args.phase_id:
        context = build_phase_context(args.phase_id)
    elif hasattr(args, 'task_id') and args.task_id:
        context = build_task_context(args.task_id)
    else:
        # Use current context
        current_phase = None
        if config:
            current_phase = config.get("current_phase")
        if current_phase:
            context = build_phase_context(current_phase)
        else:
            context = build_track_context(None)

    mode = choose_mode(getattr(args, "mode", None))
    dry_run = getattr(args, "dry_run", False)
    return run_discussion(context, mode, dry_run=dry_run)


def handle_track_discuss(track_id: Optional[str], args) -> int:
    context = build_track_context(track_id)
    mode = choose_mode(getattr(args, "mode", None))
    dry_run = getattr(args, "dry_run", False)
    return run_discussion(context, mode, dry_run=dry_run)


def handle_phase_discuss(phase_id: str, args) -> int:
    context = build_phase_context(phase_id)
    mode = choose_mode(getattr(args, "mode", None))
    dry_run = getattr(args, "dry_run", False)
    return run_discussion(context, mode, dry_run=dry_run)


def handle_task_discuss(task_id: str, args) -> int:
    context = build_task_context(task_id)
    mode = choose_mode(getattr(args, "mode", None))
    dry_run = getattr(args, "dry_run", False)
    return run_discussion(context, mode, dry_run=dry_run)


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
    return discuss_parser
