"""
Tasks pane for Maestro TUI.

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


class TasksPane(PaneView):
    """Tasks view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_task", "Select task"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    TasksPane {
        layout: vertical;
    }

    #tasks-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #tasks-body {
        height: 1fr;
    }

    #tasks-list-pane, #tasks-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #tasks-list-pane {
        width: 45%;
    }

    #tasks-detail-pane {
        width: 55%;
    }

    #tasks-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "tasks"  # Required for the contract
        self.pane_title = "Tasks"  # Required for the contract
        self.tasks: List[str] = []  # Placeholder for task data
        self.selected_task_id: Optional[str] = None

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
                    action_id="tasks.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Tasks", id="tasks-header")
        with Horizontal(id="tasks-body"):
            with Vertical(id="tasks-list-pane"):
                yield Label("Task List", id="tasks-list-title")
                yield ListView(id="tasks-list")
            with Vertical(id="tasks-detail-pane"):
                yield Label("Details", id="tasks-detail-title")
                yield Static("Select a task to view details.", id="task-detail")
        yield Label("", id="tasks-status")

    async def on_mount(self) -> None:
        """Load initial data and focus the list."""
        await self.refresh_data()
        try:
            self.query_one("#tasks-list", ListView).can_focus = False
        except Exception:
            pass
        self.focus()

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        # Placeholder implementation - would connect to tasks UI facade
        self.tasks = ["Task 1", "Task 2", "Task 3"]  # Replace with real data
        if self.tasks and self.selected_task_id is None:
            self.selected_task_id = self.tasks[0] if self.tasks else None

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Tasks refreshed")

    def _render_list(self) -> None:
        """Render the ListView from task data."""
        list_view = self.query_one("#tasks-list", ListView)
        list_view.clear()
        for task in self.tasks:
            list_view.append(ListItem(Label(task)))

        if not self.tasks:
            list_view.append(ListItem(Label("No tasks found [RO]")))
            list_view.index = 0
            self.selected_task_id = None
            return

        # Restore selection
        if self.selected_task_id not in self.tasks:
            self.selected_task_id = self.tasks[0]
        list_view.index = self.tasks.index(self.selected_task_id) if self.selected_task_id in self.tasks else 0

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected task."""
        detail_widget = self.query_one("#task-detail", Static)
        if not self.selected_task_id:
            detail_widget.update("No task selected.")
            return

        # Placeholder implementation
        detail_lines = [
            f"[b]Task:[/b] {self.selected_task_id}",
            f"[b]Status:[/b] Pending",
            f"[b]Priority:[/b] Medium",
        ]
        detail_widget.update("\n".join(detail_lines))

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#tasks-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#tasks-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_task_id from ListView and refresh details."""
        list_view = self.query_one("#tasks-list", ListView)
        if list_view.index is None or not self.tasks:
            return
        idx = max(0, min(list_view.index, len(self.tasks) - 1))
        self.selected_task_id = self.tasks[idx] if idx < len(self.tasks) else None
        await self._load_details_for_selection()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "tasks-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_select_task(self) -> None:
        """Select the current task."""
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
            self.query_one("#tasks-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("tasks", TasksPane)

# IMPORT-SAFE: no side effects allowed