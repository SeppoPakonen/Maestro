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
            {"name": "Go to memory", "action": "screen_memory", "type": "navigation"},
        ])

        # Quick action commands (read-only)
        commands.extend([
            {"name": "Show active session", "action": "show_active_session", "type": "action"},
            {"name": "List sessions", "action": "list_sessions", "type": "action"},
            {"name": "Show active plan", "action": "show_active_plan", "type": "action"},
            {"name": "List plans", "action": "list_plans", "type": "action"},
            {"name": "Show active build target", "action": "show_active_build_target", "type": "action"},
        ])

        # Plan operations
        commands.extend([
            {"name": "Plan: List all plans", "action": "plan_list", "type": "plan"},
            {"name": "Plan: Show plan tree", "action": "plan_tree", "type": "plan"},
            {"name": "Plan: Set active plan", "action": "plan_set", "type": "plan"},
            {"name": "Plan: Kill plan", "action": "plan_kill", "type": "plan"},
        ])

        # Session operations
        commands.extend([
            {"name": "Session: List all sessions", "action": "session_list", "type": "session"},
            {"name": "Session: Create new session", "action": "session_new", "type": "session"},
            {"name": "Session: Set active session", "action": "session_set", "type": "session"},
            {"name": "Session: Remove session", "action": "session_remove", "type": "session"},
        ])

        # Task operations
        commands.extend([
            {"name": "Task: Run all tasks", "action": "task_run", "type": "task"},
            {"name": "Task: Resume interrupted tasks", "action": "task_resume", "type": "task"},
            {"name": "Task: Run tasks with limit", "action": "task_run_limit", "type": "task"},
            {"name": "Task: Stop current execution", "action": "task_stop", "type": "task"},
        ])

        # Build operations
        commands.extend([
            {"name": "Build: List all build targets", "action": "build_list", "type": "build"},
            {"name": "Build: Set active build target", "action": "build_set", "type": "build"},
            {"name": "Build: Run build", "action": "build_run", "type": "build"},
            {"name": "Build: Run fix loop", "action": "build_fix", "type": "build"},
            {"name": "Build: Get status", "action": "build_status", "type": "build"},
        ])

        # Convert operations
        commands.extend([
            {"name": "Convert: Status", "action": "convert_status", "type": "convert"},
            {"name": "Convert: Run", "action": "convert_run", "type": "convert"},
            {"name": "Convert: Rehearse", "action": "convert_rehearse", "type": "convert"},
            {"name": "Convert: Promote", "action": "convert_promote", "type": "convert"},
        ])

        # Memory operations
        commands.extend([
            {"name": "Memory: Show all", "action": "memory_show", "type": "memory"},
            {"name": "Memory: Show decisions", "action": "memory_decisions", "type": "memory"},
            {"name": "Memory: Show conventions", "action": "memory_conventions", "type": "memory"},
            {"name": "Memory: Show glossary", "action": "memory_glossary", "type": "memory"},
            {"name": "Memory: Show issues", "action": "memory_issues", "type": "memory"},
            {"name": "Memory: Show summaries", "action": "memory_summaries", "type": "memory"},
        ])

        # Checkpoint operations
        commands.extend([
            {"name": "Convert: Approve checkpoint", "action": "convert_checkpoint_approve", "type": "checkpoint"},
            {"name": "Convert: Reject checkpoint", "action": "convert_checkpoint_reject", "type": "checkpoint"},
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
            # Handle plan operation commands that need special handling
            elif command["action"] in ["plan_list", "plan_tree", "plan_set", "plan_kill"]:
                result = self.execute_action_command(command["action"])
                if result == "INPUT_NEEDED":
                    # Special handling for plan operations that require input
                    if command["action"] == "plan_set":
                        # Show list of plans and let user select one to set as active
                        self._handle_plan_set()
                    elif command["action"] == "plan_kill":
                        # Show list of plans and let user select one to kill
                        self._handle_plan_kill()
                elif result == "NAVIGATE_TO_PLANS":
                    # Navigate to the plans screen
                    from maestro.tui.screens.plans import PlansScreen
                    # Switch to the plans screen content
                    self.app._switch_main_content(PlansScreen())
                    self.dismiss()
                else:
                    # For read-only operations like plan_list
                    self.app.notify(f"Plan info: {result}", timeout=5)
                    self.dismiss()
            # Handle build operation commands that need special handling
            elif command["action"] in ["build_list", "build_set", "build_run", "build_fix", "build_status"]:
                result = self.execute_action_command(command["action"])
                if result == "INPUT_NEEDED":
                    # Special handling for build operations that require input
                    if command["action"] == "build_set":
                        # Show list of build targets and let user select one to set as active
                        self._handle_build_set()
                else:
                    # For operations that don't require input
                    self.app.notify(f"Build operation: {result}", timeout=5)
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

    def _handle_plan_set(self):
        """Handle the plan set operation."""
        # Get list of plans to show to user
        if not self.session_id:
            self.app.notify("No active session", timeout=3)
            self.dismiss()
            return

        try:
            from maestro.ui_facade.plans import list_plans, set_active_plan
            plans = list_plans(self.session_id)
            if not plans:
                self.app.notify("No plans available", timeout=3)
                self.dismiss()
                return

            # Create a dialog to select plan
            from .modals import InputDialog

            def on_plan_selected(plan_id: str):
                if plan_id:
                    # Find the plan in the list
                    selected_plan = None
                    for plan in plans:
                        if plan.plan_id == plan_id or plan.plan_id.startswith(plan_id):
                            selected_plan = plan
                            break

                    if not selected_plan:
                        # If user didn't enter a full ID, try to match partial
                        matching_plans = [p for p in plans if p.plan_id.startswith(plan_id)]
                        if len(matching_plans) == 1:
                            selected_plan = matching_plans[0]
                        elif len(matching_plans) > 1:
                            self.app.notify(f"Multiple plans match '{plan_id}'. Please be more specific.", timeout=5)
                            self.dismiss()
                            return
                        else:
                            self.app.notify(f"No plan found with ID '{plan_id}'", timeout=5)
                            self.dismiss()
                            return

                    # Confirm setting active plan
                    def on_confirmed(confirmed: bool):
                        if confirmed:
                            try:
                                set_active_plan(self.session_id, selected_plan.plan_id)
                                # Update app state
                                self.app._load_status_state()
                                self.app.query_one("#active-plan").update(
                                    f" | Plan: {selected_plan.plan_id[:8]}..."
                                )
                                self.app.notify(f"Plan {selected_plan.plan_id[:8]}... set as active", timeout=3)
                            except Exception as e:
                                self.app.notify(f"Error setting active plan: {str(e)}", severity="error", timeout=5)
                        self.dismiss()

                    from .modals import ConfirmDialog
                    confirm_dialog = ConfirmDialog(
                        message=f"Set plan '{selected_plan.label}' as active?\nID: {selected_plan.plan_id[:8]}...",
                        title="Confirm Set Active Plan"
                    )
                    self.app.push_screen(confirm_dialog, callback=on_confirmed)
                else:
                    self.dismiss()

            # Show input dialog to ask for plan ID
            input_dialog = InputDialog(
                message="Enter plan ID to set as active:",
                title="Set Active Plan"
            )
            self.app.push_screen(input_dialog, callback=on_plan_selected)

        except Exception as e:
            self.app.notify(f"Error listing plans: {str(e)}", severity="error", timeout=5)
            self.dismiss()

    def _handle_build_set(self):
        """Handle the build set operation."""
        # Get list of build targets to show to user
        if not self.session_id:
            self.app.notify("No active session", timeout=3)
            self.dismiss()
            return

        try:
            from maestro.ui_facade.build import list_build_targets, set_active_build_target
            targets = list_build_targets(self.session_id)
            if not targets:
                self.app.notify("No build targets available", timeout=3)
                self.dismiss()
                return

            # Create a dialog to select build target
            from .modals import InputDialog

            def on_target_selected(target_id: str):
                if target_id:
                    # Find the target in the list
                    selected_target = None
                    for target in targets:
                        if target.id == target_id or target.id.startswith(target_id):
                            selected_target = target
                            break

                    if not selected_target:
                        # If user didn't enter a full ID, try to match partial
                        matching_targets = [t for t in targets if t.id.startswith(target_id)]
                        if len(matching_targets) == 1:
                            selected_target = matching_targets[0]
                        elif len(matching_targets) > 1:
                            self.app.notify(f"Multiple targets match '{target_id}'. Please be more specific.", timeout=5)
                            self.dismiss()
                            return
                        else:
                            self.app.notify(f"No build target found with ID '{target_id}'", timeout=5)
                            self.dismiss()
                            return

                    # Confirm setting active build target
                    def on_confirmed(confirmed: bool):
                        if confirmed:
                            try:
                                set_active_build_target(self.session_id, selected_target.id)
                                # Update app state
                                self.app._load_status_state()
                                self.app.query_one("#active-build").update(
                                    f" | Build: {selected_target.id[:8]}..."
                                )
                                self.app.notify(f"Build target {selected_target.id[:8]}... set as active", timeout=3)
                            except Exception as e:
                                self.app.notify(f"Error setting active build target: {str(e)}", severity="error", timeout=5)
                        self.dismiss()

                    from .modals import ConfirmDialog
                    confirm_dialog = ConfirmDialog(
                        message=f"Set build target '{selected_target.name}' as active?\nID: {selected_target.id[:8]}...",
                        title="Confirm Set Active Build Target"
                    )
                    self.app.push_screen(confirm_dialog, callback=on_confirmed)
                else:
                    self.dismiss()

            # Show input dialog to ask for build target ID
            input_dialog = InputDialog(
                message="Enter build target ID to set as active:",
                title="Set Active Build Target"
            )
            self.app.push_screen(input_dialog, callback=on_target_selected)

        except Exception as e:
            self.app.notify(f"Error listing build targets: {str(e)}", severity="error", timeout=5)
            self.dismiss()

    def _handle_plan_kill(self):
        """Handle the plan kill operation."""
        # Get list of plans to show to user
        if not self.session_id:
            self.app.notify("No active session", timeout=3)
            self.dismiss()
            return

        try:
            from maestro.ui_facade.plans import list_plans, kill_plan, get_plan_details
            plans = list_plans(self.session_id)
            if not plans:
                self.app.notify("No plans available", timeout=3)
                self.dismiss()
                return

            # Create a dialog to select plan
            from .modals import InputDialog

            def on_plan_selected(plan_id: str):
                if plan_id:
                    # Find the plan in the list
                    selected_plan = None
                    for plan in plans:
                        if plan.plan_id == plan_id or plan.plan_id.startswith(plan_id):
                            selected_plan = plan
                            break

                    if not selected_plan:
                        # If user didn't enter a full ID, try to match partial
                        matching_plans = [p for p in plans if p.plan_id.startswith(plan_id)]
                        if len(matching_plans) == 1:
                            selected_plan = matching_plans[0]
                        elif len(matching_plans) > 1:
                            self.app.notify(f"Multiple plans match '{plan_id}'. Please be more specific.", timeout=5)
                            self.dismiss()
                            return
                        else:
                            self.app.notify(f"No plan found with ID '{plan_id}'", timeout=5)
                            self.dismiss()
                            return

                    # Check if this plan is the active one
                    is_active = False
                    try:
                        active_plan = get_plan_details(self.session_id, selected_plan.plan_id)
                        if active_plan and self.app.active_session and self.app.active_session.active_plan_id == selected_plan.plan_id:
                            is_active = True
                    except:
                        pass  # If we can't determine if it's active, continue anyway

                    # Confirm killing the plan
                    def on_confirmed(confirmed: bool):
                        if confirmed:
                            try:
                                kill_plan(self.session_id, selected_plan.plan_id)
                                msg = f"Plan '{selected_plan.label}' killed"
                                if is_active:
                                    msg += " (was active plan)"
                                self.app.notify(msg, timeout=3)
                                # Update app state if needed
                                self.app._load_status_state()
                            except Exception as e:
                                self.app.notify(f"Error killing plan: {str(e)}", severity="error", timeout=5)
                        self.dismiss()

                    # Prepare confirmation message based on whether it's active
                    message = f"Kill plan '{selected_plan.label}'?\nID: {selected_plan.plan_id[:8]}..."
                    if is_active:
                        message += "\n\nWARNING: This is the active plan and will be deactivated."

                    from .modals import ConfirmDialog
                    confirm_dialog = ConfirmDialog(
                        message=message,
                        title="Confirm Kill Plan"
                    )
                    self.app.push_screen(confirm_dialog, callback=on_confirmed)
                else:
                    self.dismiss()

            # Show input dialog to ask for plan ID
            input_dialog = InputDialog(
                message="Enter plan ID to kill:",
                title="Kill Plan"
            )
            self.app.push_screen(input_dialog, callback=on_plan_selected)

        except Exception as e:
            self.app.notify(f"Error listing plans: {str(e)}", severity="error", timeout=5)
            self.dismiss()

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
            elif action_name == "plan_list":
                # Return plan list
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
            elif action_name == "plan_tree":
                # Navigate to plan tree screen
                return "NAVIGATE_TO_PLANS"
            elif action_name == "plan_set":
                # This operation requires user input for selecting the plan
                return "INPUT_NEEDED"
            elif action_name == "plan_kill":
                # This operation requires user input for selecting the plan
                return "INPUT_NEEDED"
            elif action_name == "build_set":
                # This operation requires user input for selecting the build target
                return "INPUT_NEEDED"
            elif action_name == "task_run":
                # Run all tasks
                from maestro.ui_facade.tasks import run_tasks, get_current_execution_state
                session = self.app.active_session
                if not session:
                    return "No active session to run tasks"

                exec_state = get_current_execution_state()
                if exec_state.get("is_running", False):
                    return "Tasks are already running"

                # Call run_tasks in a separate thread to prevent blocking
                def run_in_thread():
                    try:
                        run_tasks(session.id)
                    except Exception as e:
                        self.app.notify(f"Error running tasks: {str(e)}", severity="error")

                import threading
                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()

                return "Tasks started successfully"
            elif action_name == "task_resume":
                # Resume interrupted tasks
                from maestro.ui_facade.tasks import resume_tasks, get_current_execution_state
                session = self.app.active_session
                if not session:
                    return "No active session to resume tasks"

                exec_state = get_current_execution_state()
                if exec_state.get("is_running", False):
                    return "Tasks are already running"

                # Call resume_tasks in a separate thread to prevent blocking
                def resume_in_thread():
                    try:
                        resume_tasks(session.id)
                    except Exception as e:
                        self.app.notify(f"Error resuming tasks: {str(e)}", severity="error")

                import threading
                thread = threading.Thread(target=resume_in_thread, daemon=True)
                thread.start()

                return "Resume started successfully"
            elif action_name == "task_run_limit":
                # Run tasks with limit
                from maestro.ui_facade.tasks import run_tasks, get_current_execution_state
                session = self.app.active_session
                if not session:
                    return "No active session to run tasks"

                exec_state = get_current_execution_state()
                if exec_state.get("is_running", False):
                    return "Tasks are already running"

                # For now, we'll just run with a default limit of 2
                # In a real implementation, this would prompt for the limit value
                def run_with_limit_in_thread():
                    try:
                        run_tasks(session.id, limit=2)
                    except Exception as e:
                        self.app.notify(f"Error running tasks with limit: {str(e)}", severity="error")

                import threading
                thread = threading.Thread(target=run_with_limit_in_thread, daemon=True)
                thread.start()

                return "Tasks with limit started successfully"
            elif action_name == "task_stop":
                # Stop current execution
                from maestro.ui_facade.tasks import stop_tasks
                success = stop_tasks()
                if success:
                    return "Stop request sent successfully"
                else:
                    return "No running tasks to stop"
            elif action_name == "build_list":
                # List all build targets
                from maestro.ui_facade.build import list_build_targets
                session = self.app.active_session
                if session:
                    targets = list_build_targets(session.id)
                    if targets:
                        target_list = [f"{t.id[:8]}... - {t.name} ({t.status})" for t in targets]
                        return f"Build targets ({len(targets)}): {', '.join(target_list)}"
                    else:
                        return "No build targets found"
                else:
                    return "No active session for build targets"
            elif action_name == "build_set":
                # This operation requires user input for selecting the build target
                return "INPUT_NEEDED"
            elif action_name == "build_run":
                # Run build for active or selected target
                from maestro.ui_facade.build import run_build
                session = self.app.active_session
                if not session:
                    return "No active session to run build"

                # For now, run build with default target
                def run_build_in_thread():
                    try:
                        run_build(session.id)
                    except Exception as e:
                        self.app.notify(f"Error running build: {str(e)}", severity="error")

                import threading
                thread = threading.Thread(target=run_build_in_thread, daemon=True)
                thread.start()

                return "Build started successfully"
            elif action_name == "build_fix":
                # Run fix loop
                from maestro.ui_facade.build import run_fix_loop
                session = self.app.active_session
                if not session:
                    return "No active session to run fix loop"

                # For now, run fix loop with default settings
                def run_fix_in_thread():
                    try:
                        run_fix_loop(session.id)
                    except Exception as e:
                        self.app.notify(f"Error running fix loop: {str(e)}", severity="error")

                import threading
                thread = threading.Thread(target=run_fix_in_thread, daemon=True)
                thread.start()

                return "Fix loop started successfully"
            elif action_name == "build_status":
                # Get build status
                from maestro.ui_facade.build import get_build_status
                session = self.app.active_session
                if session:
                    status = get_build_status(session.id)
                    return f"Build Status: {status.state}, Errors: {status.error_count}"
                else:
                    return "No active session for build status"
            elif action_name == "convert_status":
                # Get convert pipeline status
                from maestro.ui_facade.convert import get_pipeline_status
                status = get_pipeline_status()
                if status:
                    return f"Convert Pipeline: {status.name}, Status: {status.status}, Active: {status.active_stage or 'None'}"
                else:
                    return "No convert pipeline found"
            elif action_name == "convert_run":
                # Run convert pipeline
                from maestro.ui_facade.convert import get_pipeline_status, list_stages, run_stage
                status = get_pipeline_status()
                if status and status.stages:
                    # Find the next pending stage and run it
                    for stage in status.stages:
                        if stage.status == "pending":
                            success = run_stage(status.id, stage.name)
                            if success:
                                return f"Started running {stage.name} stage"
                            else:
                                return f"Failed to start {stage.name} stage"
                    return "No pending stages to run"
                else:
                    return "No convert pipeline or stages found"
            elif action_name == "convert_rehearse":
                # Rehearse convert pipeline
                from maestro.ui_facade.convert import get_pipeline_status
                status = get_pipeline_status()
                if status:
                    # This would trigger a rehearsal mode in a real implementation
                    return f"Rehearse mode started for {status.name}"
                else:
                    return "No convert pipeline found"
            elif action_name == "convert_promote":
                # Promote convert results
                from maestro.ui_facade.convert import get_pipeline_status
                status = get_pipeline_status()
                if status:
                    # In a real implementation, this would promote changes
                    return f"Promoting results for {status.name}"
                else:
                    return "No convert pipeline found"
            elif action_name == "convert_checkpoint_approve":
                # Approve checkpoint
                from maestro.ui_facade.convert import get_pipeline_status, get_checkpoints, approve_checkpoint
                status = get_pipeline_status()
                if status:
                    checkpoints = get_checkpoints(status.id)
                    if checkpoints:
                        # For simplicity, approve the first pending checkpoint
                        for checkpoint in checkpoints:
                            if checkpoint.status == "pending":
                                success = approve_checkpoint(status.id, checkpoint.id)
                                if success:
                                    return f"Approved checkpoint: {checkpoint.name}"
                                else:
                                    return f"Failed to approve checkpoint: {checkpoint.name}"
                        return "No pending checkpoints to approve"
                    else:
                        return "No checkpoints found"
                else:
                    return "No convert pipeline found"
            elif action_name == "convert_checkpoint_reject":
                # Reject checkpoint
                from maestro.ui_facade.convert import get_pipeline_status, get_checkpoints, reject_checkpoint
                status = get_pipeline_status()
                if status:
                    checkpoints = get_checkpoints(status.id)
                    if checkpoints:
                        # For simplicity, reject the first pending checkpoint
                        for checkpoint in checkpoints:
                            if checkpoint.status == "pending":
                                success = reject_checkpoint(status.id, checkpoint.id)
                                if success:
                                    return f"Rejected checkpoint: {checkpoint.name}"
                                else:
                                    return f"Failed to reject checkpoint: {checkpoint.name}"
                        return "No pending checkpoints to reject"
                    else:
                        return "No checkpoints found"
                else:
                    return "No convert pipeline found"
            elif action_name == "screen_memory":
                # Navigate to memory screen
                from maestro.tui.screens.memory import MemoryScreen
                # Switch to the memory screen content
                self.app._switch_main_content(MemoryScreen())
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_show":
                # Navigate to memory screen (default to decisions)
                from maestro.tui.screens.memory import MemoryScreen
                # Switch to the memory screen content
                self.app._switch_main_content(MemoryScreen())
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_decisions":
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="decisions"))
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_conventions":
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="conventions"))
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_glossary":
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="glossary"))
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_issues":
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="open_issues"))
                self.dismiss()
                return "COMPLETED"
            elif action_name == "memory_summaries":
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="task_summaries"))
                self.dismiss()
                return "COMPLETED"
            else:
                return f"Unknown command: {action_name}"
        except Exception as e:
            return f"Error executing command: {str(e)}"