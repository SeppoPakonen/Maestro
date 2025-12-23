"""Codex engine specification."""

from ..types import AiEngineName, EngineCapabilities, PromptRef, RunOpts


def get_spec():
    """Get the specification for the Codex engine."""
    from ..types import AiEngineSpec

    class CodexEngineSpec:
        name: AiEngineName = "codex"
        binary = "codex"
        capabilities = EngineCapabilities(
            supports_stdin=True,
            supports_resume=True,
            supports_stream_json=True,
            supports_model_select=True,
            supports_permissions_bypass=True
        )

        def get_config(self):
            return {"binary": "codex", "args": ["exec", "--dangerously-bypass-approvals-and-sandbox"]}

        def build_base_cmd(self, opts: RunOpts) -> list[str]:
            """Build the base command with options."""
            # For resume sessions, the base command is different
            if isinstance(opts.resume, str):
                # If resuming, the base command is just "codex" without "exec"
                cmd = [self.binary]
            else:
                cmd = [self.binary, "exec"]

            # Add dangerous permissions flag if requested
            if opts.dangerously_skip_permissions:
                cmd.append("--dangerously-bypass-approvals-and-sandbox")

            # Add stream-json flag if requested
            if opts.stream_json:
                cmd.append("--json")

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
                # For stdin, no additional args needed as prompt will be piped
                return []
            else:
                # For prompt text, add it as an argument
                return [str(prompt_ref.source)]

        def build_resume_args(self, opts: RunOpts) -> list[str]:
            """Build arguments for resuming a session."""
            if opts.resume is True:
                # If resume is True without a session ID, we can't build resume args
                return []
            elif isinstance(opts.resume, str):
                # If resume is a session ID, use the resume subcommand
                return ["exec", "resume", opts.resume]
            else:
                # If resume is False, don't add resume args
                return []

        def validate(self):
            return True

    return CodexEngineSpec()