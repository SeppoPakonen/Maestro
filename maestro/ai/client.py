"""AI client abstractions and external command integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
import shutil
import subprocess
from typing import Dict, Iterator, List, Optional

from maestro.data import parse_config_md


class AIClient(ABC):
    """Abstract base class for AI clients."""

    @abstractmethod
    def send_message(self, messages: List[Dict[str, str]], context: str) -> str:
        """Send messages and return the full response."""

    @abstractmethod
    def stream_message(self, messages: List[Dict[str, str]], context: str) -> Iterator[str]:
        """Stream the response as tokens/lines."""


class ExternalCommandClient(AIClient):
    """AI client that shells out to local CLI providers."""

    PROVIDER_COMMANDS = {
        "local": ["~/node_modules/.bin/qwen", "-y"],
        "anthropic": ["claude", "--print", "--output-format", "text", "--permission-mode", "bypassPermissions"],
        "openai": ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"],
    }

    def __init__(self, provider: Optional[str] = None):
        config = parse_config_md("docs/config.md")
        ai_settings = config.get("ai_settings", {})
        resolved_provider = (provider or ai_settings.get("ai_provider") or "local").lower()
        if resolved_provider not in self.PROVIDER_COMMANDS:
            raise ValueError(f"Unsupported AI provider: {resolved_provider}")
        self.provider = resolved_provider
        self.command = self._resolve_command(self.PROVIDER_COMMANDS[resolved_provider])

    def send_message(self, messages: List[Dict[str, str]], context: str) -> str:
        prompt = self._build_prompt(messages, context)
        result = subprocess.run(
            self.command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "AI command failed.")
        return result.stdout.strip()

    def stream_message(self, messages: List[Dict[str, str]], context: str) -> Iterator[str]:
        prompt = self._build_prompt(messages, context)
        process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        for line in process.stdout:
            yield line
        process.wait()
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(stderr.strip() or "AI command failed.")

    def _resolve_command(self, command: List[str]) -> List[str]:
        resolved: List[str] = []
        for idx, part in enumerate(command):
            if idx == 0 and part.startswith("~"):
                expanded = os.path.expanduser(part)
                resolved.append(expanded)
            else:
                resolved.append(part)
        executable = resolved[0]
        if os.path.isabs(executable):
            if not Path(executable).exists():
                raise RuntimeError(f"AI command not found: {executable}")
        else:
            if not shutil.which(executable):
                raise RuntimeError(f"AI command not found: {executable}")
        return resolved

    def _build_prompt(self, messages: List[Dict[str, str]], context: str) -> str:
        lines = [context.strip(), ""]
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            if role == "SYSTEM":
                continue
            lines.append(f"{role}: {content}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)
