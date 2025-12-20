"""AI command helpers for task sync workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

from maestro.ai.task_sync import (
    build_task_prompt,
    build_task_queue,
    find_task_context,
    load_sync_state,
    task_is_done,
    write_sync_state,
)
from maestro.breadcrumb import create_breadcrumb, estimate_tokens, write_breadcrumb
from maestro.work_session import SessionStatus, SessionType, WorkSession, list_sessions, load_session, save_session


def add_ai_parser(subparsers):
    ai_parser = subparsers.add_parser("ai", help="AI workflow helpers")
    ai_subparsers = ai_parser.add_subparsers(dest="ai_subcommand", help="AI subcommands")

    sync_parser = ai_subparsers.add_parser("sync", help="Sync to the next task in the active AI session")
    sync_parser.add_argument("--session", help="Work session ID to sync (default: most recent work_task)")
    sync_parser.add_argument("--task", help="Override current task ID when syncing")
    sync_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch docs/ai_sync.json and sync whenever it changes",
    )
    sync_parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds when using --watch (default: 1.0)",
    )
    sync_parser.add_argument(
        "--once",
        action="store_true",
        help="Exit after the first sync when using --watch",
    )
    sync_parser.add_argument("--verbose", action="store_true", help="Show extra selection details")

    ai_subparsers.add_parser("help", aliases=["h"], help="Show help for AI commands")
    return ai_parser


def handle_ai_sync(args) -> int:
    if getattr(args, "watch", False):
        return _watch_ai_sync(args)
    if getattr(args, "once", False):
        print("Warning: --once has no effect without --watch.")

    session = _resolve_session(args)
    if not session:
        print("Error: No work_task session found. Run: python maestro.py work task <id>")
        return 1

    session_path = _find_session_path(session.session_id)
    if not session_path:
        print(f"Error: Could not locate session file for {session.session_id}.")
        return 1

    sync_state = load_sync_state()
    task_id = getattr(args, "task", None)
    if not task_id:
        task_id = sync_state.get("current_task_id") or session.metadata.get("current_task_id")
    if not task_id:
        print("Error: No current task set for this session.")
        return 1

    if getattr(args, "verbose", False):
        print(f"Syncing session {session.session_id} from task {task_id}...")

    task_context = find_task_context(task_id)
    if not task_context:
        print(f"Error: Task '{task_id}' not found in docs/phases.")
        return 1

    phase = task_context["phase"]
    task_queue = session.metadata.get("task_queue") or build_task_queue(phase)

    next_task_id = _select_next_task(task_queue, phase, task_id)
    if not next_task_id:
        session.status = SessionStatus.COMPLETED.value
        session.metadata["last_sync"] = datetime.now().isoformat()
        save_session(session, session_path)
        print("No pending tasks found in this session queue.")
        return 0

    next_context = find_task_context(next_task_id)
    if not next_context:
        print(f"Error: Next task '{next_task_id}' not found in docs/phases.")
        return 1

    prompt = build_task_prompt(
        next_task_id,
        next_context["task"],
        next_context["phase"],
        session_id=session.session_id,
        sync_source="ai sync",
    )

    session.metadata["task_queue"] = task_queue
    session.metadata["current_task_id"] = next_task_id
    session.metadata["last_sync"] = datetime.now().isoformat()
    save_session(session, session_path)
    if not getattr(args, "no_write", False):
        write_sync_state(session, task_queue, next_task_id)

    _write_sync_breadcrumb(session, prompt)

    print(prompt)
    return 0


def _resolve_session(args) -> Optional[WorkSession]:
    sync_state = load_sync_state()
    session_override = getattr(args, "session", None) or sync_state.get("session_id")

    if session_override:
        session_path = _find_session_path(session_override)
        if not session_path:
            return None
        return load_session(session_path)

    sessions = list_sessions(session_type=SessionType.WORK_TASK.value)
    if not sessions:
        return None

    def _parse_time(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.min

    sessions.sort(key=lambda s: _parse_time(s.modified), reverse=True)
    return sessions[0]


def _find_session_path(session_id: str) -> Optional[Path]:
    base = Path("docs/sessions")
    if not base.exists():
        return None
    for session_file in base.rglob("session.json"):
        if session_file.parent.name == session_id:
            return session_file
    return None


def _select_next_task(task_queue: list[str], phase: Dict[str, Any], current_task_id: str) -> Optional[str]:
    tasks_by_id: Dict[str, Dict[str, Any]] = {}
    ordered_ids: list[str] = []

    for task in phase.get("tasks", []):
        task_id = task.get("task_id") or task.get("task_number")
        if not task_id:
            continue
        tasks_by_id[task_id] = task
        ordered_ids.append(task_id)

    if not task_queue:
        task_queue = ordered_ids

    start_idx = 0
    if current_task_id in task_queue:
        start_idx = task_queue.index(current_task_id) + 1

    for task_id in task_queue[start_idx:]:
        task = tasks_by_id.get(task_id)
        if not task:
            continue
        if not task_is_done(task):
            return task_id

    for task_id in task_queue[:start_idx]:
        task = tasks_by_id.get(task_id)
        if not task:
            continue
        if not task_is_done(task):
            return task_id

    return None


def _write_sync_breadcrumb(session: WorkSession, prompt: str) -> None:
    input_tokens = estimate_tokens("ai sync")
    output_tokens = estimate_tokens(prompt)
    breadcrumb = create_breadcrumb(
        prompt="ai sync",
        response=prompt,
        tools_called=[],
        files_modified=[],
        parent_session_id=session.parent_session_id,
        depth_level=0,
        model_used="maestro",
        token_count={"input": input_tokens, "output": output_tokens},
        cost=0.0,
    )
    write_breadcrumb(breadcrumb, session.session_id)


def _watch_ai_sync(args) -> int:
    sync_path = Path("docs/ai_sync.json")
    last_signature = None
    if sync_path.exists():
        last_signature = _read_sync_signature(sync_path)

    if getattr(args, "verbose", False):
        print(
            f"Watching {sync_path.resolve()} for changes (cwd {Path.cwd()}). Press Ctrl+C to stop.",
            flush=True,
        )

    try:
        while True:
            if sync_path.exists():
                signature = _read_sync_signature(sync_path)
                if signature != last_signature:
                    handle_ai_sync(_clone_args_without_watch(args))
                    try:
                        sys.stdout.flush()
                        sys.stderr.flush()
                    except Exception:
                        pass
                    if sync_path.exists():
                        last_signature = _read_sync_signature(sync_path)
                    if getattr(args, "once", False):
                        return 0
            time.sleep(max(getattr(args, "poll_interval", 1.0), 0.1))
    except KeyboardInterrupt:
        if getattr(args, "verbose", False):
            print("Stopped watching.", flush=True)
        return 0


def _clone_args_without_watch(args):
    class _Args:
        pass
    cloned = _Args()
    for key, value in vars(args).items():
        if key in ("watch", "poll_interval"):
            continue
        setattr(cloned, key, value)
    setattr(cloned, "no_write", True)
    return cloned


def _read_sync_signature(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
