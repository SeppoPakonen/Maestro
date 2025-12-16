"""
Pure data structures for the Midnight Commander–style menubar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Union

MenuAction = Callable[[], Optional[Awaitable[None]]]


@dataclass
class Separator:
    """Visual separator between menu items."""

    label: str = "─" * 10


@dataclass
class MenuItem:
    """Single menu entry with metadata."""

    id: str
    label: str
    action: Optional[MenuAction] = None
    key_hint: Optional[str] = None
    enabled: bool = True
    trust_label: str = ""
    requires_confirmation: bool = False
    confirmation_label: Optional[str] = None
    # Optional standardized action identifier (e.g. "sessions.new")
    action_id: Optional[str] = None
    # Optional explicit F-key hint separate from legacy key_hint
    fkey: Optional[str] = None

    def display_label(self) -> str:
        """Compose the visible label with key hints and trust indicators."""
        hint = f"[{self.key_hint}]" if self.key_hint else ""
        trust = f" {self.trust_label}" if self.trust_label else ""
        return f"{self.label} {hint}{trust}".strip()


MenuEntry = Union[MenuItem, Separator]


@dataclass
class Menu:
    """Top-level menu definition."""

    label: str
    items: List[MenuEntry] = field(default_factory=list)


@dataclass
class MenuBar:
    """Menubar definition containing the ordered menus."""

    menus: List[Menu] = field(default_factory=list)
    session_summary: str = ""

