"""Unit tests for AI command building functionality."""

import pytest
from maestro.ai.types import PromptRef, RunOpts
from maestro.ai.manager import AiEngineManager


def test_qwen_command_building():
    """Test command building for Qwen engine."""
    manager = AiEngineManager()

    # Test basic command
    prompt = PromptRef(source="Hello, Qwen!")
    opts = RunOpts()
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "Hello, Qwen!"]

    # Test with dangerous permissions
    opts = RunOpts(dangerously_skip_permissions=True)
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "-y", "Hello, Qwen!"]

    # Test with stream_json
    opts = RunOpts(stream_json=True)
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "-o", "stream-json", "Hello, Qwen!"]

    # Test with continue_latest
    opts = RunOpts(continue_latest=True)
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "-c", "Hello, Qwen!"]

    # Test with resume_id
    opts = RunOpts(resume_id="session123")
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "-c", "session123", "Hello, Qwen!"]

    # Test with stdin
    prompt_stdin = PromptRef(source="", is_stdin=True)
    opts = RunOpts()
    cmd = manager.build_command("qwen", prompt_stdin, opts)
    assert cmd == ["qwen"]

    # Test with model
    opts = RunOpts(model="qwen-max")
    cmd = manager.build_command("qwen", prompt, opts)
    assert cmd == ["qwen", "--model", "qwen-max", "Hello, Qwen!"]


def test_gemini_command_building():
    """Test command building for Gemini engine."""
    manager = AiEngineManager()

    # Test basic command
    prompt = PromptRef(source="Hello, Gemini!")
    opts = RunOpts()
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "Hello, Gemini!"]

    # Test with dangerous permissions
    opts = RunOpts(dangerously_skip_permissions=True)
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "-y", "Hello, Gemini!"]

    # Test with stream_json
    opts = RunOpts(stream_json=True)
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "-o", "stream-json", "Hello, Gemini!"]

    # Test with continue_latest
    opts = RunOpts(continue_latest=True)
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "-r", "latest", "Hello, Gemini!"]

    # Test with resume_id
    opts = RunOpts(resume_id="session123")
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "-r", "session123", "Hello, Gemini!"]

    # Test with stdin
    prompt_stdin = PromptRef(source="", is_stdin=True)
    opts = RunOpts()
    cmd = manager.build_command("gemini", prompt_stdin, opts)
    assert cmd == ["gemini"]

    # Test with model
    opts = RunOpts(model="gemini-pro")
    cmd = manager.build_command("gemini", prompt, opts)
    assert cmd == ["gemini", "--model", "gemini-pro", "Hello, Gemini!"]


def test_codex_command_building():
    """Test command building for Codex engine."""
    manager = AiEngineManager()

    # Test basic command
    prompt = PromptRef(source="Hello, Codex!")
    opts = RunOpts()
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "Hello, Codex!"]

    # Test with dangerous permissions
    opts = RunOpts(dangerously_skip_permissions=True)
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "Hello, Codex!"]

    # Test with stream_json
    opts = RunOpts(stream_json=True)
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "--json", "Hello, Codex!"]

    # Test with continue_latest
    opts = RunOpts(continue_latest=True)
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "resume", "--last", "Hello, Codex!"]

    # Test with resume_id
    opts = RunOpts(resume_id="session123")
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "resume", "session123", "Hello, Codex!"]

    # Test with stdin
    prompt_stdin = PromptRef(source="", is_stdin=True)
    opts = RunOpts()
    cmd = manager.build_command("codex", prompt_stdin, opts)
    assert cmd == ["codex", "exec"]

    # Test with model
    opts = RunOpts(model="codex-main")
    cmd = manager.build_command("codex", prompt, opts)
    assert cmd == ["codex", "exec", "--model", "codex-main", "Hello, Codex!"]


def test_claude_command_building():
    """Test command building for Claude engine."""
    manager = AiEngineManager()

    # Test basic command
    prompt = PromptRef(source="Hello, Claude!")
    opts = RunOpts()
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "Hello, Claude!"]

    # Test with dangerous permissions
    opts = RunOpts(dangerously_skip_permissions=True)
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "--allow-dangerously-skip-permissions", "Hello, Claude!"]

    # Test with stream_json
    opts = RunOpts(stream_json=True)
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "--output-format", "stream-json", "--include-partial-messages", "Hello, Claude!"]

    # Test with continue_latest
    opts = RunOpts(continue_latest=True)
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "-c", "Hello, Claude!"]

    # Test with resume_id
    opts = RunOpts(resume_id="session123")
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "-r", "session123", "Hello, Claude!"]

    # Test with model
    opts = RunOpts(model="claude-opus")
    cmd = manager.build_command("claude", prompt, opts)
    assert cmd == ["claude", "--model", "claude-opus", "Hello, Claude!"]

    # Test that Claude accepts stdin (handled via temp file in runner)
    prompt_stdin = PromptRef(source="Test stdin content", is_stdin=True)
    opts = RunOpts()
    cmd = manager.build_command("claude", prompt_stdin, opts)
    # Should just be the binary without the prompt since it's stdin
    assert cmd == ["claude"]


def test_stdin_for_claude():
    """Test that Claude engine accepts stdin (handled via temp file in runner)."""
    manager = AiEngineManager()

    prompt_stdin = PromptRef(source="Test stdin content", is_stdin=True)
    opts = RunOpts()

    cmd = manager.build_command("claude", prompt_stdin, opts)
    # Should just be the binary without the prompt since it's stdin
    assert cmd == ["claude"]


def test_explain_command():
    """Test the explain_command functionality."""
    manager = AiEngineManager()

    prompt = PromptRef(source="Hello, Qwen!", is_stdin=False)
    opts = RunOpts(dangerously_skip_permissions=True, stream_json=True, model="qwen-max", resume_id="session123")

    explanation = manager.explain_command("qwen", prompt, opts)

    # Check that the explanation contains the expected elements
    assert "Command for qwen engine:" in explanation
    assert "qwen -y -o stream-json --model qwen-max -c session123 Hello, Qwen!" in explanation
    assert "Permissions bypass enabled" in explanation
    assert "Stream JSON output enabled" in explanation
    assert "Model specified: qwen-max" in explanation
    assert "Resume with session ID: session123" in explanation
    assert "Prompt input: direct argument" in explanation