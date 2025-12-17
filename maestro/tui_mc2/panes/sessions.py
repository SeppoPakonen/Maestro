"""
Sessions pane for MC2 Curses TUI
Shows list of sessions in left pane and session details in right pane
"""
import curses
import os
from typing import Optional, List
from dataclasses import dataclass

from maestro.ui_facade.build import get_active_build_target
from maestro.ui_facade.sessions import (
    list_sessions,
    get_session_details,
    create_session,
    remove_session,
    set_active_session,
    get_active_session,
)
from maestro.tui_mc2.ui.modals import ConfirmModal, InputModal


@dataclass
class SessionDisplay:
    id: str
    display_name: str
    root_task: str
    status: str
    created_at: str
    updated_at: str
    active_plan_id: Optional[str] = None


class SessionsPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.sessions: List[SessionDisplay] = []
        self.filtered_sessions: List[SessionDisplay] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.current_session_details = None
        self.current_session_path: Optional[str] = None
        self.current_build_target = None
        self.last_loaded_session_id: Optional[str] = None
        self.filter_text = ""
        self.sessions_dir = "./.maestro/sessions"

        # Load initial data
        self.refresh_data()

    def set_window(self, window):
        """Set the curses window for this pane."""
        self.window = window

    def set_focused(self, focused: bool):
        """Set focus state for this pane."""
        self.is_focused = focused
        if focused and self.position == "right":
            self._load_session_details()

    def refresh_data(self):
        """Refresh the session data."""
        try:
            session_list = list_sessions()
            self.sessions = [
                SessionDisplay(
                    id=session.id,
                    display_name=f"{session.root_task[:30]}..." if len(session.root_task) > 30 else session.root_task,
                    root_task=session.root_task,
                    status=session.status,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    active_plan_id=session.active_plan_id,
                )
                for session in session_list
            ]

            active = get_active_session()
            if active:
                self.context.active_session_id = active.id

            preserve_id = self.context.selected_session_id
            if preserve_id is None and self.sessions and self.position == "left":
                preserve_id = self.sessions[0].id
                self.context.selected_session_id = preserve_id

            self._apply_filter(preserve_id)

            if self.position == "right":
                self._sync_selected_index_from_context()
                self.last_loaded_session_id = None
                self._load_session_details()

        except Exception as e:
            self.context.status_message = f"Error loading sessions: {str(e)}"

    def _apply_filter(self, preserve_selected_id: Optional[str] = None):
        filter_value = self.filter_text.lower()
        if filter_value:
            self.filtered_sessions = [
                session
                for session in self.sessions
                if filter_value in session.display_name.lower() or filter_value in session.id.lower()
            ]
        else:
            self.filtered_sessions = list(self.sessions)

        if preserve_selected_id:
            self._set_selected_by_id(preserve_selected_id)
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()

        self._update_filter_status()

    def _update_filter_status(self):
        self.context.sessions_filter_text = self.filter_text
        self.context.sessions_filter_visible = len(self.filtered_sessions)
        self.context.sessions_filter_total = len(self.sessions)

    def _get_selected_session(self) -> Optional[SessionDisplay]:
        if self.position == "right":
            target_id = self.context.selected_session_id
            if not target_id:
                return None
            for session in self.sessions:
                if session.id == target_id:
                    return session
            return None
        if not self.filtered_sessions:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_sessions):
            return None
        return self.filtered_sessions[self.selected_index]

    def _sync_selected_id(self):
        if self.position != "left":
            return
        selected = self._get_selected_session()
        self.context.selected_session_id = selected.id if selected else None

    def _sync_selected_index_from_context(self):
        if not self.filtered_sessions:
            self.selected_index = 0
            return
        target_id = self.context.selected_session_id
        if not target_id:
            self.selected_index = 0
            return
        for idx, session in enumerate(self.filtered_sessions):
            if session.id == target_id:
                self.selected_index = idx
                break

    def _set_selected_by_id(self, session_id: str):
        if not self.filtered_sessions:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()
            return
        for idx, session in enumerate(self.filtered_sessions):
            if session.id == session_id:
                self.selected_index = idx
                self._ensure_visible()
                self._sync_selected_id()
                return
        self.selected_index = 0
        self.scroll_offset = 0
        self._sync_selected_id()

    def _ensure_visible(self):
        if not self.window:
            return
        height = max(1, self.window.getmaxyx()[0] - 2)
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + height:
            self.scroll_offset = self.selected_index - height + 1

    def _load_session_details(self):
        session_id = self.context.selected_session_id
        if not session_id:
            self.current_session_details = None
            self.current_session_path = None
            self.current_build_target = None
            self.last_loaded_session_id = None
            return
        if session_id == self.last_loaded_session_id:
            return

        try:
            details = get_session_details(session_id)
            self.current_session_details = details
            self.current_session_path = os.path.join(self.sessions_dir, f"{session_id}.json")
            self.current_build_target = get_active_build_target(session_id)
            self.last_loaded_session_id = session_id
        except Exception as e:
            self.context.status_message = f"Error loading session details: {str(e)}"
            self.current_session_details = None
            self.current_session_path = None
            self.current_build_target = None
            self.last_loaded_session_id = None

    def _move_selection(self, delta: int):
        if self.position != "left" or not self.filtered_sessions:
            return
        new_index = max(0, min(len(self.filtered_sessions) - 1, self.selected_index + delta))
        if new_index != self.selected_index:
            self.selected_index = new_index
            self._ensure_visible()
            self._sync_selected_id()

    def move_up(self):
        """Move selection up."""
        self._move_selection(-1)

    def move_down(self):
        """Move selection down."""
        self._move_selection(1)

    def page_up(self):
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(-step)

    def page_down(self):
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(step)

    def move_home(self):
        if self.position == "left":
            self._move_selection(-len(self.filtered_sessions))

    def move_end(self):
        if self.position == "left":
            self._move_selection(len(self.filtered_sessions))

    def handle_enter(self):
        """Handle enter key press."""
        self.handle_set_active()

    def handle_new(self):
        """Handle F7 (New) action."""
        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return

        input_modal = InputModal(parent, "New Session", "Session Name:", "New Session")
        session_name = input_modal.show()

        if session_name and session_name.strip():
            try:
                created_session = create_session(session_name.strip())
                activated_session = set_active_session(created_session.id)
                self.context.active_session_id = activated_session.id
                self.context.selected_session_id = created_session.id
                self.refresh_data()
                self.context.status_message = f"Created session: {created_session.id[:8]}... (active)"
            except Exception as e:
                self.context.status_message = f"Error creating session: {str(e)}"
        else:
            self.context.status_message = "Session creation cancelled"

    def handle_delete(self):
        """Handle F8 (Delete) action."""
        selected = self._get_selected_session()
        if not selected:
            self.context.status_message = "No session selected"
            return

        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return

        lines = [
            f"Delete session '{selected.display_name}'?",
            f"ID: {selected.id[:8]}...",
        ]
        if self.context.active_session_id == selected.id:
            lines.append("WARNING: This is the active session.")
        lines.append("")
        lines.append("Confirm delete?")

        confirm_modal = ConfirmModal(parent, "Confirm Delete", lines)
        if not confirm_modal.show():
            self.context.status_message = "Delete cancelled"
            return

        try:
            remove_session(selected.id)
            if self.context.active_session_id == selected.id:
                self.context.active_session_id = None
            self.refresh_data()
            self.context.status_message = f"Deleted session: {selected.id[:8]}..."
        except Exception as e:
            self.context.status_message = f"Error deleting session: {str(e)}"

    def handle_set_active(self):
        """Handle setting session as active."""
        selected = self._get_selected_session()
        if not selected:
            self.context.status_message = "No session selected"
            return
        if self.context.active_session_id == selected.id:
            self.context.status_message = "Session already active"
            return

        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return

        lines = [
            f"Set active session '{selected.display_name}'?",
            f"ID: {selected.id[:8]}...",
        ]
        confirm_modal = ConfirmModal(parent, "Set Active Session", lines)
        if not confirm_modal.show():
            self.context.status_message = "Set active cancelled"
            return

        try:
            activated_session = set_active_session(selected.id)
            self.context.active_session_id = activated_session.id
            self.refresh_data()
            self.context.status_message = f"Set active: {activated_session.id[:8]}..."
        except Exception as e:
            self.context.status_message = f"Error setting active session: {str(e)}"

    def handle_filter_char(self, ch: str) -> bool:
        if not ch or not ch.isalnum():
            return False
        self.filter_text += ch
        self._apply_filter()
        return True

    def handle_filter_backspace(self) -> bool:
        if not self.filter_text:
            return False
        self.filter_text = self.filter_text[:-1]
        self._apply_filter()
        return True

    def clear_filter(self) -> bool:
        if not self.filter_text:
            return False
        self.filter_text = ""
        self._apply_filter()
        return True

    def render(self):
        """Render the sessions pane."""
        if os.getenv("MAESTRO_MC2_FAULT_INJECT") == "pane_render":
            raise RuntimeError("Injected pane render failure")
        if not self.window:
            return

        if self.position == "right":
            self._load_session_details()

        self.window.erase()
        height, width = self.window.getmaxyx()

        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        elif curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(0))

        if self.position == "left":
            title = "Sessions"
        else:
            details_name = None
            if self.current_session_details and self.current_session_details.root_task:
                details_name = self.current_session_details.root_task
            elif self.context.selected_session_id:
                details_name = self.context.selected_session_id[:8] + "..."
            title = f"Session Details: {details_name or 'None'}"

        try:
            self.window.addstr(0, 1, title[: width - 3], curses.A_BOLD)
        except Exception:
            pass

        if self.position == "left":
            self._render_sessions_list(height, width)
        else:
            self._render_session_details(height, width)

        self.window.noutrefresh()

    def _render_sessions_list(self, height, width):
        if not self.filtered_sessions:
            message = "No sessions found"
            if self.filter_text:
                message = "No sessions match filter"
            try:
                self.window.addstr(2, 1, message, curses.A_DIM)
            except Exception:
                pass
            return

        display_count = height - 2
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.filtered_sessions))

        for idx in range(start_idx, end_idx):
            session = self.filtered_sessions[idx]
            row = 1 + (idx - start_idx)

            is_selected = (idx == self.selected_index)
            display_text = f"{session.display_name} [{session.status}]"
            if len(display_text) >= width - 2:
                display_text = display_text[: width - 5] + "..."

            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width - 2), attr)
            except Exception:
                break

    def _render_session_details(self, height, width):
        if not self.current_session_details:
            try:
                self.window.addstr(2, 1, "Select a session in the left pane", curses.A_DIM)
            except Exception:
                pass
            return

        details = self.current_session_details
        row = 2

        def _value(value: Optional[str]) -> str:
            if value is None or value == "":
                return "(not available)"
            return str(value)

        def _add_line(label: str, value: Optional[str]):
            nonlocal row
            if row >= height - 1:
                return
            text = f"{label}: {_value(value)}"
            try:
                self.window.addstr(row, 1, text[: width - 2], curses.A_NORMAL)
            except Exception:
                pass
            row += 1

        short_id = details.id[:8] + "..." if details.id and len(details.id) > 8 else details.id
        _add_line("Name", details.root_task)
        _add_line("Active", "Yes" if self.context.active_session_id == details.id else "No")
        _add_line("ID", short_id)
        _add_line("Full ID", details.id)
        _add_line("Session JSON", self.current_session_path)
        _add_line("Last Modified", details.updated_at)
        _add_line("Status", details.status)

        active_plan = details.active_plan_id or "(not available)"
        _add_line("Active Plan", active_plan)

        build_display = "(not available)"
        if self.current_build_target:
            build_name = self.current_build_target.name or self.current_build_target.id
            build_id = self.current_build_target.id or ""
            if build_id and build_id not in build_name:
                build_display = f"{build_name} ({build_id[:8]}...)"
            else:
                build_display = build_name
        _add_line("Active Build", build_display)
