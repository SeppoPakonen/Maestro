"""Unified AI Engine Manager."""

from pathlib import Path
from typing import Optional
from .types import AiEngineName, PromptRef, RunOpts, AiEngineSpec, AiRunResult, AiSubprocessRunner
from maestro.config.settings import get_settings
from .session_manager import AISessionManager, extract_session_id


class AiEngineManager:
    """Unified manager for all AI engines."""

    def __init__(self, config_path: Optional[Path] = None, runner: Optional[AiSubprocessRunner] = None):
        """Initialize the manager with optional config and runner."""
        self.config_path = config_path
        self.settings = get_settings()
        self.session_manager = AISessionManager()
        self.runner = runner  # Store the runner for use in run_once

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
        from ..modules.utils import print_info, Colors

        # Build the command
        cmd = self.build_command(engine, prompt, opts)

        # In verbose mode, print engine invocation header
        if opts.verbose:
            print_info(f"AI Engine: {engine}", 2)
            spec = self.get_engine_spec(engine)
            print_info(f"Binary: {spec.binary}", 2)
            print_info(f"Arguments: {' '.join(cmd)}", 2)
            if prompt.is_stdin:
                print_info("Input: stdin", 2)
            else:
                print_info(f"Input: direct argument", 2)
            if opts.model:
                print_info(f"Model: {opts.model}", 2)
            if opts.dangerously_skip_permissions:
                print_info("Danger mode: enabled", 2)

            # Show resume information
            if opts.continue_latest and opts.resume_id:
                print_info(f"Resume: -c {opts.resume_id}", 2)  # Using specific session ID with -c
            elif opts.continue_latest:
                print_info("Resume: -c", 2)  # Using latest with -c
            elif opts.resume_id:
                print_info(f"Resume: -c {opts.resume_id}", 2)  # Using specific session ID with -c for Qwen
            else:
                print_info("Resume: none (starting new session)", 2)

            print_info("Starting engine execution...", 2)

        # Run the command with the optional runner
        start_time = __import__('time').time()
        result = run_engine_command(
            engine=engine,
            argv=cmd,
            stdin_text=prompt.source if prompt.is_stdin else None,
            stream=not opts.quiet,
            stream_json=opts.stream_json,
            quiet=opts.quiet,
            verbose=opts.verbose,  # Pass verbose flag to runner
            runner=self.runner
        )
        end_time = __import__('time').time()
        duration = end_time - start_time

        # In verbose mode, print engine result footer
        if opts.verbose:
            print_info(f"Engine execution completed (exit code: {result.exit_code}, duration: {duration:.2f}s)", 2)
            if result.stdout_path:
                print_info(f"Output saved to: {result.stdout_path}", 2)
            if result.stderr_path:
                print_info(f"Error output saved to: {result.stderr_path}", 2)
            if result.session_id:
                print_info(f"Session ID: {result.session_id}", 2)

            # Print stderr if there was an error
            if result.exit_code != 0 and result.stderr_path:
                try:
                    with open(result.stderr_path, 'r', encoding='utf-8') as f:
                        stderr_content = f.read()
                        if stderr_content:
                            print_info(f"Stderr excerpt (first 50 lines):", 2)
                            lines = stderr_content.split('\n')[:50]
                            for line in lines:
                                print_info(f"  {line}", 2)
                except Exception as e:
                    print_info(f"Could not read stderr: {str(e)}", 2)

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