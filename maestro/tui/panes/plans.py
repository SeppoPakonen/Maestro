"""
Plans pane for Maestro TUI.

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


class PlansPane(PaneView):
    """Plans view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_plan", "Select plan"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    PlansPane {
        layout: vertical;
    }

    #plans-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #plans-body {
        height: 1fr;
    }

    #plans-list-pane, #plans-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #plans-list-pane {
        width: 45%;
    }

    #plans-detail-pane {
        width: 55%;
    }

    #plans-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "plans"  # Required for the contract
        self.pane_title = "Plans"  # Required for the contract
        self.plans: List[str] = []  # Placeholder for plan data
        self.selected_plan_id: Optional[str] = None

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
                    action_id="plans.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Plans", id="plans-header")
        with Horizontal(id="plans-body"):
            with Vertical(id="plans-list-pane"):
                yield Label("Plan List", id="plans-list-title")
                yield ListView(id="plans-list")
            with Vertical(id="plans-detail-pane"):
                yield Label("Details", id="plans-detail-title")
                yield Static("Select a plan to view details.", id="plan-detail")
        yield Label("", id="plans-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#plans-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to plans UI facade
        self.plans = ["Plan 1", "Plan 2", "Plan 3"]  # Replace with real data
        if self.plans and self.selected_plan_id is None:
            self.selected_plan_id = self.plans[0] if self.plans else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Plans refreshed")

    def _render_list(self) -> None:
        """Render the ListView from plan data."""
        list_view = self.query_one("#plans-list", ListView)
        list_view.clear()
        for plan in self.plans:
            list_view.append(ListItem(Label(plan)))

        if not self.plans:
            list_view.append(ListItem(Label("No plans found [RO]")))
            list_view.index = 0
            self.selected_plan_id = None
            return

        # Restore selection
        if self.selected_plan_id not in self.plans:
            self.selected_plan_id = self.plans[0]
        list_view.index = self.plans.index(self.selected_plan_id) if self.selected_plan_id in self.plans else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected plan."""
        detail_widget = self.query_one("#plan-detail", Static)
        if not self.selected_plan_id:
            detail_widget.update("No plan selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Plan:[/b] {self.selected_plan_id}",
            f"[b]Status:[/b] Active",
            f"[b]Progress:[/b] 50%",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#plans-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#plans-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_plan_id from ListView and refresh details."""
        list_view = self.query_one("#plans-list", ListView)
        if list_view.index is None or not self.plans:
            return
        idx = max(0, min(list_view.index, len(self.plans) - 1))
        self.selected_plan_id = self.plans[idx] if idx < len(self.plans) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "plans-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_plan(self) -> None:
        """Select the current plan."""
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
            self.query_one("#plans-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("plans", PlansPane)

# IMPORT-SAFE: no side effects allowed