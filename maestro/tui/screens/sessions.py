"""
Sessions Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, ListView, ListItem, Static
from textual.containers import Horizontal, Vertical, ScrollableContainer
from maestro.ui_facade.sessions import list_sessions, get_session_details, create_session, set_active_session, remove_session
from maestro.tui.widgets import ConfirmDialog, InputDialog


class SessionsScreen(Screen):
    """Sessions screen of the Maestro TUI with master-detail layout."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("n", "create_session", "New"),
        ("d", "delete_session", "Delete"),
        ("enter", "set_active", "Set Active"),
    ]

    def __init__(self):
        super().__init__()
        self.sessions_list = []
        self.selected_session_idx = 0
        self.current_session_details = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the sessions screen."""
        yield Header()

        # Master-detail layout - horizontal split
        with Horizontal(id="sessions-main-container"):
            # Left pane - sessions list
            with Vertical(id="sessions-list-pane", classes="pane"):
                yield Label("[b]Sessions[/b]", classes="title")

                # Create the session list view
                session_items = []
                try:
                    self.sessions_list = list_sessions()
                    for i, session in enumerate(self.sessions_list):
                        # Check if this session is the active one
                        active_marker = "●" if self.app.active_session and self.app.active_session.id == session.id else "○"

                        # Format last modified time
                        import datetime
                        try:
                            # Parse the datetime string and format it nicely
                            dt = datetime.datetime.fromisoformat(session.updated_at.replace('Z', '+00:00'))
                            formatted_time = dt.strftime("%m/%d %H:%M")
                        except:
                            formatted_time = session.updated_at

                        # Shorten the ID for display
                        short_id = session.id[:8] + "..."

                        session_label = f"{active_marker} {session.root_task[:30]}{'...' if len(session.root_task) > 30 else ''} ({short_id}) [{formatted_time}]"
                        item = ListItem(Label(session_label), id=f"session-{i}")
                        session_items.append(item)
                except Exception as e:
                    session_items = [ListItem(Label(f"Error loading sessions: {str(e)}"))]

                yield ListView(*session_items, id="sessions-list-view")

            # Right pane - session details
            with Vertical(id="session-details-pane", classes="pane"):
                yield Label("[b]Session Details[/b]", classes="title")

                if self.sessions_list and len(self.sessions_list) > 0:
                    # Show details for the first session by default
                    try:
                        session_id = self.sessions_list[0].id
                        self.current_session_details = get_session_details(session_id)
                        yield self._create_session_details_view()
                    except Exception as e:
                        yield Label(f"Error loading session details: {str(e)}")
                else:
                    yield Label("No sessions available", classes="placeholder")

        yield Footer()

    def _create_session_details_view(self):
        """Create the session details view."""
        if not self.current_session_details:
            return Label("No session selected", classes="placeholder")

        details_content = [
            Label(f"[b]Session ID:[/b] {self.current_session_details.id}"),
            Label(f"[b]Created:[/b] {self.current_session_details.created_at}"),
            Label(f"[b]Modified:[/b] {self.current_session_details.updated_at}"),
            Label(f"[b]Status:[/b] {self.current_session_details.status}"),
        ]

        if self.current_session_details.active_plan_id:
            details_content.append(Label(f"[b]Active Plan ID:[/b] {self.current_session_details.active_plan_id}"))

        if self.current_session_details.root_task_summary:
            details_content.append(Label(f"[b]Summary:[/b] {self.current_session_details.root_task_summary[:100]}{'...' if len(self.current_session_details.root_task_summary) > 100 else ''}"))

        if self.current_session_details.rules_path:
            details_content.append(Label(f"[b]Rules Path:[/b] {self.current_session_details.rules_path}"))

        return ScrollableContainer(*details_content, id="session-details-content")

    def action_refresh(self):
        """Refresh the session list."""
        self.refresh_sessions_list()

    def refresh_sessions_list(self):
        """Refresh the session list view."""
        try:
            # Get the selected index before refreshing
            current_idx = self.selected_session_idx

            # Reload sessions
            self.sessions_list = list_sessions()

            # Update the list view
            session_items = []
            for i, session in enumerate(self.sessions_list):
                # Check if this session is the active one
                active_marker = "●" if self.app.active_session and self.app.active_session.id == session.id else "○"

                # Format last modified time
                import datetime
                try:
                    # Parse the datetime string and format it nicely
                    dt = datetime.datetime.fromisoformat(session.updated_at.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%m/%d %H:%M")
                except:
                    formatted_time = session.updated_at

                # Shorten the ID for display
                short_id = session.id[:8] + "..."

                session_label = f"{active_marker} {session.root_task[:30]}{'...' if len(session.root_task) > 30 else ''} ({short_id}) [{formatted_time}]"
                item = ListItem(Label(session_label), id=f"session-{i}")
                session_items.append(item)

            # Update the list view with new items
            list_view = self.query_one("#sessions-list-view", ListView)
            list_view.clear()
            for item in session_items:
                list_view.append(item)

            # Restore selection if possible
            if self.sessions_list and current_idx < len(self.sessions_list):
                self.selected_session_idx = current_idx
                # Update the details panel for the selected session
                self._update_selected_session(current_idx)
            elif self.sessions_list:
                self.selected_session_idx = 0
                # Update the details panel for the first session
                self._update_selected_session(0)
        except Exception as e:
            # Handle error in loading sessions
            pass

    def on_list_view_highlighted(self, event):
        """Handle when a session in the list is highlighted/selected."""
        # Extract index from the event
        session_idx_str = event.item.id.split("-")[1] if event.item.id else "0"
        try:
            session_idx = int(session_idx_str)
            self.selected_session_idx = session_idx
            self._update_selected_session(session_idx)
        except ValueError:
            pass

    def _update_selected_session(self, idx):
        """Update the details view for the selected session."""
        try:
            if 0 <= idx < len(self.sessions_list):
                session_id = self.sessions_list[idx].id
                self.current_session_details = get_session_details(session_id)

                # Update the details container
                details_container = self.query_one("#session-details-content", ScrollableContainer)
                details_container.remove_children()

                details_content = [
                    Label(f"[b]Session ID:[/b] {self.current_session_details.id}"),
                    Label(f"[b]Created:[/b] {self.current_session_details.created_at}"),
                    Label(f"[b]Modified:[/b] {self.current_session_details.updated_at}"),
                    Label(f"[b]Status:[/b] {self.current_session_details.status}"),
                ]

                if self.current_session_details.active_plan_id:
                    details_content.append(Label(f"[b]Active Plan ID:[/b] {self.current_session_details.active_plan_id}"))

                if self.current_session_details.root_task_summary:
                    details_content.append(Label(f"[b]Summary:[/b] {self.current_session_details.root_task_summary[:100]}{'...' if len(self.current_session_details.root_task_summary) > 100 else ''}"))

                if self.current_session_details.rules_path:
                    details_content.append(Label(f"[b]Rules Path:[/b] {self.current_session_details.rules_path}"))

                for content in details_content:
                    details_container.mount(content)
        except Exception as e:
            # Handle error in loading session details
            details_container = self.query_one("#session-details-content", ScrollableContainer)
            details_container.remove_children()
            details_container.mount(Label(f"Error loading session details: {str(e)}"))

    def action_create_session(self):
        """Show the create session dialog."""
        # Use the InputDialog to get session name and optionally root task
        def on_input_submitted(session_input: str):
            if session_input:
                try:
                    # For now, just use the input as both name and root task text
                    # Split by newlines if user entered multiple lines (first for name, rest for root task)
                    lines = session_input.split('\n', 1)
                    name = lines[0].strip()
                    root_task_text = lines[1].strip() if len(lines) > 1 else name

                    # Create the session
                    created_session = create_session(name, root_task_text)

                    # Refresh the session list
                    self.refresh_sessions_list()

                    # Show success message
                    self.notify(f"Session '{name}' created successfully", timeout=3)
                except Exception as e:
                    self.notify(f"Error creating session: {str(e)}", severity="error", timeout=5)

        # Show input dialog for session name
        input_dialog = InputDialog(
            message="Enter session name and optionally root task (separate with newline):",
            title="Create New Session"
        )
        self.app.push_screen(input_dialog, callback=on_input_submitted)

    def action_set_active(self):
        """Set the selected session as active."""
        if not self.sessions_list or self.selected_session_idx >= len(self.sessions_list):
            self.notify("No session selected", severity="warning", timeout=3)
            return

        selected_session = self.sessions_list[self.selected_session_idx]

        def on_confirmed(confirmed: bool):
            if confirmed:
                try:
                    # Set the session as active
                    set_active_session(selected_session.id)

                    # Refresh the session list to update the active marker
                    self.refresh_sessions_list()

                    # Update app's active session
                    self.app._load_status_state()

                    # Update the status bar
                    self.app.query_one("#active-session").update(
                        f" | Session: {selected_session.id[:8] + '...'}"
                    )

                    self.notify(f"Session '{selected_session.root_task[:20]}...' set as active", timeout=3)
                except Exception as e:
                    self.notify(f"Error setting session as active: {str(e)}", severity="error", timeout=5)

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=f"Set '{selected_session.root_task[:30]}...' as active session?",
            title="Confirm Set Active"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)

    def action_delete_session(self):
        """Delete the selected session with confirmation."""
        if not self.sessions_list or self.selected_session_idx >= len(self.sessions_list):
            self.notify("No session selected", severity="warning", timeout=3)
            return

        selected_session = self.sessions_list[self.selected_session_idx]

        def on_confirmed(confirmed: bool):
            if confirmed:
                try:
                    # Remove the session
                    remove_session(selected_session.id)

                    # Refresh the session list
                    self.refresh_sessions_list()

                    self.notify(f"Session '{selected_session.root_task[:20]}...' deleted", timeout=3)
                except Exception as e:
                    self.notify(f"Error deleting session: {str(e)}", severity="error", timeout=5)

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=f"Permanently remove session '{selected_session.root_task[:30]}...'?\nThis cannot be undone.",
            title="Confirm Delete"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)