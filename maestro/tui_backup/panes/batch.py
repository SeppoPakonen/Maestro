"""
Batch pane for Maestro TUI.

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


class BatchPane(PaneView):
    """Batch view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_job", "Select job"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    BatchPane {
        layout: vertical;
    }

    #batch-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #batch-body {
        height: 1fr;
    }

    #batch-list-pane, #batch-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #batch-list-pane {
        width: 45%;
    }

    #batch-detail-pane {
        width: 55%;
    }

    #batch-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "batch"  # Required for the contract
        self.pane_title = "Batch"  # Required for the contract
        self.jobs: List[str] = []  # Placeholder for batch job data
        self.selected_job_id: Optional[str] = None

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
                    action_id="batch.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Batch", id="batch-header")
        with Horizontal(id="batch-body"):
            with Vertical(id="batch-list-pane"):
                yield Label("Batch Jobs", id="batch-list-title")
                yield ListView(id="batch-list")
            with Vertical(id="batch-detail-pane"):
                yield Label("Details", id="batch-detail-title")
                yield Static("Select a batch job to view details.", id="batch-detail")
        yield Label("", id="batch-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#batch-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to batch UI facade
        self.jobs = ["Job 1", "Job 2", "Job 3"]  # Replace with real data
        if self.jobs and self.selected_job_id is None:
            self.selected_job_id = self.jobs[0] if self.jobs else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Batch jobs refreshed")

    def _render_list(self) -> None:
        """Render the ListView from job data."""
        list_view = self.query_one("#batch-list", ListView)
        list_view.clear()
        for job in self.jobs:
            list_view.append(ListItem(Label(job)))

        if not self.jobs:
            list_view.append(ListItem(Label("No batch jobs found [RO]")))
            list_view.index = 0
            self.selected_job_id = None
            return

        # Restore selection
        if self.selected_job_id not in self.jobs:
            self.selected_job_id = self.jobs[0]
        list_view.index = self.jobs.index(self.selected_job_id) if self.selected_job_id in self.jobs else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected job."""
        detail_widget = self.query_one("#batch-detail", Static)
        if not self.selected_job_id:
            detail_widget.update("No batch job selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Job:[/b] {self.selected_job_id}",
            f"[b]Status:[/b] Pending",
            f"[b]Progress:[/b] 0%",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#batch-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#batch-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_job_id from ListView and refresh details."""
        list_view = self.query_one("#batch-list", ListView)
        if list_view.index is None or not self.jobs:
            return
        idx = max(0, min(list_view.index, len(self.jobs) - 1))
        self.selected_job_id = self.jobs[idx] if idx < len(self.jobs) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "batch-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_job(self) -> None:
        """Select the current job."""
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
            self.query_one("#batch-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("batch", BatchPane)

# IMPORT-SAFE: no side effects allowed