"""
Sessions pane hosted inside the MC shell.
This pane implements the MCPane contract for reliable pane behavior.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ListItem, ListView, Static

from maestro.ui_facade.sessions import (
    SessionDetails,
    SessionInfo,
    create_session,
    get_active_session,
    get_session_details,
    list_sessions,
    remove_session,
    set_active_session,
)
from maestro.tui.panes.base import PaneView
from maestro.tui.menubar.model import Menu, MenuItem
from maestro.tui.utils import ErrorModal, ErrorNormalizer, memoization_cache
from maestro.tui.widgets.modals import ConfirmDialog, InputDialog
from maestro.tui.panes.registry import register_pane


class SessionsPane(PaneView):
    """Master-detail Sessions view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "set_active", "Set active [CONF]"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f9", "open_menu", "Menu"),  # Menu still handled directly by pane
    ]

    DEFAULT_CSS = """
    SessionsPane {
        layout: vertical;
    }

    #sessions-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #sessions-body {
        height: 1fr;
    }

    #sessions-list-pane, #sessions-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #sessions-list-pane {
        width: 45%;
    }

    #sessions-detail-pane {
        width: 55%;
    }

    #sessions-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }
    """

    def __init__(self, sessions_dir: Optional[str] = None) -> None:
        super().__init__()
        self.pane_id = "sessions"  # Required for the contract
        self.pane_title = "Sessions"  # Required for the contract
        self.sessions_dir = sessions_dir or "./.maestro/sessions"
        self.sessions: List[SessionInfo] = []
        self.selected_id: Optional[str] = None
        self.details: Optional[SessionDetails] = None
        self.active_session_id: Optional[str] = None

    def on_mount(self) -> None:
        """Called when the pane is mounted to the DOM. Initialize UI elements and event handlers here."""
        # Load initial data and focus the list
        # Schedule the async loading after mount
        self.call_after_refresh(self._load_initial_data)

    def _load_initial_data(self) -> None:
        """Load initial data after mount."""
        async def _async_load():
            await self.refresh_data()
            try:
                self.query_one("#sessions-list", ListView).can_focus = False
            except Exception:
                pass
            self.focus()
        self.app.call_later(_async_load)

    def on_focus(self) -> None:
        """Called when the pane receives focus. Perform focus-specific operations."""
        # Refresh data when pane comes into focus
        self.refresh()

    def on_blur(self) -> None:
        """Called when the pane loses focus. Perform cleanup of focus-specific resources."""
        # No special cleanup needed for this pane
        pass

    def refresh_data(self) -> None:
        """Refresh pane data and UI. This is for explicit refresh requests."""
        self.call_after_refresh(self._refresh_data_async)

    def _refresh_data_async(self) -> None:
        """Call the async refresh method."""
        async def _async_refresh():
            await self.refresh_data()
        self.app.call_later(_async_refresh)

    def get_menu_spec(self) -> Menu:
        """Return the menu specification for this pane."""
        # Use the existing Menu class from the menubar model
        from maestro.tui.menubar.model import Menu
        has_selection = bool(self._get_selected_session())
        return Menu(
            label=self.pane_title,
            items=[
                MenuItem(
                    "new",
                    "New",
                    action=self.action_new_session,
                    key_hint="F7",
                    fkey="F7",
                    action_id="sessions.new",
                    trust_label="[MUT][CONF]",
                ),
                MenuItem(
                    "set_active",
                    "Set Active",
                    action=self.action_set_active,
                    key_hint="Enter",
                    fkey="Enter",
                    action_id="sessions.set_active",
                    enabled=has_selection,
                    trust_label="[MUT][CONF]",
                    requires_confirmation=True,
                ),
                MenuItem(
                    "delete",
                    "Delete",
                    action=self.action_delete_session,
                    key_hint="F8",
                    fkey="F8",
                    action_id="sessions.delete",
                    enabled=has_selection,
                    trust_label="[MUT][CONF]",
                    requires_confirmation=True,
                ),
                MenuItem(
                    "refresh",
                    "Refresh",
                    action=self.refresh_data,
                    key_hint="F5",
                    fkey="F5",
                    action_id="sessions.refresh",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        yield Label("Sessions", id="sessions-header")
        with Horizontal(id="sessions-body"):
            with Vertical(id="sessions-list-pane"):
                yield Label("Session List", id="sessions-list-title")
                yield ListView(id="sessions-list")
            with Vertical(id="sessions-detail-pane"):
                yield Label("Details", id="sessions-detail-title")
                yield Static("Select a session to view details.", id="session-detail")
        yield Label("", id="sessions-status")

    async def refresh_data(self) -> None:
        """Refresh list and detail content."""
        try:
            self.sessions = list_sessions(self.sessions_dir)
            if self.sessions and self.selected_id is None:
                self.selected_id = self.sessions[0].id
            active = get_active_session(self.sessions_dir)
            self.active_session_id = active.id if active else None
        except Exception as exc:
            await self._show_error(exc, "loading sessions")
            return

        self._render_list()
        await self._load_details_for_selection()
        self.notify_status("Sessions refreshed")
        self.request_menu_refresh()

    def _render_list(self) -> None:
        """Render the ListView from session data."""
        list_view = self.query_one("#sessions-list", ListView)
        list_view.clear()
        for session in self.sessions:
            active_marker = "●" if self._is_active_session(session) else "○"
            short_id = session.id[:8] + "..."
            label = f"{active_marker} {session.root_task} ({short_id}) [{session.status}]"
            list_view.append(ListItem(Label(label)))

        if not self.sessions:
            list_view.append(ListItem(Label("No sessions found [RO]")))
            list_view.index = 0
            self.selected_id = None
            self.request_menu_refresh()
            return

        # Restore selection
        ids = [s.id for s in self.sessions]
        if self.selected_id not in ids:
            self.selected_id = ids[0]
        list_view.index = ids.index(self.selected_id)
        self.request_menu_refresh()

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected session."""
        detail_widget = self.query_one("#session-detail", Static)
        if not self.selected_id:
            detail_widget.update("No session selected.")
            return

        try:
            self.details = get_session_details(self.selected_id, self.sessions_dir)
        except Exception as exc:
            await self._show_error(exc, "loading session details")
            return

        detail_lines = [
            f"[b]ID:[/b] {self.details.id}",
            f"[b]Created:[/b] {self.details.created_at}",
            f"[b]Updated:[/b] {self.details.updated_at}",
            f"[b]Status:[/b] {self.details.status}",
        ]

        if self.details.active_phase_id:
            detail_lines.append(f"[b]Active Phase:[/b] {self.details.active_phase_id}")
        if self.details.rules_path:
            detail_lines.append(f"[b]Rules:[/b] {self.details.rules_path}")
        if self.details.root_task_summary:
            detail_lines.append(f"[b]Summary:[/b] {self.details.root_task_summary}")

        detail_widget.update("\n".join(detail_lines))

    def _get_selected_session(self) -> Optional[SessionInfo]:
        """Return the current session info."""
        if not self.sessions or not self.selected_id:
            return None
        for session in self.sessions:
            if session.id == self.selected_id:
                return session
        return None

    def _is_active_session(self, session: SessionInfo) -> bool:
        """Determine if a session is active using cached active_session_id."""
        return bool(self.active_session_id and self.active_session_id == session.id)

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#sessions-list", ListView)
        list_view.action_cursor_up()
        await self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#sessions-list", ListView)
        list_view.action_cursor_down()
        await self._sync_selection_from_list()

    async def _sync_selection_from_list(self) -> None:
        """Update selected_id from ListView and refresh details."""
        list_view = self.query_one("#sessions-list", ListView)
        if list_view.index is None or not self.sessions:
            return
        idx = max(0, min(list_view.index, len(self.sessions) - 1))
        self.selected_id = self.sessions[idx].id
        await self._load_details_for_selection()
        self.request_menu_refresh()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "sessions-list":
            return
        asyncio.create_task(self._sync_selection_from_list())

    async def action_set_active(self) -> None:
        """Set the selected session as active, with confirmation."""
        session = self._get_selected_session()
        if not session:
            self.notify_status("No session selected")
            return

        def on_confirmed(confirmed: bool) -> None:
            if not confirmed:
                self.notify_status("Set active cancelled")
                return
            try:
                set_active_session(session.id, self.sessions_dir)
                memoization_cache.clear()
                self.notify_status(f"Session {session.id[:8]} set active")
            except Exception as exc:
                asyncio.create_task(self._show_error(exc, "setting active session"))
                return
                asyncio.create_task(self.refresh_data())

        confirm = ConfirmDialog(
            message=f"Set session {session.id[:8]} as active?",
            title="Confirm Set Active",
        )
        self.app.push_screen(confirm, callback=lambda res: on_confirmed(bool(res)))
        self.request_menu_refresh()

    async def action_new_session(self) -> None:
        """Create a new session."""
        def on_input(name: Optional[str]) -> None:
            if not name:
                self.notify_status("New session cancelled")
                return

            def on_confirmed(confirmed: bool) -> None:
                if not confirmed:
                    self.notify_status("New session cancelled")
                    return
                try:
                    created = create_session(name, sessions_dir=self.sessions_dir)
                    memoization_cache.clear()
                    self.selected_id = created.id
                    self.notify_status(f"Session '{name}' created")
                except Exception as exc:
                    asyncio.create_task(self._show_error(exc, "creating session"))
                    return
                asyncio.create_task(self.refresh_data())

            confirm = ConfirmDialog(
                message=f"Create new session named '{name}'?",
                title="Confirm New Session",
            )
            self.app.push_screen(confirm, callback=lambda res: on_confirmed(bool(res)))

        dialog = InputDialog(message="Enter new session name:", title="New Session")
        self.app.push_screen(dialog, callback=on_input)
        self.request_menu_refresh()

    async def action_delete_session(self) -> None:
        """Delete the selected session."""
        session = self._get_selected_session()
        if not session:
            self.notify_status("No session selected")
            return

        def on_confirmed(confirmed: bool) -> None:
            if not confirmed:
                self.notify_status("Delete cancelled")
                return
            try:
                remove_session(session.id, self.sessions_dir)
                memoization_cache.clear()
                self.notify_status(f"Session {session.id[:8]} removed")
            except Exception as exc:
                asyncio.create_task(self._show_error(exc, "removing session"))
                return
            self.selected_id = None
            asyncio.create_task(self.refresh_data())

        confirm = ConfirmDialog(
            message=f"Delete session {session.id[:8]}? This cannot be undone.",
            title="Confirm Delete Session",
        )
        self.app.push_screen(confirm, callback=lambda res: on_confirmed(bool(res)))
        self.request_menu_refresh()

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
            self.query_one("#sessions-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)
        self.request_menu_refresh()

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))


# Register with the global pane registry
register_pane("sessions", SessionsPane)

# IMPORT-SAFE: no side effects allowed
