"""Subprocess runner for AI engines."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List


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
    argv: List[str],
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    stream: bool = False,
    stream_json: bool = False,
    quiet: bool = False
) -> RunResult:
    """
    Run an AI engine command via subprocess.
    
    Args:
        argv: Command arguments
        cwd: Working directory
        env: Environment variables to set
        stdin_text: Text to send to stdin (optional)
        stream: Whether to stream output to stdout
        stream_json: Whether to parse session IDs from JSON output
        quiet: Whether to suppress streaming output
    
    Returns:
        RunResult with exit code, stdout, stderr, and optionally session ID
    """
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
            # Look for session ID in the output (implementation depends on actual engine output format)
            # For now, just a placeholder - actual parsing would depend on the specific engine output
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