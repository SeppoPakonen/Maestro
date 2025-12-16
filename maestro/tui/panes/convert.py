"""
Convert pane for Maestro TUI.

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


class ConvertPane(PaneView):
    """Convert view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_pipeline", "Select pipeline"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    ConvertPane {
        layout: vertical;
    }

    #convert-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #convert-body {
        height: 1fr;
    }

    #convert-list-pane, #convert-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #convert-list-pane {
        width: 45%;
    }

    #convert-detail-pane {
        width: 55%;
    }

    #convert-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "convert"  # Required for the contract
        self.pane_title = "Convert"  # Required for the contract
        self.pipelines: List[str] = []  # Placeholder for conversion pipeline data
        self.selected_pipeline_id: Optional[str] = None

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
                    action_id="convert.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Convert", id="convert-header")
        with Horizontal(id="convert-body"):
            with Vertical(id="convert-list-pane"):
                yield Label("Conversion Pipelines", id="convert-list-title")
                yield ListView(id="convert-list")
            with Vertical(id="convert-detail-pane"):
                yield Label("Details", id="convert-detail-title")
                yield Static("Select a conversion pipeline to view details.", id="convert-detail")
        yield Label("", id="convert-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#convert-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to convert UI facade
        self.pipelines = ["Pipeline 1", "Pipeline 2", "Pipeline 3"]  # Replace with real data
        if self.pipelines and self.selected_pipeline_id is None:
            self.selected_pipeline_id = self.pipelines[0] if self.pipelines else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Conversion pipelines refreshed")

    def _render_list(self) -> None:
        """Render the ListView from pipeline data."""
        list_view = self.query_one("#convert-list", ListView)
        list_view.clear()
        for pipeline in self.pipelines:
            list_view.append(ListItem(Label(pipeline)))

        if not self.pipelines:
            list_view.append(ListItem(Label("No conversion pipelines found [RO]")))
            list_view.index = 0
            self.selected_pipeline_id = None
            return

        # Restore selection
        if self.selected_pipeline_id not in self.pipelines:
            self.selected_pipeline_id = self.pipelines[0]
        list_view.index = self.pipelines.index(self.selected_pipeline_id) if self.selected_pipeline_id in self.pipelines else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected pipeline."""
        detail_widget = self.query_one("#convert-detail", Static)
        if not self.selected_pipeline_id:
            detail_widget.update("No conversion pipeline selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Pipeline:[/b] {self.selected_pipeline_id}",
            f"[b]Status:[/b] Ready",
            f"[b]Source:[/b] src/",
            f"[b]Target:[/b] dest/",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#convert-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#convert-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_pipeline_id from ListView and refresh details."""
        list_view = self.query_one("#convert-list", ListView)
        if list_view.index is None or not self.pipelines:
            return
        idx = max(0, min(list_view.index, len(self.pipelines) - 1))
        self.selected_pipeline_id = self.pipelines[idx] if idx < len(self.pipelines) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "convert-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_pipeline(self) -> None:
        """Select the current pipeline."""
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
            self.query_one("#convert-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("convert", ConvertPane)

# IMPORT-SAFE: no side effects allowed