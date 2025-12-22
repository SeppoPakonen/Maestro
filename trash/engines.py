#!/usr/bin/env python3
"""
Engine abstraction for LLM backends.

This module defines the interface and dummy implementations for various LLM engines
used in the orchestrator system.
"""
from dataclasses import dataclass
import json
import os
import subprocess
import sys
from typing import Protocol


# Define symbolic engine names
CODEX_PLANNER = "codex_planner"
CLAUDE_PLANNER = "claude_planner"
QWEN_WORKER = "qwen_worker"
GEMINI_WORKER = "gemini_worker"


@dataclass
class CliEngineConfig:
    """Configuration for CLI-based engines."""
    binary: str              # e.g. "qwen", "gemini", "codex", "claude"
    base_args: list[str]     # flags that are always passed, e.g. ["--output-format", "text"]
    timeout_sec: float = 300 # default timeout
    env: dict[str, str] | None = None  # optional extra environment variables
    use_stdin: bool = False  # whether to send the prompt via stdin instead of argv


@dataclass
class EngineResult:
    """Result from an engine execution, including interruption status."""
    exit_code: int
    stdout: str
    stderr: str
    interrupted: bool = False


@dataclass
class AiRunState:
    """State of an AI task run, including partial results."""
    subtask_id: str
    engine_name: str
    prompt_text: str
    partial_stdout: str = ""
    stdout_file_path: str | None = None
    interrupted: bool = False
    completed: bool = False
    error: str | None = None


import signal


def run_cli_engine(
    config: CliEngineConfig,
    prompt: str,
    debug: bool = False,
    stream_output: bool = False,
) -> EngineResult:
    """
    Run the CLI with the given prompt, with interruptible execution.

    Returns EngineResult with exit_code, stdout_text, stderr_text, and interrupted flag.
    """
    # Build the command
    cmd = [config.binary] + config.base_args
    stdin_data = None

    if config.use_stdin:
        stdin_data = prompt if prompt.endswith("\n") else prompt + "\n"
    else:
        cmd.append(prompt)

    # Debug mode: print the final command
    if debug:
        print(f"[engine-debug] running: {' '.join(cmd)}", file=sys.stderr)

    # Prepare environment
    env = os.environ.copy()
    if config.env:
        env.update(config.env)

    try:
        # Use Popen for interruptible execution
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Send prompt via stdin when requested to avoid CLI argument parsing issues
        if stdin_data is not None:
            try:
                if process.stdin:
                    process.stdin.write(stdin_data)
                    process.stdin.flush()
                    process.stdin.close()
            except BrokenPipeError:
                # If the process exited early, continue to capture stderr for error reporting
                pass

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        interrupted = False

        try:
            # Define color codes locally
            DIM = '\033[2m'  # Dark color
            RESET = '\033[0m'  # Reset to default

            def detect_tool_usage(line):
                """
                Detect if a line contains tool usage (shell commands, builtin stuff).
                """
                import re

                # Patterns for shell commands and tool usage
                patterns = [
                    # Common shell commands
                    r'\$ [^\n]+',  # Lines starting with $ (terminal commands)
                    r'# [^\n]+',  # Comment lines
                    r'\b(ls|cd|pwd|mkdir|rm|cp|mv|cat|echo|grep|find|ps|kill|git|npm|yarn|python|pip|conda|docker|kubectl|make|bash|sh)\b',
                    r'(&&|\|\||;)',  # Command chaining operators
                    r'`[^`]+`',  # Inline code (markdown)
                    r'^\s*(export|set|alias|source|chmod|chown|tar|zip|unzip|which|whereis|man|help)\b',  # More commands
                ]

                # Check if line matches any of the patterns
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        return True

                return False

            if stream_output:
                # Stream output mode: process line by line with tool usage detection and formatting
                for line in process.stdout:
                    # Check if line contains tool usage and format accordingly
                    if detect_tool_usage(line):
                        formatted_line = f"{DIM}{line}{RESET}"
                    else:
                        formatted_line = line
                    sys.stdout.write(formatted_line)
                    sys.stdout.flush()
                    stdout_chunks.append(line)  # Store unformatted version for return
            else:
                # Non-streaming mode: read line by line to allow interruption
                for line in process.stdout:
                    stdout_chunks.append(line)
        except KeyboardInterrupt:
            # Handle interrupt gracefully
            interrupted = True
            print("\n[engine-debug] Received KeyboardInterrupt, stopping AI process...", file=sys.stderr)

            # Send SIGINT to child process
            try:
                process.send_signal(signal.SIGINT)

                # Wait for graceful shutdown for up to 3 seconds
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't exit gracefully
                    process.kill()

            except ProcessLookupError:
                # Process already terminated
                pass
            except Exception as e:
                # If we can't kill the process, just continue
                print(f"[engine-debug] Could not terminate child process: {e}", file=sys.stderr)

            # Read any remaining stderr
            if process.stderr:
                try:
                    stderr_remaining = process.stderr.read()
                    if stderr_remaining:
                        stderr_chunks.append(stderr_remaining)
                except:
                    pass

        # Get final exit code and stderr if not interrupted and process still running
        if not interrupted:
            exit_code = process.wait()
            if process.stderr:
                stderr_text = process.stderr.read()
                if stderr_text:
                    stderr_chunks.append(stderr_text)
        else:
            # Use -1 or 130 to indicate interrupted
            exit_code = 130  # Standard Unix code for Ctrl+C

        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)

        return EngineResult(
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            interrupted=interrupted
        )

    except FileNotFoundError:
        # Return a synthetic non-zero exit code with helpful error message
        return EngineResult(
            exit_code=127,
            stdout="",
            stderr=f"Error: Command '{config.binary}' not found",
            interrupted=False
        )
    except subprocess.TimeoutExpired:
        # Return a non-zero exit code with timeout message
        return EngineResult(
            exit_code=124,
            stdout="",
            stderr=f"Error: Command timed out after {config.timeout_sec} seconds",
            interrupted=False
        )


class EngineError(Exception):
    """Custom exception for engine errors."""
    def __init__(self, name: str, exit_code: int, stderr: str):
        self.name = name
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"{name} failed with exit code {exit_code}: {stderr}")


class Engine(Protocol):
    """
    Protocol defining the interface for LLM engines.
    """
    name: str

    def generate(self, prompt: str) -> str:
        """
        Generate a response based on the given prompt.

        Args:
            prompt: The input prompt string

        Returns:
            The generated response string
        """
        ...


class CodexPlannerEngine:
    """
    Real implementation for the codex planner engine using codex CLI.
    """
    name = CODEX_PLANNER

    def __init__(self, config: CliEngineConfig | None = None, use_json: bool = False, debug: bool = False, stream_output: bool = False):
        self.use_json = use_json
        if config is None:
            base_args = ["exec", "--dangerously-bypass-approvals-and-sandbox"]
            if use_json:
                # For future JSON support, though codex may not support it directly
                pass  # Currently codex just uses exec, no specific JSON format option
            config = CliEngineConfig(
                binary="codex",
                base_args=base_args,
                use_stdin=True  # Pipe prompt to avoid argv parsing issues
            )
        self.config = config
        self.debug = debug
        self.stream_output = stream_output

    def generate(self, prompt: str) -> str:
        """
        Generate a response using the codex CLI in non-interactive mode.

        Args:
            prompt: The input prompt string

        Returns:
            The generated response string from codex CLI

        Raises:
            EngineError: If the codex CLI returns a non-zero exit code
        """
        result = run_cli_engine(self.config, prompt, debug=self.debug, stream_output=self.stream_output)

        if result.interrupted:
            # For planners, if interrupted, we should not update session
            print(f"\n[engine] {self.name} interrupted by user", file=sys.stderr)
            raise KeyboardInterrupt("Engine interrupted by user")

        if result.exit_code != 0:
            raise EngineError(self.name, result.exit_code, result.stderr)

        if self.use_json:
            try:
                # Attempt to parse the response as JSON
                parsed_json = json.loads(result.stdout)
                # For this task, return the original stdout_text as requested
                return result.stdout
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response from {self.name}: {e}")

        return result.stdout


class ClaudePlannerEngine:
    """
    Real implementation for the claude planner engine using claude CLI.
    """
    name = CLAUDE_PLANNER

    def __init__(self, config: CliEngineConfig | None = None, use_json: bool = False, debug: bool = False, stream_output: bool = False):
        self.use_json = use_json
        if config is None:
            base_args = [
                "--print",
                "--output-format",
                "json" if use_json else "text",
                "--permission-mode",
                "bypassPermissions",  # Auto-approve all permissions
            ]
            config = CliEngineConfig(
                binary="claude",
                base_args=base_args,
                use_stdin=True  # Pipe prompt to avoid argv parsing issues
            )
        self.config = config
        self.debug = debug
        self.stream_output = stream_output

    def generate(self, prompt: str) -> str:
        """
        Generate a response using the claude CLI in non-interactive mode.

        Args:
            prompt: The input prompt string

        Returns:
            The generated response string from claude CLI

        Raises:
            EngineError: If the claude CLI returns a non-zero exit code
        """
        result = run_cli_engine(self.config, prompt, debug=self.debug, stream_output=self.stream_output)

        if result.interrupted:
            # For planners, if interrupted, we should not update session
            print(f"\n[engine] {self.name} interrupted by user", file=sys.stderr)
            raise KeyboardInterrupt("Engine interrupted by user")

        if result.exit_code != 0:
            raise EngineError(self.name, result.exit_code, result.stderr)

        if self.use_json:
            try:
                # Attempt to parse the response as JSON
                parsed_json = json.loads(result.stdout)
                # For this task, return the original stdout_text as requested
                return result.stdout
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response from {self.name}: {e}")

        return result.stdout


class QwenWorkerEngine:
    """
    Real implementation for the qwen worker engine using qwen CLI.
    """
    name = QWEN_WORKER

    def __init__(self, config: CliEngineConfig | None = None, debug: bool = False, stream_output: bool = False):
        if config is None:
            config = CliEngineConfig(
                binary="qwen",
                base_args=["--yolo"]  # Auto-approve all permissions
            )
        self.config = config
        self.debug = debug
        self.stream_output = stream_output

    def generate(self, prompt: str) -> str:
        """
        Generate a response using the qwen CLI.

        Args:
            prompt: The input prompt string

        Returns:
            The generated response string from qwen CLI

        Raises:
            EngineError: If the qwen CLI returns a non-zero exit code
        """
        result = run_cli_engine(self.config, prompt, debug=self.debug, stream_output=self.stream_output)

        if result.interrupted:
            # For workers, return the partial result but indicate interruption
            print(f"\n[engine] {self.name} interrupted by user, returning partial result", file=sys.stderr)
            return result.stdout  # Return partial output

        if result.exit_code != 0:
            raise EngineError(self.name, result.exit_code, result.stderr)

        return result.stdout


class GeminiWorkerEngine:
    """
    Real implementation for the gemini worker engine using gemini CLI.
    """
    name = GEMINI_WORKER

    def __init__(self, config: CliEngineConfig | None = None, debug: bool = False, stream_output: bool = False):
        if config is None:
            config = CliEngineConfig(
                binary="gemini",
                base_args=["--approval-mode", "yolo"]  # Auto-approve all permissions
            )
        self.config = config
        self.debug = debug
        self.stream_output = stream_output

    def generate(self, prompt: str) -> str:
        """
        Generate a response using the gemini CLI.

        Args:
            prompt: The input prompt string

        Returns:
            The generated response string from gemini CLI

        Raises:
            EngineError: If the gemini CLI returns a non-zero exit code
        """
        result = run_cli_engine(self.config, prompt, debug=self.debug, stream_output=self.stream_output)

        if result.interrupted:
            # For workers, return the partial result but indicate interruption
            print(f"\n[engine] {self.name} interrupted by user, returning partial result", file=sys.stderr)
            return result.stdout  # Return partial output

        if result.exit_code != 0:
            raise EngineError(self.name, result.exit_code, result.stderr)

        return result.stdout


ALIASES = {
    "codex": "codex_planner",
    "claude": "claude_planner",
    "qwen": "qwen_worker",
    "gemini": "gemini_worker",
}


def get_engine(name: str, debug: bool = False, stream_output: bool = False) -> Engine:
    """
    Registry function to get an engine instance by name.

    Args:
        name: The name of the engine to retrieve (can be direct name or alias)
        debug: Whether to enable debug mode
        stream_output: Whether to stream output to stdout

    Returns:
        An instance of the requested engine
    """
    # Check if the name is a direct engine name first
    direct_engines = {
        CODEX_PLANNER: CodexPlannerEngine(debug=debug, stream_output=stream_output),
        CLAUDE_PLANNER: ClaudePlannerEngine(debug=debug, stream_output=stream_output),
        QWEN_WORKER: QwenWorkerEngine(debug=debug, stream_output=stream_output),  # Uses default config
        GEMINI_WORKER: GeminiWorkerEngine(debug=debug, stream_output=stream_output),
    }

    if name in direct_engines:
        return direct_engines[name]

    # If not a direct name, check if it's an alias
    if name in ALIASES:
        alias_target = ALIASES[name]
        if alias_target in direct_engines:
            return direct_engines[alias_target]

    # If we get here, the name is unknown
    raise KeyError(f"Unknown engine name or alias: {name}")


if __name__ == "__main__":
    # Test block to run each engine and print simulated output
    engines_to_test = [CODEX_PLANNER, CLAUDE_PLANNER, QWEN_WORKER, GEMINI_WORKER]
    test_prompt = "This is a test prompt to verify the engine functionality."

    print("Testing all engines with the same prompt:")
    print(f"Prompt: {test_prompt}")
    print("\nResults:")

    for engine_name in engines_to_test:
        engine = get_engine(engine_name, debug=False, stream_output=False)  # Debug and streaming off for tests
        result = engine.generate(test_prompt)
        print(f"\nEngine: {engine_name}")
        print(f"Output:\n{result}")

    print("\n" + "="*50)
    print("Testing CLI engine helper with echo command:")
    echo_config = CliEngineConfig(
        binary="echo",
        base_args=[],
        timeout_sec=10
    )
    exit_code, stdout, stderr = run_cli_engine(echo_config, test_prompt)
    print(f"Exit code: {exit_code}")
    print(f"Stdout: {stdout.strip()}")
    print(f"Stderr: {stderr}")
    print(f"Prompt in stdout: {test_prompt in stdout}")
