from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
import re
from typing import Dict, List, Optional, Tuple

from .model import ISSUE_STATES, ISSUE_TYPES, IssueRecord


@dataclass
class IssueDetails:
    issue_type: str
    title: str
    description: str
    file: str = ""
    line: int = 0
    column: int = 0
    source: str = "make"
    tool: Optional[str] = None
    rule: Optional[str] = None
    priority: int = 50
    state: str = "open"


def generate_issue_id(issue_type: str, fingerprint: str) -> str:
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
    return f"{issue_type}-{digest}"


def write_issue(details: IssueDetails, repo_root: str) -> str:
    if details.issue_type not in ISSUE_TYPES:
        details.issue_type = "build"
    if details.state not in ISSUE_STATES:
        details.state = "open"
    issue_id = generate_issue_id(
        details.issue_type,
        f"{details.file}:{details.line}:{details.column}:{details.description}:{details.tool}:{details.rule}",
    )
    issues_dir = os.path.join(repo_root, "docs", "issues")
    os.makedirs(issues_dir, exist_ok=True)
    issue_path = os.path.join(issues_dir, f"{issue_id}.md")
    if os.path.exists(issue_path):
        return issue_id

    now = datetime.now(timezone.utc).isoformat()
    location = ""
    if details.file:
        location = f"{details.file}:{details.line}:{details.column}".rstrip(":0")

    lines = [
        f"# Issue: {details.title}",
        "",
        f"\"issue_id\": \"{issue_id}\"",
        f"\"type\": \"{details.issue_type}\"",
        f"\"state\": \"{details.state}\"",
        f"\"priority\": {details.priority}",
        f"\"title\": \"{details.title}\"",
        f"\"description\": \"{details.description}\"",
        f"\"created_at\": \"{now}\"",
        f"\"modified_at\": \"{now}\"",
        f"\"source\": \"{details.source}\"",
    ]
    if details.tool:
        lines.append(f"\"tool\": \"{details.tool}\"")
    if details.rule:
        lines.append(f"\"rule\": \"{details.rule}\"")
    if details.file:
        lines.append(f"\"file\": \"{details.file}\"")
    if details.line:
        lines.append(f"\"line\": {details.line}")
    if details.column:
        lines.append(f"\"column\": {details.column}")

    lines.extend(
        [
            "",
            "## Description",
            details.description,
            "",
            "## Location",
            f"- {location or 'N/A'}",
            "",
        ]
    )
    lines.extend(
        [
            "## History",
            f"- {now}: {details.state}",
            "",
        ]
    )

    with open(issue_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return issue_id


def load_issue(issue_path: str) -> IssueRecord:
    metadata: Dict[str, str] = {}
    description_lines: List[str] = []
    in_description = False
    with open(issue_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.rstrip("\n")
            match = re.match(r"^\"([^\"]+)\":\s*(.+)$", stripped)
            if match:
                key = match.group(1)
                raw_value = match.group(2).strip()
                metadata[key] = _parse_value(raw_value)
                continue
            if stripped == "## Description":
                in_description = True
                continue
            if stripped.startswith("## ") and in_description:
                in_description = False
            if in_description:
                if stripped:
                    description_lines.append(stripped)

    return IssueRecord(
        issue_id=str(metadata.get("issue_id", "")),
        issue_type=str(metadata.get("type", "build")),
        state=str(metadata.get("state", "open")),
        priority=int(metadata.get("priority", 50) or 50),
        title=str(metadata.get("title", "")),
        description=str(metadata.get("description", "\n".join(description_lines))),
        file=str(metadata.get("file", "")),
        line=int(metadata.get("line", 0) or 0),
        column=int(metadata.get("column", 0) or 0),
        created_at=str(metadata.get("created_at", "")),
        modified_at=str(metadata.get("modified_at", "")),
        source=str(metadata.get("source", "")),
        tool=metadata.get("tool"),
        rule=metadata.get("rule"),
        solutions=_parse_list(metadata.get("solutions")),
        analysis_summary=str(metadata.get("analysis_summary", "")),
        analysis_confidence=int(metadata.get("analysis_confidence", 0) or 0),
        decision=str(metadata.get("decision", "")),
        fix_session=str(metadata.get("fix_session", "")),
    )


def list_issues(repo_root: str, issue_type: Optional[str] = None) -> List[IssueRecord]:
    issues_dir = os.path.join(repo_root, "docs", "issues")
    if not os.path.isdir(issues_dir):
        return []
    records: List[IssueRecord] = []
    for name in sorted(os.listdir(issues_dir)):
        if not name.endswith(".md"):
            continue
        record = load_issue(os.path.join(issues_dir, name))
        if issue_type and record.issue_type != issue_type:
            continue
        records.append(record)
    return records


def update_issue_state(repo_root: str, issue_id: str, new_state: str) -> bool:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        return False
    record = load_issue(issue_path)
    if new_state not in ISSUE_STATES:
        raise ValueError(f"Invalid state '{new_state}'")
    if record.state == new_state:
        return True
    if not record.can_transition(new_state):
        raise ValueError(f"Invalid transition {record.state} -> {new_state}")

    now = datetime.now(timezone.utc).isoformat()
    _update_metadata_line(issue_path, "state", new_state)
    _update_metadata_line(issue_path, "modified_at", now)
    _append_history(issue_path, now, new_state)
    return True


def rollback_issue_state(repo_root: str, issue_id: str) -> bool:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        return False
    history = _load_history(issue_path)
    if len(history) < 2:
        return False
    previous = history[-2][1]
    now = datetime.now(timezone.utc).isoformat()
    _update_metadata_line(issue_path, "state", previous)
    _update_metadata_line(issue_path, "modified_at", now)
    _append_history(issue_path, now, f"rollback:{previous}")
    return True


def update_issue_priority(repo_root: str, issue_id: str, priority: int) -> bool:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        return False
    now = datetime.now(timezone.utc).isoformat()
    _update_metadata_line(issue_path, "priority", priority)
    _update_metadata_line(issue_path, "modified_at", now)
    _append_history(issue_path, now, f"priority:{priority}")
    return True


def update_issue_metadata(repo_root: str, issue_id: str, key: str, value: str | int) -> bool:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        return False
    now = datetime.now(timezone.utc).isoformat()
    _update_metadata_line(issue_path, key, value)
    _update_metadata_line(issue_path, "modified_at", now)
    return True


def update_issue_section(repo_root: str, issue_id: str, section: str, content: List[str]) -> bool:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        return False
    _upsert_section(issue_path, section, content)
    now = datetime.now(timezone.utc).isoformat()
    _update_metadata_line(issue_path, "modified_at", now)
    return True


def _find_issue_path(repo_root: str, issue_id: str) -> Optional[str]:
    issues_dir = os.path.join(repo_root, "docs", "issues")
    candidate = os.path.join(issues_dir, f"{issue_id}.md")
    if os.path.exists(candidate):
        return candidate
    if not os.path.isdir(issues_dir):
        return None
    for name in os.listdir(issues_dir):
        if name.startswith(issue_id) and name.endswith(".md"):
            return os.path.join(issues_dir, name)
    return None


def _parse_value(raw_value: str):
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value.strip('"')
    if raw_value.lower() in ("true", "false"):
        return raw_value.lower() == "true"
    if re.match(r"^\d+$", raw_value):
        return int(raw_value)
    return raw_value


def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _update_metadata_line(issue_path: str, key: str, value: str) -> None:
    with open(issue_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    value_str = f"\"{value}\"" if isinstance(value, str) else str(value)
    replaced = False
    for idx, line in enumerate(lines):
        if line.startswith(f"\"{key}\":"):
            lines[idx] = f"\"{key}\": {value_str}\n"
            replaced = True
            break

    if not replaced:
        insert_at = _find_metadata_insert_index(lines)
        lines.insert(insert_at, f"\"{key}\": {value_str}\n")

    with open(issue_path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


def _find_metadata_insert_index(lines: List[str]) -> int:
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("\""):
            insert_at = idx + 1
        elif insert_at > 0 and line.strip() == "":
            break
    return max(insert_at, 2)


def _append_history(issue_path: str, timestamp: str, state: str) -> None:
    with open(issue_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    history_index = None
    for idx, line in enumerate(lines):
        if line.strip() == "## History":
            history_index = idx
            break

    entry = f"- {timestamp}: {state}\n"
    if history_index is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.extend(["## History\n", entry, "\n"])
    else:
        insert_at = history_index + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        lines.insert(insert_at, entry)

    with open(issue_path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


def _upsert_section(issue_path: str, section: str, content: List[str]) -> None:
    header = f"## {section}"
    with open(issue_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.strip() == header:
            start = idx
            end = idx + 1
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            break

    new_block = [f"{header}\n"]
    if content:
        for item in content:
            new_block.append(f"{item}\n")
    else:
        new_block.append("\n")
    new_block.append("\n")

    if start is None:
        insert_at = len(lines)
        for idx, line in enumerate(lines):
            if line.strip() == "## History":
                insert_at = idx
                break
        lines[insert_at:insert_at] = new_block
    else:
        lines[start:end] = new_block

    with open(issue_path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


def _load_history(issue_path: str) -> List[Tuple[str, str]]:
    history: List[Tuple[str, str]] = []
    with open(issue_path, "r", encoding="utf-8") as handle:
        in_history = False
        for line in handle:
            stripped = line.strip()
            if stripped == "## History":
                in_history = True
                continue
            if stripped.startswith("## ") and in_history:
                break
            if in_history and stripped.startswith("- "):
                parts = stripped[2:].split(":", 1)
                if len(parts) == 2:
                    timestamp = parts[0].strip()
                    state = parts[1].strip()
                    if state.startswith("rollback:"):
                        state = state.split("rollback:", 1)[1]
                    history.append((timestamp, state))
    return history
