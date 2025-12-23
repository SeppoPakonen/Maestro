"""Subprocess runner for AI engines."""

import os
import signal
import subprocess
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator
from maestro.config.settings import get_settings
from .types import AiSubprocessRunner, FakeProcessResult
from .stream_render import AiStreamEvent, EventType, StreamRenderer


class RunResult:
    """Result of running an AI engine command."""
    def __init__(self,
                 exit_code: int,
                 stdout_text: str,
                 stderr_text: str,
                 session_id: Optional[str] = None,
                 stdout_path: Optional[Path] = None,
                 stderr_path: Optional[Path] = None,
                 events_path: Optional[Path] = None,
                 parsed_events: Optional[list] = None):
        self.exit_code = exit_code
        self.stdout_text = stdout_text
        self.stderr_text = stderr_text
        self.session_id = session_id
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.events_path = events_path
        self.parsed_events = parsed_events or []


def run_engine_command(
    engine: str,
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    runner: Optional[AiSubprocessRunner] = None
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
        verbose: Whether to show parsed JSON events in addition to assistant text
        runner: Optional runner to use for subprocess execution (for testing)

    Returns:
        RunResult with exit code, stdout, stderr, and optionally session ID
    """
    settings = get_settings()

    # Special handling for Qwen with stdio/tcp transport
    if engine == "qwen" and settings.ai_qwen_transport in ["stdio", "tcp"]:
        return _run_qwen_transport(engine, stdin_text, stream, stream_json, quiet, verbose, settings)

    # For all other engines or Qwen with cmdline transport, use subprocess
    # If a custom runner is provided, use it instead of the default subprocess runner
    if runner:
        return _run_with_custom_runner(runner, engine, argv, cwd, env, stdin_text, stream, stream_json, quiet, verbose)
    else:
        return _run_subprocess_command(engine, argv, cwd, env, stdin_text, stream, stream_json, quiet, verbose)


def _run_with_custom_runner(
    runner: AiSubprocessRunner,
    engine: str,
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False,
    verbose: bool = False
) -> RunResult:
    """Run command using a custom runner (for testing purposes)."""
    import tempfile
    from datetime import datetime

    # Create log directories
    log_dir = Path("docs/logs/ai") / engine
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds

    # Create log file paths
    stdout_path = log_dir / f"{timestamp}_stdout.txt"
    stderr_path = log_dir / f"{timestamp}_stderr.txt"
    events_path = log_dir / f"{timestamp}_events.jsonl"

    # Initialize stream renderer
    renderer = StreamRenderer(engine, verbose=verbose)

    # Handle Claude stdin workaround - create a temporary file for stdin content
    temp_file_path = None
    if engine == "claude" and stdin_text:
        # Create a temporary file with the stdin content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='claude_stdin_') as temp_file:
            temp_file.write(stdin_text)
            temp_file_path = temp_file.name
        # Modify the command to use the temp file instead of stdin
        # Replace the last argument (which would be the prompt) with the temp file path
        # This assumes the prompt is passed as the last argument, adjust as needed
        if len(argv) > 0 and not argv[-1].startswith('-'):  # If the last argument is not an option
            argv = argv[:-1]  # Remove the last argument
        # Add the file path as the prompt argument
        argv.extend(["read", f"@{temp_file_path}"])

    try:
        # Prepare input bytes for the runner
        input_bytes = stdin_text.encode('utf-8') if stdin_text and not temp_file_path else None

        # Run the command with the custom runner
        result = runner.run(argv, input_bytes=input_bytes)

        # Convert bytes to string
        stdout_text = b''.join(result.stdout_chunks).decode('utf-8')
        stderr_text = b''.join(result.stderr_chunks).decode('utf-8')

        # Write logs to files
        with open(stdout_path, 'w', encoding='utf-8') as f:
            f.write(stdout_text)

        with open(stderr_path, 'w', encoding='utf-8') as f:
            f.write(stderr_text)

        # Initialize JSON buffer for stream-json parsing
        json_buffer = stdout_text
        parsed_events = _parse_json_events(json_buffer)

        # Render parsed events using the stream renderer
        for raw_event in parsed_events:
            normalized_event = _normalize_event(raw_event, engine)
            renderer.render_event(normalized_event)

        # Write parsed events to JSONL file
        with open(events_path, 'w', encoding='utf-8') as f:
            for event in parsed_events:
                f.write(json.dumps(event) + '\n')

        # Attempt to extract session ID from parsed events
        session_id = None
        if parsed_events:
            session_id = _extract_session_id_from_events(parsed_events)

        # Finalize the renderer
        renderer.finalize(result.returncode)

        return RunResult(
            exit_code=result.returncode,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            session_id=session_id,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            events_path=events_path,
            parsed_events=parsed_events
        )

    finally:
        # Clean up temporary file if created
        if temp_file_path and Path(temp_file_path).exists():
            try:
                Path(temp_file_path).unlink()
            except:
                pass  # Ignore errors when deleting temp file


def _run_subprocess_command(
    engine: str,
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False,
    verbose: bool = False
) -> RunResult:
    """Run command via subprocess with streaming and event parsing."""
    import tempfile
    from datetime import datetime

    # Prepare environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    # Create log directories
    log_dir = Path("docs/logs/ai") / engine
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds

    # Create log file paths
    stdout_path = log_dir / f"{timestamp}_stdout.txt"
    stderr_path = log_dir / f"{timestamp}_stderr.txt"
    events_path = log_dir / f"{timestamp}_events.jsonl"

    # Initialize stream renderer
    renderer = StreamRenderer(engine, verbose=verbose)

    # Handle Claude stdin workaround - create a temporary file for stdin content
    temp_file_path = None
    if engine == "claude" and stdin_text:
        # Create a temporary file with the stdin content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='claude_stdin_') as temp_file:
            temp_file.write(stdin_text)
            temp_file_path = temp_file.name
        # Modify the command to use the temp file instead of stdin
        # Replace the last argument (which would be the prompt) with the temp file path
        # This assumes the prompt is passed as the last argument, adjust as needed
        if len(argv) > 0 and not argv[-1].startswith('-'):  # If the last argument is not an option
            argv = argv[:-1]  # Remove the last argument
        # Add the file path as the prompt argument
        argv.extend(["read", f"@{temp_file_path}"])

    try:
        # Prepare stdin - use DEVNULL if we're using the temp file workaround
        stdin_mode = subprocess.PIPE if stdin_text and not temp_file_path else subprocess.DEVNULL
        stdout_mode = subprocess.PIPE
        stderr_mode = subprocess.PIPE

        # Start the subprocess
        process = subprocess.Popen(
            argv,
            stdin=stdin_mode,
            stdout=stdout_mode,
            stderr=stderr_mode,
            cwd=cwd,
            env=run_env,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        # Initialize variables for capturing output and events
        stdout_lines = []
        stderr_lines = []
        parsed_events = []

        # Initialize JSON buffer for stream-json parsing
        json_buffer = ""

        # Send stdin text if provided and not using temp file workaround
        if stdin_text and not temp_file_path:
            process.stdin.write(stdin_text)
            process.stdin.close()

        # Stream output line by line
        while True:
            # Check if process is still running
            if process.poll() is not None:
                # Process finished, read any remaining output
                try:
                    remaining_stdout = process.stdout.read()
                    remaining_stderr = process.stderr.read()

                    if remaining_stdout:
                        stdout_lines.append(remaining_stdout)
                        # Parse for JSON events if stream_json is enabled
                        if stream_json:
                            # Add to buffer and try to parse JSON lines
                            json_buffer += remaining_stdout
                            # Try to parse JSON events from the buffer
                            new_events = _parse_json_events(json_buffer)
                            for raw_event in new_events:
                                normalized_event = _normalize_event(raw_event, engine)
                                renderer.render_event(normalized_event)
                                parsed_events.append(raw_event)
                            # Keep only unparsed part of the buffer
                            json_buffer = _get_remaining_buffer(json_buffer)

                    if remaining_stderr:
                        stderr_lines.append(remaining_stderr)
                        if stream and not quiet:
                            print(remaining_stderr, end='', file=sys.stderr, flush=True)
                except:
                    # Handle case where streams are already closed
                    pass

                break

            # Read available stdout
            try:
                # Use a non-blocking approach to read output
                import select
                ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

                if process.stdout in ready:
                    line = process.stdout.readline()
                    if line:
                        stdout_lines.append(line)

                        # Parse for JSON events if stream_json is enabled
                        if stream_json:
                            # Add to buffer and try to parse JSON lines
                            json_buffer += line
                            # Try to parse JSON events from the buffer
                            new_events = _parse_json_events(json_buffer)
                            for raw_event in new_events:
                                normalized_event = _normalize_event(raw_event, engine)
                                renderer.render_event(normalized_event)
                                parsed_events.append(raw_event)
                            # Keep only unparsed part of the buffer
                            json_buffer = _get_remaining_buffer(json_buffer)

            except:
                # Handle case where select is not available (e.g., on Windows)
                # Fallback to readline with timeout
                try:
                    import sys
                    if sys.platform == 'win32':
                        # On Windows, we'll read line by line without select
                        line = process.stdout.readline()
                        if line:
                            stdout_lines.append(line)

                            # Parse for JSON events if stream_json is enabled
                            if stream_json:
                                json_buffer += line
                                new_events = _parse_json_events(json_buffer)
                                for raw_event in new_events:
                                    normalized_event = _normalize_event(raw_event, engine)
                                    renderer.render_event(normalized_event)
                                    parsed_events.append(raw_event)
                                json_buffer = _get_remaining_buffer(json_buffer)
                    else:
                        # On Unix systems, if select failed for some reason, just continue
                        pass
                except:
                    pass  # Continue with the loop

            # Read available stderr
            try:
                if sys.platform != 'win32':
                    import select
                    ready, _, _ = select.select([process.stderr], [], [], 0.1)

                    if process.stderr in ready:
                        line = process.stderr.readline()
                        if line:
                            stderr_lines.append(line)

                            # Stream to stderr if requested
                            if stream and not quiet:
                                print(line, end='', file=sys.stderr, flush=True)
                else:
                    # On Windows, handle stderr separately
                    pass
            except:
                # Handle Windows case for stderr
                try:
                    if sys.platform == 'win32':
                        # On Windows, read stderr if possible
                        pass
                except:
                    pass

        # Wait for process to complete
        exit_code = process.wait()

        # Join all output
        stdout_text = ''.join(stdout_lines)
        stderr_text = ''.join(stderr_lines)

        # Write logs to files
        with open(stdout_path, 'w', encoding='utf-8') as f:
            f.write(stdout_text)

        with open(stderr_path, 'w', encoding='utf-8') as f:
            f.write(stderr_text)

        # Write parsed events to JSONL file
        with open(events_path, 'w', encoding='utf-8') as f:
            for event in parsed_events:
                f.write(json.dumps(event) + '\n')

        # Attempt to extract session ID from parsed events
        session_id = None
        if parsed_events:
            session_id = _extract_session_id_from_events(parsed_events)

        # Finalize the renderer
        renderer.finalize(exit_code)

        return RunResult(
            exit_code=exit_code,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            session_id=session_id,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            events_path=events_path,
            parsed_events=parsed_events
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

        # Use renderer for interrupt handling
        renderer.handle_interrupt()

        return RunResult(
            exit_code=130,  # Standard Unix code for Ctrl+C
            stdout_text="",
            stderr_text="Process interrupted by user",
            session_id=renderer.session_id  # Preserve session ID if it was already seen
        )
    finally:
        # Clean up temporary file if created
        if temp_file_path and Path(temp_file_path).exists():
            try:
                Path(temp_file_path).unlink()
            except:
                pass  # Ignore errors when deleting temp file


def _parse_json_events(buffer: str) -> List[Dict[str, Any]]:
    """
    Parse JSON events from a buffer, handling partial JSON and multiple events.
    """
    events = []
    lines = buffer.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try to parse the line as JSON
        try:
            event = json.loads(line)
            events.append(event)
        except json.JSONDecodeError:
            # If it's not valid JSON, it might be a partial line
            # We'll leave it in the buffer for later processing
            continue

    return events


def _get_remaining_buffer(buffer: str) -> str:
    """
    Extract any remaining unparsed content from the buffer.
    """
    lines = buffer.split('\n')
    remaining = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try to parse the line as JSON
        try:
            json.loads(line)
            # If it parses, we've processed it, so we don't keep it
        except json.JSONDecodeError:
            # If it doesn't parse, it's a partial line that should remain in buffer
            remaining.append(line)

    # Return the unparsed content
    if remaining:
        # Return the last unparsed line as it might be a partial JSON
        return remaining[-1]
    else:
        return ""


def _extract_session_id_from_events(events: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract session ID from parsed JSON events.
    """
    for event in events:
        # Look for common session ID patterns in events
        if isinstance(event, dict):
            # Check for various possible session ID field names
            for key in ['session_id', 'sessionId', 'session', 'id']:
                if key in event and event[key]:
                    return str(event[key])

            # Check for session info in nested structures
            if 'metadata' in event and isinstance(event['metadata'], dict):
                for key in ['session_id', 'sessionId', 'session', 'id']:
                    if key in event['metadata'] and event['metadata'][key]:
                        return str(event['metadata'][key])

    return None


def _normalize_event(raw_event: Dict[str, Any], engine: str) -> AiStreamEvent:
    """
    Normalize raw event from AI engine to a standard format.
    """
    # Determine the event type based on the raw event structure
    event_type = EventType.MESSAGE  # Default
    role = None
    text_delta = None
    text_full = None
    session_id = None

    # Common fields across engines
    if 'type' in raw_event:
        raw_type = raw_event['type']
        if raw_type in ['init', 'initialize', 'start']:
            event_type = EventType.INIT
        elif raw_type in ['delta', 'chunk', 'stream']:
            event_type = EventType.DELTA
        elif raw_type in ['message', 'response', 'completion']:
            event_type = EventType.MESSAGE
        elif raw_type in ['result', 'status', 'done']:
            event_type = EventType.RESULT
        elif raw_type in ['error', 'exception']:
            event_type = EventType.ERROR

    # Extract role if present
    if 'role' in raw_event:
        role = raw_event['role']
    elif 'author' in raw_event:
        role = raw_event['author']

    # Extract text content
    if 'content' in raw_event:
        text_full = raw_event['content']
    elif 'text' in raw_event:
        text_full = raw_event['text']
    elif 'delta' in raw_event:
        text_delta = raw_event['delta']

    # Extract session ID
    if 'session_id' in raw_event:
        session_id = raw_event['session_id']
    elif 'sessionId' in raw_event:
        session_id = raw_event['sessionId']
    elif 'session' in raw_event:
        session_id = raw_event['session']

    # Engine-specific normalization
    if engine == 'gemini':
        # Gemini-specific fields
        if 'candidates' in raw_event:
            for candidate in raw_event.get('candidates', []):
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content:
                        for part in content['parts']:
                            if 'text' in part:
                                text_full = part['text']
                                break
        elif 'error' in raw_event:
            event_type = EventType.ERROR
            text_full = str(raw_event['error'])
    elif engine == 'claude':
        # Claude-specific fields
        if 'delta' in raw_event and 'text' in raw_event['delta']:
            text_delta = raw_event['delta']['text']
            event_type = EventType.DELTA
        elif 'message' in raw_event:
            text_full = raw_event['message']
        elif 'error' in raw_event:
            event_type = EventType.ERROR
            text_full = str(raw_event['error'])
    elif engine == 'qwen':
        # Qwen-specific fields
        if 'response' in raw_event:
            text_full = raw_event['response']
        elif 'delta' in raw_event:
            text_delta = raw_event['delta']
            event_type = EventType.DELTA
        elif 'error' in raw_event:
            event_type = EventType.ERROR
            text_full = str(raw_event['error'])
    elif engine == 'codex':
        # Codex-specific fields
        if 'choices' in raw_event:
            for choice in raw_event['choices']:
                if 'text' in choice:
                    text_full = choice['text']
                    break
                elif 'delta' in choice and 'content' in choice['delta']:
                    text_delta = choice['delta']['content']
                    event_type = EventType.DELTA
        elif 'error' in raw_event:
            event_type = EventType.ERROR
            text_full = str(raw_event['error'])

    # Handle generic error case - if type is 'error', use 'message' field
    if raw_event.get('type') == 'error' and 'message' in raw_event:
        event_type = EventType.ERROR
        text_full = str(raw_event['message'])

    # Create and return the normalized event
    return AiStreamEvent(
        type=event_type,
        role=role,
        text_delta=text_delta,
        text_full=text_full,
        session_id=session_id,
        raw=raw_event
    )


def _run_qwen_transport(
    engine: str,
    stdin_text: Optional[str],
    stream: bool,
    stream_json: bool,
    quiet: bool,
    verbose: bool,
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
    from datetime import datetime

    # Initialize stream renderer
    renderer = StreamRenderer(engine, verbose=verbose)

    # Determine transport mode
    transport_mode = settings.ai_qwen_transport
    host = settings.ai_qwen_tcp_host
    port = settings.ai_qwen_tcp_port

    # Create log directories
    log_dir = Path("docs/logs/ai") / engine
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds

    # Create log file paths
    stdout_path = log_dir / f"{timestamp}_stdout.txt"
    stderr_path = log_dir / f"{timestamp}_stderr.txt"
    events_path = log_dir / f"{timestamp}_events.jsonl"

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
            result = RunResult(
                exit_code=0,
                stdout_text="Qwen response via stdio transport",
                stderr_text="",
                session_id="mock-session-id"
            )
        elif transport_mode == "tcp":
            # Use TCP transport
            # In a real implementation, we would connect to the TCP server
            # For now, return a mock result
            result = RunResult(
                exit_code=0,
                stdout_text="Qwen response via TCP transport",
                stderr_text="",
                session_id="mock-session-id"
            )
        else:
            # Should not happen, but just in case
            result = RunResult(
                exit_code=1,
                stdout_text="",
                stderr_text=f"Unknown transport mode: {transport_mode}",
                session_id=None
            )
    except Exception as e:
        result = RunResult(
            exit_code=1,
            stdout_text="",
            stderr_text=f"Error running Qwen transport: {str(e)}",
            session_id=None
        )

    # Finalize the renderer
    renderer.finalize(result.exit_code)

    return result


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