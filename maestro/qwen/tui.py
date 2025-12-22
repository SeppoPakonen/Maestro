#!/usr/bin/env python3
"""
Simple TUI client for the Qwen TCP server.

This connects to a running QwenManager server and provides a line-based
interactive prompt. The server handles the backend qwen-code process.
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
from typing import Optional


def run_tui(
    host: str = "127.0.0.1",
    port: int = 7777,
    prompt: Optional[str] = None,
    *,
    exit_after_prompt: bool = False,
) -> int:
    try:
        sock = socket.create_connection((host, port), timeout=5)
    except OSError as exc:
        print(f"Error: failed to connect to Qwen server at {host}:{port}: {exc}")
        return 1

    stop_event = threading.Event()
    got_conversation_event = threading.Event()

    def _reader() -> None:
        buffer = ""
        try:
            while not stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if _print_message(line):
                        got_conversation_event.set()
        except OSError:
            pass
        finally:
            stop_event.set()

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    if prompt:
        _send_command(sock, {"type": "user_input", "content": prompt})
        if exit_after_prompt:
            # Wait briefly for at least one conversation message so `-p` is useful
            # in non-interactive scripting (e.g. `timeout 10 ...`).
            got_conversation_event.wait(timeout=8.0)
            stop_event.set()

    try:
        while not stop_event.is_set():
            try:
                user_input = input("> ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input in ("/exit", "/quit"):
                break
            _send_command(sock, {"type": "user_input", "content": user_input})
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        reader_thread.join(timeout=1)

    return 0


def _send_command(sock: socket.socket, cmd: dict) -> None:
    payload = json.dumps(cmd) + "\n"
    sock.sendall(payload.encode("utf-8"))


def _print_message(raw_line: str) -> bool:
    try:
        msg = json.loads(raw_line)
    except json.JSONDecodeError:
        print(raw_line)
        return False

    msg_type = msg.get("type")
    if msg_type == "conversation":
        role = msg.get("role", "assistant").upper()
        content = msg.get("content", "")
        print(f"{role}: {content}")
        return role == "ASSISTANT"

    if msg_type == "status":
        state = msg.get("state", "")
        message = msg.get("message")
        if message:
            print(f"[status:{state}] {message}")
        else:
            print(f"[status:{state}]")
        return False

    if msg_type == "tool_group":
        tool_id = msg.get("id", "")
        tools = msg.get("tools") or []
        tool_names = [tool.get("tool_name", "tool") for tool in tools if isinstance(tool, dict)]
        summary = ", ".join(tool_names) if tool_names else "tools"
        print(f"[tools:{tool_id}] {summary}")
        return False

    if msg_type == "error":
        print(f"[error] {msg.get('message', '')}")
        return False

    if msg_type == "info":
        print(f"[info] {msg.get('message', '')}")
        return False

    if msg_type == "completion_stats":
        duration = msg.get("duration", "")
        prompt_tokens = msg.get("prompt_tokens")
        completion_tokens = msg.get("completion_tokens")
        stats = [duration] if duration else []
        if prompt_tokens is not None:
            stats.append(f"prompt={prompt_tokens}")
        if completion_tokens is not None:
            stats.append(f"completion={completion_tokens}")
        stat_line = " ".join(stats)
        print(f"[stats] {stat_line}".strip())
        return False

    print(raw_line)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Qwen TUI client (TCP)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--tcp-port", type=int, default=7777, help="Server TCP port (default: 7777)")
    args = parser.parse_args()
    return run_tui(host=args.host, port=args.tcp_port)


if __name__ == "__main__":
    raise SystemExit(main())
