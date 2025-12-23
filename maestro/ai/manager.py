"""Unified AI Engine Manager."""

from pathlib import Path
from typing import Optional
from .types import AiEngineName, PromptRef, RunOpts, AiEngineSpec, AiRunResult
from maestro.config.settings import get_settings
from .session_manager import AISessionManager, extract_session_id


class AiEngineManager:
    """Unified manager for all AI engines."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the manager with optional config."""
        self.config_path = config_path
        self.settings = get_settings()
        self.session_manager = AISessionManager()

    def get_engine_spec(self, name: AiEngineName) -> AiEngineSpec:
        """Get the specification for an engine."""
        from .engines import get_spec
        return get_spec(name)

    def build_command(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> list[str]:
        """Build the command to run an engine with the given prompt and options."""
        # Special handling for Qwen transport
        if engine == "qwen":
            return self._build_qwen_command(prompt, opts)

        # For other engines, use the standard spec
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
        cmd.extend(resume_args)
        cmd.extend(prompt_args)

        return cmd

    def _build_qwen_command(self, prompt: PromptRef, opts: RunOpts) -> list[str]:
        """Build command for Qwen engine considering transport settings."""
        # Get the transport mode from settings
        transport_mode = self.settings.ai_qwen_transport  # cmdline, stdio, tcp

        if transport_mode == "cmdline":
            # Use the standard spec for command line mode
            spec = self.get_engine_spec("qwen")

            # Validate capability compatibility
            if prompt.is_stdin and not spec.capabilities.supports_stdin:
                raise ValueError("Qwen engine does not support stdin input")

            # Build the command components
            base_cmd = spec.build_base_cmd(opts)
            resume_args = spec.build_resume_args(opts)
            prompt_args = spec.build_prompt_args(prompt, opts)

            # Combine all command parts
            cmd = base_cmd
            cmd.extend(resume_args)
            cmd.extend(prompt_args)

            return cmd
        else:
            # For stdio/tcp, we don't build a command but will route through the qwen client
            # This will be handled by the runner layer
            raise NotImplementedError(f"Qwen transport mode '{transport_mode}' requires client routing, not command building")

    def explain_command(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> str:
        """Return a human-readable explanation of the command that would be built."""
        # Special handling for Qwen transport
        if engine == "qwen":
            transport_mode = self.settings.ai_qwen_transport
            if transport_mode in ["stdio", "tcp"]:
                return f"Qwen engine will use {transport_mode} transport mode (via internal client adapter)"

        spec = self.get_engine_spec(engine)
        try:
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

            if opts.continue_latest:
                explanation.append("  Continue latest session enabled")

            if opts.resume_id:
                explanation.append(f"  Resume with session ID: {opts.resume_id}")

            if prompt.is_stdin:
                explanation.append("  Prompt input: stdin")
            else:
                explanation.append(f"  Prompt input: direct argument")

            return "\n".join(explanation)
        except NotImplementedError as e:
            return str(e)

    def run_once(self, engine: AiEngineName, prompt: PromptRef, opts: RunOpts) -> AiRunResult:
        """Run an engine once with the given prompt and options."""
        from .runner import run_engine_command

        # Build the command
        cmd = self.build_command(engine, prompt, opts)

        # Run the command
        result = run_engine_command(
            engine=engine,
            argv=cmd,
            stdin_text=prompt.source if prompt.is_stdin else None,
            stream=not opts.quiet,
            stream_json=opts.stream_json,
            quiet=opts.quiet
        )

        # Extract session ID from the result
        session_id = result.session_id
        if not session_id and result.parsed_events:
            session_id = extract_session_id(engine, result.parsed_events)

        # Update session manager if a session ID was found
        if session_id:
            self.session_manager.update_session(
                engine=engine,
                session_id=session_id,
                model=opts.model,
                danger_mode=opts.dangerously_skip_permissions
            )

        # Create and return the result
        return AiRunResult(
            stdout_path=result.stdout_path,
            stderr_path=result.stderr_path,
            session_id=session_id,
            raw_events_count=len(result.parsed_events),
            exit_code=result.exit_code
        )