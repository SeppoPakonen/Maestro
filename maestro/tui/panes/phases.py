"""
Phases pane for Maestro TUI.

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


class PhasesPane(PaneView):
    """Phases view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_phase", "Select phase"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    PhasesPane {
        layout: vertical;
    }

    #phases-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #phases-body {
        height: 1fr;
    }

    #phases-list-pane, #phases-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #phases-list-pane {
        width: 45%;
    }

    #phases-detail-pane {
        width: 55%;
    }

    #phases-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "phases"  # Required for the contract
        self.pane_title = "Phases"  # Required for the contract
        self.phases: List[str] = []  # Placeholder for phase data
        self.selected_phase_id: Optional[str] = None

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
                    action_id="phases.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Phases", id="phases-header")
        with Horizontal(id="phases-body"):
            with Vertical(id="phases-list-pane"):
                yield Label("Phase List", id="phases-list-title")
                yield ListView(id="phases-list")
            with Vertical(id="phases-detail-pane"):
                yield Label("Details", id="phases-detail-title")
                yield Static("Select a phase to view details.", id="phase-detail")
        yield Label("", id="phases-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#phases-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to phases UI facade
        self.phases = ["Phase 1", "Phase 2", "Phase 3"]  # Replace with real data
        if self.phases and self.selected_phase_id is None:
            self.selected_phase_id = self.phases[0] if self.phases else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Phases refreshed")

    def _render_list(self) -> None:
        """Render the ListView from phase data."""
        list_view = self.query_one("#phases-list", ListView)
        list_view.clear()
        for phase in self.phases:
            list_view.append(ListItem(Label(phase)))

        if not self.phases:
            list_view.append(ListItem(Label("No phases found [RO]")))
            list_view.index = 0
            self.selected_phase_id = None
            return

        # Restore selection
        if self.selected_phase_id not in self.phases:
            self.selected_phase_id = self.phases[0]
        list_view.index = self.phases.index(self.selected_phase_id) if self.selected_phase_id in self.phases else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected phase."""
        detail_widget = self.query_one("#phase-detail", Static)
        if not self.selected_phase_id:
            detail_widget.update("No phase selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Phase:[/b] {self.selected_phase_id}",
            f"[b]Status:[/b] Active",
            f"[b]Progress:[/b] 50%",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#phases-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#phases-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_phase_id from ListView and refresh details."""
        list_view = self.query_one("#phases-list", ListView)
        if list_view.index is None or not self.phases:
            return
        idx = max(0, min(list_view.index, len(self.phases) - 1))
        self.selected_phase_id = self.phases[idx] if idx < len(self.phases) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "phases-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_phase(self) -> None:
        """Select the current phase."""
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
            self.query_one("#phases-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("phases", PhasesPane)

# IMPORT-SAFE: no side effects allowed