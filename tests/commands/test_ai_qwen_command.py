import pytest

from maestro.commands.ai import handle_ai_qwen


class Args:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_ai_qwen_prompt_passed_to_tui(monkeypatch, tmp_path):
    captured = {}

    def fake_run_tui(*, host, port, prompt=None, exit_after_prompt=False):
        captured["host"] = host
        captured["port"] = port
        captured["prompt"] = prompt
        captured["exit_after_prompt"] = exit_after_prompt
        return 0

    # Patch where _run_qwen_tui imports from.
    monkeypatch.setattr("maestro.qwen.tui.run_tui", fake_run_tui)

    args = Args(
        mode="tui",
        host="127.0.0.1",
        tcp_port=7777,
        attach=True,
        prompt="Hello from test",
        qwen_executable=str(tmp_path / "qwen-code.sh"),
        verbose=False,
    )

    # Create a dummy qwen-code.sh so _resolve_qwen_script succeeds.
    (tmp_path / "qwen-code.sh").write_text("#!/bin/sh\necho dummy\n")

    exit_code = handle_ai_qwen(args)

    assert exit_code == 0
    assert captured == {
        "host": "127.0.0.1",
        "port": 7777,
        "prompt": "Hello from test",
        "exit_after_prompt": True,
    }
