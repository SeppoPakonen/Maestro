"""
Lightweight Midnight Commander–style menubar widget.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView
from textual.containers import Horizontal, Vertical


@dataclass
class MenuItem:
    """Represents a single menu item with a trust label."""

    id: str
    label: str
    trust: str = "[RO]"
    payload: Optional[str] = None

    @property
    def display(self) -> str:
        """Renderable label with trust indicator."""
        trust = self.trust.strip()
        return f"{self.label} {trust}" if trust else self.label


class MenuItemActivated(Message):
    """Message posted when a menu item is activated."""

    def __init__(self, sender: Widget, menu: str, item: MenuItem) -> None:
        super().__init__()
        self.menu = menu
        self.item = item


class Menubar(Widget):
    """Top menubar with open/close navigation and dynamic actions."""

    DEFAULT_CSS = """
    Menubar {
        layout: vertical;
        background: $surface;
        color: $text;
        height: 5;
    }

    #menu-row {
        height: 1;
        padding: 0 1;
        text-style: bold;
    }

    #menu-row Label {
        height: 1;
        content-align: left middle;
        padding-right: 2;
    }

    #menu-summary {
        content-align: right middle;
    }

    #menu-items {
        height: 4;
        border: solid $primary 50%;
        background: $panel;
    }

    .menu-title--active {
        color: $accent;
        text-style: bold reverse;
    }
    """

    can_focus = True

    def __init__(self, session_summary: str = "") -> None:
        super().__init__()
        self.menu_order: List[str] = ["Maestro", "Navigation", "View", "Actions", "Help"]
        self.menu_items: Dict[str, List[MenuItem]] = {name: [] for name in self.menu_order}
        self.menu_labels: Dict[str, Label] = {}
        self.active_menu_index: int = 0
        self.active_item_index: int = 0
        self.is_open: bool = False
        self.session_summary = session_summary

    def compose(self) -> ComposeResult:
        """Compose menubar titles and placeholder for items."""
        with Horizontal(id="menu-row"):
            for title in self.menu_order:
                label = Label(title, id=f"menu-title-{title.lower()}")
                self.menu_labels[title] = label
                yield label
            yield Label(self.session_summary, id="menu-summary")
        yield ListView(id="menu-items")

    def set_session_summary(self, summary: str) -> None:
        """Update the session/plan/build summary on the right."""
        self.session_summary = summary
        summary_label = self.query_one("#menu-summary", Label)
        summary_label.update(summary)

    def set_menu_items(self, menu: str, items: List[MenuItem]) -> None:
        """Replace items for the specified menu."""
        self.menu_items[menu] = items
        if self.is_open and self.current_menu == menu:
            self._refresh_items()

    @property
    def current_menu(self) -> str:
        """Name of the currently highlighted top-level menu."""
        return self.menu_order[self.active_menu_index % len(self.menu_order)]

    def open(self, menu: Optional[str] = None) -> None:
        """Open the menubar, optionally focusing a specific menu."""
        if menu and menu in self.menu_order:
            self.active_menu_index = self.menu_order.index(menu)
        self.is_open = True
        self.focus()
        self._refresh_titles()
        self._refresh_items()

    def close(self) -> None:
        """Close the menubar and reset item index."""
        self.is_open = False
        self.active_item_index = 0
        self._refresh_titles()

    def toggle(self) -> None:
        """Toggle menu open/close."""
        if self.is_open:
            self.close()
        else:
            self.open()

    def on_key(self, event: events.Key) -> None:
        """Handle navigation when menu is open."""
        if not self.is_open:
            return

        key = event.key
        if key in ("left", "right"):
            self._move_menu(-1 if key == "left" else 1)
            event.stop()
        elif key in ("up", "down"):
            self._move_item(-1 if key == "up" else 1)
            event.stop()
        elif key == "enter":
            self._activate_current()
            event.stop()

    def _move_menu(self, delta: int) -> None:
        """Move between top-level menus."""
        self.active_menu_index = (self.active_menu_index + delta) % len(self.menu_order)
        self.active_item_index = 0
        self._refresh_titles()
        self._refresh_items()

    def _move_item(self, delta: int) -> None:
        """Move the selection within the current menu list."""
        items = self.menu_items.get(self.current_menu, [])
        if not items:
            return
        self.active_item_index = (self.active_item_index + delta) % len(items)
        list_view = self.query_one("#menu-items", ListView)
        list_view.index = self.active_item_index

    def _activate_current(self) -> None:
        """Activate the currently selected item."""
        items = self.menu_items.get(self.current_menu, [])
        if not items:
            self.close()
            return
        self.active_item_index = max(0, min(self.active_item_index, len(items) - 1))
        item = items[self.active_item_index]
        self.post_message(MenuItemActivated(self, self.current_menu, item))
        self.close()

    def _refresh_titles(self) -> None:
        """Highlight the active menu title when open."""
        for name, label in self.menu_labels.items():
            label.remove_class("menu-title--active")
            if self.is_open and name == self.current_menu:
                label.add_class("menu-title--active")

    def _refresh_items(self) -> None:
        """Refresh list of items for the active menu."""
        list_view = self.query_one("#menu-items", ListView)
        list_view.clear()
        items = self.menu_items.get(self.current_menu, [])
        if not items:
            list_view.append(ListItem(Label("No items [RO]")))
            self.active_item_index = 0
            list_view.index = 0
            return

        for menu_item in items:
            list_view.append(ListItem(Label(menu_item.display)))
        self.active_item_index = max(0, min(self.active_item_index, len(items) - 1))
        list_view.index = self.active_item_index
