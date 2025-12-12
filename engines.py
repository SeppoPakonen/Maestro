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


def run_cli_engine(
    config: CliEngineConfig,
    prompt: str,
) -> tuple[int, str, str]:
    """
    Run the CLI with the given prompt.

    Returns (exit_code, stdout_text, stderr_text).
    """
    # Build the command
    cmd = [config.binary] + config.base_args + [prompt]

    # Debug mode: print the final command
    print(f"[DEBUG] Running command: {' '.join(cmd)}", file=sys.stderr)

    # Prepare environment
    env = os.environ.copy()
    if config.env:
        env.update(config.env)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout_sec,
            env=env
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        # Return a synthetic non-zero exit code with helpful error message
        return 127, "", f"Error: Command '{config.binary}' not found"
    except subprocess.TimeoutExpired:
        # Return a non-zero exit code with timeout message
        return 124, "", f"Error: Command timed out after {config.timeout_sec} seconds"


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

    def __init__(self, config: CliEngineConfig | None = None, use_json: bool = False):
        self.use_json = use_json
        if config is None:
            base_args = ["exec"]
            if use_json:
                # For future JSON support, though codex may not support it directly
                pass  # Currently codex just uses exec, no specific JSON format option
            config = CliEngineConfig(
                binary="codex",
                base_args=base_args
            )
        self.config = config

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
        exit_code, stdout, stderr = run_cli_engine(self.config, prompt)

        if exit_code != 0:
            raise EngineError(self.name, exit_code, stderr)

        if self.use_json:
            try:
                # Attempt to parse the response as JSON
                parsed_json = json.loads(stdout)
                # For this task, return the original stdout_text as requested
                return stdout
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response from {self.name}: {e}")

        return stdout


class ClaudePlannerEngine:
    """
    Real implementation for the claude planner engine using claude CLI.
    """
    name = CLAUDE_PLANNER

    def __init__(self, config: CliEngineConfig | None = None, use_json: bool = False):
        self.use_json = use_json
        if config is None:
            base_args = ["--print", "--output-format", "json" if use_json else "text",
                         "--permission-mode", "dontAsk"]  # Auto-approve all permissions
            config = CliEngineConfig(
                binary="claude",
                base_args=base_args
            )
        self.config = config

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
        exit_code, stdout, stderr = run_cli_engine(self.config, prompt)

        if exit_code != 0:
            raise EngineError(self.name, exit_code, stderr)

        if self.use_json:
            try:
                # Attempt to parse the response as JSON
                parsed_json = json.loads(stdout)
                # For this task, return the original stdout_text as requested
                return stdout
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response from {self.name}: {e}")

        return stdout


class QwenWorkerEngine:
    """
    Real implementation for the qwen worker engine using qwen CLI.
    """
    name = QWEN_WORKER

    def __init__(self, config: CliEngineConfig | None = None):
        if config is None:
            config = CliEngineConfig(
                binary="qwen",
                base_args=["--yolo"]  # Auto-approve all permissions
            )
        self.config = config

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
        exit_code, stdout, stderr = run_cli_engine(self.config, prompt)

        if exit_code != 0:
            raise EngineError(self.name, exit_code, stderr)

        return stdout


class GeminiWorkerEngine:
    """
    Real implementation for the gemini worker engine using gemini CLI.
    """
    name = GEMINI_WORKER

    def __init__(self, config: CliEngineConfig | None = None):
        if config is None:
            config = CliEngineConfig(
                binary="gemini",
                base_args=["--approval-mode", "yolo"]  # Auto-approve all permissions
            )
        self.config = config

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
        exit_code, stdout, stderr = run_cli_engine(self.config, prompt)

        if exit_code != 0:
            raise EngineError(self.name, exit_code, stderr)

        return stdout


ALIASES = {
    "codex": "codex_planner",
    "claude": "claude_planner",
    "qwen": "qwen_worker",
    "gemini": "gemini_worker",
}


def get_engine(name: str) -> Engine:
    """
    Registry function to get an engine instance by name.

    Args:
        name: The name of the engine to retrieve (can be direct name or alias)

    Returns:
        An instance of the requested engine
    """
    # Check if the name is a direct engine name first
    direct_engines = {
        CODEX_PLANNER: CodexPlannerEngine(),
        CLAUDE_PLANNER: ClaudePlannerEngine(),
        QWEN_WORKER: QwenWorkerEngine(),  # Uses default config
        GEMINI_WORKER: GeminiWorkerEngine(),
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
        engine = get_engine(engine_name)
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