"""
Textual widget implementing Midnight Commander–style menubar behavior with true overlays.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

from maestro.tui.menubar.model import Menu, MenuBar, MenuEntry, MenuItem, Separator
from maestro.tui.menubar.dropdown_modal import MenuDropdownModal


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
    """Keyboard-first menubar with MC navigation semantics using modal overlays."""

    DEFAULT_CSS = """
    MenuBarWidget {
        layout: horizontal;
        background: $surface;
        color: $text;
        height: 1;
        border-bottom: solid $primary 50%;
    }

    #menu-row {
        height: 1;
        padding: 0 1;
        text-style: bold;
        background: $panel 80%;
        width: 1fr;
    }

    #menu-row Label {
        height: 1;
        content-align: left middle;
        padding-right: 2;
    }

    #menu-row Label:hover {
        background: $primary 20%;
        text-style: bold;
    }

    #menu-summary {
        content-align: right middle;
        width: 1fr;
        color: $text 80%;
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
        self._current_dropdown_modal: Optional[MenuDropdownModal] = None

    def compose(self) -> ComposeResult:
        """Compose the menubar row."""
        with Horizontal(id="menu-row"):
            for idx, menu in enumerate(self.menu_bar.menus):
                label = Label(menu.label, id=self._title_id(idx))
                self._menu_labels[menu.label] = label
                yield label
            self._summary_label = Label(self.menu_bar.session_summary, id="menu-summary")
            yield self._summary_label

    def on_mount(self) -> None:
        """Initial setup."""
        self._refresh_titles()

    def set_menus(self, menus: List[Menu]) -> None:
        """Replace the menus and refresh visuals."""
        self.menu_bar = replace(self.menu_bar, menus=list(menus))
        self.active_menu_index = min(self.active_menu_index, max(len(menus) - 1, 0))
        if self.is_mounted:
            self._render_titles()

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

    def deactivate(self) -> None:
        """Close any open menu and relinquish focus."""
        self.is_active = False
        self.is_open = False
        self.active_item_index = 0
        self._refresh_titles()
        self._close_dropdown_modal()
        self.post_message(MenuBarDeactivated(self))

    def open_current_menu(self) -> None:
        """Open the active menu as a modal overlay."""
        if not self.menu_bar.menus:
            return
        menu = self.current_menu
        if not menu:
            return
            
        self.active_item_index = 0
        
        # Prepare menu items for the modal
        items = []
        disabled_indices = []
        for idx, entry in enumerate(menu.items):
            if isinstance(entry, Separator):
                items.append(entry.label)
            elif isinstance(entry, MenuItem):
                items.append(entry.display_label())
                if not entry.enabled:
                    disabled_indices.append(len(items) - 1)
        
        # Create and show the modal dropdown
        self._current_dropdown_modal = MenuDropdownModal(
            items=items,
            disabled_indices=disabled_indices,
            initial_index=0
        )
        
        # Handle the result when the modal closes
        def handle_selection(result: Optional[int]) -> None:
            if result is not None and 0 <= result < len(menu.items):
                # Get the corresponding MenuItem (skip separators)
                selectable_items = [item for item in menu.items if isinstance(item, MenuItem)]
                if result < len(selectable_items):
                    item = selectable_items[result]
                    self.post_message(MenuActionRequested(self, menu, item, item.enabled))
            self.deactivate()
        
        self.app.push_screen(self._current_dropdown_modal, callback=handle_selection)
        self.is_open = True
        self._refresh_titles()

    def close_menu(self) -> None:
        """Close the currently open menu."""
        self._close_dropdown_modal()
        self.is_open = False
        self._refresh_titles()

    def _close_dropdown_modal(self) -> None:
        """Close any open dropdown modal."""
        if self._current_dropdown_modal:
            try:
                self.app.pop_screen()
            except Exception:
                # Modal might already be closed
                pass
            self._current_dropdown_modal = None

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
            # Navigation within dropdown is handled by the modal
            event.stop()
            return

        if key == "enter":
            # Selection is handled by the modal
            event.stop()

    def on_click(self, event: events.Click) -> None:
        """Handle mouse clicks on the menubar."""
        # Check if click is on the top menu row using the widget's region
        menu_row = self.query_one("#menu-row", Horizontal)
        # Use the widget's region to check if click is within the menu row area
        if menu_row.region.contains(event.x, event.y):
            # Find which menu was clicked
            for idx, (menu, label) in enumerate(zip(self.menu_bar.menus, self._menu_labels.values())):
                # Get the position and size of the label widget
                if label.region.contains(event.x, event.y):
                    self.active_menu_index = idx
                    if self.is_open and idx == self.active_menu_index:
                        # If clicked on the currently open menu, close it
                        self.close_menu()
                    else:
                        # Close any existing dropdown first
                        self._close_dropdown_modal()
                        # Open the clicked menu
                        self.open_current_menu()
                        self._refresh_titles()
                    event.stop()
                    return
            # If click was in the menu row but not on a label, close menu
            if self.is_open:
                self.close_menu()
        # Click outside the menu row - close the menu if it's open
        elif self.is_open:
            self.close_menu()

    def _move_menu(self, delta: int) -> None:
        """Switch top-level menus."""
        if not self.menu_bar.menus:
            return
        self.active_menu_index = (self.active_menu_index + delta) % len(self.menu_bar.menus)
        self.active_item_index = 0
        self._refresh_titles()
        if self.is_open:
            # If menu is open, close the current dropdown and open the new one
            self._close_dropdown_modal()
            self.open_current_menu()

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

    def _title_id(self, index: int) -> str:
        """Create a stable id for a menu label."""
        return f"menu-title-{index}"