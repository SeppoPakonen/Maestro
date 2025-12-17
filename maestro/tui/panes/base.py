"""
Pane view contract for MC shell panes.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional, Set, Protocol, Any
from abc import abstractmethod

from textual.message import Message
from textual.widget import Widget

from maestro.tui.menubar.model import Menu, MenuItem  # type: ignore


class MCPane(Protocol):
    """Formal contract for MC shell panes - following the principle: A pane is a component, not a script."""

    pane_id: str
    pane_title: str

    @abstractmethod
    def on_mount(self) -> None:
        """Called when the pane is mounted to the DOM. Initialize UI elements and event handlers here."""
        ...

    @abstractmethod
    def on_focus(self) -> None:
        """Called when the pane receives focus. Perform focus-specific operations."""
        ...

    @abstractmethod
    def on_blur(self) -> None:
        """Called when the pane loses focus. Perform cleanup of focus-specific resources."""
        ...

    @abstractmethod
    def refresh(self) -> None:
        """Refresh pane data and UI. This is for explicit refresh requests."""
        ...

    @abstractmethod
    def get_menu_spec(self) -> "Menu":
        """Return the menu specification for this pane."""
        ...


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
    """Base contract for right-pane views implementing the MCPane protocol."""

    can_focus = True

    def __init__(self) -> None:
        super().__init__()
        self._background_tasks: Set[asyncio.Task] = set()
        # Initialize required attributes for the contract
        self.pane_id: str = self.__class__.__name__
        self.pane_title: str = self.__class__.__name__

    def on_mount(self) -> None:
        """Called when the pane is mounted to the DOM. Initialize UI elements and event handlers here."""
        # Initialize the pane - override in subclass
        pass

    def on_focus(self) -> None:
        """Called when the pane receives focus. Perform focus-specific operations."""
        # Handle focus - override in subclass
        pass

    def on_blur(self) -> None:
        """Called when the pane loses focus. Perform cleanup of focus-specific resources."""
        # Handle blur - override in subclass
        pass

    def refresh(self, *, layout: bool = False, **kwargs) -> None:
        """Refresh pane data and UI. This is for explicit refresh requests."""
        # Handle the Textual Widget refresh call with proper parameters
        # Call the parent Widget's refresh for UI updates
        from textual.widget import Widget
        Widget.refresh(self, layout=layout, **kwargs)

        # Also trigger data refresh for protocol compliance
        # But do this as a deferred call to avoid blocking UI refresh
        self.call_after_refresh(self.refresh_data)

    def refresh_data(self) -> None:
        """Refresh pane's data. Override this in subclasses to trigger data reload."""
        # Refresh data - override in subclass
        pass

    def get_menu_spec(self) -> "Menu":
        """Return the menu specification for this pane."""
        # Return menu spec - override in subclass
        from maestro.tui.menubar.model import Menu
        return Menu(label=self.pane_title, items=[])

    async def refresh_data(self) -> None:  # pragma: no cover - interface
        """Refresh the pane's data."""
        # For backward compatibility - deprecated in favor of refresh()
        raise NotImplementedError

    def title(self) -> str:  # pragma: no cover - interface
        """Return the display title for this pane (backward compatibility)."""
        return self.pane_title

    def menu(self) -> Optional["Menu"]:  # pragma: no cover - interface
        """Optional menu owned by this pane (backward compatibility)."""
        return None

    def get_action(self, action_id: str) -> Optional[MenuItem]:
        """Lookup a menu item by standardized action_id or id.

        Returns the MenuItem if found, otherwise None.
        """
        try:
            menu = self.menu()
        except Exception:
            menu = None
        if not menu or not getattr(menu, "items", None):
            return None
        for entry in menu.items:
            if not isinstance(entry, MenuItem):
                continue
            if entry.action_id == action_id or entry.id == action_id:
                return entry
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

# IMPORT-SAFE: no side effects allowed
