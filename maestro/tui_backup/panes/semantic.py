"""
Semantic pane for Maestro TUI.

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


class SemanticPane(PaneView):
    """Semantic view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_finding", "Select finding"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    SemanticPane {
        layout: vertical;
    }

    #semantic-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #semantic-body {
        height: 1fr;
    }

    #semantic-list-pane, #semantic-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #semantic-list-pane {
        width: 45%;
    }

    #semantic-detail-pane {
        width: 55%;
    }

    #semantic-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "semantic"  # Required for the contract
        self.pane_title = "Semantic"  # Required for the contract
        self.findings: List[str] = []  # Placeholder for semantic finding data
        self.selected_finding_id: Optional[str] = None

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
                    action_id="semantic.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Semantic", id="semantic-header")
        with Horizontal(id="semantic-body"):
            with Vertical(id="semantic-list-pane"):
                yield Label("Semantic Findings", id="semantic-list-title")
                yield ListView(id="semantic-list")
            with Vertical(id="semantic-detail-pane"):
                yield Label("Details", id="semantic-detail-title")
                yield Static("Select a semantic finding to view details.", id="semantic-detail")
        yield Label("", id="semantic-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#semantic-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to semantic UI facade
        self.findings = ["Finding 1", "Finding 2", "Finding 3"]  # Replace with real data
        if self.findings and self.selected_finding_id is None:
            self.selected_finding_id = self.findings[0] if self.findings else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Semantic findings refreshed")

    def _render_list(self) -> None:
        """Render the ListView from finding data."""
        list_view = self.query_one("#semantic-list", ListView)
        list_view.clear()
        for finding in self.findings:
            list_view.append(ListItem(Label(finding)))

        if not self.findings:
            list_view.append(ListItem(Label("No semantic findings found [RO]")))
            list_view.index = 0
            self.selected_finding_id = None
            return

        # Restore selection
        if self.selected_finding_id not in self.findings:
            self.selected_finding_id = self.findings[0]
        list_view.index = self.findings.index(self.selected_finding_id) if self.selected_finding_id in self.findings else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected finding."""
        detail_widget = self.query_one("#semantic-detail", Static)
        if not self.selected_finding_id:
            detail_widget.update("No semantic finding selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Finding:[/b] {self.selected_finding_id}",
            f"[b]Status:[/b] Pending",
            f"[b]Risk Level:[/b] Medium",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#semantic-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#semantic-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_finding_id from ListView and refresh details."""
        list_view = self.query_one("#semantic-list", ListView)
        if list_view.index is None or not self.findings:
            return
        idx = max(0, min(list_view.index, len(self.findings) - 1))
        self.selected_finding_id = self.findings[idx] if idx < len(self.findings) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "semantic-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_finding(self) -> None:
        """Select the current finding."""
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
            self.query_one("#semantic-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("semantic", SemanticPane)

# IMPORT-SAFE: no side effects allowed