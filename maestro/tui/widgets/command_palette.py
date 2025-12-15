"""
Command Palette Modal for Maestro TUI
"""
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Label, Static
from textual import events
from textual.message import Message
from textual.screen import ModalScreen
from maestro.ui_facade.sessions import list_sessions, get_active_session, create_session, set_active_session, remove_session
from maestro.ui_facade.plans import list_plans, get_active_plan
from maestro.ui_facade.build import get_active_build_target


class CommandPaletteScreen(ModalScreen):
    """A modal command palette screen."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("enter", "select_command", "Select"),
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
    ]

    def __init__(self, session_id=None):
        super().__init__()
        self.session_id = session_id
        self.commands = self._setup_commands()
        self.active_index = 0
        self.filtered_commands = self.commands

    def _setup_commands(self):
        """Setup all available commands."""
        commands = []
        # Navigation commands
        commands.extend([
            {"name": "Go to home", "action": "screen_home", "type": "navigation"},
            {"name": "Go to sessions", "action": "screen_sessions", "type": "navigation"},
            {"name": "Go to plans", "action": "screen_plans", "type": "navigation"},
            {"name": "Go to tasks", "action": "screen_tasks", "type": "navigation"},
            {"name": "Go to build", "action": "screen_build", "type": "navigation"},
            {"name": "Go to convert", "action": "screen_convert", "type": "navigation"},
            {"name": "Go to logs", "action": "screen_logs", "type": "navigation"},
            {"name": "Go to help", "action": "screen_help", "type": "navigation"},
        ])

        # Quick action commands (read-only)
        commands.extend([
            {"name": "Show active session", "action": "show_active_session", "type": "action"},
            {"name": "List sessions", "action": "list_sessions", "type": "action"},
            {"name": "Show active plan", "action": "show_active_plan", "type": "action"},
            {"name": "List plans", "action": "list_plans", "type": "action"},
            {"name": "Show active build target", "action": "show_active_build_target", "type": "action"},
        ])

        # Session operations
        commands.extend([
            {"name": "Session: List all sessions", "action": "session_list", "type": "session"},
            {"name": "Session: Create new session", "action": "session_new", "type": "session"},
            {"name": "Session: Set active session", "action": "session_set", "type": "session"},
            {"name": "Session: Remove session", "action": "session_remove", "type": "session"},
        ])

        return commands

    def compose(self) -> ComposeResult:
        """Create child widgets for the command palette."""
        with Container(id="palette-container"):
            yield Input(placeholder="Type command or search...", id="palette-input")
            with VerticalScroll(id="palette-results"):
                for i, cmd in enumerate(self.filtered_commands):
                    css_class = "selected" if i == self.active_index else ""
                    yield Label(cmd["name"], id=f"cmd-{i}", classes=css_class)

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        self.query_one("#palette-input").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter commands as user types."""
        query = event.value.lower()
        if not query:
            self.filtered_commands = self.commands
        else:
            self.filtered_commands = [
                cmd for cmd in self.commands
                if query in cmd["name"].lower()
            ]

        # Update results display
        results_container = self.query_one("#palette-results")
        results_container.remove_children()

        for i, cmd in enumerate(self.filtered_commands):
            css_class = "selected" if i == self.active_index else ""
            results_container.mount(Label(cmd["name"], id=f"cmd-{i}", classes=css_class))

        self.active_index = 0

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command selection."""
        self.select_command()

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        self.active_index = max(0, self.active_index - 1)
        self._update_selection_display()

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        self.active_index = min(len(self.filtered_commands) - 1, self.active_index + 1)
        self._update_selection_display()

    def _update_selection_display(self) -> None:
        """Update the display to show the selected command."""
        # Remove all selected classes
        for i in range(len(self.filtered_commands)):
            label = self.query_one(f"#cmd-{i}", Label)
            label.remove_class("selected")

        # Add selected class to current selection
        if 0 <= self.active_index < len(self.filtered_commands):
            label = self.query_one(f"#cmd-{self.active_index}", Label)
            label.add_class("selected")

    def action_select_command(self) -> None:
        """Execute the selected command."""
        if 0 <= self.active_index < len(self.filtered_commands):
            command = self.filtered_commands[self.active_index]

            # Handle session operation commands that need special handling
            if command["action"] in ["session_list", "session_set", "session_remove", "session_new"]:
                result = self.execute_action_command(command["action"])
                # For session operations that require user input or confirmation,
                # we'll need to handle them differently from read-only commands
                if result == "INPUT_NEEDED":
                    # Special handling for session operations that require input
                    if command["action"] == "session_set":
                        # Show list of sessions and let user select one
                        self._handle_session_set()
                    elif command["action"] == "session_remove":
                        # Show list of sessions and let user select one to remove
                        self._handle_session_remove()
                    elif command["action"] == "session_new":
                        # Prompt for session name
                        self._handle_session_new()
                elif result == "COMPLETED":
                    # Operation completed successfully
                    self.app.notify("Operation completed", timeout=3)
                    self.dismiss()
                else:
                    # For read-only operations like session_list
                    self.app.notify(f"Session info: {result}", timeout=5)
                    self.dismiss()
            else:
                self.app.post_message(command["action"])
                self.dismiss()

    def _handle_session_set(self):
        """Handle the session set operation."""
        # Get list of sessions to show to user
        try:
            sessions = list_sessions()
            if not sessions:
                self.app.notify("No sessions available", timeout=3)
                self.dismiss()
                return

            # Create a dialog to select session
            from textual.widgets import Select
            from textual.containers import Vertical
            from .modals import InputDialog

            def on_session_selected(session_name: str):
                if session_name:
                    try:
                        set_active_session(session_name)
                        self.app._load_status_state()  # Refresh app state
                        self.app.notify(f"Session {session_name} set as active", timeout=3)
                    except Exception as e:
                        self.app.notify(f"Error setting active session: {str(e)}", severity="error", timeout=5)
                self.dismiss()

            # Show input dialog to ask for session ID or name
            input_dialog = InputDialog(
                message="Enter session ID or name to set as active:",
                title="Set Active Session"
            )
            self.app.push_screen(input_dialog, callback=on_session_selected)

        except Exception as e:
            self.app.notify(f"Error listing sessions: {str(e)}", severity="error", timeout=5)
            self.dismiss()

    def _handle_session_remove(self):
        """Handle the session remove operation."""
        def on_session_name_entered(session_name: str):
            if session_name:
                # Confirm deletion before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            remove_session(session_name)
                            self.app.notify(f"Session {session_name} removed", timeout=3)
                        except Exception as e:
                            self.app.notify(f"Error removing session: {str(e)}", severity="error", timeout=5)
                    self.dismiss()

                from .modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Permanently remove session '{session_name}'?\nThis cannot be undone.",
                    title="Confirm Delete"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.dismiss()

        # Show input dialog to ask for session ID or name
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter session ID or name to remove:",
            title="Remove Session"
        )
        self.app.push_screen(input_dialog, callback=on_session_name_entered)

    def _handle_session_new(self):
        """Handle the session new operation."""
        def on_session_info_entered(session_info: str):
            if session_info:
                try:
                    # Split by newline if provided (first line as name, second as root task)
                    lines = session_info.split('\n', 1)
                    name = lines[0].strip()
                    root_task_text = lines[1].strip() if len(lines) > 1 else name

                    created_session = create_session(name, root_task_text)
                    self.app.notify(f"Session '{name}' created successfully", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error creating session: {str(e)}", severity="error", timeout=5)
            self.dismiss()

        # Show input dialog for session name and optional root task
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter session name and optionally root task (separate with newline):",
            title="Create New Session"
        )
        self.app.push_screen(input_dialog, callback=on_session_info_entered)

    def execute_action_command(self, action_name: str):
        """Execute a specific action command and return result."""
        try:
            if action_name == "show_active_session":
                session = get_active_session()
                if session:
                    return f"Active Session: {session.id[:8]}... - {session.root_task[:50]}..."
                else:
                    return "No active session found"
            elif action_name == "list_sessions":
                sessions = list_sessions()
                if sessions:
                    session_list = [f"{s.id[:8]}... - {s.root_task[:30]}..." for s in sessions]
                    return f"Sessions ({len(sessions)}): {', '.join(session_list)}"
                else:
                    return "No sessions found"
            elif action_name == "show_active_plan":
                # For this to work, we need an active session
                if self.session_id:
                    from maestro.ui_facade.plans import get_active_plan
                    plan = get_active_plan(self.session_id)
                    if plan:
                        return f"Active Plan: {plan.plan_id[:8]}... - {plan.label}"
                    else:
                        return "No active plan found for session"
                else:
                    return "No session context for plan"
            elif action_name == "list_plans":
                # For this to work, we need an active session
                if self.session_id:
                    from maestro.ui_facade.plans import list_plans
                    plans = list_plans(self.session_id)
                    if plans:
                        plan_list = [f"{p.plan_id[:8]}... - {p.label}" for p in plans]
                        return f"Plans ({len(plans)}): {', '.join(plan_list)}"
                    else:
                        return "No plans found for session"
                else:
                    return "No session context for plans"
            elif action_name == "show_active_build_target":
                # Use a placeholder session ID
                build_target = get_active_build_target("default_session")
                if build_target:
                    return f"Active Build Target: {build_target.id[:8]}... - {build_target.name}"
                else:
                    return "No active build target found"
            elif action_name == "session_list":
                # Return sessions list
                sessions = list_sessions()
                if sessions:
                    session_list = [f"{s.id[:8]}... - {s.root_task[:30]}..." for s in sessions]
                    return f"Sessions ({len(sessions)}): {', '.join(session_list)}"
                else:
                    return "No sessions found"
            elif action_name == "session_new":
                # This operation requires user input, so we return a special value
                return "INPUT_NEEDED"
            elif action_name == "session_set":
                # This operation requires user input, so we return a special value
                return "INPUT_NEEDED"
            elif action_name == "session_remove":
                # This operation requires user input, so we return a special value
                return "INPUT_NEEDED"
            else:
                return f"Unknown command: {action_name}"
        except Exception as e:
            return f"Error executing command: {str(e)}"