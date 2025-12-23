"""Shared types for the unified AI Engine Manager."""

from dataclasses import dataclass
from typing import Literal, Union, Optional, Callable, Protocol
from pathlib import Path


# Define the supported AI engine names
AiEngineName = Literal["qwen", "gemini", "codex", "claude"]


@dataclass
class PromptRef:
    """Reference to a prompt - can be text, stdin, or file path."""
    source: Union[str, Path]  # Either the actual prompt text, or a file path
    is_stdin: bool = False    # Whether this refers to stdin


@dataclass
class RunOpts:
    """Options for running an AI engine."""
    dangerously_skip_permissions: bool = False
    stream_json: bool = False
    quiet: bool = False
    model: Optional[str] = None
    extra_args: Optional[list[str]] = None
    resume: bool = False


class AiEngineSpec(Protocol):
    """Specification of an AI engine - methods as callable placeholders."""
    
    name: AiEngineName
    
    # Callable placeholders for engine methods
    get_config: Callable[[], dict]
    build_command: Callable[[PromptRef, RunOpts], list[str]]
    validate: Callable[[], bool]


@dataclass
class AiRunResult:
    """Result of an AI engine run."""
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    session_id: Optional[str]
    raw_events_count: int
    exit_code: int