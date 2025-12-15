"""
Convert Screen for Maestro TUI - Pipeline Dashboard
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, Static
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from maestro.ui_facade.convert import get_pipeline_status, list_stages, get_stage_details, run_stage, get_checkpoints, list_run_history
from datetime import datetime


class RunHistoryPanel(Vertical):
    """Panel showing run history and statistics."""
    def __init__(self, pipeline_id: str = None):
        super().__init__()
        self.pipeline_id = pipeline_id

    def compose(self) -> ComposeResult:
        """Create child widgets for the run history panel."""
        try:
            # Get run history from facade
            run_histories = list_run_history(self.pipeline_id) if self.pipeline_id else []

            if run_histories:
                yield Label("[b]Recent Runs[/b]", classes="run-history-title")

                for history in run_histories[-5:]:  # Show last 5 runs
                    status_color = {
                        "completed": "green",
                        "running": "yellow",
                        "failed": "red",
                        "blocked": "orange",
                        "idle": "dim"
                    }.get(history.status, "dim")

                    yield Label(
                        f"[{status_color}]{history.run_id[:8]}... - {history.status.title()}[/]",
                        classes="run-item"
                    )

                    # Show summary of this run
                    yield Label(
                        f"  Stages: {len(history.stages)}, Checkpoints: {len(history.checkpoints)}, Warnings: {history.semantic_warnings}",
                        classes="run-summary"
                    )
            else:
                yield Label("No run history available", classes="placeholder")

        except Exception as e:
            yield Label(f"Error loading run history: {str(e)}", classes="error")


class StageTimeline(Vertical):
    """Left region: Shows stages in the conversion pipeline."""
    def __init__(self, pipeline_id: str = None):
        super().__init__()
        self.pipeline_id = pipeline_id
        self.current_selection = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the stage timeline."""
        # Get pipeline status from facade
        try:
            pipeline_status = get_pipeline_status(self.pipeline_id)
            stages = pipeline_status.stages
        except Exception:
            # If no pipeline found, show a placeholder
            stages = []

        # Create a list of stage labels for the timeline
        for i, stage in enumerate(stages):
            # Color based on status
            status_colors = {
                "pending": "dim",
                "running": "yellow",
                "completed": "green",
                "failed": "red",
                "blocked": "orange"
            }
            color = status_colors.get(stage.status, "dim")

            # Icon based on status
            status_icons = {
                "pending": "○",
                "running": "↻",
                "completed": "✓",
                "failed": "✗",
                "blocked": "⚠"
            }
            icon = status_icons.get(stage.status, "○")

            # Create stage label with status icon and color
            css_class = "selected" if i == 0 else ""
            yield Label(
                f"{icon} {stage.name.title()} [{stage.status}]",
                id=f"stage-{i}",
                classes=f"stage-item {css_class}",
                tooltip=stage.description
            )

        if not stages:
            yield Label("No conversion pipelines found", classes="placeholder")


class StageDetails(Vertical):
    """Center region: Shows details for selected stage."""
    def __init__(self, pipeline_id: str = None):
        super().__init__()
        self.pipeline_id = pipeline_id
        self.selected_stage = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the stage details."""
        if self.selected_stage:
            yield Label(f"[b]{self.selected_stage.name.title()}[/b]", classes="stage-title")
            yield Label(f"Status: [b]{self.selected_stage.status}[/b]", classes="stage-status")

            if self.selected_stage.start_time:
                start_time = datetime.fromisoformat(self.selected_stage.start_time.replace('Z', '+00:00'))
                yield Label(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", classes="stage-detail")

            if self.selected_stage.end_time:
                end_time = datetime.fromisoformat(self.selected_stage.end_time.replace('Z', '+00:00'))
                yield Label(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", classes="stage-detail")

            # Show artifacts if any
            if self.selected_stage.artifacts:
                yield Label("[b]Artifacts:[/b]", classes="artifacts-title")
                for artifact in self.selected_stage.artifacts:
                    yield Label(f"• {artifact}", classes="artifact-item")

            # Show description
            yield Label("\n[b]Description:[/b]", classes="description-title")
            yield Label(self.selected_stage.description, classes="description-text")

            # Show blocking reason if stage is blocked
            if self.selected_stage.status == "blocked" and self.selected_stage.reason:
                yield Label("\n[b]Blocking Reason:[/b]", classes="blocking-title")
                yield Label(self.selected_stage.reason, classes="blocking-reason")
        else:
            yield Label("Select a stage to view details", classes="placeholder")


class ControlsAndStatus(Vertical):
    """Right region: Shows controls and pipeline status."""
    def __init__(self, pipeline_id: str = None):
        super().__init__()
        self.pipeline_id = pipeline_id

    def compose(self) -> ComposeResult:
        """Create child widgets for controls and status."""
        # Pipeline status
        try:
            pipeline_status = get_pipeline_status(self.pipeline_id)
            yield Label(f"[b]Pipeline Status:[/b] {pipeline_status.status.title()}", classes="pipeline-status")
            if pipeline_status.active_stage:
                yield Label(f"[b]Active Stage:[/b] {pipeline_status.active_stage.title()}", classes="active-stage")
        except Exception:
            yield Label("[b]Pipeline Status:[/b] No pipeline found", classes="pipeline-status")

        # Context-sensitive buttons
        yield Button("Run Next Stage", id="run-next", variant="primary")
        yield Button("Run with Limit", id="run-limit", variant="default")
        yield Button("Rehearse", id="rehearse", variant="default")
        yield Button("Promote", id="promote", variant="success")
        yield Button("Stop", id="stop", variant="warning")

        # Checkpoint controls (if applicable)
        try:
            checkpoints = get_checkpoints(self.pipeline_id) if self.pipeline_id else []
            if checkpoints:
                yield Label("\n[b]Checkpoints:[/b]", classes="checkpoints-title")
                for checkpoint in checkpoints:
                    with Horizontal(classes="checkpoint-controls"):
                        yield Button(f"Approve {checkpoint.name}", id=f"approve-{checkpoint.id}", variant="primary", classes="checkpoint-button")
                        yield Button(f"Reject", id=f"reject-{checkpoint.id}", variant="error", classes="checkpoint-button")
                        yield Button(f"Override", id=f"override-{checkpoint.id}", variant="warning", classes="checkpoint-button")
        except Exception:
            pass

        # Run history section
        yield Label("\n[b]Run History:[/b]", classes="history-title")
        try:
            run_histories = list_run_history(self.pipeline_id) if self.pipeline_id else []
            if run_histories:
                for history in run_histories[-3:]:  # Show last 3 runs
                    status_color = {
                        "completed": "green",
                        "running": "yellow",
                        "failed": "red",
                        "blocked": "orange",
                        "idle": "dim"
                    }.get(history.status, "dim")

                    yield Label(
                        f"[{status_color}]{history.run_id[:8]}... - {history.status.title()}[/]",
                        classes="run-item-sm"
                    )
            else:
                yield Label("No history", classes="history-placeholder")
        except Exception:
            yield Label("History unavailable", classes="history-placeholder")


class ConvertScreen(Screen):
    """Convert screen of the Maestro TUI - Pipeline Dashboard."""

    # Reactive variables to track state
    selected_stage_index = reactive(0)
    pipeline_status = reactive("idle")

    BINDINGS = [
        ("enter", "run_next_stage", "Run next stage"),
        ("l", "run_with_limit", "Run with limit"),
        ("r", "rehearse", "Rehearse"),
        ("p", "promote", "Promote"),
        ("s", "stop", "Stop"),
        ("escape", "app.pop_screen", "Back"),
        ("ctrl+c", "stop", "Stop"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the convert screen."""
        yield Header(show_clock=True)

        # Create the main dashboard layout with three regions
        with Horizontal(id="dashboard-container"):
            # Left: Stage Timeline
            with Vertical(id="stage-timeline-container", classes="dashboard-panel"):
                yield StageTimeline()

            # Center: Stage Details
            with Vertical(id="stage-details-container", classes="dashboard-panel"):
                yield StageDetails()

            # Right: Controls & Status
            with Vertical(id="controls-container", classes="dashboard-panel"):
                yield ControlsAndStatus()

        yield Footer()

    def watch_pipeline_status(self, pipeline_status: str) -> None:
        """Called when the pipeline status changes."""
        # Update the screen title to reflect the current conversion state
        self.title = f"Maestro TUI - Convert Dashboard ({pipeline_status})"

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load initial pipeline data
        self.refresh_pipeline_display()

    def refresh_pipeline_display(self) -> None:
        """Refresh the pipeline display."""
        try:
            # Load pipeline status
            pipeline_status_obj = get_pipeline_status()

            # Update the reactive variable to reflect current status
            self.pipeline_status = pipeline_status_obj.status

            # Update the timeline
            timeline_container = self.query_one("#stage-timeline-container", expect_type=Vertical)
            timeline_container.remove_children()
            timeline = StageTimeline()
            timeline.mount_all(list(timeline.compose()))

            # Update the details panel for the first stage if available
            if pipeline_status_obj.stages:
                details_container = self.query_one("#stage-details-container", expect_type=Vertical)
                details_container.remove_children()
                details = StageDetails()
                details.selected_stage = pipeline_status_obj.stages[0]
                details.mount_all(list(details.compose()))

        except Exception as e:
            # If there's an error loading pipeline data, show appropriate message
            self.pipeline_status = "error"
            pass

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a stage in the timeline."""
        # Extract stage index from the clicked label
        if event.label.id and event.label.id.startswith("stage-"):
            try:
                stage_index = int(event.label.id.split("-")[1])

                # Update selection display
                for i in range(10):  # Assume max 10 stages for now
                    try:
                        label = self.query_one(f"#stage-{i}", expect_type=Label)
                        if i == stage_index:
                            label.add_class("selected")
                        else:
                            label.remove_class("selected")
                    except:
                        continue  # Skip if label doesn't exist

                # Update the details panel
                try:
                    pipeline_status = get_pipeline_status()
                    if stage_index < len(pipeline_status.stages):
                        selected_stage = pipeline_status.stages[stage_index]

                        # Update details panel
                        details_container = self.query_one("#stage-details-container", expect_type=Vertical)
                        details_container.remove_children()

                        details = StageDetails()
                        details.selected_stage = selected_stage
                        details.mount_all(list(details.compose()))

                except Exception:
                    pass
            except ValueError:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "run-next":
            self.action_run_next_stage()
        elif button_id == "run-limit":
            self.action_run_with_limit()
        elif button_id == "rehearse":
            self.action_rehearse()
        elif button_id == "promote":
            self.action_promote()
        elif button_id == "stop":
            self.action_stop()
        elif button_id and button_id.startswith("approve-"):
            # Handle checkpoint approval
            checkpoint_id = button_id.replace("approve-", "")
            self.action_approve_checkpoint(checkpoint_id)
        elif button_id and button_id.startswith("reject-"):
            # Handle checkpoint rejection
            checkpoint_id = button_id.replace("reject-", "")
            self.action_reject_checkpoint(checkpoint_id)
        elif button_id and button_id.startswith("override-"):
            # Handle checkpoint override
            checkpoint_id = button_id.replace("override-", "")
            self.action_override_checkpoint(checkpoint_id)

    def action_run_next_stage(self) -> None:
        """Action to run the next stage."""
        try:
            pipeline_status = get_pipeline_status()
            if pipeline_status.stages:
                # Find the next pending stage
                for stage in pipeline_status.stages:
                    if stage.status == "pending":
                        # Run this stage
                        success = run_stage(pipeline_status.id, stage.name)
                        if success:
                            self.app.notify(f"Started running {stage.name} stage", timeout=3)
                        else:
                            self.app.notify(f"Failed to start {stage.name} stage", timeout=3, severity="error")
                        break
                else:
                    self.app.notify("No pending stages to run", timeout=2)
            else:
                self.app.notify("No stages available in pipeline", timeout=2)
        except Exception as e:
            self.app.notify(f"Error running stage: {str(e)}", timeout=3, severity="error")

    def action_run_with_limit(self) -> None:
        """Action to run stage with limit."""
        # In a real implementation, this would prompt for the limit
        # For now, we'll just run with a default limit of 1
        try:
            pipeline_status = get_pipeline_status()
            if pipeline_status.stages:
                # Find the next pending stage
                for stage in pipeline_status.stages:
                    if stage.status == "pending":
                        # Run this stage with limit
                        success = run_stage(pipeline_status.id, stage.name, limit=1)
                        if success:
                            self.app.notify(f"Started running {stage.name} stage with limit", timeout=3)
                        else:
                            self.app.notify(f"Failed to start {stage.name} stage with limit", timeout=3, severity="error")
                        break
                else:
                    self.app.notify("No pending stages to run", timeout=2)
            else:
                self.app.notify("No stages available in pipeline", timeout=2)
        except Exception as e:
            self.app.notify(f"Error running stage with limit: {str(e)}", timeout=3, severity="error")

    def action_rehearse(self) -> None:
        """Action to rehearse (dry run)."""
        # For now, rehearse means running a stage in rehearsal mode
        # In a real implementation, this would be more complex
        self.app.notify("Rehearse mode - changes will not be applied", timeout=3)

    def action_promote(self) -> None:
        """Action to promote changes."""
        # In a real implementation, this would promote rehearsal results
        # For now, we'll just show a notification with confirmation
        def on_confirm(confirmed: bool):
            if confirmed:
                self.app.notify("Promoting changes...", timeout=3)
            else:
                self.app.notify("Promotion cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message="Promote rehearsal results to production?\nThis will apply all changes permanently.",
            title="Confirm Promotion"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_stop(self) -> None:
        """Action to stop execution."""
        self.app.notify("Stopping execution...", timeout=2)

    def action_approve_checkpoint(self, checkpoint_id: str) -> None:
        """Action to approve a checkpoint."""
        try:
            pipeline_status = get_pipeline_status()
            success = approve_checkpoint(pipeline_status.id, checkpoint_id)
            if success:
                self.app.notify(f"Checkpoint approved", timeout=3)
                # Refresh the display
                self.refresh_pipeline_display()
            else:
                self.app.notify(f"Failed to approve checkpoint", timeout=3, severity="error")
        except Exception as e:
            self.app.notify(f"Error approving checkpoint: {str(e)}", timeout=3, severity="error")

    def action_reject_checkpoint(self, checkpoint_id: str) -> None:
        """Action to reject a checkpoint."""
        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    pipeline_status = get_pipeline_status()
                    success = reject_checkpoint(pipeline_status.id, checkpoint_id)
                    if success:
                        self.app.notify(f"Checkpoint rejected", timeout=3)
                        # Refresh the display
                        self.refresh_pipeline_display()
                    else:
                        self.app.notify(f"Failed to reject checkpoint", timeout=3, severity="error")
                except Exception as e:
                    self.app.notify(f"Error rejecting checkpoint: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Checkpoint rejection cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message="Reject checkpoint?\nThis will mark the stage as failed.",
            title="Confirm Checkpoint Rejection"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_override_checkpoint(self, checkpoint_id: str) -> None:
        """Action to override a checkpoint."""
        def on_reason_entered(reason: str):
            if reason:
                try:
                    pipeline_status = get_pipeline_status()
                    success = override_checkpoint(pipeline_status.id, checkpoint_id, reason)
                    if success:
                        self.app.notify(f"Checkpoint overridden", timeout=3)
                        # Refresh the display
                        self.refresh_pipeline_display()
                    else:
                        self.app.notify(f"Failed to override checkpoint", timeout=3, severity="error")
                except Exception as e:
                    self.app.notify(f"Error overriding checkpoint: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Checkpoint override cancelled", timeout=2)

        from maestro.tui.widgets.modals import InputDialog
        input_dialog = InputDialog(
            message="Enter reason for overriding checkpoint:",
            title="Override Checkpoint"
        )
        self.app.push_screen(input_dialog, callback=on_reason_entered)