"""AI discussion system package."""

from .discussion import (
    Discussion,
    DiscussionContext,
    DiscussionMode,
    DiscussionResult,
    build_phase_context,
    build_task_context,
    build_track_context,
)
from .editor import EditorDiscussion
from .terminal import TerminalDiscussion
from .actions import ActionProcessor, ActionResult, extract_json_actions
from .client import AIClient, ExternalCommandClient
from .manager import AiEngineManager
from .chat import run_interactive_chat, run_one_shot
from .types import AiEngineName, PromptRef, RunOpts, AiEngineSpec, AiRunResult
from .runner import run_engine_command, RunResult

__all__ = [
    "Discussion",
    "DiscussionContext",
    "DiscussionMode",
    "DiscussionResult",
    "EditorDiscussion",
    "TerminalDiscussion",
    "ActionProcessor",
    "ActionResult",
    "extract_json_actions",
    "AIClient",
    "ExternalCommandClient",
    "build_track_context",
    "build_phase_context",
    "build_task_context",
    "AiEngineManager",
    "run_interactive_chat",
    "run_one_shot",
    "run_engine_command",
    "RunResult",
    "AiEngineName",
    "PromptRef",
    "RunOpts",
    "AiEngineSpec",
    "AiRunResult",
]