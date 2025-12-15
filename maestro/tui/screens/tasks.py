"""
Tasks Screen for Maestro TUI - Task Runner Control Room
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, RichLog
from textual.containers import Vertical, Horizontal, Container
from textual import on
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from maestro.ui_facade.tasks import list_tasks, run_tasks, resume_tasks, stop_tasks, get_current_execution_state, get_task_logs
from maestro.ui_facade.sessions import get_active_session
from maestro.tui.utils import ErrorNormalizer, ErrorModal
import asyncio


class TaskList(Widget):
    """Widget to display task list with status indicators."""

    # Reactive attribute to track selected task
    selected_task_id = reactive(None)

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_task", "Select"),
    ]

    def __init__(self, tasks=None, **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks or []
        self.focused_task_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the task list."""
        if not self.tasks:
            # Show a stable placeholder when no tasks are available
            yield Label("[i]Loading tasks...[/i]", id="loading-placeholder", classes="placeholder-stable")
        else:
            for i, task in enumerate(self.tasks):
                task_classes = ["task-item"]
                if task.id == self.selected_task_id:
                    task_classes.append("selected")
                if task.status == "in_progress":
                    task_classes.append("running")

                yield Label(
                    f"{task.id[:8]}... | {task.status.upper():>12} | {task.title}",
                    id=f"task-{task.id}",
                    classes=" ".join(task_classes)
                )

    def on_mount(self) -> None:
        """Set up keyboard focus for navigation."""
        self.focus()

    def update_tasks(self, tasks):
        """Update the task list."""
        self.tasks = tasks
        # Reset index when tasks are updated
        if self.tasks:
            self.focused_task_index = 0
            self.selected_task_id = self.tasks[0].id if self.tasks else None
        else:
            self.selected_task_id = None
        # Refresh the whole widget to update the content
        self.refresh()

    def action_cursor_up(self) -> None:
        """Move selection cursor up in the task list."""
        if self.tasks:
            self.focused_task_index = max(0, self.focused_task_index - 1)
            if self.focused_task_index < len(self.tasks):
                self.selected_task_id = self.tasks[self.focused_task_index].id
                self._notify_task_selection()

    def action_cursor_down(self) -> None:
        """Move selection cursor down in the task list."""
        if self.tasks:
            self.focused_task_index = min(len(self.tasks) - 1, self.focused_task_index + 1)
            if self.focused_task_index < len(self.tasks):
                self.selected_task_id = self.tasks[self.focused_task_index].id
                self._notify_task_selection()

    def action_select_task(self) -> None:
        """Select the currently focused task."""
        if self.tasks and 0 <= self.focused_task_index < len(self.tasks):
            self.selected_task_id = self.tasks[self.focused_task_index].id
            self._notify_task_selection()

    def _notify_task_selection(self) -> None:
        """Notify parent screen about task selection."""
        if self.selected_task_id:
            self.post_message(TaskSelected(self.selected_task_id))

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a task to select it."""
        # Extract task ID from the label's ID
        if event.label.id and event.label.id.startswith("task-"):
            task_id = event.label.id[5:]  # Remove "task-" prefix
            self.selected_task_id = task_id
            # Update focused index based on selected task
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    self.focused_task_index = i
                    break
            # Notify parent screen about task selection
            self.post_message(TaskSelected(task_id))


class LogViewer(Widget):
    """Widget to display live logs for the selected task."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logs = RichLog(
            max_lines=1000,
            markup=True,
            wrap=True,
            highlight=True,
            id="log-viewer"
        )
        # Auto-scroll is enabled by default in RichLog
        self.auto_scroll = True
        self.current_task_id = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the log viewer."""
        yield self.logs

    def append_log(self, text: str):
        """Append text to the log viewer."""
        try:
            self.logs.write(text)
        except Exception:
            # If there's an issue writing to the log, silently continue
            pass

    def clear_logs(self):
        """Clear all logs."""
        self.logs.clear()

    def toggle_auto_scroll(self):
        """Toggle auto-scrolling."""
        self.auto_scroll = not self.auto_scroll
        # RichLog auto-scroll is controlled by its internal state
        # This is a placeholder for more advanced scrolling control if needed

    def set_task_id(self, task_id: str):
        """Set the current task ID for log streaming."""
        self.current_task_id = task_id


class ControlBar(Widget):
    """Widget for execution control buttons."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_buttons_state()

    def compose(self) -> ComposeResult:
        """Create child widgets for the control bar."""
        with Horizontal(classes="control-buttons"):
            run_all_btn = Button("Run All (R)", id="run-all", variant="primary")
            run_all_btn.tooltip = "Will execute all pending tasks. [yellow]Requires confirmation[/yellow]"
            yield run_all_btn

            resume_btn = Button("Resume (Enter)", id="resume", variant="success")
            resume_btn.tooltip = "Will resume previously interrupted task execution. [yellow]Requires confirmation[/yellow]"
            yield resume_btn

            run_limit_btn = Button("Run with Limit (L)", id="run-limit", variant="warning")
            run_limit_btn.tooltip = "Will run a limited number of tasks. [yellow]Requires confirmation[/yellow]"
            yield run_limit_btn

            stop_btn = Button("Stop (S)", id="stop", variant="error")
            stop_btn.tooltip = "Will stop current execution. [yellow]Safe operation[/yellow]"
            yield stop_btn

    def _update_buttons_state(self):
        """Update button states based on execution state."""
        exec_state = get_current_execution_state()
        is_running = exec_state.get("is_running", False)

        # Update button states
        try:
            run_btn = self.query_one("#run-all", Button)
            resume_btn = self.query_one("#resume", Button)
            limit_btn = self.query_one("#run-limit", Button)
            stop_btn = self.query_one("#stop", Button)

            run_btn.disabled = is_running
            resume_btn.disabled = is_running
            limit_btn.disabled = is_running
            stop_btn.disabled = not is_running

        except:
            # If widgets are not ready yet, skip updating
            pass


class TasksScreen(Screen):
    """Task Runner Control Room screen of the Maestro TUI."""

    # Reactive attribute to track execution state
    execution_state = reactive("idle")  # idle, running, paused, interrupted

    BINDINGS = [
        ("r", "run_tasks", "Run All [i](Will modify state)[/i]"),
        ("enter", "resume_tasks", "Resume [i](Will modify state)[/i]"),
        ("l", "run_with_limit", "Run with Limit [i](Will modify state)[/i]"),
        ("s", "stop_tasks", "Stop [i](Will modify state)[/i]"),
        ("ctrl+c", "interrupt_execution", "Interrupt [i](Will modify state)[/i]"),
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the tasks screen."""
        yield Header()

        # Top: Execution Controls
        yield ControlBar(id="control-bar")

        # Center: Task List
        with Horizontal(id="main-content"):
            yield TaskList(id="task-list", classes="task-list-container")

            # Right: Log Viewer
            yield LogViewer(id="log-viewer", classes="log-viewer-container")

        # Status message area
        yield Label("Ready", id="status-message", classes="status-message")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load initial task list
        self.refresh_task_list()

        # Set up periodic refresh to update task statuses
        self.set_interval(2.0, self.refresh_task_list)

        # Set up periodic check for execution state
        self.set_interval(0.5, self._check_execution_state)

    def refresh_task_list(self) -> None:
        """Refresh the task list from the backend."""
        try:
            session = get_active_session()
            if session:
                tasks = list_tasks(session.id)
                # Use call_later to ensure UI is ready before updating
                self.call_later(lambda: self._update_task_list(tasks))
            else:
                # No active session
                self.call_later(lambda: self._update_task_list([]))
        except Exception as e:
            # If we can't load tasks, show empty list and notify user
            error_msg = ErrorNormalizer.normalize_exception(e, "loading tasks")
            self.app.push_screen(ErrorModal(error_msg))
            self.call_later(lambda: self._update_task_list([]))

    def _update_task_list(self, tasks):
        """Safely update the task list."""
        try:
            task_list = self.query_one("#task-list", TaskList)
            if task_list:
                task_list.update_tasks(tasks)
        except Exception:
            # If query fails, silently continue
            pass

    def _check_execution_state(self) -> None:
        """Check execution state and update UI accordingly."""
        try:
            exec_state = get_current_execution_state()
            is_running = exec_state.get("is_running", False)

            # Update control bar button states
            control_bar = self.query_one("#control-bar", ControlBar)
            if control_bar:
                control_bar._update_buttons_state()

            # Update status message
            status_label = self.query_one("#status-message", Label)
            if status_label:
                if is_running:
                    current_task_id = exec_state.get("current_task_id", "unknown")
                    status_label.update(f"[bold green]RUNNING[/bold green] - Current task: {current_task_id}")
                else:
                    status_label.update("Ready")
        except Exception:
            # If there's an issue checking execution state, silently continue
            pass

    @on(Button.Pressed, "#run-all")
    def on_run_all_pressed(self) -> None:
        """Handle Run All button press."""
        self.action_run_tasks()

    @on(Button.Pressed, "#resume")
    def on_resume_pressed(self) -> None:
        """Handle Resume button press."""
        self.action_resume_tasks()

    @on(Button.Pressed, "#run-limit")
    def on_run_limit_pressed(self) -> None:
        """Handle Run with Limit button press."""
        self.action_run_with_limit()

    @on(Button.Pressed, "#stop")
    def on_stop_pressed(self) -> None:
        """Handle Stop button press."""
        self.action_stop_tasks()

    def action_run_tasks(self) -> None:
        """Run all pending tasks."""
        session = get_active_session()
        if not session:
            self.notify("No active session found - please create or select a session first", severity="error")
            status_label = self.query_one("#status-message", Label)
            if status_label:
                status_label.update("[bold red]ERROR[/bold red] - No active session")
            return

        # Check if execution is already running
        exec_state = get_current_execution_state()
        if exec_state.get("is_running", False):
            self.notify("Tasks are already running - stop current execution first", severity="warning")
            return

        # Update status message
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update("[bold yellow]RUNNING[/bold yellow] - Starting task execution... (Press S to stop, Ctrl+C to interrupt)")

        # Run tasks in a separate thread to not block UI
        def status_callback(message):
            try:
                self.call_from_thread(lambda: self._update_status_safely(f"[bold yellow]RUNNING[/bold yellow] - {message}"))
            except:
                pass

        def output_callback(output):
            # Stream output to the log viewer
            try:
                self.call_from_thread(lambda: self._stream_output_to_viewer(output))
            except:
                pass

        try:
            # This would be done in a background thread in a real implementation
            # For this implementation, we'll use the facade directly
            run_tasks(session.id, on_status_change=status_callback, on_output=output_callback)
        except Exception as e:
            error_msg = ErrorNormalizer.normalize_exception(e, "running tasks")
            if status_label:
                status_label.update(f"[bold red]ERROR[/bold red] - {error_msg.message}")
            self.app.push_screen(ErrorModal(error_msg))

    def _update_status_safely(self, message: str):
        """Safely update the status message."""
        try:
            status_label = self.query_one("#status-message", Label)
            if status_label:
                status_label.update(message)
        except Exception:
            pass

    def _stream_output_to_viewer(self, output: str):
        """Stream output to the appropriate log viewer."""
        try:
            log_viewer = self.query_one("#log-viewer", LogViewer)

            # If there's a selected task or current running task, update that
            exec_state = get_current_execution_state()
            current_task_id = exec_state.get("current_task_id")

            if current_task_id and log_viewer.current_task_id == current_task_id:
                # Append to current log viewer
                log_viewer.append_log(output)
            elif log_viewer.current_task_id is None:
                # If no specific task selected, append to general view
                log_viewer.append_log(output)
            else:
                # Only append if we're showing logs for the current running task
                log_viewer.append_log(output)
        except Exception:
            # If there's an issue updating the log viewer, silently continue
            # or could use self.app.call_from_thread for safety
            pass

    def action_resume_tasks(self) -> None:
        """Resume interrupted tasks."""
        session = get_active_session()
        if not session:
            self.notify("No active session found", severity="error")
            return

        # Check if execution is already running
        exec_state = get_current_execution_state()
        if exec_state.get("is_running", False):
            self.notify("Tasks are already running", severity="warning")
            return

        # Update status message
        status_label = self.query_one("#status-message", Label)
        status_label.update("[bold yellow]RUNNING[/bold yellow] - Resuming interrupted tasks...")

        # Resume tasks in a separate thread to not block UI
        def status_callback(message):
            self.call_from_thread(lambda: status_label.update(f"[bold yellow]RUNNING[/bold yellow] - {message}"))

        def output_callback(output):
            # Stream output to the log viewer
            self.call_from_thread(lambda: self._stream_output_to_viewer(output))

        try:
            # This would be done in a background thread in a real implementation
            # For this implementation, we'll use the facade directly
            resume_tasks(session.id, on_status_change=status_callback, on_output=output_callback)
        except ValueError as e:
            # ValueError typically means no tasks to resume or session issues
            status_label.update(f"[bold red]NO TASKS TO RESUME[/bold red] - {str(e)}")
            self.app.push_screen(ErrorModal(ErrorNormalizer.normalize_exception(e, "resuming tasks")))
        except Exception as e:
            error_msg = ErrorNormalizer.normalize_exception(e, "resuming tasks")
            status_label.update(f"[bold red]ERROR[/bold red] - {error_msg.message}")
            self.app.push_screen(ErrorModal(error_msg))

    def action_run_with_limit(self) -> None:
        """Run tasks with a limit."""
        # In a real implementation, this would show a dialog to get the limit value
        # For now, we'll just run with a default limit of 2
        session = get_active_session()
        if not session:
            self.notify("No active session found", severity="error")
            return

        # Check if execution is already running
        exec_state = get_current_execution_state()
        if exec_state.get("is_running", False):
            self.notify("Tasks are already running", severity="warning")
            return

        # Update status message
        status_label = self.query_one("#status-message", Label)
        status_label.update("[bold yellow]RUNNING[/bold yellow] - Running tasks with limit...")

        # Run tasks with limit in a separate thread to not block UI
        def status_callback(message):
            self.call_from_thread(lambda: status_label.update(f"[bold yellow]RUNNING[/bold yellow] - {message}"))

        def output_callback(output):
            # Stream output to the log viewer
            self.call_from_thread(lambda: self._stream_output_to_viewer(output))

        try:
            # This would be done in a background thread in a real implementation
            # For this implementation, we'll use the facade directly with limit=2
            run_tasks(session.id, limit=2, on_status_change=status_callback, on_output=output_callback)
        except Exception as e:
            error_msg = ErrorNormalizer.normalize_exception(e, "running tasks with limit")
            status_label.update(f"[bold red]ERROR[/bold red] - {error_msg.message}")
            self.app.push_screen(ErrorModal(error_msg))

    def action_stop_tasks(self) -> None:
        """Request graceful stop of current execution."""
        success = stop_tasks()
        status_label = self.query_one("#status-message", Label)
        if success:
            if status_label:
                status_label.update("[bold red]STOPPING[/bold red] - Requesting graceful stop...")
            self.notify("Stop requested - tasks will finish gracefully", severity="warning", timeout=3)
        else:
            if status_label:
                status_label.update("Ready - No running tasks")
            self.notify("No running tasks to stop", severity="info", timeout=3)

    def action_interrupt_execution(self) -> None:
        """Handle Ctrl+C interrupt."""
        # Show a clear message about the interrupt
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update("[bold red]INTERRUPTING[/bold red] - Requesting graceful interruption...")

        # Call the stop function which handles soft interruption
        success = stop_tasks()
        if success:
            if status_label:
                status_label.update("[bold red]INTERRUPTED[/bold red] - Execution stopped. Press Enter to resume when ready.")
            self.notify("Execution interrupted. You can resume safely with Enter key or Resume button.", timeout=8)
        else:
            # If no tasks were running, just show current status
            if status_label:
                status_label.update("Ready")
            self.notify("No running tasks to interrupt", timeout=3)

    def action_cursor_up(self) -> None:
        """Pass up arrow to task list if focused there."""
        task_list = self.query_one("#task-list", TaskList)
        if task_list.has_focus:
            task_list.action_cursor_up()
        else:
            # If task list doesn't have focus, give it focus
            task_list.focus()

    def action_cursor_down(self) -> None:
        """Pass down arrow to task list if focused there."""
        task_list = self.query_one("#task-list", TaskList)
        if task_list.has_focus:
            task_list.action_cursor_down()
        else:
            # If task list doesn't have focus, give it focus
            task_list.focus()

    def watch_execution_state(self, old_state: str, new_state: str) -> None:
        """Watch for changes in execution state."""
        # Update UI elements based on state change
        status_label = self.query_one("#status-message", Label)
        if new_state == "running":
            status_label.update("[bold green]RUNNING[/bold green]")
        elif new_state == "idle":
            status_label.update("Ready")
        elif new_state == "interrupted":
            status_label.update("[bold red]INTERRUPTED[/bold red]")

    def on_task_selected(self, message: TaskSelected) -> None:
        """Handle when a task is selected to show its logs."""
        task_id = message.task_id
        session = get_active_session()
        if session and task_id:
            log_viewer = self.query_one("#log-viewer", LogViewer)
            log_viewer.set_task_id(task_id)  # Set the task ID for streaming
            try:
                log_content = get_task_logs(task_id, session.id)
                log_viewer.clear_logs()
                log_viewer.append_log(log_content)
            except Exception:
                log_viewer.clear_logs()
                log_viewer.append_log(f"Could not load logs for task {task_id}")


class TaskSelected(Message):
    """Message sent when a task is selected in the task list."""

    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id