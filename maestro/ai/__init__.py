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
from .contracts import (
    ContractType,
    TrackContract,
    PhaseContract,
    TaskContract,
    GlobalContract,
)
from .manager import AiEngineManager
from .chat import run_interactive_chat, run_one_shot
from .types import AiEngineName, PromptRef, RunOpts, AiEngineSpec, AiRunResult
from .runner import run_engine_command, RunResult
from .discuss_router import DiscussionRouter, JsonContract, PatchOperation, PatchOperationType
from .session_manager import AISessionManager, extract_session_id

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
    "ContractType",
    "TrackContract",
    "PhaseContract",
    "TaskContract",
    "GlobalContract",
    "AiEngineManager",
    "run_interactive_chat",
    "run_one_shot",
    "run_engine_command",
    "RunResult",
    "DiscussionRouter",
    "JsonContract",
    "PatchOperation",
    "PatchOperationType",
    "AiEngineName",
    "PromptRef",
    "RunOpts",
    "AiEngineSpec",
    "AiRunResult",
    "AISessionManager",
    "extract_session_id",
]