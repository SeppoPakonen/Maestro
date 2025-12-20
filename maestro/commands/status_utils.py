from __future__ import annotations

from datetime import datetime
from typing import Optional


def normalize_status(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "plan": "planned",
        "planned": "planned",
        "todo": "planned",
        "in_progress": "in_progress",
        "progress": "in_progress",
        "doing": "in_progress",
        "active": "in_progress",
        "done": "done",
        "complete": "done",
        "completed": "done",
        "finish": "done",
        "finished": "done",
        "proposed": "proposed",
        "proposal": "proposed",
        "idea": "proposed",
        "suggested": "proposed",
    }
    return aliases.get(normalized)


def status_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def allowed_statuses() -> str:
    return "planned, in_progress, done, proposed"


def status_badge(status: str) -> str:
    badge_map = {
        "planned": ("📋", "Planned"),
        "in_progress": ("🚧", "In Progress"),
        "done": ("✅", "Done"),
        "proposed": ("💡", "Proposed"),
    }
    emoji, label = badge_map.get(status, ("❔", "Unknown"))
    return f"{emoji} **[{label}]**"
