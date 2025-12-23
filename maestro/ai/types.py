"""Shared types for the unified AI Engine Manager."""

from dataclasses import dataclass
from typing import Literal, Union, Optional, Callable, Protocol, List
from pathlib import Path


# Define the supported AI engine names
AiEngineName = Literal["qwen", "gemini", "codex", "claude"]


@dataclass
class EngineCapabilities:
    """Capabilities of an AI engine."""
    supports_stdin: bool
    supports_resume: bool
    supports_stream_json: bool
    supports_model_select: bool
    supports_permissions_bypass: bool


@dataclass
class PromptRef:
    """Reference to a prompt - can be text, stdin, or file path."""
    source: Union[str, Path]  # Either the actual prompt text, or a file path
    is_stdin: bool = False    # Whether this refers to stdin


@dataclass
class RunOpts:
    """Options for running an AI engine."""
    dangerously_skip_permissions: bool = False
    continue_latest: bool = False  # Continue the most recent session
    resume_id: Optional[str] = None  # Resume with specific session ID
    stream_json: bool = False
    quiet: bool = False
    model: Optional[str] = None
    extra_args: Optional[list[str]] = None


class AiSubprocessRunner(Protocol):
    """Protocol for AI subprocess runner."""

    def run(self, argv: List[str], *, input_bytes: Optional[bytes] = None) -> 'FakeProcessResult':
        """Run a subprocess command and return the result."""
        ...


@dataclass
class FakeProcessResult:
    """Result of a fake process run."""
    stdout_chunks: List[bytes]
    stderr_chunks: List[bytes]
    returncode: int


class AiEngineSpec(Protocol):
    """Specification of an AI engine - methods as callable placeholders."""

    name: AiEngineName
    binary: str
    capabilities: EngineCapabilities

    # Callable placeholders for engine methods
    get_config: Callable[[], dict]
    build_base_cmd: Callable[[RunOpts], list[str]]
    build_prompt_args: Callable[[PromptRef, RunOpts], list[str]]
    build_resume_args: Callable[[RunOpts], list[str]]
    validate: Callable[[], bool]


@dataclass
class AiRunResult:
    """Result of an AI engine run."""
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    session_id: Optional[str]
    raw_events_count: int
    exit_code: int