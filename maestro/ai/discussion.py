"""Core discussion models and context builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
from typing import Any, Dict, List, Optional

from maestro.data import parse_phase_md, parse_todo_md
from .actions import extract_json_actions


class DiscussionMode(Enum):
    """Input modes for discussions."""

    EDITOR = "editor"
    TERMINAL = "terminal"


@dataclass
class DiscussionContext:
    """Structured context for a discussion."""

    context_type: str
    context_id: Optional[str]
    allowed_actions: List[str]
    system_prompt: str


@dataclass
class DiscussionResult:
    """Final result of a discussion session."""

    messages: List[Dict[str, str]]
    actions: List[Dict[str, Any]]
    completed: bool


class Discussion:
    """Base discussion class."""

    def __init__(self, context: DiscussionContext, mode: DiscussionMode, ai_client):
        self.context = context
        self.mode = mode
        self.ai_client = ai_client
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": context.system_prompt}
        ]
        self.actions: List[Dict[str, Any]] = []
        self.completed = False

    def start(self) -> DiscussionResult:
        raise NotImplementedError

    def add_user_message(self, msg: str) -> None:
        self.messages.append({"role": "user", "content": msg})

    def add_ai_message(self, msg: str) -> None:
        self.messages.append({"role": "assistant", "content": msg})
        self.actions.extend(extract_json_actions(msg))

    def process_command(self, cmd: str) -> bool:
        normalized = cmd.strip().lower()
        if normalized == "/done":
            self.completed = True
            return True
        if normalized == "/quit":
            self.completed = False
            return True
        return False

    def serialize_result(self, output_dir: Path = Path("docs/discussions")) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        context_id = self.context.context_id or "general"
        sanitized = "".join(c for c in context_id if c.isalnum() or c in "-_.")
        filename = f"{timestamp}_{self.context.context_type}_{sanitized}.md"
        path = output_dir / filename

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"# Discussion: {self.context.context_type}\n\n")
            handle.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            if self.context.context_id:
                handle.write(f"Context ID: {self.context.context_id}\n\n")
            handle.write("## Messages\n\n")
            for message in self.messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                handle.write(f"### {role}\n\n{content}\n\n")
            if self.actions:
                handle.write("## Actions\n\n```json\n")
                handle.write(f"{json.dumps(self.actions, indent=2)}\n")
                handle.write("```\n")
            handle.write(f"\nCompleted: {self.completed}\n")
        return path


def build_track_context(track_id: Optional[str]) -> DiscussionContext:
    todo = parse_todo_md("docs/todo.md")
    tracks = todo.get("tracks", [])
    track = None
    if track_id:
        for item in tracks:
            if item.get("track_id") == track_id:
                track = item
                break
        if not track:
            raise ValueError(f"Track '{track_id}' not found.")
    context_type = "track" if track_id else "general"
    allowed_actions = ["track.add", "track.edit", "phase.add"]
    details = track or {"tracks": [t.get("track_id") for t in tracks]}
    prompt = _build_system_prompt(context_type, track_id, allowed_actions, details)
    return DiscussionContext(
        context_type=context_type,
        context_id=track_id,
        allowed_actions=allowed_actions,
        system_prompt=prompt,
    )


def build_phase_context(phase_id: str) -> DiscussionContext:
    phase_file = Path(f"docs/phases/{phase_id}.md")
    if phase_file.exists():
        phase = parse_phase_md(str(phase_file))
    else:
        todo = parse_todo_md("docs/todo.md")
        phase = None
        for track in todo.get("tracks", []):
            for item in track.get("phases", []):
                if item.get("phase_id") == phase_id:
                    phase = item
                    break
            if phase:
                break
        if not phase:
            raise ValueError(f"Phase '{phase_id}' not found.")
    allowed_actions = ["phase.edit", "task.add", "task.edit"]
    prompt = _build_system_prompt("phase", phase_id, allowed_actions, phase)
    return DiscussionContext(
        context_type="phase",
        context_id=phase_id,
        allowed_actions=allowed_actions,
        system_prompt=prompt,
    )


def build_task_context(task_id: str) -> DiscussionContext:
    phases_dir = Path("docs/phases")
    if not phases_dir.exists():
        raise ValueError("docs/phases directory not found.")
    task = None
    phase_context = None
    for phase_file in phases_dir.glob("*.md"):
        phase = parse_phase_md(str(phase_file))
        for item in phase.get("tasks", []):
            if item.get("task_id") == task_id or item.get("task_number") == task_id:
                task = item
                phase_context = {"phase_id": phase.get("phase_id"), "phase_name": phase.get("name")}
                break
        if task:
            break
    if not task:
        raise ValueError(f"Task '{task_id}' not found.")
    details = {"task": task, "phase": phase_context}
    allowed_actions = ["task.edit", "task.complete"]
    prompt = _build_system_prompt("task", task_id, allowed_actions, details)
    return DiscussionContext(
        context_type="task",
        context_id=task_id,
        allowed_actions=allowed_actions,
        system_prompt=prompt,
    )


def _build_system_prompt(
    context_type: str,
    context_id: Optional[str],
    allowed_actions: List[str],
    details: Dict[str, Any],
) -> str:
    action_schema = {
        "actions": [
            {"type": "track.add", "data": {"name": "Track name", "priority": 1}},
            {"type": "phase.add", "data": {"track_id": "cli-tpt", "name": "Phase name"}},
            {"type": "task.add", "data": {"phase_id": "cli-tpt-1", "name": "Task name", "priority": "P0"}},
        ]
    }
    context_line = context_id or "general"
    prompt_lines = [
        "You are a project planning assistant for Maestro.",
        f"Context: {context_type} ({context_line})",
        f"Details: {details}",
        "",
        "You can suggest actions in JSON format:",
        f"{action_schema}",
        f"Allowed actions: {allowed_actions}",
        "Provide helpful guidance and suggest concrete actions.",
    ]
    return "\n".join(prompt_lines)
