"""
Textual widget implementing Midnight Commander–style menubar behavior.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static

from maestro.tui.menubar.model import Menu, MenuBar, MenuEntry, MenuItem, Separator


class MenuActionRequested(Message):
    """Raised when the user activates a menu item."""

    def __init__(self, sender: Widget, menu: Menu, item: MenuItem, enabled: bool) -> None:
        super().__init__()
        self.menu = menu
        self.item = item
        self.enabled = enabled


class MenuBarDeactivated(Message):
    """Raised when the menubar closes and focus should be restored."""

    def __init__(self, sender: Widget) -> None:
        super().__init__()


class MenuBarWidget(Widget):
    """Keyboard-first menubar with MC navigation semantics."""

    DEFAULT_CSS = """
    MenuBarWidget {
        layout: vertical;
        background: $surface;
        color: $text;
        height: 5;
        border-bottom: solid $primary 50%;
    }

    #menu-row {
        height: 1;
        padding: 0 1;
        text-style: bold;
        background: $panel 80%;
    }

    #menu-row Label {
        height: 1;
        content-align: left middle;
        padding-right: 2;
    }

    #menu-summary {
        content-align: right middle;
        width: 1fr;
        color: $text 80%;
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

    .menu-item--disabled {
        color: $text 40%;
    }
    """

    can_focus = True
    is_active: reactive[bool] = reactive(False)
    is_open: reactive[bool] = reactive(False)

    def __init__(self, menu_bar: Optional[MenuBar] = None) -> None:
        super().__init__()
        self.menu_bar: MenuBar = menu_bar or MenuBar()
        self._menu_labels: Dict[str, Label] = {}
        self.active_menu_index: int = 0
        self.active_item_index: int = 0
        self._summary_label: Optional[Label] = None
        self._render_serial: int = 0

    def compose(self) -> ComposeResult:
        """Compose the menubar rows."""
        with Vertical():
            with Horizontal(id="menu-row"):
                for idx, menu in enumerate(self.menu_bar.menus):
                    label = Label(menu.label, id=self._title_id(idx))
                    self._menu_labels[menu.label] = label
                    yield label
                self._summary_label = Label(self.menu_bar.session_summary, id="menu-summary")
                yield self._summary_label
            yield ListView(id="menu-items")

    def on_mount(self) -> None:
        """Ensure the list view starts closed."""
        self._refresh_titles()
        self._refresh_items()
        self._set_items_visible(False)

    def set_menus(self, menus: List[Menu]) -> None:
        """Replace the menus and refresh visuals."""
        self.menu_bar = replace(self.menu_bar, menus=list(menus))
        self.active_menu_index = min(self.active_menu_index, max(len(menus) - 1, 0))
        if self.is_mounted:
            self._render_titles()
            self._refresh_items()

    def set_session_summary(self, summary: str) -> None:
        """Update the session summary label."""
        self.menu_bar = replace(self.menu_bar, session_summary=summary)
        if self.is_mounted:
            summary_label = self._summary_label or self.query_one("#menu-summary", Label)
            summary_label.update(summary)

    def activate(self) -> None:
        """Focus the menubar without opening items."""
        self.is_active = True
        self.is_open = False
        self.active_menu_index = 0
        self.active_item_index = 0
        self.focus()
        self._refresh_titles()
        self._set_items_visible(False)

    def deactivate(self) -> None:
        """Close any open menu and relinquish focus."""
        self.is_active = False
        self.is_open = False
        self.active_item_index = 0
        self._refresh_titles()
        self._set_items_visible(False)
        self.post_message(MenuBarDeactivated(self))

    def open_current_menu(self) -> None:
        """Open the active menu."""
        if not self.menu_bar.menus:
            return
        self.active_item_index = 0
        self.is_open = True
        self._set_items_visible(True)
        self._refresh_items()

    def close_menu(self) -> None:
        """Close the currently open menu."""
        self.is_open = False
        self._set_items_visible(False)
        self._refresh_titles()

    @property
    def current_menu(self) -> Optional[Menu]:
        """Return the active menu if one exists."""
        if not self.menu_bar.menus:
            return None
        return self.menu_bar.menus[self.active_menu_index % len(self.menu_bar.menus)]

    def on_key(self, event: events.Key) -> None:
        """MC-style keyboard handling."""
        if not self.is_active:
            return

        key = event.key
        if key == "escape":
            self.deactivate()
            event.stop()
            return

        if key in ("left", "right"):
            self._move_menu(-1 if key == "left" else 1)
            event.stop()
            return

        if not self.is_open and key in ("enter", "down"):
            self.open_current_menu()
            event.stop()
            return

        if not self.is_open:
            return

        if key in ("up", "down"):
            self._move_item(-1 if key == "up" else 1)
            event.stop()
            return

        if key == "enter":
            self._activate_current()
            event.stop()

    def _move_menu(self, delta: int) -> None:
        """Switch top-level menus."""
        if not self.menu_bar.menus:
            return
        self.active_menu_index = (self.active_menu_index + delta) % len(self.menu_bar.menus)
        self.active_item_index = 0
        self._refresh_titles()
        if self.is_open:
            self._refresh_items()

    def _move_item(self, delta: int) -> None:
        """Move the selection inside the open menu."""
        menu = self.current_menu
        if not menu or not menu.items:
            return
        selectable = [i for i in menu.items if isinstance(i, MenuItem)]
        if not selectable:
            return
        self.active_item_index = (self.active_item_index + delta) % len(selectable)
        self._sync_list_index()

    def _activate_current(self) -> None:
        """Activate the current item if enabled."""
        menu = self.current_menu
        if not menu:
            self.deactivate()
            return
        items = [i for i in menu.items if isinstance(i, MenuItem)]
        if not items:
            self.deactivate()
            return
        self.active_item_index = max(0, min(self.active_item_index, len(items) - 1))
        item = items[self.active_item_index]
        self.post_message(MenuActionRequested(self, menu, item, item.enabled))
        self.deactivate()

    def _refresh_titles(self) -> None:
        """Update top row highlighting."""
        if not self.is_mounted:
            return
        for menu in self.menu_bar.menus:
            label = self._menu_labels.get(menu.label)
            if not label:
                continue
            label.remove_class("menu-title--active")
            if self.is_active and menu == self.current_menu:
                label.add_class("menu-title--active")

    def _render_titles(self) -> None:
        """Rebuild the top row when menus change."""
        row = self.query_one("#menu-row", Horizontal)
        existing_labels = [child for child in row.children if isinstance(child, Label) and child.id != "menu-summary"]
        summary_label = self._summary_label or self.query_one("#menu-summary", Label)
        summary_label.update(self.menu_bar.session_summary)

        if existing_labels and len(existing_labels) == len(self.menu_bar.menus):
            self._menu_labels.clear()
            for idx, (label_widget, menu) in enumerate(zip(existing_labels, self.menu_bar.menus)):
                label_widget.update(menu.label)
                self._menu_labels[menu.label] = label_widget
            self._refresh_titles()
            return

        await_remove = row.remove_children(selector="*")
        if hasattr(await_remove, "wait"):
            try:
                await_remove.wait()
            except Exception:
                pass

        self._menu_labels.clear()
        for idx, menu in enumerate(self.menu_bar.menus):
            label = Label(menu.label, id=self._title_id(idx))
            self._menu_labels[menu.label] = label
            row.mount(label)
        self._summary_label = Label(self.menu_bar.session_summary, id="menu-summary")
        row.mount(self._summary_label)
        self._refresh_titles()

    def _refresh_items(self) -> None:
        """Populate the ListView with the current menu items."""
        if not self.is_mounted:
            return
        self._render_serial += 1
        list_view = self.query_one("#menu-items", ListView)
        cleared = list_view.clear()
        if hasattr(cleared, "wait"):
            try:
                cleared.wait()
            except Exception:
                pass
        menu = self.current_menu
        if not menu or not menu.items:
            list_view.append(ListItem(Label("No items [RO]")))
            list_view.index = 0
            return

        selectable_index = 0
        for entry in menu.items:
            if isinstance(entry, Separator):
                list_view.append(ListItem(Static(entry.label)))
                continue

            label = Label(entry.display_label())
            classes = []
            if not entry.enabled:
                classes.append("menu-item--disabled")
            item_id = f"menu-item-{self._render_serial}-{entry.id}"
            list_view.append(ListItem(label, classes=" ".join(classes) if classes else None, id=item_id))
            selectable_index += 1

        self._sync_list_index()

    def _sync_list_index(self) -> None:
        """Ensure the ListView cursor matches active_item_index."""
        list_view = self.query_one("#menu-items", ListView)
        menu = self.current_menu
        selectable = [i for i in (menu.items if menu else []) if isinstance(i, MenuItem)]
        if not selectable:
            list_view.index = 0
            return
        self.active_item_index = max(0, min(self.active_item_index, len(selectable) - 1))
        list_view.index = self.active_item_index

    def _set_items_visible(self, visible: bool) -> None:
        """Show or hide the dropdown area without changing height."""
        if not self.is_mounted:
            return
        list_view = self.query_one("#menu-items", ListView)
        list_view.display = "block" if visible else "none"

    def _title_id(self, index: int) -> str:
        """Create a stable id for a menu label."""
        return f"menu-title-{index}"
