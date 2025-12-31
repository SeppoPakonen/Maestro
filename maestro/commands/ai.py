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

    # Add new unified AI engine subcommands with consistent flags
    qwen_parser = ai_subparsers.add_parser("qwen", help="Run Qwen engine interactively")
    qwen_parser.add_argument("--one-shot", help="Run once with the provided text and exit")
    qwen_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    qwen_parser.add_argument("--resume", help="Resume with specific session ID or 'latest'")
    qwen_parser.add_argument("--continue-latest", action="store_true", help="Continue the most recent session")
    qwen_parser.add_argument("--model", help="Specify model to use")
    qwen_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress streaming output")
    qwen_parser.add_argument("--stream-json", action="store_true", default=None, help="Enable JSON stream output")
    qwen_parser.add_argument("--print-cmd", nargs="?", const="", help="Print the engine command and exit (optional prompt)")
    qwen_parser.add_argument("--no-danger", action="store_true", help="Override global ai_dangerously_skip_permissions for this invocation")
    qwen_parser.add_argument("--verbose", "-v", action="store_true", help="Show parsed stream event JSON")

    gemini_parser = ai_subparsers.add_parser("gemini", help="Run Gemini engine interactively")
    gemini_parser.add_argument("--one-shot", help="Run once with the provided text and exit")
    gemini_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    gemini_parser.add_argument("--resume", help="Resume with specific session ID or 'latest'")
    gemini_parser.add_argument("--continue-latest", action="store_true", help="Continue the most recent session")
    gemini_parser.add_argument("--model", help="Specify model to use")
    gemini_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress streaming output")
    gemini_parser.add_argument("--stream-json", action="store_true", default=None, help="Enable JSON stream output")
    gemini_parser.add_argument("--print-cmd", nargs="?", const="", help="Print the engine command and exit (optional prompt)")
    gemini_parser.add_argument("--no-danger", action="store_true", help="Override global ai_dangerously_skip_permissions for this invocation")
    gemini_parser.add_argument("--verbose", "-v", action="store_true", help="Show parsed stream event JSON")

    codex_parser = ai_subparsers.add_parser("codex", help="Run Codex engine interactively")
    codex_parser.add_argument("--one-shot", help="Run once with the provided text and exit")
    codex_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    codex_parser.add_argument("--resume", help="Resume with specific session ID or 'latest'")
    codex_parser.add_argument("--continue-latest", action="store_true", help="Continue the most recent session")
    codex_parser.add_argument("--model", help="Specify model to use")
    codex_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress streaming output")
    codex_parser.add_argument("--stream-json", action="store_true", default=None, help="Enable JSON stream output")
    codex_parser.add_argument("--print-cmd", nargs="?", const="", help="Print the engine command and exit (optional prompt)")
    codex_parser.add_argument("--no-danger", action="store_true", help="Override global ai_dangerously_skip_permissions for this invocation")
    codex_parser.add_argument("--verbose", "-v", action="store_true", help="Show parsed stream event JSON")

    claude_parser = ai_subparsers.add_parser("claude", help="Run Claude engine interactively")
    claude_parser.add_argument("--one-shot", help="Run once with the provided text and exit")
    claude_parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    claude_parser.add_argument("--resume", help="Resume with specific session ID or 'latest'")
    claude_parser.add_argument("--continue-latest", action="store_true", help="Continue the most recent session")
    claude_parser.add_argument("--model", help="Specify model to use")
    claude_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress streaming output")
    claude_parser.add_argument("--stream-json", action="store_true", default=None, help="Enable JSON stream output")
    claude_parser.add_argument("--print-cmd", nargs="?", const="", help="Print the engine command and exit (optional prompt)")
    claude_parser.add_argument("--no-danger", action="store_true", help="Override global ai_dangerously_skip_permissions for this invocation")
    claude_parser.add_argument("--verbose", "-v", action="store_true", help="Show parsed stream event JSON")

    # Keep the original qwen command for backward compatibility
    old_qwen_parser = ai_subparsers.add_parser("qwen-old", help="Run Qwen server or TUI client (legacy)")
    old_qwen_parser.add_argument(
        "mode",
        nargs="?",
        choices=["tui", "server"],
        default="tui",
        help="Run the TUI client (default) or the server only.",
    )
    old_qwen_parser.add_argument(
        "-p",
        "--prompt",
        help="Initial prompt to send after connecting (TUI mode only).",
    )
    old_qwen_parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    old_qwen_parser.add_argument("--tcp-port", type=int, help="Server TCP port (default: auto)")
    old_qwen_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show Qwen server logs and extra connection details.",
    )
    old_qwen_parser.add_argument(
        "--attach",
        action="store_true",
        help="Connect to an existing server instead of starting one.",
    )
    old_qwen_parser.add_argument(
        "--qwen-executable",
        help="Path to qwen-code.sh (default: repo root qwen-code.sh).",
    )

    ai_subparsers.add_parser("help", aliases=["h"], help="Show help for AI commands")
    return ai_parser


def _build_print_prompt_ref(args, prompt_value: Optional[str]):
    from maestro.ai.types import PromptRef

    if getattr(args, "stdin", False):
        return PromptRef(source="", is_stdin=True)
    if prompt_value:
        return PromptRef(source=prompt_value, is_stdin=False)
    one_shot = getattr(args, "one_shot", None)
    if one_shot:
        return PromptRef(source=one_shot, is_stdin=False)
    return PromptRef(source="", is_stdin=True)


def _print_engine_cmd(manager, engine: str, prompt_ref, opts) -> None:
    try:
        cmd = manager.build_command(engine, prompt_ref, opts)
        print(" ".join(cmd))
    except NotImplementedError:
        print(manager.explain_command(engine, prompt_ref, opts))


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
    from maestro.ai import AiEngineManager, PromptRef, RunOpts, run_interactive_chat
    from maestro.config.settings import get_settings

    # Check if this is the legacy command
    if hasattr(args, 'mode'):
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

        # For TUI mode, we'll start the manager directly in stdin mode for a better user experience
        if mode == "tui":
            return _run_qwen_stdin_chat(qwen_script, repo_root, verbose, getattr(args, "prompt", None))
    else:
        # Handle the new unified command
        manager = AiEngineManager()

        # Get settings to determine dangerous permissions flag
        settings = get_settings()

        # Build RunOpts from command line arguments
        # Override dangerous permissions if --no-danger is set
        dangerously_skip_permissions = settings.ai_dangerously_skip_permissions
        if getattr(args, 'no_danger', False):
            dangerously_skip_permissions = False

        # Handle resume flag - if it's 'latest', we'll handle it specially
        continue_latest = getattr(args, "continue_latest", False)
        resume_id = getattr(args, "resume", None)
        if resume_id == "latest":
            continue_latest = True
            resume_id = None
        if continue_latest:
            resume_id = None

        stream_json = getattr(args, "stream_json", None)
        if stream_json is None:
            stream_json = True

        opts = RunOpts(
            dangerously_skip_permissions=dangerously_skip_permissions,
            continue_latest=continue_latest,
            resume_id=resume_id,
            stream_json=stream_json,  # Enable stream_json by default for session ID extraction
            quiet=getattr(args, 'quiet', False),
            model=getattr(args, 'model', None),
            verbose=getattr(args, 'verbose', False)
        )

        print_cmd = getattr(args, "print_cmd", None)
        if print_cmd is not None:
            prompt_ref = _build_print_prompt_ref(args, print_cmd)
            _print_engine_cmd(manager, "qwen", prompt_ref, opts)
            return 0

        # Determine if reading from stdin
        if getattr(args, 'stdin', False):
            # Read from stdin
            import sys
            prompt_text = sys.stdin.read()
            prompt = PromptRef(source=prompt_text, is_stdin=True)
            # For stdin mode, run one-shot
            from maestro.ai import run_one_shot
            run_one_shot(manager, 'qwen', prompt_text, opts)
        else:
            # Check if --one-shot flag is set
            one_shot_text = getattr(args, 'one_shot', None)
            if one_shot_text is not None:
                # One-shot mode
                from maestro.ai import run_one_shot
                run_one_shot(manager, 'qwen', one_shot_text, opts)
            else:
                # Interactive mode
                run_interactive_chat(manager, 'qwen', opts)


def handle_ai_gemini(args) -> int:
    from maestro.ai import AiEngineManager, PromptRef, RunOpts, run_interactive_chat
    from maestro.config.settings import get_settings

    manager = AiEngineManager()

    # Get settings to determine dangerous permissions flag
    settings = get_settings()

    # Build RunOpts from command line arguments
    # Override dangerous permissions if --no-danger is set
    dangerously_skip_permissions = settings.ai_dangerously_skip_permissions
    if getattr(args, 'no_danger', False):
        dangerously_skip_permissions = False

    # Handle resume flag - if it's 'latest', we'll handle it specially
    continue_latest = getattr(args, "continue_latest", False)
    resume_id = getattr(args, "resume", None)
    if resume_id == "latest":
        continue_latest = True
        resume_id = None
    if continue_latest:
        resume_id = None

    stream_json = getattr(args, "stream_json", None)
    if stream_json is None:
        stream_json = True

    opts = RunOpts(
        dangerously_skip_permissions=dangerously_skip_permissions,
        continue_latest=continue_latest,
        resume_id=resume_id,
        stream_json=stream_json,  # Enable stream_json by default for session ID extraction
        quiet=getattr(args, 'quiet', False),
        model=getattr(args, 'model', None),
        verbose=getattr(args, 'verbose', False)
    )

    print_cmd = getattr(args, "print_cmd", None)
    if print_cmd is not None:
        prompt_ref = _build_print_prompt_ref(args, print_cmd)
        _print_engine_cmd(manager, "gemini", prompt_ref, opts)
        return 0

    # Determine if reading from stdin
    if getattr(args, 'stdin', False):
        # Read from stdin
        import sys
        prompt_text = sys.stdin.read()
        prompt = PromptRef(source=prompt_text, is_stdin=True)
        # For stdin mode, run one-shot
        from maestro.ai import run_one_shot
        run_one_shot(manager, 'gemini', prompt_text, opts)
    else:
        # Check if --one-shot flag is set
        one_shot_text = getattr(args, 'one_shot', None)
        if one_shot_text is not None:
            # One-shot mode
            from maestro.ai import run_one_shot
            run_one_shot(manager, 'gemini', one_shot_text, opts)
        else:
            # Interactive mode
            run_interactive_chat(manager, 'gemini', opts)


def handle_ai_codex(args) -> int:
    from maestro.ai import AiEngineManager, PromptRef, RunOpts, run_interactive_chat
    from maestro.config.settings import get_settings

    manager = AiEngineManager()

    # Get settings to determine dangerous permissions flag
    settings = get_settings()

    # Build RunOpts from command line arguments
    # Override dangerous permissions if --no-danger is set
    dangerously_skip_permissions = settings.ai_dangerously_skip_permissions
    if getattr(args, 'no_danger', False):
        dangerously_skip_permissions = False

    # Handle resume flag - if it's 'latest', we'll handle it specially
    continue_latest = getattr(args, "continue_latest", False)
    resume_id = getattr(args, "resume", None)
    if resume_id == "latest":
        continue_latest = True
        resume_id = None
    if continue_latest:
        resume_id = None

    stream_json = getattr(args, "stream_json", None)
    if stream_json is None:
        stream_json = True

    opts = RunOpts(
        dangerously_skip_permissions=dangerously_skip_permissions,
        continue_latest=continue_latest,
        resume_id=resume_id,
        stream_json=stream_json,  # Enable stream_json by default for session ID extraction
        quiet=getattr(args, 'quiet', False),
        model=getattr(args, 'model', None),
        verbose=getattr(args, 'verbose', False)
    )

    print_cmd = getattr(args, "print_cmd", None)
    if print_cmd is not None:
        prompt_ref = _build_print_prompt_ref(args, print_cmd)
        _print_engine_cmd(manager, "codex", prompt_ref, opts)
        return 0

    # Determine if reading from stdin
    if getattr(args, 'stdin', False):
        # Read from stdin
        import sys
        prompt_text = sys.stdin.read()
        prompt = PromptRef(source=prompt_text, is_stdin=True)
        # For stdin mode, run one-shot
        from maestro.ai import run_one_shot
        run_one_shot(manager, 'codex', prompt_text, opts)
    else:
        # Check if --one-shot flag is set
        one_shot_text = getattr(args, 'one_shot', None)
        if one_shot_text is not None:
            # One-shot mode
            from maestro.ai import run_one_shot
            run_one_shot(manager, 'codex', one_shot_text, opts)
        else:
            # Interactive mode
            run_interactive_chat(manager, 'codex', opts)


def handle_ai_claude(args) -> int:
    from maestro.ai import AiEngineManager, PromptRef, RunOpts, run_interactive_chat
    from maestro.config.settings import get_settings

    manager = AiEngineManager()

    # Get settings to determine dangerous permissions flag
    settings = get_settings()

    # Build RunOpts from command line arguments
    # Override dangerous permissions if --no-danger is set
    dangerously_skip_permissions = settings.ai_dangerously_skip_permissions
    if getattr(args, 'no_danger', False):
        dangerously_skip_permissions = False

    # Handle resume flag - if it's 'latest', we'll handle it specially
    continue_latest = getattr(args, "continue_latest", False)
    resume_id = getattr(args, "resume", None)
    if resume_id == "latest":
        continue_latest = True
        resume_id = None
    if continue_latest:
        resume_id = None

    stream_json = getattr(args, "stream_json", None)
    if stream_json is None:
        stream_json = True

    opts = RunOpts(
        dangerously_skip_permissions=dangerously_skip_permissions,
        continue_latest=continue_latest,
        resume_id=resume_id,
        stream_json=stream_json,  # Enable stream_json by default for session ID extraction
        quiet=getattr(args, 'quiet', False),
        model=getattr(args, 'model', None),
        verbose=getattr(args, 'verbose', False)
    )

    print_cmd = getattr(args, "print_cmd", None)
    if print_cmd is not None:
        prompt_ref = _build_print_prompt_ref(args, print_cmd)
        _print_engine_cmd(manager, "claude", prompt_ref, opts)
        return 0

    # Determine if reading from stdin
    if getattr(args, 'stdin', False):
        # Read from stdin
        import sys
        prompt_text = sys.stdin.read()
        try:
            prompt = PromptRef(source=prompt_text, is_stdin=True)
            # For stdin mode, run one-shot
            from maestro.ai import run_one_shot
            run_one_shot(manager, 'claude', prompt_text, opts)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        # Check if --one-shot flag is set
        one_shot_text = getattr(args, 'one_shot', None)
        if one_shot_text is not None:
            # One-shot mode
            from maestro.ai import run_one_shot
            try:
                run_one_shot(manager, 'claude', one_shot_text, opts)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        else:
            # Interactive mode
            try:
                run_interactive_chat(manager, 'claude', opts)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1


def _run_qwen_stdin_chat(qwen_script: Path, repo_root: Path, verbose: bool, initial_prompt: Optional[str] = None) -> int:
    """Run Qwen in a user-friendly chat interface using stdin/stdout mode"""
    from maestro.qwen.client import MessageHandlers, QwenClientConfig, QwenClient
    from maestro.qwen.server import QwenInitMessage, QwenConversationMessage, QwenToolGroup, QwenStatusUpdate, QwenInfoMessage, QwenErrorMessage, QwenCompletionStats
    import threading
    import json
    import sys
    import time

    # Create client directly instead of using the manager
    client_config = QwenClientConfig()
    client_config.qwen_executable = str(qwen_script)
    client_config.qwen_args = ["--server-mode", "stdin"]
    client_config.verbose = verbose

    client = QwenClient(client_config)

    # Set up message handlers for streaming output
    handlers = MessageHandlers()

    # Track streaming state
    current_streaming_id = None
    current_streaming_buffer = ""

    def handle_init(msg: QwenInitMessage):
        nonlocal current_streaming_id, current_streaming_buffer
        if verbose:
            print(f"Connected to Qwen service. Version: {msg.version}, Model: {msg.model}")

    def handle_conversation(msg: QwenConversationMessage):
        nonlocal current_streaming_id, current_streaming_buffer
        if msg.role == 'user':
            # Print user message
            print(f"\nYou: {msg.content}")
            print()  # Add a blank line after user input
        elif msg.role == 'assistant':
            if msg.isStreaming:
                # Handle streaming responses
                if current_streaming_id != msg.id:
                    # New streaming response
                    if current_streaming_id is not None:
                        # Finish previous streaming if needed
                        print()  # New line after previous response
                    current_streaming_id = msg.id
                    current_streaming_buffer = ""
                    print(f"AI: ", end="", flush=True)

                # Append to current streaming buffer and print
                current_streaming_buffer += msg.content
                print(msg.content, end="", flush=True)
            else:
                # Non-streaming or end of streaming
                if current_streaming_id == msg.id and current_streaming_buffer:
                    # This is the end of a streaming response
                    print()  # New line after response
                    current_streaming_id = None
                    current_streaming_buffer = ""
                    streaming_active.clear()  # Clear flag when streaming ends
                elif msg.content:  # Non-streaming response
                    print(f"AI: {msg.content}")
                    print()  # Add a blank line after AI response
        else:
            # System messages
            print(f"[System]: {msg.content}")
            print()

    def handle_tool_group(group: QwenToolGroup):
        # Calculate terminal width for the box
        import os
        try:
            terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        except OSError:
            # Handle case where we're not connected to a terminal (e.g. piped input)
            terminal_width = 80
        # Limit the box width to 80% of terminal width, but minimum 60
        box_width = max(min(int(terminal_width * 0.9), 120), 60)

        # Print the top border
        print("╭" + "─" * (box_width - 2) + "╮")

        # Print tool information
        for tool in group.tools:
            # Extract command from args if available
            command = ''
            description = f'{tool.tool_name} execution'

            if tool.args and isinstance(tool.args, dict):
                command = tool.args.get('command', '')
                description = tool.args.get('description', f'{tool.tool_name} execution')

            # Create a summary line for the tool
            tool_summary = f"✓  {tool.tool_name} {command} ({description})"
            # Truncate if too long
            if len(tool_summary) > box_width - 4:  # -4 for borders and padding
                tool_summary = tool_summary[:box_width - 7] + "..."

            print(f"│ {tool_summary:<{box_width - 3}}│")  # -3 for border and padding

        # Print an empty line inside the box if there are results
        has_results = any(tool.result for tool in group.tools)
        if has_results:
            print("│" + " " * (box_width - 2) + "│")

        # If the tool has results, print them inside the box
        for tool in group.tools:
            if tool.result is not None:
                # Format the tool result, adding it inside the box
                result_str = str(tool.result)
                lines = result_str.split('\n')
                for line in lines:
                    # Truncate lines that are too long
                    if len(line) > box_width - 4:  # -4 for borders and padding
                        line = line[:box_width - 7] + "..."
                    print(f"│ {line:<{box_width - 3}}│")  # -3 for border and padding

        # Print the bottom border
        print("╰" + "─" * (box_width - 2) + "╯")
        print()  # Add a blank line after the box

    def handle_status(msg: QwenStatusUpdate):
        if verbose:
            print(f"[Status: {msg.state}] {msg.message or ''}")
            print()

    def handle_info(msg: QwenInfoMessage):
        if verbose:
            print(f"[Info] {msg.message}")
            print()

    def handle_error(msg: QwenErrorMessage):
        print(f"[Error] {msg.message}")
        print()

    def handle_completion_stats(stats: QwenCompletionStats):
        if verbose:
            print(f"[Stats] {stats.duration or ''} | Prompt: {stats.prompt_tokens or 0}, Completion: {stats.completion_tokens or 0}")
            print()

    # Set up the handlers
    handlers.on_init = handle_init
    handlers.on_conversation = handle_conversation
    handlers.on_tool_group = handle_tool_group
    handlers.on_status = handle_status
    handlers.on_info = handle_info
    handlers.on_error = handle_error
    handlers.on_completion_stats = handle_completion_stats

    # Apply handlers to the client
    client.set_handlers(handlers)

    # Start the client
    if not client.start():
        print("Error: Failed to start Qwen client")
        return 1

    # Wait for initialization
    time.sleep(0.5)

    # Print initial instructions after connection
    print("Qwen is ready! You can start chatting now.")
    print("Send messages directly, for example:")
    print('Hello, Qwen!')
    print()
    print("Type 'exit' or 'quit' to stop.")
    print()

    # Send initial prompt if provided
    if initial_prompt:
        client.send_user_input(initial_prompt)

    # Global flag to indicate when streaming is active
    streaming_active = threading.Event()

    # Update the conversation handler to manage the streaming flag
    original_handle_conversation = handle_conversation
    def enhanced_handle_conversation(msg: QwenConversationMessage):
        nonlocal current_streaming_id, current_streaming_buffer
        if msg.role == 'assistant':
            if msg.isStreaming:
                streaming_active.set()  # Set flag when streaming starts
            else:
                # Only clear the flag if this is the end of a streaming response
                if current_streaming_id is not None and current_streaming_buffer:
                    streaming_active.clear()  # Clear flag when streaming ends
                    current_streaming_id = None
                    current_streaming_buffer = ""

        original_handle_conversation(msg)

    # Update the handler
    handlers.on_conversation = enhanced_handle_conversation

    # Start a thread to handle user input
    def input_thread():
        try:
            while client.is_running():
                try:
                    # Wait for any previous streaming to finish before showing the prompt
                    while streaming_active.is_set() and client.is_running():
                        time.sleep(0.1)  # Small delay to avoid busy waiting
                    user_input = input(">>> ").strip()
                    if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                        print("\nExiting...")
                        client.stop()
                        break
                    if user_input:
                        client.send_user_input(user_input)
                        # Now wait for the response to finish before continuing
                        while streaming_active.is_set() and client.is_running():
                            time.sleep(0.1)  # Wait for response to finish
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nExiting...")
                    client.stop()
                    break
        except Exception as e:
            if client.is_running():
                print(f"Error in input thread: {e}")

    input_thread = threading.Thread(target=input_thread, daemon=True)
    input_thread.start()

    try:
        # Keep the main thread alive
        while client.is_running():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        client.stop()
        input_thread.join(timeout=1)

    return 0


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
