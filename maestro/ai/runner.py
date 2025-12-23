"""Subprocess runner for AI engines."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from maestro.config.settings import get_settings


class RunResult:
    """Result of running an AI engine command."""
    def __init__(self,
                 exit_code: int,
                 stdout_text: str,
                 stderr_text: str,
                 session_id: Optional[str] = None,
                 stdout_path: Optional[Path] = None,
                 stderr_path: Optional[Path] = None):
        self.exit_code = exit_code
        self.stdout_text = stdout_text
        self.stderr_text = stderr_text
        self.session_id = session_id
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path


def run_engine_command(
    engine: str,
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False
) -> RunResult:
    """
    Run an AI engine command via subprocess or internal client (for Qwen transport).

    Args:
        engine: Name of the engine (e.g., 'qwen', 'gemini', etc.)
        argv: Command arguments (for subprocess mode)
        cwd: Working directory
        env: Environment variables to set
        stdin_text: Text to send to stdin (optional)
        stream: Whether to stream output to stdout
        stream_json: Whether to parse session IDs from JSON output
        quiet: Whether to suppress streaming output

    Returns:
        RunResult with exit code, stdout, stderr, and optionally session ID
    """
    settings = get_settings()

    # Special handling for Qwen with stdio/tcp transport
    if engine == "qwen" and settings.ai_qwen_transport in ["stdio", "tcp"]:
        return _run_qwen_transport(engine, stdin_text, stream, stream_json, quiet, settings)

    # For all other engines or Qwen with cmdline transport, use subprocess
    return _run_subprocess_command(argv, cwd, env, stdin_text, stream, stream_json, quiet)


def _run_subprocess_command(
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False
) -> RunResult:
    """Run command via subprocess."""
    # Prepare environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    # Prepare stdin
    stdin_mode = subprocess.PIPE if stdin_text else subprocess.DEVNULL
    stdout_mode = subprocess.PIPE
    stderr_mode = subprocess.PIPE

    try:
        # Start the subprocess
        process = subprocess.Popen(
            argv,
            stdin=stdin_mode,
            stdout=stdout_mode,
            stderr=stderr_mode,
            cwd=cwd,
            env=run_env,
            text=True
        )

        # Send stdin text if provided
        if stdin_text:
            stdout_data, stderr_data = process.communicate(input=stdin_text)
        else:
            stdout_data, stderr_data = process.communicate()

        exit_code = process.returncode

        # If streaming is enabled, output the results
        if stream and not quiet:
            print(stdout_data, end='')
            if stderr_data:
                print(stderr_data, end='', file=sys.stderr)

        # Attempt to parse session ID if stream_json mode is enabled
        session_id = None
        if stream_json:
            session_id = _parse_session_id(stdout_data)

        return RunResult(
            exit_code=exit_code,
            stdout_text=stdout_data,
            stderr_text=stderr_data,
            session_id=session_id
        )

    except FileNotFoundError:
        return RunResult(
            exit_code=127,
            stdout_text="",
            stderr_text=f"Command not found: {argv[0]}",
            session_id=None
        )
    except KeyboardInterrupt:
        # Handle Ctrl+C: terminate child process cleanly
        try:
            process.send_signal(signal.SIGTERM)
            # Give it a moment to terminate gracefully
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                process.kill()
                process.wait()
        except:
            pass  # Process might already be terminated

        return RunResult(
            exit_code=130,  # Standard Unix code for Ctrl+C
            stdout_text="",
            stderr_text="Process interrupted by user",
            session_id=None
        )


def _run_qwen_transport(
    engine: str,
    stdin_text: Optional[str],
    stream: bool,
    stream_json: bool,
    quiet: bool,
    settings
) -> RunResult:
    """
    Run Qwen using the internal client for stdio/tcp transport.
    """
    from maestro.qwen.main import QwenManager
    from maestro.qwen.server import create_qwen_server
    import tempfile
    import json
    import time
    import threading

    # Determine transport mode
    transport_mode = settings.ai_qwen_transport
    host = settings.ai_qwen_tcp_host
    port = settings.ai_qwen_tcp_port

    try:
        if transport_mode == "stdio":
            # Use stdio transport
            server = create_qwen_server('stdin')

            # Send the prompt
            if stdin_text:
                user_input = {"type": "user_input", "content": stdin_text}
                server.send_message(user_input)

            # For now, return a mock result - in a real implementation,
            # we would handle the communication properly
            return RunResult(
                exit_code=0,
                stdout_text="Qwen response via stdio transport",
                stderr_text="",
                session_id="mock-session-id"
            )
        elif transport_mode == "tcp":
            # Use TCP transport
            # In a real implementation, we would connect to the TCP server
            # For now, return a mock result
            return RunResult(
                exit_code=0,
                stdout_text="Qwen response via TCP transport",
                stderr_text="",
                session_id="mock-session-id"
            )
        else:
            # Should not happen, but just in case
            return RunResult(
                exit_code=1,
                stdout_text="",
                stderr_text=f"Unknown transport mode: {transport_mode}",
                session_id=None
            )
    except Exception as e:
        return RunResult(
            exit_code=1,
            stdout_text="",
            stderr_text=f"Error running Qwen transport: {str(e)}",
            session_id=None
        )


def _parse_session_id(output: str) -> Optional[str]:
    """
    Parse session ID from engine output.
    This is a placeholder implementation - actual parsing would depend on
    the specific engine output format.
    """
    # Example: Look for patterns like "Session ID: abc123" or similar
    # Actual implementation would need to match the real engine output format
    lines = output.split('\n')
    for line in lines:
        # This is just a placeholder - would need to match real engine output
        if 'session' in line.lower() and ':' in line:
            parts = line.split(':')
            if len(parts) > 1:
                session_id = parts[1].strip()
                if session_id:  # If we found something that looks like an ID
                    return session_id
    return None