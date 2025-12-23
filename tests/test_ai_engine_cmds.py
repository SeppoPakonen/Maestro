"""Unit tests for AI engine command construction."""

import pytest
from maestro.ai.types import PromptRef, RunOpts
from maestro.ai.manager import AiEngineManager


class TestEngineDangerMode:
    """Test danger mode flag inclusion/exclusion for each engine."""

    def test_qwen_danger_mode_on_off(self):
        """Test Qwen danger mode on/off."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # Danger mode off - no flag
        opts = RunOpts(dangerously_skip_permissions=False)
        cmd = manager.build_command("qwen", prompt, opts)
        assert "-y" not in cmd

        # Danger mode on - includes flag
        opts = RunOpts(dangerously_skip_permissions=True)
        cmd = manager.build_command("qwen", prompt, opts)
        assert "-y" in cmd

    def test_gemini_danger_mode_on_off(self):
        """Test Gemini danger mode on/off."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # Danger mode off - no flag
        opts = RunOpts(dangerously_skip_permissions=False)
        cmd = manager.build_command("gemini", prompt, opts)
        assert "-y" not in cmd

        # Danger mode on - includes flag
        opts = RunOpts(dangerously_skip_permissions=True)
        cmd = manager.build_command("gemini", prompt, opts)
        assert "-y" in cmd

    def test_codex_danger_mode_on_off(self):
        """Test Codex danger mode on/off."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # Danger mode off - no flag
        opts = RunOpts(dangerously_skip_permissions=False)
        cmd = manager.build_command("codex", prompt, opts)
        assert "--dangerously-bypass-approvals-and-sandbox" not in cmd

        # Danger mode on - includes flag
        opts = RunOpts(dangerously_skip_permissions=True)
        cmd = manager.build_command("codex", prompt, opts)
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd

    def test_claude_danger_mode_on_off(self):
        """Test Claude danger mode on/off."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # Danger mode off - no flag
        opts = RunOpts(dangerously_skip_permissions=False)
        cmd = manager.build_command("claude", prompt, opts)
        assert "--allow-dangerously-skip-permissions" not in cmd

        # Danger mode on - includes flag
        opts = RunOpts(dangerously_skip_permissions=True)
        cmd = manager.build_command("claude", prompt, opts)
        assert "--allow-dangerously-skip-permissions" in cmd


class TestEngineResumeSession:
    """Test resume vs new session command construction."""

    def test_qwen_resume_vs_new(self):
        """Test Qwen resume vs new session."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # New session command
        opts = RunOpts(continue_latest=False, resume_id=None)
        cmd = manager.build_command("qwen", prompt, opts)
        assert "-c" not in cmd  # Should not have continue flag

        # Resume with latest - should include -c flag but keep original prompt
        opts = RunOpts(continue_latest=True, resume_id=None)
        cmd = manager.build_command("qwen", prompt, opts)
        assert "-c" in cmd  # Should have continue flag
        assert "Hello" in cmd  # Should still have original prompt

        # Resume with specific session ID - includes both session ID and original prompt
        opts = RunOpts(continue_latest=False, resume_id="session123")
        cmd = manager.build_command("qwen", prompt, opts)
        assert "-c" in cmd  # Should have continue flag
        assert "session123" in cmd  # Should have the specific session ID
        assert "Hello" in cmd  # Original prompt should also be included

    def test_gemini_resume_vs_new(self):
        """Test Gemini resume vs new session."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # New session command
        opts = RunOpts(continue_latest=False, resume_id=None)
        cmd = manager.build_command("gemini", prompt, opts)
        assert "-r" not in cmd  # Should not have resume flag

        # Resume with latest
        opts = RunOpts(continue_latest=True, resume_id=None)
        cmd = manager.build_command("gemini", prompt, opts)
        assert "-r" in cmd  # Should have resume flag
        assert "latest" in cmd  # Should have latest keyword

        # Resume with specific session ID
        opts = RunOpts(continue_latest=False, resume_id="session123")
        cmd = manager.build_command("gemini", prompt, opts)
        assert "-r" in cmd  # Should have resume flag
        assert "session123" in cmd  # Should have the specific session ID

    def test_codex_resume_vs_new(self):
        """Test Codex resume vs new session."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # New session command
        opts = RunOpts(continue_latest=False, resume_id=None)
        cmd = manager.build_command("codex", prompt, opts)
        # Should not have resume-specific flags
        assert "resume" not in cmd or cmd[cmd.index("resume") - 1] != "exec"

        # Resume with latest
        opts = RunOpts(continue_latest=True, resume_id=None)
        cmd = manager.build_command("codex", prompt, opts)
        assert "resume" in cmd  # Should have resume subcommand
        assert "--last" in cmd  # Should have --last flag

        # Resume with specific session ID
        opts = RunOpts(continue_latest=False, resume_id="session123")
        cmd = manager.build_command("codex", prompt, opts)
        assert "resume" in cmd  # Should have resume subcommand
        assert "session123" in cmd  # Should have the specific session ID

    def test_claude_resume_vs_new(self):
        """Test Claude resume vs new session."""
        manager = AiEngineManager()
        prompt = PromptRef(source="Hello")

        # New session command
        opts = RunOpts(continue_latest=False, resume_id=None)
        cmd = manager.build_command("claude", prompt, opts)
        assert "-c" not in cmd and "-r" not in cmd  # Should not have continue/resume flags

        # Resume with latest - Claude might not support this
        opts = RunOpts(continue_latest=True, resume_id=None)
        cmd = manager.build_command("claude", prompt, opts)
        # Based on the existing tests, Claude uses -c for continue_latest
        assert "-c" in cmd  # Should have continue flag

        # Resume with specific session ID
        opts = RunOpts(continue_latest=False, resume_id="session123")
        cmd = manager.build_command("claude", prompt, opts)
        assert "-r" in cmd  # Should have resume flag
        assert "session123" in cmd  # Should have the specific session ID


class TestEngineStdinMode:
    """Test stdin mode handling for each engine."""

    def test_qwen_stdin_mode(self):
        """Test Qwen stdin mode."""
        manager = AiEngineManager()
        prompt_stdin = PromptRef(source="", is_stdin=True)

        opts = RunOpts()
        cmd = manager.build_command("qwen", prompt_stdin, opts)
        # Qwen with stdin should not include the prompt in argv
        assert cmd == ["qwen"]  # Just the binary, no prompt argument

    def test_gemini_stdin_mode(self):
        """Test Gemini stdin mode."""
        manager = AiEngineManager()
        prompt_stdin = PromptRef(source="", is_stdin=True)

        opts = RunOpts()
        cmd = manager.build_command("gemini", prompt_stdin, opts)
        # Gemini with stdin should not include the prompt in argv
        assert cmd == ["gemini"]  # Just the binary, no prompt argument

    def test_codex_stdin_mode(self):
        """Test Codex stdin mode."""
        manager = AiEngineManager()
        prompt_stdin = PromptRef(source="", is_stdin=True)

        opts = RunOpts()
        cmd = manager.build_command("codex", prompt_stdin, opts)
        # Codex with stdin should not include the prompt in argv
        assert cmd == ["codex", "exec"]  # Binary and exec, no prompt argument

    def test_claude_stdin_mode(self):
        """Test Claude stdin mode - should be accepted (handled via temp file in runner)."""
        manager = AiEngineManager()
        prompt_stdin = PromptRef(source="test content", is_stdin=True)

        opts = RunOpts()
        # Claude accepts stdin in command building (handled via temp file in runner)
        cmd = manager.build_command("claude", prompt_stdin, opts)
        # Should just be the binary without the prompt since it's stdin
        assert cmd == ["claude"]

    def test_claude_stdin_workaround(self):
        """Test that Claude handles stdin via temp file workaround in runner."""
        # This test verifies that Claude accepts stdin in command building
        # (the temp file handling happens in the runner)
        manager = AiEngineManager()
        prompt_stdin = PromptRef(source="test content", is_stdin=True)

        opts = RunOpts()
        cmd = manager.build_command("claude", prompt_stdin, opts)
        # Should just be the binary without the prompt since it's stdin
        assert cmd == ["claude"]