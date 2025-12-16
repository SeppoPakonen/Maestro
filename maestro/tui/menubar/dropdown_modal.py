"""
Modal screen for MC-style dropdown menus that appears as an overlay.
"""
from __future__ import annotations

from typing import List, Optional

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


class MenuActionRequested(Message):
    """Raised when the user selects a menu item."""

    def __init__(self, sender: 'MenuDropdownModal', item_index: int) -> None:
        super().__init__()
        self.item_index = item_index


class MenuDropdownModal(ModalScreen[Optional[int]]):
    """Modal screen for displaying menu items as a dropdown overlay."""

    DEFAULT_CSS = """
    MenuDropdownModal {
        layout: vertical;
    }

    #menu-dropdown {
        border: solid $primary;
        background: $panel;
        width: auto;
        height: auto;
        max-height: 10;
        margin: 0;
    }

    #menu-dropdown ListItem {
        height: 1;
        padding: 0 1;
    }

    #menu-dropdown ListItem:hover {
        background: $primary 20%;
        text-style: bold;
    }

    #menu-dropdown .menu-item--disabled {
        color: $text 40%;
    }
    """

    BINDINGS = [
        ("escape", "close_dropdown", "Close"),
        ("enter", "select_item", "Select"),
    ]

    def __init__(
        self,
        items: List[str],
        disabled_indices: List[int],
        title: str = "",
        initial_index: int = 0,
    ) -> None:
        super().__init__()
        self.items = items
        self.disabled_indices = set(disabled_indices)
        self.title = title
        self.initial_index = initial_index

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        # Create ListView with menu items
        list_items = []
        for idx, item in enumerate(self.items):
            classes = []
            if idx in self.disabled_indices:
                classes.append("menu-item--disabled")

            item_id = f"menu-item-{idx}"
            label = Label(item)
            list_item = ListItem(label, id=item_id, classes=" ".join(classes) if classes else None)
            list_items.append(list_item)

        yield ListView(*list_items, id="menu-dropdown")

    def on_mount(self) -> None:
        """Set up the list view and initial selection."""
        list_view = self.query_one("#menu-dropdown", ListView)
        # Set initial selection
        if 0 <= self.initial_index < len(self.items):
            list_view.index = self.initial_index
        list_view.focus()

    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key in ("enter", "space"):
            # Get currently selected item from the ListView
            list_view = self.query_one("#menu-dropdown", ListView)
            selected_index = list_view.index
            self.dismiss(selected_index)
            event.stop()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection."""
        # Get the index from the event or the current index
        list_view = event.list_view
        selected_index = list_view.index if list_view.index is not None else 0
        self.dismiss(selected_index)

    def on_click(self, event: events.Click) -> None:
        """Handle clicks on menu items."""
        # Check which menu item was clicked in the ListView
        list_view = self.query_one("#menu-dropdown", ListView)
        for idx, child in enumerate(list_view.children):
            if child.region.contains(event.x, event.y):
                if idx not in self.disabled_indices:
                    self.dismiss(idx)
                else:
                    # Item is disabled, close without action
                    self.dismiss(None)
                event.stop()
                return
        # Click outside of items - close without action
        self.dismiss(None)

    def action_close_dropdown(self) -> None:
        """Close dropdown without selecting anything."""
        self.dismiss(None)

    def action_select_item(self) -> None:
        """Select the currently focused item."""
        list_view = self.query_one("#menu-dropdown", ListView)
        selected_index = list_view.index if list_view.index is not None else 0
        self.dismiss(selected_index)