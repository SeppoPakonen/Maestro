"""Action parsing and processing for AI discussions."""

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro.data import (
    parse_heading,
    parse_phase_heading,
    parse_phase_md,
    parse_quoted_value,
    parse_task_heading,
    parse_todo_md,
    parse_track_heading,
)


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
    todo = parse_todo_md("docs/todo.md")
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
            todo = parse_todo_md("docs/todo.md")
            tracks = todo.get("tracks", [])
            phase_ids = {phase.get("phase_id") for track in tracks for phase in track.get("phases", [])}
            track_ids = {track.get("track_id") for track in tracks}
            if "track_id" in data and data["track_id"] not in track_ids:
                errors.append(f"Action {idx + 1}: track_id '{data['track_id']}' not found in docs/todo.md.")
            if "phase_id" in data and data["phase_id"] not in phase_ids:
                errors.append(f"Action {idx + 1}: phase_id '{data['phase_id']}' not found in docs/todo.md.")
        if action_type.startswith("task."):
            task_id = data.get("task_id")
            if task_id:
                phases_dir = Path("docs/phases")
                if phases_dir.exists():
                    if not self._task_exists(phases_dir, task_id):
                        errors.append(f"Action {idx + 1}: task_id '{task_id}' not found in phase files.")

    def _task_exists(self, phases_dir: Path, task_id: str) -> bool:
        for phase_file in phases_dir.glob("*.md"):
            phase = parse_phase_md(str(phase_file))
            for task in phase.get("tasks", []):
                if task.get("task_id") == task_id or task.get("task_number") == task_id:
                    return True
        return False

    def _apply_track_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        if not name:
            raise ActionExecutionError("track.add requires a name.")
        track_id = data.get("track_id") or _slugify(name)
        priority = data.get("priority", 0)
        status = data.get("status", "planned")
        description = data.get("description")
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"## Track: {name}")
        lines.append(_format_quoted_value("track_id", track_id))
        lines.append(_format_quoted_value("priority", priority))
        lines.append(_format_quoted_value("status", status))
        lines.append("")
        if description:
            lines.append(str(description))
            lines.append("")
        _write_lines(todo_path, lines)
        return f"Added track '{track_id}'."

    def _apply_track_edit(self, data: Dict[str, Any]) -> str:
        track_id = data.get("track_id")
        if not track_id:
            raise ActionExecutionError("track.edit requires track_id.")
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        block = _find_track_block(lines, track_id)
        if not block:
            raise ActionExecutionError(f"Track '{track_id}' not found in docs/todo.md.")
        start, _ = block
        if "name" in data and data["name"]:
            lines[start] = _replace_heading_name(
                lines[start],
                r"^(##\\s+(?:🔥\\s+)?(?:TOP PRIORITY\\s+)?Track:\\s+)(.+?)(\\s+[✅🚧📋💡].*)?$",
                data["name"],
            )
        _update_metadata_block(
            lines,
            start + 1,
            {
                "track_id": track_id,
                "priority": data.get("priority"),
                "status": data.get("status"),
                "completion": data.get("completion"),
            },
        )
        _write_lines(todo_path, lines)
        return f"Updated track '{track_id}'."

    def _apply_track_remove(self, data: Dict[str, Any]) -> str:
        track_id = data.get("track_id")
        if not track_id:
            raise ActionExecutionError("track.remove requires track_id.")
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        block = _find_track_block(lines, track_id)
        if not block:
            raise ActionExecutionError(f"Track '{track_id}' not found in docs/todo.md.")
        start, end = block
        del lines[start:end]
        _write_lines(todo_path, lines)
        return f"Removed track '{track_id}'."

    def _apply_phase_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        track_id = data.get("track_id")
        if not name or not track_id:
            raise ActionExecutionError("phase.add requires track_id and name.")
        phase_id = data.get("phase_id") or _next_phase_id(track_id)
        status = data.get("status", "planned")
        completion = data.get("completion", 0)
        heading_id = _phase_heading_id(phase_id, track_id)
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        track_block = _find_track_block(lines, track_id)
        if not track_block:
            raise ActionExecutionError(f"Track '{track_id}' not found in docs/todo.md.")
        _, track_end = track_block
        insert_at = track_end
        if insert_at > 0 and lines[insert_at - 1].strip():
            lines.insert(insert_at, "")
            insert_at += 1
        phase_lines = [
            f"### Phase {heading_id}: {name}",
            _format_quoted_value("phase_id", phase_id),
            _format_quoted_value("status", status),
            _format_quoted_value("completion", completion),
            "",
            f"- [ ] [Phase {heading_id}: {name}](phases/{phase_id}.md) 📋 **[Planned]**",
            "",
        ]
        lines[insert_at:insert_at] = phase_lines
        _write_lines(todo_path, lines)
        phase_path = Path("docs/phases") / f"{phase_id}.md"
        if not phase_path.exists():
            phase_file_lines = [
                f"# Phase {heading_id}: {name} 📋 **[Planned]**",
                "",
                _format_quoted_value("phase_id", phase_id),
                _format_quoted_value("track_id", track_id),
                _format_quoted_value("status", status),
                _format_quoted_value("completion", completion),
                "",
                "## Tasks",
                "",
            ]
            _write_lines(phase_path, phase_file_lines)
        return f"Added phase '{phase_id}' to track '{track_id}'."

    def _apply_phase_edit(self, data: Dict[str, Any]) -> str:
        phase_id = data.get("phase_id")
        if not phase_id:
            raise ActionExecutionError("phase.edit requires phase_id.")
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        block = _find_phase_block(lines, phase_id)
        if not block:
            raise ActionExecutionError(f"Phase '{phase_id}' not found in docs/todo.md.")
        start, _ = block
        if "name" in data and data["name"]:
            lines[start] = _replace_heading_name(
                lines[start],
                r"^(###\\s+Phase\\s+[\\w\\d]+:\\s+)(.+?)(\\s+[✅🚧📋💡].*)?$",
                data["name"],
            )
        _update_metadata_block(
            lines,
            start + 1,
            {
                "duration": data.get("duration"),
                "status": data.get("status"),
                "priority": data.get("priority"),
                "completion": data.get("completion"),
            },
        )
        _write_lines(todo_path, lines)
        phase_path = Path("docs/phases") / f"{phase_id}.md"
        if phase_path.exists():
            phase_lines = _read_lines(phase_path)
            if phase_lines:
                if "name" in data and data["name"]:
                    phase_lines[0] = _replace_heading_name(
                        phase_lines[0],
                        r"^(#\\s+Phase\\s+[\\w\\d]+:\\s+)(.+?)(\\s+[✅🚧📋💡].*)?$",
                        data["name"],
                    )
                _update_metadata_block(
                    phase_lines,
                    1,
                    {
                        "duration": data.get("duration"),
                        "status": data.get("status"),
                        "priority": data.get("priority"),
                        "completion": data.get("completion"),
                    },
                )
                _write_lines(phase_path, phase_lines)
        return f"Updated phase '{phase_id}'."

    def _apply_phase_remove(self, data: Dict[str, Any]) -> str:
        phase_id = data.get("phase_id")
        if not phase_id:
            raise ActionExecutionError("phase.remove requires phase_id.")
        todo_path = Path("docs/todo.md")
        lines = _read_lines(todo_path)
        block = _find_phase_block(lines, phase_id)
        if not block:
            raise ActionExecutionError(f"Phase '{phase_id}' not found in docs/todo.md.")
        start, end = block
        del lines[start:end]
        _write_lines(todo_path, lines)
        phase_path = Path("docs/phases") / f"{phase_id}.md"
        if phase_path.exists():
            phase_path.unlink()
        return f"Removed phase '{phase_id}'."

    def _apply_task_add(self, data: Dict[str, Any]) -> str:
        name = data.get("name")
        phase_id = data.get("phase_id")
        if not name or not phase_id:
            raise ActionExecutionError("task.add requires phase_id and name.")
        phase_path = Path("docs/phases") / f"{phase_id}.md"
        if not phase_path.exists():
            raise ActionExecutionError(f"Phase file docs/phases/{phase_id}.md not found.")
        lines = _read_lines(phase_path)
        task_number = _next_task_number(phase_id, lines)
        suffix_match = re.search(r"(\\d+)$", task_number)
        task_suffix = suffix_match.group(1) if suffix_match else task_number.split(".")[-1]
        task_id = data.get("task_id") or f"{phase_id}-{task_suffix}"
        insert_at = len(lines)
        found_task = False
        for idx, line in enumerate(lines):
            if parse_task_heading(line.strip()):
                found_task = True
                end = idx + 1
                while end < len(lines):
                    if parse_task_heading(lines[end].strip()):
                        break
                    if parse_heading(lines[end].strip()):
                        break
                    end += 1
                insert_at = end
        if not found_task:
            for idx, line in enumerate(lines):
                heading = parse_heading(line.strip())
                if heading and heading[0] == 2 and heading[1].strip().lower().startswith("tasks"):
                    insert_at = idx + 1
                    while insert_at < len(lines) and not lines[insert_at].strip():
                        insert_at += 1
                    break
        if insert_at > 0 and lines[insert_at - 1].strip():
            lines.insert(insert_at, "")
            insert_at += 1
        task_lines = [
            f"### Task {task_number}: {name}",
            _format_quoted_value("task_id", task_id),
        ]
        if "priority" in data:
            task_lines.append(_format_quoted_value("priority", data.get("priority")))
        if "estimated_hours" in data:
            task_lines.append(_format_quoted_value("estimated_hours", data.get("estimated_hours")))
        task_lines.extend([""])
        lines[insert_at:insert_at] = task_lines
        _write_lines(phase_path, lines)
        return f"Added task '{task_id}' to phase '{phase_id}'."

    def _apply_task_edit(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.edit requires task_id.")
        phases_dir = Path("docs/phases")
        if not phases_dir.exists():
            raise ActionExecutionError("docs/phases directory not found.")
        for phase_path in phases_dir.glob("*.md"):
            lines = _read_lines(phase_path)
            block = _find_task_block(lines, task_id)
            if not block:
                continue
            start, _ = block
            if "name" in data and data["name"]:
                lines[start] = _replace_heading_name(
                    lines[start],
                    r"^(###\\s+Task\\s+[\\d.]+:\\s+)(.+?)(\\s+[✅🚧📋💡].*)?$",
                    data["name"],
                )
            _update_metadata_block(
                lines,
                start + 1,
                {
                    "priority": data.get("priority"),
                    "estimated_hours": data.get("estimated_hours"),
                    "completed": data.get("completed"),
                },
            )
            _write_lines(phase_path, lines)
            return f"Updated task '{task_id}'."
        raise ActionExecutionError(f"Task '{task_id}' not found in phase files.")

    def _apply_task_complete(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.complete requires task_id.")
        phases_dir = Path("docs/phases")
        if not phases_dir.exists():
            raise ActionExecutionError("docs/phases directory not found.")
        for phase_path in phases_dir.glob("*.md"):
            lines = _read_lines(phase_path)
            block = _find_task_block(lines, task_id)
            if not block:
                continue
            start, _ = block
            _update_metadata_block(lines, start + 1, {"completed": True})
            _write_lines(phase_path, lines)
            return f"Completed task '{task_id}'."
        raise ActionExecutionError(f"Task '{task_id}' not found in phase files.")

    def _apply_task_remove(self, data: Dict[str, Any]) -> str:
        task_id = data.get("task_id")
        if not task_id:
            raise ActionExecutionError("task.remove requires task_id.")
        phases_dir = Path("docs/phases")
        if not phases_dir.exists():
            raise ActionExecutionError("docs/phases directory not found.")
        for phase_path in phases_dir.glob("*.md"):
            lines = _read_lines(phase_path)
            block = _find_task_block(lines, task_id)
            if not block:
                continue
            start, end = block
            del lines[start:end]
            _write_lines(phase_path, lines)
            return f"Removed task '{task_id}'."
        raise ActionExecutionError(f"Task '{task_id}' not found in phase files.")
