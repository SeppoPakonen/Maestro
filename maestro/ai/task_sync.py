"""Shared helpers for task-based AI work sessions."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro.commands.status_utils import normalize_status
from maestro.data import parse_phase_md

try:
    from multiprocessing import shared_memory
except ImportError:  # pragma: no cover - shared_memory not available on older runtimes
    shared_memory = None

SHARED_SYNC_NAME = "maestro_ai_sync"
SHARED_SYNC_SIZE = 65536


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
    shared_state = _read_shared_sync_state()
    if shared_state is not None:
        return shared_state

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
    _write_shared_sync_state(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_shared_sync_state() -> Optional[Dict[str, Any]]:
    if shared_memory is None:
        return None

    try:
        shm = shared_memory.SharedMemory(name=SHARED_SYNC_NAME, create=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        logging.debug("Shared memory not available: %s", exc)
        return None

    try:
        raw = bytes(shm.buf).split(b"\x00", 1)[0].decode("utf-8").strip()
    except Exception as exc:
        logging.debug("Failed to read shared sync state: %s", exc)
        raw = ""
    finally:
        shm.close()

    if not raw:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        logging.debug("Shared sync state contained invalid JSON.")
        return None


def _write_shared_sync_state(payload: Dict[str, Any]) -> None:
    if shared_memory is None:
        return

    data = json.dumps(payload).encode("utf-8")
    if len(data) >= SHARED_SYNC_SIZE:
        logging.warning("Shared sync state exceeds %s bytes; skipping shared memory.", SHARED_SYNC_SIZE)
        return

    try:
        shm = shared_memory.SharedMemory(name=SHARED_SYNC_NAME, create=True, size=SHARED_SYNC_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHARED_SYNC_NAME, create=False)
    except OSError as exc:
        logging.debug("Failed to allocate shared sync memory: %s", exc)
        return

    try:
        shm.buf[:len(data)] = data
        shm.buf[len(data):] = b"\x00" * (SHARED_SYNC_SIZE - len(data))
    finally:
        shm.close()
