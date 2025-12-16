"""
Pane view contract for MC shell panes.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional, Set

from textual.message import Message
from textual.widget import Widget

try:
    from maestro.tui.menubar.model import Menu  # type: ignore
except Exception:  # pragma: no cover - defensive import
    Menu = None  # type: ignore


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


class PaneMenuRequest(Message):
    """Notify the shell that the pane's menu definition changed."""

    def __init__(self, sender: Widget) -> None:
        super().__init__()


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

    def menu(self) -> Optional["Menu"]:  # pragma: no cover - interface
        """Optional menu owned by this pane."""
        return None

    def notify_status(self, message: str) -> None:
        """Send a status update to the hosting shell."""
        self.post_message(PaneStatus(self, message))

    def request_focus_left(self) -> None:
        """Ask the shell to move focus back to the left navigation."""
        self.post_message(PaneFocusRequest(self, "left"))

    def request_menu_refresh(self) -> None:
        """Notify the shell to rebuild the pane-owned menu."""
        self.post_message(PaneMenuRequest(self))

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
