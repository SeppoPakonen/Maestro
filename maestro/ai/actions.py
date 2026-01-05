"""Action parsing and processing for AI discussions."""

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro.data import (
    parse_heading,
    parse_phase_heading,
    parse_quoted_value,
    parse_task_heading,
    parse_track_heading,
)
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track, Phase, Task


ACTION_SCHEMA: Dict[str, Dict[str, List[str]]] = {
    "track.add": {"required": ["name"], "optional": ["description", "priority", "status", "completion", "track_id"]},
    "track.edit": {"required": ["track_id"], "optional": ["name", "description", "priority", "status", "completion"]},
    "track.remove": {"required": ["track_id"], "optional": []},
    "phase.add": {"required": ["track_id", "name"], "optional": ["duration", "status", "priority", "phase_id"]},
    "phase.edit": {"required": ["phase_id"], "optional": ["name", "duration", "status", "priority", "completion"]},
    "phase.remove": {"required": ["phase_id"], "optional": []},
    "task.add": {"required": ["phase_id", "name"], "optional": ["priority", "estimated_hours", "task_id"]},
    "task.edit": {"required": ["task_id"], "optional": ["name", "priority", "estimated_hours", "completed"]},
    "task.complete": {"required": ["task_id"], "optional": []},
    "task.remove": {"required": ["task_id"], "optional": []},
}


@dataclass
class ActionResult:
    """Result of executing a list of actions."""

    success: bool
    errors: List[str] = field(default_factory=list)
    summary: List[str] = field(default_factory=list)
    applied_actions: List[Dict[str, Any]] = field(default_factory=list)


def extract_json_actions(text: str) -> List[Dict[str, Any]]:
    """Extract JSON action lists from AI responses."""
    actions: List[Dict[str, Any]] = []
    blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("actions"), list):
            for action in payload["actions"]:
                if isinstance(action, dict):
                    actions.append(action)
    return actions


class ActionExecutionError(RuntimeError):
    """Raised when an action cannot be executed."""


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "track"


def _format_quoted_value(key: str, value: Any) -> str:
    if isinstance(value, bool):
        rendered = "true" if value else "false"
    elif value is None:
        rendered = "null"
    elif isinstance(value, (int, float)):
        rendered = str(value)
    else:
        escaped = str(value).replace('"', '\\"')
        rendered = f"\"{escaped}\""
    return f"\"{key}\": {rendered}"


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")


def _metadata_block_bounds(lines: List[str], start_idx: int) -> Tuple[int, int]:
    idx = start_idx
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    meta_start = idx
    while idx < len(lines) and parse_quoted_value(lines[idx].strip()):
        idx += 1
    meta_end = idx
    return meta_start, meta_end


def _parse_metadata(lines: List[str], start_idx: int) -> Dict[str, Any]:
    meta_start, meta_end = _metadata_block_bounds(lines, start_idx)
    metadata: Dict[str, Any] = {}
    for idx in range(meta_start, meta_end):
        result = parse_quoted_value(lines[idx].strip())
        if result:
            key, value = result
            metadata[key] = value
    return metadata


def _update_metadata_block(lines: List[str], start_idx: int, updates: Dict[str, Any]) -> None:
    meta_start, meta_end = _metadata_block_bounds(lines, start_idx)
    existing: Dict[str, int] = {}
    for idx in range(meta_start, meta_end):
        result = parse_quoted_value(lines[idx].strip())
        if result:
            key, _ = result
            existing[key] = idx
    insert_at = meta_end
    inserted = False
    for key, value in updates.items():
        if value is None:
            continue
        line = _format_quoted_value(key, value)
        if key in existing:
            lines[existing[key]] = line
        else:
            lines.insert(insert_at, line)
            insert_at += 1
            inserted = True
    if inserted and insert_at < len(lines) and lines[insert_at].strip():
        lines.insert(insert_at, "")


def _phase_heading_id(phase_id: str, track_id: Optional[str] = None) -> str:
    if phase_id and re.fullmatch(r"[A-Za-z0-9]+", phase_id):
        return phase_id.upper()
    prefix = ""
    suffix = ""
    if phase_id:
        parts = phase_id.split("-")
        if parts:
            prefix = parts[0].upper()
        for part in reversed(parts):
            if part.isdigit():
                suffix = part
                break
    if not prefix and track_id:
        prefix = track_id.split("-")[0].upper()
    if prefix and suffix:
        return f"{prefix}{suffix}"
    return prefix or "PHASE"


def _next_phase_id(track_id: str) -> str:
    json_store = JsonStore()
    todo = {"tracks": []}
    tracks = []
    for tid in json_store.list_all_tracks():
        track = json_store.load_track(tid, load_phases=False, load_tasks=False)
        if track:
            tracks.append({"track_id": track.track_id, "phases": track.phases})
    todo["tracks"] = tracks
    numeric_suffixes: List[int] = []
    for track in todo.get("tracks", []):
        if track.get("track_id") != track_id:
            continue
        for phase in track.get("phases", []):
            phase_id = phase.get("phase_id")
            if isinstance(phase_id, str) and phase_id.startswith(f"{track_id}-"):
                match = re.search(r"(\\d+)$", phase_id)
                if match:
                    numeric_suffixes.append(int(match.group(1)))
    next_num = max(numeric_suffixes) + 1 if numeric_suffixes else 1
    return f"{track_id}-{next_num}"


def _next_task_number(phase_id: str, lines: List[str]) -> str:
    numbers: List[str] = []
    for line in lines:
        result = parse_task_heading(line.strip())
        if result:
            numbers.append(result[0])
    dotted: List[Tuple[str, int]] = []
    integers: List[int] = []
    for number in numbers:
        if "." in number:
            major, minor = number.split(".", 1)
            if major.isdigit() and minor.isdigit():
                dotted.append((major, int(minor)))
        elif number.isdigit():
            integers.append(int(number))
    if dotted:
        major = dotted[0][0]
        max_minor = max(minor for major_val, minor in dotted if major_val == major)
        return f"{major}.{max_minor + 1}"
    if integers:
        return str(max(integers) + 1)
    match = re.search(r"(\\d+)$", phase_id)
    if match:
        return f"{match.group(1)}.1"
    return "1.1"


def _find_track_block(lines: List[str], track_id: str) -> Optional[Tuple[int, int]]:
    idx = 0
    while idx < len(lines):
        if parse_track_heading(lines[idx].strip()):
            start = idx
            metadata = _parse_metadata(lines, start + 1)
            end = start + 1
            while end < len(lines) and not parse_track_heading(lines[end].strip()):
                end += 1
            if metadata.get("track_id") == track_id:
                return start, end
            idx = end
        else:
            idx += 1
    return None


def _find_phase_block(lines: List[str], phase_id: str) -> Optional[Tuple[int, int]]:
    idx = 0
    while idx < len(lines):
        if parse_phase_heading(lines[idx].strip()):
            start = idx
            metadata = _parse_metadata(lines, start + 1)
            end = start + 1
            while end < len(lines):
                if parse_phase_heading(lines[end].strip()) or parse_track_heading(lines[end].strip()):
                    break
                heading = parse_heading(lines[end].strip())
                if heading and heading[0] == 2:
                    break
                end += 1
            if metadata.get("phase_id") == phase_id:
                return start, end
            idx = end
        else:
            idx += 1
    return None


def _find_task_block(lines: List[str], task_id: str) -> Optional[Tuple[int, int]]:
    idx = 0
    while idx < len(lines):
        result = parse_task_heading(lines[idx].strip())
        if result:
            start = idx
            metadata = _parse_metadata(lines, start + 1)
            task_number = result[0]
            end = start + 1
            while end < len(lines):
                if parse_task_heading(lines[end].strip()):
                    break
                if parse_heading(lines[end].strip()):
                    break
                end += 1
            if metadata.get("task_id") == task_id or metadata.get("task_number") == task_id or task_number == task_id:
                return start, end
            idx = end
        else:
            idx += 1
    return None


def _replace_heading_name(line: str, pattern: str, name: str) -> str:
    match = re.match(pattern, line)
    if not match:
        return line
    prefix = match.group(1)
    suffix = match.group(3) or ""
    return f"{prefix}{name}{suffix}"


class ActionProcessor:
    """Validate and execute AI actions."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def validate_actions(self, actions: List[Dict[str, Any]], allowed_actions: Optional[List[str]] = None) -> List[str]:
        """Return a list of validation errors."""
        errors: List[str] = []
        for idx, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"Action {idx + 1}: action is not a dict.")
                continue
            action_type = action.get("type")
            data = action.get("data")
            if not action_type or not isinstance(action_type, str):
                errors.append(f"Action {idx + 1}: missing or invalid 'type'.")
                continue
            if allowed_actions is not None and action_type not in allowed_actions:
                errors.append(f"Action {idx + 1}: action '{action_type}' is not allowed in this context.")
                continue
            schema = ACTION_SCHEMA.get(action_type)
            if not schema:
                errors.append(f"Action {idx + 1}: unknown action type '{action_type}'.")
                continue
            if not isinstance(data, dict):
                errors.append(f"Action {idx + 1}: missing or invalid 'data' object.")
                continue
            for field in schema["required"]:
                if field not in data:
                    errors.append(f"Action {idx + 1}: missing required field '{field}'.")
            for field in data.keys():
                if field not in schema["required"] and field not in schema["optional"]:
                    errors.append(f"Action {idx + 1}: unexpected field '{field}'.")
            self._validate_references(action_type, data, errors, idx)
        return errors

    def execute_actions(self, actions: List[Dict[str, Any]]) -> ActionResult:
        """Execute actions. Returns ActionResult with summary/errors."""
        if not actions:
            return ActionResult(success=True, summary=["No actions to execute."])
        if self.dry_run:
            summary = [f"Dry run: {action.get('type', 'unknown')}" for action in actions]
            return ActionResult(success=True, summary=summary, applied_actions=list(actions))
        summary: List[str] = []
        applied: List[Dict[str, Any]] = []
        try:
            for action in actions:
                action_type = action.get("type")
                data = action.get("data", {})
                if action_type == "track.add":
                    summary.append(self._apply_track_add(data))
                elif action_type == "track.edit":
                    summary.append(self._apply_track_edit(data))
                elif action_type == "track.remove":
                    summary.append(self._apply_track_remove(data))
                elif action_type == "phase.add":
                    summary.append(self._apply_phase_add(data))
                elif action_type == "phase.edit":
                    summary.append(self._apply_phase_edit(data))
                elif action_type == "phase.remove":
                    summary.append(self._apply_phase_remove(data))
                elif action_type == "task.add":
                    summary.append(self._apply_task_add(data))
                elif action_type == "task.edit":
                    summary.append(self._apply_task_edit(data))
                elif action_type == "task.complete":
                    summary.append(self._apply_task_complete(data))
                elif action_type == "task.remove":
                    summary.append(self._apply_task_remove(data))
                else:
                    raise ActionExecutionError(f"Unknown action type '{action_type}'.")
                applied.append(action)
        except ActionExecutionError as exc:
            return ActionResult(success=False, errors=[str(exc)], summary=summary, applied_actions=applied)
        return ActionResult(success=True, summary=summary, applied_actions=applied)

    def _validate_references(
        self, action_type: str, data: Dict[str, Any], errors: List[str], idx: int
    ) -> None:
        """Validate referenced IDs exist in docs data."""
        if action_type.startswith("track."):
            return
        if action_type.startswith("phase.") or action_type.startswith("task."):
            json_store = JsonStore()
            track_ids = set(json_store.list_all_tracks())
            phase_ids = set(json_store.list_all_phases())
            if "track_id" in data and data["track_id"] not in track_ids:
                errors.append(f"Action {idx + 1}: track_id '{data['track_id']}' not found.")
            if "phase_id" in data and data["phase_id"] not in phase_ids:
                errors.append(f"Action {idx + 1}: phase_id '{data['phase_id']}' not found.")
        if action_type.startswith("task."):
            task_id = data.get("task_id")
            if task_id:
                json_store = JsonStore()
                if not json_store.load_task(task_id):
                    errors.append(f"Action {idx + 1}: task_id '{task_id}' not found.")

    def _task_exists(self, task_id: str) -> bool:
        json_store = JsonStore()
        return json_store.load_task(task_id) is not None

    def _apply_track_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        if not name:
            raise ActionExecutionError("track.add requires a name.")
        track_id = data.get("track_id") or _slugify(name)
        priority = data.get("priority", 0)
        status = data.get("status", "planned")
        description = data.get("description")
        json_store = JsonStore()
        if json_store.load_track(track_id, load_phases=False, load_tasks=False):
            raise ActionExecutionError(f"Track '{track_id}' already exists.")
        track = Track(
            track_id=track_id,
            name=name,
            status=status,
            completion=data.get("completion", 0),
            description=[str(description)] if isinstance(description, str) else (description or []),
            phases=[],
            priority=priority,
        )
        json_store.save_track(track)
        return f"Added track '{track_id}'."

    def _apply_track_edit(self, data: Dict[str, Any]) -> str:
        track_id = data.get("track_id")
        if not track_id:
            raise ActionExecutionError("track.edit requires track_id.")
        json_store = JsonStore()
        track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
        if not track:
            raise ActionExecutionError(f"Track '{track_id}' not found.")
        if "name" in data and data["name"]:
            track.name = data["name"]
        if "priority" in data and data["priority"] is not None:
            track.priority = data["priority"]
        if "status" in data and data["status"]:
            track.status = data["status"]
        if "completion" in data and data["completion"] is not None:
            track.completion = data["completion"]
        description = data.get("description")
        if description is not None:
            track.description = [str(description)] if isinstance(description, str) else description
        json_store.save_track(track)
        return f"Updated track '{track_id}'."

    def _apply_track_remove(self, data: Dict[str, Any]) -> str:
        track_id = data.get("track_id")
        if not track_id:
            raise ActionExecutionError("track.remove requires track_id.")
        json_store = JsonStore()
        if not json_store.delete_track(track_id, delete_phases=True, delete_tasks=True):
            raise ActionExecutionError(f"Track '{track_id}' not found.")
        return f"Removed track '{track_id}'."

    def _apply_phase_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        track_id = data.get("track_id")
        if not name or not track_id:
            raise ActionExecutionError("phase.add requires track_id and name.")
        phase_id = data.get("phase_id") or _slugify(f"{track_id}-{name}")
        status = data.get("status", "planned")
        completion = data.get("completion", 0)
        json_store = JsonStore()
        track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
        if not track:
            raise ActionExecutionError(f"Track '{track_id}' not found.")
        if json_store.load_phase(phase_id, load_tasks=False):
            raise ActionExecutionError(f"Phase '{phase_id}' already exists.")
        phase = Phase(
            phase_id=phase_id,
            name=name,
            status=status,
            completion=completion,
            description=[],
            tasks=[],
            track_id=track_id,
            priority=data.get("priority", 0),
        )
        json_store.save_phase(phase)
        if phase_id not in track.phases:
            track.phases.append(phase_id)
            json_store.save_track(track)
        return f"Added phase '{phase_id}' to track '{track_id}'."

    def _apply_phase_edit(self, data: Dict[str, Any]) -> str:
        phase_id = data.get("phase_id")
        if not phase_id:
            raise ActionExecutionError("phase.edit requires phase_id.")
        json_store = JsonStore()
        phase = json_store.load_phase(phase_id, load_tasks=False)
        if not phase:
            raise ActionExecutionError(f"Phase '{phase_id}' not found.")
        if "name" in data and data["name"]:
            phase.name = data["name"]
        if "status" in data and data["status"]:
            phase.status = data["status"]
        if "priority" in data and data["priority"] is not None:
            phase.priority = data["priority"]
        if "completion" in data and data["completion"] is not None:
            phase.completion = data["completion"]
        json_store.save_phase(phase)
        return f"Updated phase '{phase_id}'."

    def _apply_phase_remove(self, data: Dict[str, Any]) -> str:
        phase_id = data.get("phase_id")
        if not phase_id:
            raise ActionExecutionError("phase.remove requires phase_id.")
        json_store = JsonStore()
        phase = json_store.load_phase(phase_id, load_tasks=False)
        if not phase:
            raise ActionExecutionError(f"Phase '{phase_id}' not found.")
        track_id = phase.track_id
        json_store.delete_phase(phase_id, delete_tasks=True)
        if track_id:
            track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if track and phase_id in track.phases:
                track.phases = [p for p in track.phases if p != phase_id]
                json_store.save_track(track)
        return f"Removed phase '{phase_id}'."

    def _apply_task_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        phase_id = data.get("phase_id")
        if not name or not phase_id:
            raise ActionExecutionError("task.add requires phase_id and name.")
        json_store = JsonStore()
        phase = json_store.load_phase(phase_id, load_tasks=False)
        if not phase:
            raise ActionExecutionError(f"Phase '{phase_id}' not found.")
        task_id = data.get("task_id") or _slugify(f"{phase_id}-{name}")
        if json_store.load_task(task_id):
            raise ActionExecutionError(f"Task '{task_id}' already exists.")
        task = Task(
            task_id=task_id,
            name=name,
            status=data.get("status", "todo"),
            priority=data.get("priority", "P2"),
            estimated_hours=data.get("estimated_hours"),
            description=[],
            phase_id=phase_id,
            completed=False,
        )
        json_store.save_task(task)
        if task_id not in phase.tasks:
            phase.tasks.append(task_id)
            json_store.save_phase(phase)
        return f"Added task '{task_id}' to phase '{phase_id}'."

    def _apply_task_edit(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.edit requires task_id.")
        json_store = JsonStore()
        task = json_store.load_task(task_id)
        if not task:
            raise ActionExecutionError(f"Task '{task_id}' not found.")
        if "name" in data and data["name"]:
            task.name = data["name"]
        if "priority" in data and data["priority"] is not None:
            task.priority = data["priority"]
        if "estimated_hours" in data and data["estimated_hours"] is not None:
            task.estimated_hours = data["estimated_hours"]
        if "completed" in data and data["completed"] is not None:
            task.completed = bool(data["completed"])
            if task.completed:
                task.status = "done"
        json_store.save_task(task)
        return f"Updated task '{task_id}'."

    def _apply_task_complete(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.complete requires task_id.")
        json_store = JsonStore()
        task = json_store.load_task(task_id)
        if not task:
            raise ActionExecutionError(f"Task '{task_id}' not found.")
        task.completed = True
        task.status = "done"
        json_store.save_task(task)
        return f"Completed task '{task_id}'."

    def _apply_task_remove(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.remove requires task_id.")
        json_store = JsonStore()
        task = json_store.load_task(task_id)
        if not task:
            raise ActionExecutionError(f"Task '{task_id}' not found.")
        phase_id = task.phase_id
        json_store.delete_task(task_id)
        if phase_id:
            phase = json_store.load_phase(phase_id, load_tasks=False)
            if phase and task_id in phase.tasks:
                phase.tasks = [t for t in phase.tasks if t != task_id]
                json_store.save_phase(phase)
        return f"Removed task '{task_id}'."
