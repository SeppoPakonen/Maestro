"""Qwen engine specification."""

from ..types import AiEngineName, EngineCapabilities, PromptRef, RunOpts


def get_spec():
    """Get the specification for the Qwen engine."""
    from ..types import AiEngineSpec

    class QwenEngineSpec:
        name: AiEngineName = "qwen"
        binary = "qwen"
        capabilities = EngineCapabilities(
            supports_stdin=True,
            supports_resume=True,
            supports_stream_json=True,
            supports_model_select=True,
            supports_permissions_bypass=True
        )

        def get_config(self):
            return {"binary": "qwen", "args": ["--yolo"]}

        def build_base_cmd(self, opts: RunOpts) -> list[str]:
            """Build the base command with options."""
            cmd = [self.binary]

            # Add dangerous permissions flag if requested
            if opts.dangerously_skip_permissions:
                cmd.append("-y")  # --yolo

            # Add stream-json flag if requested
            if opts.stream_json:
                cmd.extend(["-o", "stream-json"])

            # Note: qwen doesn't support --quiet flag, so we skip it
            # if opts.quiet:
            #     cmd.append("--quiet")

            # Add model selection if specified
            if opts.model:
                cmd.extend(["--model", opts.model])

            # Add extra args if provided
            if opts.extra_args:
                cmd.extend(opts.extra_args)

            return cmd

        def build_prompt_args(self, prompt_ref: PromptRef, opts: RunOpts) -> list[str]:
            """Build arguments for the prompt."""
            if prompt_ref.is_stdin:
                # For stdin, no additional args needed as prompt will be piped
                return []
            else:
                # For prompt text, add it as an argument
                return [str(prompt_ref.source)]

        def build_resume_args(self, opts: RunOpts) -> list[str]:
            """Build arguments for resuming a session."""
            args = []

            # Add continue_latest flag if requested
            if opts.continue_latest:
                args.extend(["-c"])  # Continue most recent session

            # Add resume_id flag if specified
            if opts.resume_id:
                args.extend(["-c", opts.resume_id])  # Resume with specific session ID

            return args

        def validate(self):
            return True

    return QwenEngineSpec()