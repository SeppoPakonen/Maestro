"""Unified AI Engine Manager."""

from pathlib import Path
from typing import Optional
from .types import AiEngineName, PromptRef, RunOpts, AiEngineSpec, AiRunResult


class AiEngineManager:
    """Unified manager for all AI engines."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the manager with optional config."""
        self.config_path = config_path

    def get_engine_spec(self, name: AiEngineName) -> AiEngineSpec:
        """Get the specification for an engine."""
        from .engines import get_spec
        return get_spec(name)

    def build_command(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> list[str]:
        """Build the command to run an engine with the given prompt and options."""
        spec = self.get_engine_spec(engine)
        # For now, return a placeholder command - the actual implementation will come later
        return [engine, "--placeholder"]

    def run_once(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> AiRunResult:
        """Run an engine once with the given prompt and options."""
        raise NotImplementedError("Engine execution not implemented yet")