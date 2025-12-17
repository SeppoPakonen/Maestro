"""
Sessions pane for MC2 Curses TUI
Shows list of sessions in left pane and session details in right pane
"""
import curses
from typing import Optional, List
from dataclasses import dataclass

from maestro.ui_facade.sessions import list_sessions, get_session_details, create_session, remove_session, set_active_session


@dataclass
class SessionDisplay:
    id: str
    display_name: str
    status: str
    created_at: str


class SessionsPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.sessions: List[SessionDisplay] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.current_session_details = None
        
        # Load initial data
        self.refresh_data()
    
    def set_window(self, window):
        """Set the curses window for this pane"""
        self.window = window
        
    def set_focused(self, focused: bool):
        """Set focus state for this pane"""
        self.is_focused = focused
        # When right pane gets focus, load details for selected session
        if focused and self.position == "right" and self.sessions:
            self._load_session_details()
    
    def refresh_data(self):
        """Refresh the session data"""
        try:
            # Get sessions from UI facade
            session_list = list_sessions()
            self.sessions = [
                SessionDisplay(
                    id=session.id,
                    display_name=f"{session.root_task[:30]}..." if len(session.root_task) > 30 else session.root_task,
                    status=session.status,
                    created_at=session.created_at
                )
                for session in session_list
            ]
            
            # If this is the right pane, load the currently selected session details
            if self.position == "right" and self.sessions:
                self._load_session_details()
                
        except Exception as e:
            self.context.status_message = f"Error loading sessions: {str(e)}"
    
    def _load_session_details(self):
        """Load details for the currently selected session"""
        if not self.sessions or self.selected_index >= len(self.sessions):
            self.current_session_details = None
            return
            
        selected_session = self.sessions[self.selected_index]
        try:
            details = get_session_details(selected_session.id)
            self.current_session_details = details
        except Exception as e:
            self.context.status_message = f"Error loading session details: {str(e)}"
            self.current_session_details = None
    
    def move_up(self):
        """Move selection up"""
        if self.position == "left" and self.sessions:
            if self.selected_index > 0:
                self.selected_index -= 1
                # Adjust scroll offset to keep selection visible
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
                # When moving in left pane, update right pane
                self._load_session_details()
    
    def move_down(self):
        """Move selection down"""
        if self.position == "left" and self.sessions:
            if self.selected_index < len(self.sessions) - 1:
                self.selected_index += 1
                # Adjust scroll offset to keep selection visible
                height = self.window.getmaxyx()[0] - 2  # -2 for borders/padding
                if self.selected_index >= self.scroll_offset + height:
                    self.scroll_offset = self.selected_index - height + 1
                # When moving in left pane, update right pane
                self._load_session_details()
    
    def handle_enter(self):
        """Handle enter key press"""
        if self.position == "left" and self.sessions and 0 <= self.selected_index < len(self.sessions):
            # If in left pane, this might switch to right pane or perform action
            # For now, just ensure right pane has updated details
            self._load_session_details()
            self.context.status_message = f"Selected: {self.sessions[self.selected_index].display_name}"
        elif self.position == "right" and self.current_session_details:
            # In right pane, enter might perform an action on the session
            self.context.status_message = f"Session: {self.current_session_details.id}"
    
    def handle_new(self):
        """Handle F7 (New) action"""
        from maestro.tui_mc2.ui.modals import InputModal
        
        # Create a temporary parent window for the modal
        temp_parent = curses.newwin(5, 5, 0, 0)
        try:
            # Use a temporary window for input modal since curses has issues with overlapping windows
            input_modal = InputModal(temp_parent, "New Session", "Session Name:", "New Session")
            session_name = input_modal.show()
            
            if session_name and session_name.strip():
                try:
                    created_session = create_session(session_name.strip())
                    self.context.status_message = f"Created session: {created_session.id[:8]}..."
                    self.refresh_data()  # Refresh the list
                except Exception as e:
                    self.context.status_message = f"Error creating session: {str(e)}"
            else:
                self.context.status_message = "Session creation cancelled"
        finally:
            del temp_parent
    
    def handle_delete(self):
        """Handle F8 (Delete) action"""
        if not self.sessions or self.selected_index >= len(self.sessions):
            self.context.status_message = "No session selected"
            return
            
        from maestro.tui_mc2.ui.modals import ModalDialog
        
        # Create a temporary parent window for the modal
        temp_parent = curses.newwin(5, 5, 0, 0)
        try:
            selected_session = self.sessions[self.selected_index]
            confirm_modal = ModalDialog(
                temp_parent, 
                "Confirm Delete", 
                [
                    f"Delete session '{selected_session.display_name}'?",
                    f"ID: {selected_session.id[:8]}...",
                    "",
                    "Press Y to confirm, any other key to cancel"
                ]
            )
            result = confirm_modal.show()
            
            if result and result.lower() == 'y':
                try:
                    remove_session(selected_session.id)
                    self.context.status_message = f"Deleted session: {selected_session.id[:8]}..."
                    self.refresh_data()  # Refresh the list
                    # Adjust selection if needed
                    if self.selected_index >= len(self.sessions):
                        self.selected_index = max(0, len(self.sessions) - 1)
                except Exception as e:
                    self.context.status_message = f"Error deleting session: {str(e)}"
            else:
                self.context.status_message = "Delete cancelled"
        finally:
            del temp_parent
    
    def handle_set_active(self):
        """Handle setting session as active"""
        if not self.sessions or self.selected_index >= len(self.sessions):
            self.context.status_message = "No session selected"
            return
            
        try:
            selected_session = self.sessions[self.selected_index]
            activated_session = set_active_session(selected_session.id)
            self.context.active_session_id = activated_session.id
            self.context.status_message = f"Set active: {activated_session.id[:8]}..."
        except Exception as e:
            self.context.status_message = f"Error setting active session: {str(e)}"
    
    def render(self):
        """Render the sessions pane"""
        if not self.window:
            return
            
        self.window.clear()
        height, width = self.window.getmaxyx()
        
        # Set visual style based on focus
        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        
        title = "Sessions" if self.position == "left" else f"Session Details: {self.sessions[self.selected_index].display_name if self.sessions and self.selected_index < len(self.sessions) else 'None'}"
        
        # Draw title
        try:
            self.window.addstr(0, 1, title[:width-3], curses.A_BOLD)
        except:
            pass
        
        if self.position == "left":
            # Render sessions list
            self._render_sessions_list(height, width)
        else:
            # Render session details
            self._render_session_details(height, width)
        
        # Draw border if we want one
        # self.window.border()
        self.window.refresh()
    
    def _render_sessions_list(self, height, width):
        """Render the sessions list in the left pane"""
        if not self.sessions:
            try:
                self.window.addstr(2, 1, "No sessions found", curses.A_DIM)
            except:
                pass
            return
        
        # Calculate how many sessions we can display
        display_count = height - 2  # -2 for title
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.sessions))
        
        for i in range(start_idx, end_idx):
            session = self.sessions[i]
            row = 1 + (i - start_idx)  # +1 for title row
            
            # Determine if this item is selected
            is_selected = (i == self.selected_index)
            
            # Prepare display text
            display_text = f"{session.display_name} [{session.status}]"
            if len(display_text) >= width - 2:
                display_text = display_text[:width-5] + "..."
            
            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width-2), attr)
            except:
                # Handle case where we try to write outside window bounds
                break
    
    def _render_session_details(self, height, width):
        """Render session details in the right pane"""
        if not self.current_session_details:
            try:
                self.window.addstr(2, 1, "Select a session in the left pane", curses.A_DIM)
            except:
                pass
            return
        
        details = self.current_session_details
        row = 2  # Start after title
        
        try:
            self.window.addstr(row, 1, f"ID: {details.id}", curses.A_NORMAL)
            row += 1
            self.window.addstr(row, 1, f"Created: {details.created_at}", curses.A_NORMAL)
            row += 1
            self.window.addstr(row, 1, f"Updated: {details.updated_at}", curses.A_NORMAL)
            row += 1
            self.window.addstr(row, 1, f"Status: {details.status}", curses.A_NORMAL)
            row += 1
            if details.root_task:
                self.window.addstr(row, 1, f"Task: {details.root_task[:width-8]}", curses.A_NORMAL)
                row += 1
            if details.rules_path:
                self.window.addstr(row, 1, f"Rules: {details.rules_path[:width-9]}", curses.A_NORMAL)
                row += 1
            if details.root_task_summary:
                self.window.addstr(row, 1, f"Summary: {details.root_task_summary[:width-11]}", curses.A_NORMAL)
                row += 1
            if details.active_plan_id:
                self.window.addstr(row, 1, f"Active Plan: {details.active_plan_id}", curses.A_NORMAL)
        except:
            # Handle case where we try to write outside window bounds
            pass