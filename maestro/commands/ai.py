"""AI command helpers for task sync workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json
import socket
import subprocess
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

    qwen_parser = ai_subparsers.add_parser("qwen", help="Run Qwen server or TUI client")
    qwen_parser.add_argument(
        "mode",
        nargs="?",
        choices=["tui", "server"],
        default="tui",
        help="Run the TUI client (default) or the server only.",
    )
    qwen_parser.add_argument(
        "-p",
        "--prompt",
        help="Initial prompt to send after connecting (TUI mode only).",
    )
    qwen_parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    qwen_parser.add_argument("--tcp-port", type=int, help="Server TCP port (default: auto)")
    qwen_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show Qwen server logs and extra connection details.",
    )
    qwen_parser.add_argument(
        "--attach",
        action="store_true",
        help="Connect to an existing server instead of starting one.",
    )
    qwen_parser.add_argument(
        "--qwen-executable",
        help="Path to qwen-code.sh (default: repo root qwen-code.sh).",
    )

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


def handle_ai_qwen(args) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    qwen_script = _resolve_qwen_script(args, repo_root)
    if not qwen_script:
        return 1

    mode = getattr(args, "mode", "tui")
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "tcp_port", None)
    attach = getattr(args, "attach", False)
    verbose = getattr(args, "verbose", False)

    if mode == "server":
        if port is None:
            port = 7777
        return _run_qwen_server(qwen_script, repo_root, host, port, verbose)

    if attach:
        if port is None:
            port = 7777
        return _run_qwen_tui(host, port, getattr(args, "prompt", None))

    if port is None:
        port = _pick_free_port()

    server_proc = _start_qwen_server(qwen_script, repo_root, host, port, verbose)
    if not server_proc:
        return 1

    try:
        if not _wait_for_server(host, port, timeout=10.0):
            print("Error: Qwen server did not become ready in time.")
            return 1
        return _run_qwen_tui(host, port, getattr(args, "prompt", None))
    finally:
        _stop_server_process(server_proc, verbose)


def _resolve_qwen_script(args, repo_root: Path) -> Optional[Path]:
    override = getattr(args, "qwen_executable", None)
    if override:
        script_path = Path(override).expanduser()
        if not script_path.is_absolute():
            script_path = repo_root / script_path
    else:
        script_path = repo_root / "qwen-code.sh"

    if not script_path.exists():
        print(f"Error: qwen-code.sh not found at {script_path}.")
        return None
    return script_path


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_qwen_server(
    qwen_script: Path,
    repo_root: Path,
    host: str,
    port: int,
    verbose: bool,
) -> int:
    cmd = _build_qwen_server_cmd(qwen_script, host, port)
    stdout = None if verbose else subprocess.DEVNULL
    stderr = None if verbose else subprocess.DEVNULL
    try:
        return subprocess.call(cmd, cwd=str(repo_root), stdout=stdout, stderr=stderr)
    except FileNotFoundError:
        print(f"Error: failed to run {cmd[0]}.")
        return 1


def _start_qwen_server(
    qwen_script: Path,
    repo_root: Path,
    host: str,
    port: int,
    verbose: bool,
):
    cmd = _build_qwen_server_cmd(qwen_script, host, port)
    stdout = None if verbose else subprocess.DEVNULL
    stderr = None if verbose else subprocess.DEVNULL
    try:
        return subprocess.Popen(cmd, cwd=str(repo_root), stdout=stdout, stderr=stderr)
    except FileNotFoundError:
        print(f"Error: failed to run {cmd[0]}.")
        return None


def _build_qwen_server_cmd(qwen_script: Path, host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "maestro.qwen.main",
        "--mode",
        "tcp",
        "--tcp-host",
        host,
        "--tcp-port",
        str(port),
        "--qwen-executable",
        str(qwen_script),
    ]


def _wait_for_server(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _run_qwen_tui(host: str, port: int, prompt: Optional[str]) -> int:
    try:
        from maestro.qwen.tui import run_tui
    except Exception as exc:
        print(f"Error: failed to load Qwen TUI: {exc}")
        return 1

    # When a prompt is provided, run in a non-interactive "fire-and-exit" mode.
    # This makes `maestro ai qwen -p "..."` scriptable and compatible with `timeout`.
    exit_after_prompt = bool(prompt)
    return run_tui(host=host, port=port, prompt=prompt, exit_after_prompt=exit_after_prompt)


def _stop_server_process(proc: subprocess.Popen, verbose: bool) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=1)
        except Exception:
            if verbose:
                print("Warning: failed to stop Qwen server process.")


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
        sessions = list_sessions(session_type=SessionType.WORK_TRACK.value)
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
    last_signature = _read_sync_signature()

    if getattr(args, "verbose", False):
        print(
            f"Watching {sync_path.resolve()} for changes (cwd {Path.cwd()}). Press Ctrl+C to stop.",
            flush=True,
        )

    try:
        while True:
            signature = _read_sync_signature()
            if signature != last_signature:
                handle_ai_sync(_clone_args_without_watch(args))
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                except Exception:
                    pass
                last_signature = _read_sync_signature()
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


def _read_sync_signature() -> str:
    state = load_sync_state()
    if not state:
        return ""
    try:
        return json.dumps(state, sort_keys=True)
    except (TypeError, ValueError):
        return ""
