"""
Pane view contract for MC shell panes.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Iterable, List, Optional, Set

from textual.message import Message
from textual.widget import Widget

try:
    # Reuse existing menu item definition when available
    from maestro.tui.widgets.menubar import MenuItem  # type: ignore
except Exception:  # pragma: no cover - defensive import
    MenuItem = None  # type: ignore


class PaneStatus(Message):
    """Notify the shell of a status update originating from a pane."""

    def __init__(self, sender: Widget, message: str) -> None:
        super().__init__()
        self.message = message


class PaneFocusRequest(Message):
    """Request that the shell move focus to a target pane."""

    def __init__(self, sender: Widget, target: str) -> None:
        super().__init__()
        self.target = target


class PaneView(Widget):
    """Base contract for right-pane views."""

    can_focus = True

    def __init__(self) -> None:
        super().__init__()
        self._background_tasks: Set[asyncio.Task] = set()

    async def refresh_data(self) -> None:  # pragma: no cover - interface
        """Refresh the pane's data."""
        raise NotImplementedError

    def title(self) -> str:  # pragma: no cover - interface
        """Return the display title for this pane."""
        return self.__class__.__name__

    def menu_actions(self) -> Optional[List["MenuItem"]]:  # pragma: no cover - interface
        """Optional menu actions specific to this pane."""
        return None

    def handle_action(self, action_id: str) -> bool:
        """Handle an action triggered from the menubar. Return True if handled."""
        return False

    def notify_status(self, message: str) -> None:
        """Send a status update to the hosting shell."""
        self.post_message(PaneStatus(self, message))

    def request_focus_left(self) -> None:
        """Ask the shell to move focus back to the left navigation."""
        self.post_message(PaneFocusRequest(self, "left"))

    def add_background_task(self, coro: asyncio.Future) -> None:
        """Track a background coroutine and ensure cleanup on unmount."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(lambda t: self._background_tasks.discard(t))

    def on_unmount(self) -> None:
        """Ensure background tasks are cancelled."""
        for task in list(self._background_tasks):
            task.cancel()
        self._background_tasks.clear()


PaneFactory = Callable[[], PaneView]


def ensure_iterable(items: Optional[Iterable["MenuItem"]]) -> List["MenuItem"]:
    """Utility to normalize optional iterable results."""
    return list(items) if items else []
