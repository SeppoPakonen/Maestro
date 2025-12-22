import json
import threading
import time

import maestro.qwen.tui as tui


class FakeSocket:
    def __init__(self, recv_lines):
        self._recv_lines = list(recv_lines)
        self.sent = []
        self.closed = False

    def recv(self, n):
        if not self._recv_lines:
            time.sleep(0.01)
            return b""
        return self._recv_lines.pop(0)

    def sendall(self, data):
        self.sent.append(data)

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


def test_run_tui_exit_after_prompt_waits_for_assistant(monkeypatch, capsys):
    # Server sends init, then echoes user, then assistant response.
    recv_lines = [
        (json.dumps({"type": "init", "version": "x"}) + "\n").encode(),
        (json.dumps({"type": "conversation", "role": "user", "content": "hello"}) + "\n").encode(),
        (json.dumps({"type": "conversation", "role": "assistant", "content": "hi"}) + "\n").encode(),
    ]
    sock = FakeSocket(recv_lines)

    monkeypatch.setattr(tui.socket, "create_connection", lambda *a, **k: sock)

    exit_code = tui.run_tui(host="127.0.0.1", port=7777, prompt="hello", exit_after_prompt=True)

    assert exit_code == 0

    # Ensure we sent the prompt.
    assert sock.sent, "Expected run_tui to send at least one command"
    sent_payload = sock.sent[0].decode("utf-8")
    assert "user_input" in sent_payload
    assert "hello" in sent_payload

    out = capsys.readouterr().out
    assert "ASSISTANT: hi" in out
