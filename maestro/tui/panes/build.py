"""
Build pane for Maestro TUI.

Implements the MCPane contract for reliable pane behavior.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ListItem, ListView, Static

from maestro.tui.panes.base import PaneView
from maestro.tui.menubar.model import Menu, MenuItem
from maestro.tui.utils import ErrorModal, ErrorNormalizer
from maestro.tui.panes.registry import register_pane


class BuildPane(PaneView):
    """Build view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_target", "Select target"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    BuildPane {
        layout: vertical;
    }

    #build-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #build-body {
        height: 1fr;
    }

    #build-list-pane, #build-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #build-list-pane {
        width: 45%;
    }

    #build-detail-pane {
        width: 55%;
    }

    #build-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "build"  # Required for the contract
        self.pane_title = "Build"  # Required for the contract
        self.targets: List[str] = []  # Placeholder for build target data
        self.selected_target_id: Optional[str] = None

    def get_menu_spec(self) -> Menu:
        """Return the menu specification for this pane."""
        return Menu(
            label=self.pane_title,
            items=[
                MenuItem(
                    "refresh",
                    "Refresh",
                    action=self.action_refresh_data,
                    key_hint="F5",
                    fkey="F5",
                    action_id="build.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Build", id="build-header")
        with Horizontal(id="build-body"):
            with Vertical(id="build-list-pane"):
                yield Label("Build Targets", id="build-list-title")
                yield ListView(id="build-list")
            with Vertical(id="build-detail-pane"):
                yield Label("Details", id="build-detail-title")
                yield Static("Select a build target to view details.", id="build-detail")
        yield Label("", id="build-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#build-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to build UI facade
        self.targets = ["Build Target 1", "Build Target 2", "Build Target 3"]  # Replace with real data
        if self.targets and self.selected_target_id is None:
            self.selected_target_id = self.targets[0] if self.targets else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Build targets refreshed")

    def _render_list(self) -> None:
        """Render the ListView from target data."""
        list_view = self.query_one("#build-list", ListView)
        list_view.clear()
        for target in self.targets:
            list_view.append(ListItem(Label(target)))

        if not self.targets:
            list_view.append(ListItem(Label("No build targets found [RO]")))
            list_view.index = 0
            self.selected_target_id = None
            return

        # Restore selection
        if self.selected_target_id not in self.targets:
            self.selected_target_id = self.targets[0]
        list_view.index = self.targets.index(self.selected_target_id) if self.selected_target_id in self.targets else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected target."""
        detail_widget = self.query_one("#build-detail", Static)
        if not self.selected_target_id:
            detail_widget.update("No build target selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Target:[/b] {self.selected_target_id}",
            f"[b]Status:[/b] Ready",
            f"[b]Last Built:[/b] Never",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#build-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#build-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_target_id from ListView and refresh details."""
        list_view = self.query_one("#build-list", ListView)
        if list_view.index is None or not self.targets:
            return
        idx = max(0, min(list_view.index, len(self.targets) - 1))
        self.selected_target_id = self.targets[idx] if idx < len(self.targets) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "build-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_target(self) -> None:
        """Select the current target."""
        await self._sync_selection_from_list()

    async def action_refresh_data(self) -> None:
        """Allow BINDINGS to call the refresh coroutine."""
        await self.refresh_data()

    def action_focus_left(self) -> None:
        """Tab returns focus to the left navigation."""
        self.request_focus_left()

    def action_open_menu(self) -> None:
        """Expose menubar toggle from inside the pane."""
        try:
            if hasattr(self.app, "screen") and hasattr(self.app.screen, "action_toggle_menu"):
                self.app.screen.action_toggle_menu()  # type: ignore
        except Exception:
            pass

    def notify_status(self, message: str) -> None:
        """Update local status and inform shell."""
        try:
            self.query_one("#build-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("build", BuildPane)

# IMPORT-SAFE: no side effects allowed