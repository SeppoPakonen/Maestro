"""Claude engine specification."""

from ..types import AiEngineName, EngineCapabilities, PromptRef, RunOpts


def get_spec():
    """Get the specification for the Claude engine."""
    from ..types import AiEngineSpec

    class ClaudeEngineSpec:
        name: AiEngineName = "claude"
        binary = "claude"
        capabilities = EngineCapabilities(
            supports_stdin=False,  # Claude does not support stdin
            supports_resume=True,
            supports_stream_json=True,
            supports_model_select=True,
            supports_permissions_bypass=True
        )

        def get_config(self):
            return {"binary": "claude", "args": ["--print", "--output-format", "text", "--permission-mode", "bypassPermissions"]}

        def build_base_cmd(self, opts: RunOpts) -> list[str]:
            """Build the base command with options."""
            cmd = [self.binary]

            # Add dangerous permissions flag if requested
            if opts.dangerously_skip_permissions:
                cmd.append("--allow-dangerously-skip-permissions")  # Use the allow flag as specified

            # Add stream-json flag if requested
            if opts.stream_json:
                cmd.extend(["--output-format", "stream-json", "--include-partial-messages"])

            # Add quiet flag if requested
            if opts.quiet:
                cmd.append("--quiet")

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
                # Claude does not support stdin, so this should raise an error
                raise ValueError("Claude engine does not support stdin input")
            else:
                # For prompt text, add it as an argument
                return [str(prompt_ref.source)]

        def build_resume_args(self, opts: RunOpts) -> list[str]:
            """Build arguments for resuming a session."""
            args = []

            # For claude, use -c for continue latest or -r for resume with ID
            if opts.continue_latest:
                args.extend(["-c"])  # Continue most recent session
            elif opts.resume_id:
                args.extend(["-r", opts.resume_id])  # Resume with specific session ID

            return args

        def validate(self):
            return True

    return ClaudeEngineSpec()