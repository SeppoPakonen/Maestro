"""
Replay & Baselines Screen
"""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Label, 
    DataTable, 
    TabbedContent, 
    TabPane, 
    Static, 
    Button,
    Tabs,
    ContentSwitcher
)
from textual import on
from maestro.ui_facade.runs import list_runs, get_run, get_run_manifest, replay_run, diff_runs, set_baseline


class ReplayScreen:
    """Screen for replaying runs and managing baselines"""
    
    def compose(self) -> ComposeResult:
        """Compose the replay screen with four regions"""
        # Main layout - four regions
        with Horizontal(id="main-content"):
            # Left: Run List
            with Vertical(id="run-list-container", classes="dashboard-panel"):
                yield Label("Run History", classes="history-title")
                yield DataTable(id="run-list-table", cursor_type="row")
            
            # Center-Left: Run Summary  
            with Vertical(id="run-summary-container", classes="dashboard-panel"):
                yield Label("Run Summary", classes="history-title")
                yield Static(id="run-summary-details", expand=True)
                
            # Center-Right: Diff & Drift Panel
            with Vertical(id="diff-drift-container", classes="dashboard-panel"):
                yield Label("Diff & Drift Analysis", classes="history-title")
                with TabbedContent(id="diff-tabs"):
                    with TabPane("Structural Drift", id="structural-drift-tab"):
                        yield Static("Structural drift details will appear here", id="structural-drift-content")
                    with TabPane("Decision Drift", id="decision-drift-tab"):
                        yield Static("Decision drift details will appear here", id="decision-drift-content")
                    with TabPane("Semantic Drift", id="semantic-drift-tab"):
                        yield Static("Semantic drift details will appear here", id="semantic-drift-content")
                        
            # Right: Actions Panel
            with Vertical(id="actions-container", classes="dashboard-panel"):
                yield Label("Actions", classes="history-title")
                yield Button("Replay (Dry)", variant="primary", id="replay-dry-btn")
                yield Button("Replay (Apply)", variant="error", id="replay-apply-btn")
                yield Button("Compare Against Baseline", variant="secondary", id="compare-baseline-btn")
                yield Button("Mark as Baseline", variant="success", id="mark-baseline-btn")
                yield Button("Export Run Manifest", variant="default", id="export-manifest-btn")

    def on_mount(self) -> None:
        """Initialize the screen when mounted"""
        self.load_run_list()
        
        # Setup button bindings
        self.query_one("#replay-dry-btn").disabled = True
        self.query_one("#replay-apply-btn").disabled = True
        self.query_one("#compare-baseline-btn").disabled = True
        self.query_one("#mark-baseline-btn").disabled = True
        self.query_one("#export-manifest-btn").disabled = True
        
        # Bind table selection to update run summary
        table = self.query_one("#run-list-table", DataTable)
        table.can_focus = True
        table.zebra_stripes = True

    def load_run_list(self) -> None:
        """Load the list of runs into the table"""
        table = self.query_one("#run-list-table", DataTable)
        
        # Clear existing data
        table.clear()
        
        # Add headers
        table.add_columns("Run ID", "Timestamp", "Mode", "Status", "Baseline Tag")

        # Get runs from facade
        runs = list_runs()

        # Add rows with styling based on status
        for run in runs:
            # Determine row color based on status
            status_display = run.status
            if run.status == "drift":
                status_display = f"[red]{run.status}[/red]"
            elif run.status == "blocked":
                status_display = f"[yellow]{run.status}[/yellow]"
            elif run.status == "ok":
                status_display = f"[green]{run.status}[/green]"

            table.add_row(
                run.run_id,
                run.timestamp.strftime("%Y-%m-%d %H:%M:%S") if run.timestamp else "",
                run.mode,
                status_display,
                run.baseline_tag or ""
            )
        
        # Bind selection event
        table.action_select_cursor_cell()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the run list table"""
        # Get selected row data
        table = self.query_one("#run-list-table", DataTable)
        selected_run_id = table.get_cell_at((event.cursor_row, 0))
        
        # Load run summary
        self.load_run_summary(selected_run_id)
        
        # Enable action buttons
        self.query_one("#replay-dry-btn").disabled = False
        self.query_one("#export-manifest-btn").disabled = False
        
        # Check if this run can be marked as baseline or compared
        run = get_run(selected_run_id)
        if run:
            if not run.baseline_tag:  # Only allow marking non-baselines
                self.query_one("#mark-baseline-btn").disabled = False
            else:
                self.query_one("#compare-baseline-btn").disabled = False

    def load_run_summary(self, run_id: str) -> None:
        """Load run summary details"""
        run = get_run(run_id)
        if not run:
            return
            
        summary_text = f"""Run ID: {run.run_id}
Timestamp: {run.timestamp.strftime("%Y-%m-%d %H:%M:%S") if run.timestamp else ""}
Mode: {run.mode}
Status: {run.status}
Baseline Tag: {run.baseline_tag or "N/A"}
Plan Revision: {run.plan_revision or "N/A"}
Decision Fingerprint: {run.decision_fingerprint or "N/A"}
Playbook Hash: {run.playbook_hash or "N/A"}
Engines Used: {", ".join(run.engines_used) if run.engines_used else "N/A"}
Checkpoints Hit: {run.checkpoints_hit or "N/A"}
Semantic Warnings: {run.semantic_warnings_count or "N/A"}
Arbitration Usage: {run.arbitration_usage_count or "N/A"}"""
        
        self.query_one("#run-summary-details", Static).update(summary_text)

    @on(Button.Pressed, "#replay-dry-btn")
    def on_replay_dry_pressed(self) -> None:
        """Handle dry replay button press"""
        table = self.query_one("#run-list-table", DataTable)
        if table.cursor_row is not None:
            selected_run_id = table.get_cell_at((table.cursor_row, 0))
            result = replay_run(selected_run_id, apply=False)
            # Show notification or update UI with results
            self.notify(f"Dry replay completed: {result['message']}")

    @on(Button.Pressed, "#replay-apply-btn")
    def on_replay_apply_pressed(self) -> None:
        """Handle apply replay button press"""
        table = self.query_one("#run-list-table", DataTable)
        if table.cursor_row is not None:
            selected_run_id = table.get_cell_at((table.cursor_row, 0))

            # First try to replay without override
            result = replay_run(selected_run_id, apply=True)

            if result.get("requires_override", False):
                # Drift threshold exceeded, ask for confirmation to override
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        # Try replay again with override
                        override_result = replay_run(selected_run_id, apply=True, override_drift_threshold=True)
                        self.notify(f"Apply replay completed: {override_result['message']}")
                    else:
                        self.notify("Apply replay cancelled by user")

                from textual.containers import Vertical
                from textual.widgets import Button, Label
                from textual.screen import ModalScreen

                class DriftOverrideModal(ModalScreen):
                    def compose(self) -> ComposeResult:
                        with Vertical(classes="dialog"):
                            yield Label("Drift threshold exceeded!")
                            yield Label(result.get("message", "Significant drift detected"))
                            yield Label("Do you want to override and proceed with apply?")
                            with Horizontal():
                                yield Button("Cancel", variant="default", id="cancel")
                                yield Button("Override & Apply", variant="error", id="override")

                    def on_button_pressed(self, event: Button.Pressed) -> None:
                        if event.button.id == "override":
                            on_confirmed(True)
                            self.dismiss()
                        else:
                            on_confirmed(False)
                            self.dismiss()

                # Show the modal
                self.app.push_screen(DriftOverrideModal())
            elif result.get("success"):
                self.notify(f"Apply replay completed: {result['message']}")
            else:
                self.notify(f"Apply replay failed: {result.get('message', 'Unknown error')}")

    @on(Button.Pressed, "#mark-baseline-btn")
    def on_mark_baseline_pressed(self) -> None:
        """Handle mark as baseline button press"""
        table = self.query_one("#run-list-table", DataTable)
        if table.cursor_row is not None:
            selected_run_id = table.get_cell_at((table.cursor_row, 0))
            result = set_baseline(selected_run_id)
            self.notify(f"{result['message']}")
            # Refresh the run list to show the updated baseline tag
            self.load_run_list()

    @on(Button.Pressed, "#compare-baseline-btn")
    def on_compare_baseline_pressed(self) -> None:
        """Handle compare against baseline button press"""
        # This would open a modal to select the baseline to compare against
        # For now, we'll just show a simple comparison to any available baseline
        table = self.query_one("#run-list-table", DataTable)
        if table.cursor_row is not None:
            selected_run_id = table.get_cell_at((table.cursor_row, 0))
            # Find the most recent baseline to compare against
            baseline_run = None
            for run in list_runs():
                if run.baseline_tag and run.run_id != selected_run_id:
                    baseline_run = run
                    break
            
            if baseline_run:
                diff_info = diff_runs(selected_run_id, baseline_run.run_id)
                if diff_info:
                    self.update_diff_panes(diff_info)
                else:
                    self.notify("Could not compare runs")
            else:
                self.notify("No baseline run found for comparison")

    @on(Button.Pressed, "#export-manifest-btn")
    def on_export_manifest_pressed(self) -> None:
        """Handle export run manifest button press"""
        table = self.query_one("#run-list-table", DataTable)
        if table.cursor_row is not None:
            selected_run_id = table.get_cell_at((table.cursor_row, 0))
            manifest = get_run_manifest(selected_run_id)
            if manifest:
                # In a real implementation, this would export to a file
                self.notify(f"Manifest for {selected_run_id} exported")

    def update_diff_panes(self, diff_info) -> None:
        """Update the diff panes with drift information"""
        # Update structural drift tab
        structural_content = f"""Files Changed: {len(diff_info.structural_drift.get('files_changed', []))}
Files Added: {len(diff_info.structural_drift.get('files_added', []))}
Files Removed: {len(diff_info.structural_drift.get('files_removed', []))}"""
        self.query_one("#structural-drift-content", Static).update(structural_content)
        
        # Update decision drift tab
        decision_content = f"""Fingerprint Delta: {diff_info.decision_drift.get('fingerprint_delta', 'N/A')}
Decisions Different: {len(diff_info.decision_drift.get('decisions_different', []))}"""
        self.query_one("#decision-drift-content", Static).update(decision_content)
        
        # Update semantic drift tab
        semantic_content = f"""Summary: {diff_info.semantic_drift.get('summary', 'N/A')}
Flags: {', '.join(diff_info.semantic_drift.get('flags', [])) if diff_info.semantic_drift.get('flags') else 'None'}"""
        self.query_one("#semantic-drift-content", Static).update(semantic_content)