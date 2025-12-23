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

        # Validate capability compatibility
        if prompt.is_stdin and not spec.capabilities.supports_stdin:
            raise ValueError(f"{engine} engine does not support stdin input")

        # Build the command components
        base_cmd = spec.build_base_cmd(opts)
        resume_args = spec.build_resume_args(opts)
        prompt_args = spec.build_prompt_args(prompt, opts)

        # Combine all command parts
        cmd = base_cmd

        # Add resume args if applicable
        if resume_args:
            # For some engines like codex, resume completely changes the command structure
            # In this case, we use the resume args as the main command
            if engine == "codex" and isinstance(opts.resume, str):
                # For codex with resume, the command is [codex, exec, resume, session_id, prompt]
                cmd = [spec.binary, "exec", "resume", opts.resume] + prompt_args
            else:
                cmd.extend(resume_args)
                cmd.extend(prompt_args)
        else:
            cmd.extend(prompt_args)

        return cmd

    def explain_command(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> str:
        """Return a human-readable explanation of the command that would be built."""
        spec = self.get_engine_spec(engine)
        cmd = self.build_command(engine, prompt, opts)

        explanation = [
            f"Command for {engine} engine:",
            f"  Full command: {' '.join(cmd)}",
            f"  Binary: {spec.binary}",
            f"  Stdin supported: {spec.capabilities.supports_stdin}",
            f"  Resume supported: {spec.capabilities.supports_resume}",
            f"  Stream JSON supported: {spec.capabilities.supports_stream_json}",
            f"  Model selection supported: {spec.capabilities.supports_model_select}",
            f"  Permissions bypass supported: {spec.capabilities.supports_permissions_bypass}",
        ]

        if opts.dangerously_skip_permissions:
            explanation.append("  Permissions bypass enabled")

        if opts.stream_json:
            explanation.append("  Stream JSON output enabled")

        if opts.model:
            explanation.append(f"  Model specified: {opts.model}")

        if opts.resume:
            if opts.resume is True:
                explanation.append("  Resume requested (without session ID)")
            elif isinstance(opts.resume, str):
                explanation.append(f"  Resume with session ID: {opts.resume}")

        if prompt.is_stdin:
            explanation.append("  Prompt input: stdin")
        else:
            explanation.append(f"  Prompt input: direct argument")

        return "\n".join(explanation)

    def run_once(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> AiRunResult:
        """Run an engine once with the given prompt and options."""
        raise NotImplementedError("Engine execution not implemented yet")