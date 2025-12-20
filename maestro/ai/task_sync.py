"""Shared helpers for task-based AI work sessions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro.commands.status_utils import normalize_status
from maestro.data import parse_phase_md


def find_task_context(task_id: str) -> Optional[Dict[str, Any]]:
    phases_dir = Path("docs/phases")
    if not phases_dir.exists():
        return None

    for phase_file in phases_dir.glob("*.md"):
        phase = parse_phase_md(str(phase_file))
        for task in phase.get("tasks", []):
            candidate = task.get("task_id") or task.get("task_number")
            if candidate == task_id:
                return {
                    "task": task,
                    "phase": phase,
                    "phase_file": phase_file,
                }
    return None


def build_task_queue(phase: Dict[str, Any]) -> List[str]:
    queue: List[str] = []
    for task in phase.get("tasks", []):
        task_id = task.get("task_id") or task.get("task_number")
        if task_id:
            queue.append(task_id)
    return queue


def task_is_done(task: Dict[str, Any]) -> bool:
    status_value = normalize_status(task.get("status"))
    if status_value == "done":
        return True
    return bool(task.get("completed"))


def build_task_prompt(
    task_id: str,
    task: Dict[str, Any],
    phase: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    sync_source: str = "work",
) -> str:
    description_lines = task.get("description", []) or []

    def _clean_description(line: str) -> str:
        cleaned = line.strip()
        if cleaned.startswith("- "):
            cleaned = cleaned[2:].strip()
        return cleaned

    description = "\n".join(
        f"- {_clean_description(line)}"
        for line in description_lines
        if _clean_description(line)
    )
    if not description:
        description = "- (no description provided)"

    phase_id = phase.get("phase_id", "unknown")
    phase_name = phase.get("name", "Unnamed Phase")
    track_id = phase.get("track_id") or phase.get("track") or "unknown"

    lines = [
        "You are an autonomous coding agent working in this repository.",
        f"Task: {task_id} - {task.get('name', 'Unnamed Task')}",
        f"Phase: {phase_id} - {phase_name}",
        f"Track: {track_id}",
    ]

    if session_id:
        lines.append(f"Session: {session_id}")

    lines.extend([
        "",
        "Task details:",
        description,
        "",
        "Workflow:",
        f"1) Do the work for task {task_id}.",
        f"2) Mark it done with: python maestro.py task status {task_id} done --summary \"<short summary>\"",
        "3) Immediately request the next task with: python maestro.py ai sync",
        "",
        "Stay in the current AI session and follow new instructions from each ai sync call.",
        f"(sync source: {sync_source})",
    ])

    return "\n".join(lines).strip()


def load_sync_state() -> Dict[str, Any]:
    path = Path("docs/ai_sync.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def write_sync_state(session, task_queue: List[str], current_task_id: str) -> None:
    path = Path("docs/ai_sync.json")
    payload = {
        "session_id": session.session_id,
        "current_task_id": current_task_id,
        "task_queue": task_queue,
        "updated_at": datetime.now().isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
