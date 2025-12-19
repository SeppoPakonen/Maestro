from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


ISSUE_TYPES: Set[str] = {
    "hier",
    "convention",
    "build",
    "runtime",
    "features",
    "product",
    "look",
    "ux",
}

ISSUE_STATES: List[str] = [
    "open",
    "reacted",
    "analyzing",
    "analyzed",
    "decided",
    "fixing",
    "fixed",
    "closed",
    "cancelled",
]

STATE_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"reacted", "analyzing", "cancelled"},
    "reacted": {"analyzing", "cancelled"},
    "analyzing": {"analyzed", "cancelled"},
    "analyzed": {"decided", "cancelled"},
    "decided": {"fixing", "cancelled"},
    "fixing": {"fixed", "cancelled"},
    "fixed": {"closed", "cancelled"},
    "closed": set(),
    "cancelled": set(),
}


@dataclass
class IssueRecord:
    issue_id: str
    issue_type: str
    state: str
    priority: int
    title: str
    description: str
    file: str = ""
    line: int = 0
    column: int = 0
    created_at: str = ""
    modified_at: str = ""
    source: str = ""
    tool: Optional[str] = None
    rule: Optional[str] = None

    def is_valid_type(self) -> bool:
        return self.issue_type in ISSUE_TYPES

    def can_transition(self, next_state: str) -> bool:
        if next_state not in ISSUE_STATES:
            return False
        return next_state in STATE_TRANSITIONS.get(self.state, set())
