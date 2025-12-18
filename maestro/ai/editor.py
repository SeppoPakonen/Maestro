"""Editor-based discussion mode."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from typing import List

from .discussion import Discussion, DiscussionResult


class EditorDiscussion(Discussion):
    """Discussion loop using $VISUAL/$EDITOR."""

    def start(self) -> DiscussionResult:
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
        last_ai: List[str] = []

        while True:
            temp_path = self._write_prompt_file(last_ai)
            try:
                subprocess.run([editor, temp_path], check=False)
            except Exception as exc:
                self.add_ai_message(f"Editor error: {exc}")
                self.completed = False
                break

            user_input = self._read_user_input(temp_path)
            if not user_input:
                continue
            if self.process_command(user_input):
                break
            if user_input.strip().lower() == "/help":
                last_ai = [
                    "Commands:",
                    "/done - finish and apply actions",
                    "/quit - cancel the discussion",
                ]
                continue

            self.add_user_message(user_input)
            response = self.ai_client.send_message(self.messages, self.context.system_prompt)
            self.add_ai_message(response)
            last_ai = response.splitlines()

        return DiscussionResult(
            messages=self.messages,
            actions=self.actions,
            completed=self.completed,
        )

    def _write_prompt_file(self, last_ai: List[str]) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as handle:
            handle.write(f"# Discussion: {self.context.context_type}\n\n")
            handle.write("# Type your message below, then save and exit.\n")
            handle.write("# Special commands: /done (finish), /quit (cancel), /help\n")
            handle.write("\n")
            for message in self.messages:
                if message["role"] == "assistant":
                    handle.write("# AI response:\n")
                    for line in message["content"].splitlines():
                        handle.write(f"# {line}\n")
                    handle.write("\n")
            if last_ai:
                handle.write("# Most recent AI response:\n")
                for line in last_ai:
                    handle.write(f"# {line}\n")
                handle.write("\n")
            handle.write("\n")
            return handle.name

    def _read_user_input(self, temp_path: str) -> str:
        try:
            with open(temp_path, "r", encoding="utf-8") as handle:
                lines = []
                for line in handle:
                    stripped = line.rstrip("\n")
                    if stripped.strip().startswith("#"):
                        continue
                    lines.append(stripped)
            content = "\n".join(lines).strip()
            return content
        finally:
            try:
                Path(temp_path).unlink()
            except OSError:
                pass
