"""Chat interface for the unified AI Engine Manager."""

from .manager import AiEngineManager
from .types import AiEngineName
from typing import Optional


def run_interactive_chat(
    manager: AiEngineManager, 
    engine: AiEngineName, 
    initial_prompt: Optional[str] = None
) -> None:
    """
    Run an interactive chat session with the specified engine.
    
    This will wrap or extend the existing chat functionality.
    """
    # Placeholder implementation - will be connected to existing chat loop later
    print(f"Starting interactive chat with {engine} engine")
    if initial_prompt:
        print(f"Initial prompt: {initial_prompt}")
    # This will eventually connect to the existing discussion loop in maestro/ai/discussion.py


def run_one_shot(
    manager: AiEngineManager,
    engine: AiEngineName,
    prompt: str
) -> None:
    """
    Run a one-shot query with the specified engine.
    """
    # Placeholder implementation
    print(f"Running one-shot query with {engine} engine")
    print(f"Prompt: {prompt}")