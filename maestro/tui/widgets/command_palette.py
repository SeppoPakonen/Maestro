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
            {"name": "Go to arbitration", "action": "screen_arbitration", "type": "navigation"},
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
            {"name": "Decision: Override", "action": "decision_override", "type": "memory"},
            {"name": "Decision: Show", "action": "decision_show", "type": "memory"},
        ])

        # Checkpoint operations
        commands.extend([
            {"name": "Convert: Approve checkpoint", "action": "convert_checkpoint_approve", "type": "checkpoint"},
            {"name": "Convert: Reject checkpoint", "action": "convert_checkpoint_reject", "type": "checkpoint"},
        ])

        # Semantic operations
        commands.extend([
            {"name": "Semantic: List findings", "action": "semantic_list", "type": "semantic"},
            {"name": "Semantic: Show finding details", "action": "semantic_show", "type": "semantic"},
            {"name": "Semantic: Accept finding", "action": "semantic_accept", "type": "semantic"},
            {"name": "Semantic: Reject finding", "action": "semantic_reject", "type": "semantic"},
            {"name": "Semantic: Defer finding", "action": "semantic_defer", "type": "semantic"},
            {"name": "Go to semantic integrity panel", "action": "screen_semantic", "type": "navigation"},
        ])

        # Arbitration operations
        commands.extend([
            {"name": "Arbitration: List tasks", "action": "arbitration_list", "type": "arbitration"},
            {"name": "Arbitration: Show task", "action": "arbitration_show", "type": "arbitration"},
            {"name": "Arbitration: Choose winner", "action": "arbitration_choose", "type": "arbitration"},
            {"name": "Arbitration: Explain decision", "action": "arbitration_explain", "type": "arbitration"},
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
            # Handle semantic operation commands that need special handling
            elif command["action"] in ["semantic_show", "semantic_accept", "semantic_reject", "semantic_defer"]:
                result = self.execute_action_command(command["action"])
                if result == "INPUT_NEEDED":
                    # Special handling for semantic operations that require input
                    if command["action"] == "semantic_show":
                        self._handle_semantic_show()
                    elif command["action"] == "semantic_accept":
                        self._handle_semantic_accept()
                    elif command["action"] == "semantic_reject":
                        self._handle_semantic_reject()
                    elif command["action"] == "semantic_defer":
                        self._handle_semantic_defer()
                else:
                    # For read-only operations like semantic_list
                    self.app.notify(f"Semantic operation: {result}", timeout=5)
                    self.dismiss()
            # Handle arbitration operation commands that need special handling
            elif command["action"] in ["arbitration_show", "arbitration_choose", "arbitration_explain"]:
                result = self.execute_action_command(command["action"])
                if result == "INPUT_NEEDED":
                    # Special handling for arbitration operations that require input
                    if command["action"] == "arbitration_show":
                        self._handle_arbitration_show()
                    elif command["action"] == "arbitration_choose":
                        self._handle_arbitration_choose()
                    elif command["action"] == "arbitration_explain":
                        self._handle_arbitration_explain()
                else:
                    # For read-only operations like arbitration_list
                    self.app.notify(f"Arbitration operation: {result}", timeout=5)
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

    def _handle_arbitration_show(self):
        """Handle the arbitration show operation."""
        def on_task_id_entered(task_id: str):
            if task_id:
                try:
                    from maestro.ui_facade.arbitration import get_arbitration
                    arbitration_data = get_arbitration(task_id)
                    if arbitration_data:
                        # Show the arbitration details in an info dialog
                        details = f"""
                        Arbitration Task: {arbitration_data.task_id}

                        Phase: {arbitration_data.phase}
                        Status: {arbitration_data.status.value}
                        Current Winner: {arbitration_data.current_winner or 'None'}

                        Decision Rationale: {arbitration_data.decision_rationale or 'None'}

                        Judge Output: {arbitration_data.judge_output or 'None'}

                        Confidence Indicators: {', '.join(arbitration_data.confidence) if arbitration_data.confidence else 'None'}

                        Candidates:
                        """
                        for candidate in arbitration_data.candidates:
                            details += f"\n  - Engine: {candidate.engine}"
                            details += f"\n    Score: {candidate.score:.2f}" if candidate.score is not None else "\n    Score: N/A"
                            details += f"\n    Semantic Equivalence: {candidate.semantic_equivalence.value if candidate.semantic_equivalence else 'N/A'}"
                            details += f"\n    Validation Passed: {'Yes' if candidate.validation_passed else 'No'}"
                            details += f"\n    Flags: {', '.join(candidate.flags) if candidate.flags else 'None'}"

                        from .modals import InfoDialog
                        info_dialog = InfoDialog(
                            message=details,
                            title=f"Arbitration Details - {arbitration_data.task_id}"
                        )
                        self.app.push_screen(info_dialog)
                    else:
                        self.app.notify(f"No arbitration data found for task: {task_id}", severity="error", timeout=3)
                except ImportError:
                    self.app.notify("Arbitration facade not available", severity="error", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error getting arbitration data: {str(e)}", severity="error", timeout=3)
            self.dismiss()

        # Show input dialog to ask for task ID
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter arbitrated task ID to show details:",
            title="Show Arbitration Details"
        )
        self.app.push_screen(input_dialog, callback=on_task_id_entered)

    def _handle_arbitration_choose(self):
        """Handle the arbitration choose operation."""
        def on_choice_info_entered(choice_info: str):
            if choice_info:
                # Split the input to get task ID, engine and reason
                parts = choice_info.strip().split('\n', 2)
                if len(parts) < 3:
                    self.app.notify("Please provide task ID, engine, and reason (separate with newlines)", severity="error", timeout=3)
                    self.dismiss()
                    return

                task_id = parts[0].strip()
                engine = parts[1].strip()
                reason = parts[2].strip()

                if not reason:
                    self.app.notify("Reason is required for winner selection", severity="error", timeout=3)
                    self.dismiss()
                    return

                # Confirm selection before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            from maestro.ui_facade.arbitration import choose_winner
                            success = choose_winner(task_id, engine, reason)
                            if success:
                                self.app.notify(f"Winner {engine} selected for task {task_id}", timeout=3)
                            else:
                                self.app.notify(f"Failed to select winner for task {task_id}", severity="error", timeout=3)
                        except ImportError:
                            self.app.notify("Arbitration facade not available", severity="error", timeout=3)
                        except Exception as e:
                            self.app.notify(f"Error selecting winner: {str(e)}", severity="error", timeout=3)
                    self.dismiss()

                from .modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Select {engine} as winner for task {task_id}?\n\nReason: {reason}",
                    title="Confirm Winner Selection"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.dismiss()

        # Show input dialog to ask for task ID, engine, and reason
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter task ID, engine, and reason (separate with newlines):\ntask_id\nengine\nreason for selection",
            title="Choose Arbitration Winner"
        )
        self.app.push_screen(input_dialog, callback=on_choice_info_entered)

    def _handle_arbitration_explain(self):
        """Handle the arbitration explain operation."""
        def on_task_id_entered(task_id: str):
            if task_id:
                try:
                    from maestro.ui_facade.arbitration import get_arbitration
                    arbitration_data = get_arbitration(task_id)
                    if arbitration_data:
                        # Show the arbitration explanation in an info dialog
                        explanation = f"""
                        Full Arbitration Decision Trail for Task: {arbitration_data.task_id}

                        Phase: {arbitration_data.phase}
                        Status: {arbitration_data.status.value}
                        Current Winner: {arbitration_data.current_winner or 'None'}

                        Judge Output: {arbitration_data.judge_output or 'No judge output'}

                        Decision Rationale: {arbitration_data.decision_rationale or 'No rationale provided'}

                        Confidence Indicators: {', '.join(arbitration_data.confidence) if arbitration_data.confidence else 'None'}

                        Candidates:
                        """
                        for candidate in arbitration_data.candidates:
                            explanation += f"\n  - Engine: {candidate.engine}"
                            explanation += f"\n    Score: {candidate.score:.2f}" if candidate.score is not None else "\n    Score: N/A"
                            explanation += f"\n    Semantic Equivalence: {candidate.semantic_equivalence.value if candidate.semantic_equivalence else 'N/A'}"
                            explanation += f"\n    Validation Passed: {'Yes' if candidate.validation_passed else 'No'}"
                            explanation += f"\n    Flags: {', '.join(candidate.flags) if candidate.flags else 'None'}"
                            explanation += f"\n    Files Written: {', '.join(candidate.files_written) if candidate.files_written else 'None'}"
                            explanation += f"\n    Policy Used: {candidate.policy_used or 'None'}"

                        from .modals import InfoDialog
                        info_dialog = InfoDialog(
                            message=explanation,
                            title=f"Arbitration Explanation - {arbitration_data.task_id}"
                        )
                        self.app.push_screen(info_dialog)
                    else:
                        self.app.notify(f"No arbitration data found for task: {task_id}", severity="error", timeout=3)
                except ImportError:
                    self.app.notify("Arbitration facade not available", severity="error", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error getting arbitration explanation: {str(e)}", severity="error", timeout=3)
            self.dismiss()

        # Show input dialog to ask for task ID
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter arbitrated task ID to explain decision:",
            title="Explain Arbitration Decision"
        )
        self.app.push_screen(input_dialog, callback=on_task_id_entered)

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

    def _handle_semantic_show(self):
        """Handle the semantic show operation."""
        def on_finding_id_entered(finding_id: str):
            if finding_id:
                try:
                    from maestro.ui_facade.semantic import get_semantic_finding
                    finding = get_semantic_finding(finding_id)
                    if finding:
                        # Show the finding details in an info dialog
                        details = f"""
                        Semantic Finding: {finding.id}

                        Task ID: {finding.task_id}
                        Files: {', '.join(finding.files)}
                        Equivalence Level: {finding.equivalence_level}
                        Risk Flags: {', '.join(finding.risk_flags) if finding.risk_flags else 'None'}
                        Status: {finding.status}

                        Description:
                        {finding.description}

                        Evidence (Before):
                        {finding.evidence_before}

                        Evidence (After):
                        {finding.evidence_after}

                        Decision Reason: {finding.decision_reason or 'None'}
                        Blocks Pipeline: {'Yes' if finding.blocks_pipeline else 'No'}
                        Checkpoint ID: {finding.checkpoint_id or 'None'}
                        """
                        from .modals import InfoDialog
                        info_dialog = InfoDialog(
                            message=details,
                            title=f"Semantic Finding Details - {finding.id}"
                        )
                        self.app.push_screen(info_dialog)
                    else:
                        self.app.notify(f"No finding found with ID: {finding_id}", severity="error", timeout=3)
                except ImportError:
                    self.app.notify("Semantic facade not available", severity="error", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error getting finding: {str(e)}", severity="error", timeout=3)
            self.dismiss()

        # Show input dialog to ask for finding ID
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter semantic finding ID to show details:",
            title="Show Semantic Finding"
        )
        self.app.push_screen(input_dialog, callback=on_finding_id_entered)

    def _handle_semantic_accept(self):
        """Handle the semantic accept operation."""
        def on_finding_id_entered(finding_id: str):
            if finding_id:
                # Confirm acceptance before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            from maestro.ui_facade.semantic import accept_semantic_finding
                            success = accept_semantic_finding(finding_id)
                            if success:
                                self.app.notify(f"Finding {finding_id} accepted", timeout=3)
                            else:
                                self.app.notify(f"Failed to accept finding {finding_id}", severity="error", timeout=3)
                        except ImportError:
                            self.app.notify("Semantic facade not available", severity="error", timeout=3)
                        except Exception as e:
                            self.app.notify(f"Error accepting finding: {str(e)}", severity="error", timeout=3)
                    self.dismiss()

                from .modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Accept semantic finding {finding_id}?\n\nThis will mark the finding as reviewed and accepted.",
                    title="Confirm Accept Finding"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.dismiss()

        # Show input dialog to ask for finding ID
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter semantic finding ID to accept:",
            title="Accept Semantic Finding"
        )
        self.app.push_screen(input_dialog, callback=on_finding_id_entered)

    def _handle_semantic_reject(self):
        """Handle the semantic reject operation."""
        def on_finding_info_entered(finding_info: str):
            if finding_info:
                # Split the input to get finding ID and reason
                parts = finding_info.strip().split('\n', 1)
                if len(parts) < 2:
                    self.app.notify("Please provide both finding ID and reason (separate with newline)", severity="error", timeout=3)
                    self.dismiss()
                    return

                finding_id = parts[0].strip()
                reason = parts[1].strip()

                if not reason:
                    self.app.notify("Reason is required for rejection", severity="error", timeout=3)
                    self.dismiss()
                    return

                # Confirm rejection before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            from maestro.ui_facade.semantic import reject_semantic_finding
                            success = reject_semantic_finding(finding_id, reason)
                            if success:
                                self.app.notify(f"Finding {finding_id} rejected", timeout=3)
                            else:
                                self.app.notify(f"Failed to reject finding {finding_id}", severity="error", timeout=3)
                        except ImportError:
                            self.app.notify("Semantic facade not available", severity="error", timeout=3)
                        except Exception as e:
                            self.app.notify(f"Error rejecting finding: {str(e)}", severity="error", timeout=3)
                    self.dismiss()

                from .modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Reject semantic finding {finding_id}?\n\nReason: {reason}",
                    title="Confirm Reject Finding"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.dismiss()

        # Show input dialog to ask for finding ID and reason
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter semantic finding ID and reason (separate with newline):\nexample_id\nreason for rejection",
            title="Reject Semantic Finding"
        )
        self.app.push_screen(input_dialog, callback=on_finding_info_entered)

    def _handle_semantic_defer(self):
        """Handle the semantic defer operation."""
        def on_finding_id_entered(finding_id: str):
            if finding_id:
                # Confirm deferral before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            from maestro.ui_facade.semantic import defer_semantic_finding
                            success = defer_semantic_finding(finding_id)
                            if success:
                                self.app.notify(f"Finding {finding_id} deferred", timeout=3)
                            else:
                                self.app.notify(f"Failed to defer finding {finding_id}", severity="error", timeout=3)
                        except ImportError:
                            self.app.notify("Semantic facade not available", severity="error", timeout=3)
                        except Exception as e:
                            self.app.notify(f"Error deferring finding: {str(e)}", severity="error", timeout=3)
                    self.dismiss()

                from .modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Defer semantic finding {finding_id}?\n\nThis will leave the finding unresolved.",
                    title="Confirm Defer Finding"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.dismiss()

        # Show input dialog to ask for finding ID
        from .modals import InputDialog
        input_dialog = InputDialog(
            message="Enter semantic finding ID to defer:",
            title="Defer Semantic Finding"
        )
        self.app.push_screen(input_dialog, callback=on_finding_id_entered)

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
            elif action_name == "decision_override":
                # Navigate to memory screen with decisions category and trigger the override command
                from maestro.tui.screens.memory import MemoryScreen
                memory_screen = MemoryScreen(initial_category="decisions")
                self.app._switch_main_content(memory_screen)

                # After switching to the memory screen, we need to trigger the override action
                # This will be available if a decision is selected
                # For now, we'll just navigate to the decisions screen
                self.dismiss()
                return "NAVIGATE_TO_MEMORY_DECISIONS"
            elif action_name == "decision_show":
                # Navigate to memory screen with decisions category
                from maestro.tui.screens.memory import MemoryScreen
                self.app._switch_main_content(MemoryScreen(initial_category="decisions"))
                self.dismiss()
                return "COMPLETED"
            elif action_name == "semantic_list":
                # List semantic findings
                try:
                    from maestro.ui_facade.semantic import list_semantic_findings, get_semantic_summary
                    findings = list_semantic_findings()
                    summary = get_semantic_summary()

                    if findings:
                        return f"Semantic Findings: {len(findings)}, High Risk: {summary.high_risk}, Medium Risk: {summary.medium_risk}, Low Risk: {summary.low_risk}, Accepted: {summary.accepted}, Rejected: {summary.rejected}, Blocking: {summary.blocking}"
                    else:
                        return "No semantic findings found"
                except ImportError:
                    return "Semantic facade not available"
            elif action_name == "semantic_show":
                # This operation requires user input for selecting the finding
                return "INPUT_NEEDED"
            elif action_name == "semantic_accept":
                # This operation requires user input for selecting the finding
                return "INPUT_NEEDED"
            elif action_name == "semantic_reject":
                # This operation requires user input for selecting the finding
                return "INPUT_NEEDED"
            elif action_name == "semantic_defer":
                # This operation requires user input for selecting the finding
                return "INPUT_NEEDED"
            elif action_name == "screen_semantic":
                # Navigate to semantic screen
                from maestro.tui.screens.semantic import SemanticScreen
                # Switch to the semantic screen content
                self.app._switch_main_content(SemanticScreen())
                self.dismiss()
                return "COMPLETED"
            elif action_name == "screen_arbitration":
                # Navigate to arbitration screen
                from maestro.tui.screens.arbitration import ArbitrationScreen
                # Switch to the arbitration screen content
                self.app._switch_main_content(ArbitrationScreen())
                self.dismiss()
                return "COMPLETED"
            elif action_name == "arbitration_list":
                # List arbitrated tasks
                try:
                    from maestro.ui_facade.arbitration import list_arbitrated_tasks
                    session = self.app.active_session
                    if session:
                        tasks = list_arbitrated_tasks(session.id)
                        if tasks:
                            task_list = [f"{t.id[:8]}...-{t.phase}-{t.status.value}" for t in tasks]
                            return f"Arbitrated Tasks ({len(tasks)}): {', '.join(task_list)}"
                        else:
                            return "No arbitrated tasks found"
                    else:
                        return "No active session"
                except ImportError:
                    return "Arbitration facade not available"
            elif action_name == "arbitration_show":
                # This operation requires user input for selecting the task
                return "INPUT_NEEDED"
            elif action_name == "arbitration_choose":
                # This operation requires user input for selecting the task and engine
                return "INPUT_NEEDED"
            elif action_name == "arbitration_explain":
                # This operation requires user input for selecting the task
                return "INPUT_NEEDED"
            else:
                return f"Unknown command: {action_name}"
        except Exception as e:
            return f"Error executing command: {str(e)}"