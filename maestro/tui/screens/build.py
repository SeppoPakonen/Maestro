"""
Build Screen for Maestro TUI - Engineering Pit
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, RichLog, Tree, Collapsible, Input, Static
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual import on
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.css.query import NoMatches
from maestro.ui_facade.build import list_build_targets, get_active_build_target, set_active_build_target
from maestro.ui_facade.build import run_build, get_build_status, run_fix_loop, get_diagnostics, BuildTargetInfo, DiagnosticInfo
from maestro.ui_facade.sessions import get_active_session
import asyncio
from typing import List, Optional


class BuildTargetList(Widget):
    """Widget to display build target list."""

    # Reactive attribute to track selected build target
    selected_target_id = reactive(None)

    def __init__(self, targets=None, **kwargs):
        super().__init__(**kwargs)
        self.targets = targets or []

    def compose(self) -> ComposeResult:
        """Create child widgets for the build target list."""
        for i, target in enumerate(self.targets):
            # Determine active status
            is_active = self.app.active_build_target and self.app.active_build_target.id == target.id
            target_classes = ["build-target-item"]
            if target.id == self.selected_target_id:
                target_classes.append("selected")
            if is_active:
                target_classes.append("active")

            status_symbol = "✓" if target.status == "ok" else "✗" if target.status == "failed" else "?"

            yield Label(
                f"{target.name} ({target.id[:8]}...) {status_symbol}",
                id=f"target-{target.id}",
                classes=" ".join(target_classes)
            )

    def update_targets(self, targets):
        """Update the build target list."""
        self.targets = targets
        self.refresh()

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a build target to select it."""
        # Extract target ID from the label's ID
        if event.label.id and event.label.id.startswith("target-"):
            target_id = event.label.id[7:]  # Remove "target-" prefix
            self.selected_target_id = target_id
            # Notify parent screen about target selection
            self.post_message(BuildTargetSelected(target_id))


class TargetDetails(Widget):
    """Widget to display details about the selected build target."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.target = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the target details."""
        if self.target:
            yield Label(f"[b]Name:[/b] {self.target.name}", classes="target-detail")
            yield Label(f"[b]ID:[/b] {self.target.id}", classes="target-detail")
            yield Label(f"[b]Status:[/b] {self.target.status}", classes="target-detail")
            yield Label(f"[b]Path:[/b] {self.target.path}", classes="target-detail")
            if self.target.last_build_time:
                yield Label(f"[b]Last Built:[/b] {self.target.last_build_time}", classes="target-detail")
            if self.target.description:
                yield Label(f"[b]Description:[/b] {self.target.description}", classes="target-detail")
            if self.target.dependencies:
                dependencies_str = ", ".join(self.target.dependencies)
                yield Label(f"[b]Dependencies:[/b] {dependencies_str}", classes="target-detail")
        else:
            yield Label("Select a build target to view details", classes="placeholder")

    def set_target(self, target: BuildTargetInfo):
        """Set the target to display details for."""
        self.target = target
        self.refresh()


class DiagnosticGroup(Widget):
    """Widget to display diagnostics grouped by severity."""

    def __init__(self, level: str, diagnostics: List[DiagnosticInfo], **kwargs):
        super().__init__(**kwargs)
        self.level = level
        self.diagnostics = diagnostics
        self.is_collapsed = True

    def compose(self) -> ComposeResult:
        """Create child widgets for the diagnostic group."""
        # Header with toggle
        yield Label(f"[b]{self.level.upper()} ({len(self.diagnostics)})[/b]", id=f"diagnostic-group-header-{self.level}", classes="diagnostic-group-header")

        # Collapsible content
        collapsible = Collapsible(id=f"diagnostic-group-{self.level}", collapsed=True)
        with collapsible:
            for i, diag in enumerate(self.diagnostics):
                # Create a diagnostic item
                message = diag.message
                if diag.file_path:
                    message = f"{diag.file_path}:{diag.line_number or ''} - {message}"

                yield Label(
                    f"• {message}",
                    id=f"diagnostic-{diag.id}",
                    classes="diagnostic-item"
                )

    def toggle_collapse(self):
        """Toggle the collapsed state of the diagnostics."""
        try:
            collapsible = self.query_one(f"#diagnostic-group-{self.level}", Collapsible)
            collapsible.collapsed = not collapsible.collapsed
        except NoMatches:
            pass


class DiagnosticsViewer(Widget):
    """Widget to display build diagnostics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.diagnostics = []
        self.selected_diagnostic_id = reactive(None)

    def compose(self) -> ComposeResult:
        """Create child widgets for the diagnostics viewer."""
        if self.diagnostics:
            # Group diagnostics by level
            error_diags = [d for d in self.diagnostics if d.level == "error"]
            warning_diags = [d for d in self.diagnostics if d.level == "warning"]
            note_diags = [d for d in self.diagnostics if d.level == "note"]

            # Only create groups for levels that have diagnostics
            if error_diags:
                yield DiagnosticGroup("error", error_diags)
            if warning_diags:
                yield DiagnosticGroup("warning", warning_diags)
            if note_diags:
                yield DiagnosticGroup("note", note_diags)
        else:
            yield Label("No diagnostics to display", classes="placeholder")

    def update_diagnostics(self, diagnostics):
        """Update the diagnostics to display."""
        self.diagnostics = diagnostics
        self.refresh()

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a diagnostic message."""
        if event.label.id and event.label.id.startswith("diagnostic-"):
            diag_id = event.label.id[11:]  # Remove "diagnostic-" prefix
            self.selected_diagnostic_id = diag_id
            # Notify parent screen about diagnostic selection
            self.post_message(DiagnosticSelected(diag_id))
        elif event.label.id and event.label.id.startswith("diagnostic-group-header-"):
            # Toggle the group when header is clicked
            level = event.label.id[24:]  # Remove "diagnostic-group-header-" prefix
            try:
                group_widget = self.query_one(f"#diagnostic-group-{level}", Collapsible)
                group_widget.collapsed = not group_widget.collapsed
            except NoMatches:
                pass


class BuildControlBar(Widget):
    """Widget for build control buttons."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_buttons_state()

    def compose(self) -> ComposeResult:
        """Create child widgets for the control bar."""
        with Horizontal(classes="build-control-buttons"):
            yield Button("Run (R)", id="run-build", variant="primary")
            yield Button("Fix Loop (F)", id="run-fix-loop", variant="warning")
            yield Button("Status (S)", id="get-status", variant="default")
            yield Button("Refresh (r)", id="refresh", variant="success")

    def _update_buttons_state(self):
        """Update button states based on build state."""
        session = self.app.active_session
        if not session:
            return

        try:
            build_status = get_build_status(session.id)
            is_running = build_status.state == "running"

            # Update button states
            run_btn = self.query_one("#run-build", Button)
            fix_btn = self.query_one("#run-fix-loop", Button)
            status_btn = self.query_one("#get-status", Button)
            refresh_btn = self.query_one("#refresh", Button)

            run_btn.disabled = is_running
            fix_btn.disabled = is_running
            status_btn.disabled = is_running
            refresh_btn.disabled = is_running

        except Exception:
            # If widgets are not ready yet, skip updating
            pass


class StatusInfo(Widget):
    """Widget to display build status information."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_state = "idle"
        self.error_count = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the status info."""
        yield Label(f"State: {self.build_state.upper()}", id="build-state", classes="status-info")
        yield Label(f"Errors: {self.error_count}", id="error-count", classes="status-info")

    def update_status(self, state: str, error_count: int):
        """Update the status information."""
        self.build_state = state
        self.error_count = error_count
        self.refresh()
        try:
            state_label = self.query_one("#build-state", Label)
            error_label = self.query_one("#error-count", Label)
            state_label.update(f"State: {self.build_state.upper()}")
            error_label.update(f"Errors: {self.error_count}")
        except NoMatches:
            pass


class BuildScreen(Screen):
    """Build Studio screen of the Maestro TUI - The Engineering Pit."""

    CSS = """
    #main-content {
        layout: horizontal;
        height: 1fr;
    }

    .build-target-list-container {
        width: 30%;
        height: 1fr;
        border-right: solid $primary;
    }

    .center-panel {
        width: 50%;
        height: 1fr;
    }

    .target-details-container {
        height: 50%;
        border-bottom: solid $primary;
    }

    .diagnostics-container {
        height: 50%;
    }

    .actions-status-container {
        width: 20%;
        height: 1fr;
        border-left: solid $primary;
    }

    .build-control-buttons {
        height: auto;
        width: 100%;
        align: center middle;
        margin: 1 0;
    }

    .build-control-buttons Button {
        width: 100%;
        margin: 0.5 0;
    }

    .status-info {
        margin: 0.5 0;
    }

    .build-target-item {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    .build-target-item.selected {
        background: $accent 20%;
        text-style: reverse;
    }

    .build-target-item.active {
        text-style: bold;
    }

    .target-detail {
        margin: 0.2 0;
    }

    .placeholder {
        color: $text-muted;
        text-style: italic;
    }

    .diagnostic-group-header {
        cursor: pointer;
        background: $surface;
        padding: 0.5 1;
        border-bottom: solid $primary 1;
    }

    .diagnostic-item {
        padding: 0 1;
        margin: 0.2 0;
    }
    """

    # Reactive attribute to track execution state
    build_state = reactive("idle")  # idle, running, failed, ok
    fix_loop_state = reactive("idle")  # idle, running, stopped

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("R", "run_build", "Run Build"),
        ("F", "run_fix_loop", "Fix Loop"),
        ("s", "get_status", "Get Status"),
        ("enter", "set_active_target", "Set Active Target"),
        ("n", "create_new_target", "New Target"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the build screen."""
        yield Header()

        # Four-panel layout: Left (Targets), Center-Top (Details), Center-Bottom (Diagnostics), Right (Controls)
        with Horizontal(id="main-content"):
            # Left: Build Target List
            with Vertical(classes="build-target-list-container"):
                yield BuildTargetList(id="build-target-list")

            # Center: Details (top) and Diagnostics (bottom)
            with Vertical(classes="center-panel"):
                # Center-Top: Target Details
                with Container(classes="target-details-container"):
                    yield TargetDetails(id="target-details")

                # Center-Bottom: Diagnostics Viewer
                with Container(classes="diagnostics-container"):
                    yield DiagnosticsViewer(id="diagnostics-viewer")

            # Right: Actions & Status
            with Vertical(classes="actions-status-container"):
                yield BuildControlBar(id="control-bar")
                yield StatusInfo(id="status-info")

        # Status message area
        yield Label("Ready", id="status-message", classes="status-message")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load initial build target list
        self.refresh_build_targets()

        # Set up periodic refresh to update build statuses
        self.set_interval(2.0, self.refresh_build_targets)

        # Set up periodic check for build state
        self.set_interval(1.0, self._check_build_state)

    def refresh_build_targets(self) -> None:
        """Refresh the build target list from the backend."""
        try:
            session = get_active_session()
            if session:
                targets = list_build_targets(session.id)
                # Use call_later to ensure UI is ready before updating
                self.call_later(lambda: self._update_build_target_list(targets))
            else:
                # No active session
                self.call_later(lambda: self._update_build_target_list([]))
        except Exception:
            # If we can't load targets, show empty list
            self.call_later(lambda: self._update_build_target_list([]))

    def _update_build_target_list(self, targets):
        """Safely update the build target list."""
        try:
            target_list = self.query_one("#build-target-list", BuildTargetList)
            if target_list:
                target_list.update_targets(targets)
        except Exception:
            # If query fails, silently continue
            pass

    def _check_build_state(self) -> None:
        """Check build state and update UI accordingly."""
        try:
            session = get_active_session()
            if not session:
                return

            # Get build status and update status info
            build_status = get_build_status(session.id)

            # Update status info widget
            status_info = self.query_one("#status-info", StatusInfo)
            if status_info:
                status_info.update_status(build_status.state, build_status.error_count)

            # Update control bar button states
            control_bar = self.query_one("#control-bar", BuildControlBar)
            if control_bar:
                control_bar._update_buttons_state()

            # Update status message
            status_label = self.query_one("#status-message", Label)
            if status_label:
                if build_status.state == "running":
                    status_label.update(f"[bold green]RUNNING[/bold green] - Build in progress...")
                elif build_status.state == "failed":
                    status_label.update(f"[bold red]FAILED[/bold red] - {build_status.last_error_message or 'Build failed'}")
                elif build_status.state == "ok":
                    status_label.update("[bold green]OK[/bold green] - Build completed successfully")
                else:
                    status_label.update("Ready")
        except Exception:
            # If there's an issue checking build state, silently continue
            pass

    @on(Button.Pressed, "#run-build")
    def on_run_build_pressed(self) -> None:
        """Handle Run Build button press."""
        self.action_run_build()

    @on(Button.Pressed, "#run-fix-loop")
    def on_run_fix_loop_pressed(self) -> None:
        """Handle Fix Loop button press."""
        self.action_run_fix_loop()

    @on(Button.Pressed, "#get-status")
    def on_get_status_pressed(self) -> None:
        """Handle Get Status button press."""
        self.action_get_status()

    @on(Button.Pressed, "#refresh")
    def on_refresh_pressed(self) -> None:
        """Handle Refresh button press."""
        self.action_refresh()

    def action_set_active_target(self) -> None:
        """Set the selected build target as active."""
        try:
            target_list = self.query_one("#build-target-list", BuildTargetList)
            if target_list.selected_target_id:
                session = get_active_session()
                if session:
                    success = set_active_build_target(session.id, target_list.selected_target_id)
                    if success:
                        self.app._load_status_state()  # Refresh app state
                        self.notify(f"Build target {target_list.selected_target_id} set as active", timeout=3)
                        self.refresh_build_targets()  # Refresh to show active status
                    else:
                        self.notify(f"Failed to set {target_list.selected_target_id} as active", severity="error", timeout=3)
            else:
                self.notify("Please select a build target first", severity="warning", timeout=3)
        except NoMatches:
            self.notify("Build target list not found", severity="error", timeout=3)

    def action_create_new_target(self) -> None:
        """Create a new build target."""
        # In a real implementation, this would show a modal dialog for input
        # For now, show a notification
        self.notify("New target creation would open a modal dialog", timeout=3)

    def action_refresh(self) -> None:
        """Refresh the build target list and diagnostics."""
        self.refresh_build_targets()
        self.refresh_diagnostics()

    def action_run_build(self) -> None:
        """Run the selected build target."""
        try:
            session = get_active_session()
            if not session:
                self.notify("No active session found - please create or select a session first", severity="error")
                status_label = self.query_one("#status-message", Label)
                if status_label:
                    status_label.update("[bold red]ERROR[/bold red] - No active session")
                return

            target_list = self.query_one("#build-target-list", BuildTargetList)
            selected_target_id = target_list.selected_target_id

            # Check if build is already running
            build_status = get_build_status(session.id)
            if build_status.state == "running":
                self.notify("Build is already running - wait for completion", severity="warning")
                return

            # Update status message
            status_label = self.query_one("#status-message", Label)
            if status_label:
                status_label.update(f"[bold yellow]RUNNING[/bold yellow] - Starting build for {selected_target_id or 'active target'}... (Press S to check status)")

            # Run build in a separate thread to not block UI
            def run_build_in_thread():
                try:
                    result = run_build(session.id, selected_target_id)
                    if result.get("status") == "success":
                        self.call_from_thread(lambda: self._on_build_success(result))
                    else:
                        self.call_from_thread(lambda: self._on_build_failure(result))
                except Exception as e:
                    self.call_from_thread(lambda: self._on_build_error(str(e)))

            import threading
            thread = threading.Thread(target=run_build_in_thread, daemon=True)
            thread.start()
        except NoMatches:
            self.notify("Build target list not found", severity="error", timeout=3)

    def _on_build_success(self, result):
        """Handle successful build completion."""
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update("[bold green]SUCCESS[/bold green] - Build completed successfully")
        self.notify("Build completed successfully", timeout=3)

        # Refresh diagnostics after build
        self.refresh_diagnostics()

    def _on_build_failure(self, result):
        """Handle build failure."""
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update(f"[bold red]FAILED[/bold red] - Build failed: {result.get('error', 'Unknown error')}")
        self.notify("Build failed", severity="error", timeout=5)

    def _on_build_error(self, error_msg):
        """Handle build error."""
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update(f"[bold red]ERROR[/bold red] - {error_msg}")
        self.notify(f"Build error: {error_msg}", severity="error", timeout=5)

    def action_run_fix_loop(self) -> None:
        """Run the fix loop for the selected target."""
        try:
            session = get_active_session()
            if not session:
                self.notify("No active session found", severity="error")
                return

            target_list = self.query_one("#build-target-list", BuildTargetList)
            selected_target_id = target_list.selected_target_id

            # Check if build is already running
            build_status = get_build_status(session.id)
            if build_status.state == "running":
                self.notify("Build/fix loop is already running - wait for completion", severity="warning")
                return

            # Update status message
            status_label = self.query_one("#status-message", Label)
            if status_label:
                status_label.update("[bold yellow]RUNNING[/bold yellow] - Starting fix loop...")

            # Run fix loop in a separate thread to not block UI
            def run_fix_loop_in_thread():
                try:
                    result = run_fix_loop(session.id, selected_target_id, limit=None)
                    self.call_from_thread(lambda: self._on_fix_loop_complete(result))
                except Exception as e:
                    self.call_from_thread(lambda: self._on_fix_loop_error(str(e)))

            import threading
            thread = threading.Thread(target=run_fix_loop_in_thread, daemon=True)
            thread.start()
        except NoMatches:
            self.notify("Build target list not found", severity="error", timeout=3)

    def _on_fix_loop_complete(self, result):
        """Handle fix loop completion."""
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update(f"[bold green]FIX LOOP COMPLETE[/bold green] - Iteration: {result.get('iteration', 0)}, Remaining errors: {result.get('remaining_error_count', 0)}")
        self.notify(f"Fix loop iteration {result.get('iteration', 0)} completed. Remaining errors: {result.get('remaining_error_count', 0)}", timeout=5)

        # Refresh diagnostics after fix loop
        self.refresh_diagnostics()

    def _on_fix_loop_error(self, error_msg):
        """Handle fix loop error."""
        status_label = self.query_one("#status-message", Label)
        if status_label:
            status_label.update(f"[bold red]FIX LOOP ERROR[/bold red] - {error_msg}")
        self.notify(f"Fix loop error: {error_msg}", severity="error", timeout=5)

    def action_get_status(self) -> None:
        """Get current build status."""
        session = get_active_session()
        if not session:
            self.notify("No active session found", severity="error")
            return

        try:
            build_status = get_build_status(session.id)
            status_label = self.query_one("#status-message", Label)
            if status_label:
                status_label.update(f"Build Status: {build_status.state.upper()}, Errors: {build_status.error_count}")
            self.notify(f"Build State: {build_status.state}, Errors: {build_status.error_count}", timeout=3)
        except Exception as e:
            self.notify(f"Error getting build status: {str(e)}", severity="error", timeout=5)

    def on_build_target_selected(self, message: BuildTargetSelected) -> None:
        """Handle when a build target is selected to show its details."""
        target_id = message.target_id
        session = get_active_session()
        if session and target_id:
            # Find the selected target
            all_targets = list_build_targets(session.id)
            selected_target = next((t for t in all_targets if t.id == target_id), None)

            if selected_target:
                # Update target details
                target_details = self.query_one("#target-details", TargetDetails)
                target_details.set_target(selected_target)

                # Also update diagnostics for this target
                self.refresh_diagnostics(target_id)
            else:
                # Target not found, show placeholder
                target_details = self.query_one("#target-details", TargetDetails)
                target_details.set_target(None)

    def refresh_diagnostics(self, target_id: str = None):
        """Refresh the diagnostics display."""
        session = get_active_session()
        if session:
            try:
                diags = get_diagnostics(session.id, target_id)
                # Use call_later to ensure UI is ready before updating
                self.call_later(lambda: self._update_diagnostics(diags))
            except Exception as e:
                # If we can't load diagnostics, update with empty list
                self.call_later(lambda: self._update_diagnostics([]))

    def _update_diagnostics(self, diags):
        """Safely update the diagnostics viewer."""
        try:
            diagnostics_viewer = self.query_one("#diagnostics-viewer", DiagnosticsViewer)
            if diagnostics_viewer:
                diagnostics_viewer.update_diagnostics(diags)
        except Exception:
            # If query fails, silently continue
            pass

    def on_diagnostic_selected(self, message: DiagnosticSelected) -> None:
        """Handle when a diagnostic is selected."""
        diag_id = message.diag_id
        self.notify(f"Diagnostic selected: {diag_id}", timeout=2)


class BuildTargetSelected(Message):
    """Message sent when a build target is selected in the target list."""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id


class DiagnosticSelected(Message):
    """Message sent when a diagnostic is selected in the diagnostics viewer."""

    def __init__(self, diag_id: str) -> None:
        super().__init__()
        self.diag_id = diag_id