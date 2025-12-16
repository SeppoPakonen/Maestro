"""
RunsPane - Run History and Management Pane for MC shell.

Implements run history management features including:
- Listing all past runs
- Showing details of specific runs
- Replaying runs
- Creating baselines
- Comparing runs for drift analysis
"""
from __future__ import annotations

import asyncio
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Label, ListItem, ListView, Static, Button
from textual.message import Message
from textual.reactive import reactive

from maestro.tui.panes.base import PaneView
from maestro.tui.menubar.model import Menu, MenuItem, Separator
from maestro.tui.utils import ErrorModal, ErrorNormalizer, memoization_cache
from maestro.tui.panes.registry import register_pane
from maestro.ui_facade.runs import (
    list_runs,
    get_run,
    get_run_manifest,
    replay_run,
    diff_runs,
    set_baseline,
    RunSummary,
    DriftInfo,
    RunManifest
)


class RunsPane(PaneView):
    """Run history and management view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_item", "Select"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f5", "refresh", "Refresh"),
        ("f6", "replay_run", "Replay Run"),
        ("f7", "create_baseline", "Create Baseline"),
        ("f8", "compare_runs", "Compare Runs"),
        ("f9", "open_menu", "Menu"),
    ]

    DEFAULT_CSS = """
    RunsPane {
        layout: vertical;
    }

    #runs-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #runs-body {
        height: 1fr;
    }

    #runs-list-pane, #runs-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #runs-list-pane {
        width: 45%;
    }

    #runs-detail-pane {
        width: 55%;
    }

    #runs-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }

    #runs-list {
        height: 1fr;
    }

    .run-status-ok {
        color: $success;
    }

    .run-status-drift {
        color: $warning;
    }

    .run-status-blocked {
        color: $error;
    }

    .run-mode-normal {
        color: $text;
    }

    .run-mode-rehearse {
        color: $info;
    }

    .run-mode-replay {
        color: $primary;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.pane_id = "runs"  # Required for the contract
        self.pane_title = "Runs"  # Required for the contract
        self.runs: List[RunSummary] = []
        self.selected_run_id: Optional[str] = None

    def on_mount(self) -> None:
        """Called when the pane is mounted to the DOM. Initialize UI elements and event handlers here."""
        self.call_after_refresh(self._load_initial_data)

    def _load_initial_data(self) -> None:
        """Load initial data after mount."""
        async def _async_load():
            await self.refresh_data()
        self.app.call_later(_async_load)

    def on_focus(self) -> None:
        """Called when the pane receives focus. Perform focus-specific operations."""
        # Refresh data when pane comes into focus
        self.refresh()

    def on_blur(self) -> None:
        """Called when the pane loses focus. Perform cleanup of focus-specific resources."""
        # No special cleanup needed for this pane
        pass

    def refresh_data(self) -> None:
        """Refresh pane data and UI. This is for explicit refresh requests."""
        self.call_after_refresh(self._refresh_data_async)

    def _refresh_data_async(self) -> None:
        """Call the async refresh method."""
        async def _async_refresh():
            await self.refresh_data()
        self.app.call_later(_async_refresh)

    def get_menu_spec(self) -> Menu:
        """Return the menu specification for this pane."""
        return Menu(
            label=self.pane_title,
            items=[
                MenuItem(
                    "refresh",
                    "Refresh",
                    action=self.refresh_data,
                    key_hint="F5",
                    fkey="F5",
                    action_id="runs.refresh",
                    trust_label="[RO]",
                ),
                Separator(),
                MenuItem(
                    "replay_run",
                    "Replay Selected Run",
                    action=self.replay_run_action,
                    key_hint="F6",
                    fkey="F6",
                    action_id="runs.replay",
                    trust_label="[MUT]",
                    requires_confirmation=True,
                    confirmation_label="Replay the selected run? This will re-execute with same parameters."
                ),
                MenuItem(
                    "create_baseline",
                    "Create Baseline",
                    action=self.create_baseline_action,
                    key_hint="F7",
                    fkey="F7",
                    action_id="runs.baseline",
                    trust_label="[MUT]",
                    requires_confirmation=True,
                    confirmation_label="Mark selected run as baseline? This affects future drift analysis."
                ),
                MenuItem(
                    "compare_runs",
                    "Compare Runs",
                    action=self.compare_runs_action,
                    key_hint="F8",
                    fkey="F8",
                    action_id="runs.compare",
                    trust_label="[RO]",
                ),
                Separator(),
                MenuItem(
                    "menu",
                    "Menu",
                    action=self.menu_action,
                    key_hint="F9",
                    fkey="F9",
                    action_id="runs.menu",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        try:
            yield Label("Run History & Management", id="runs-header")
            with Horizontal(id="runs-body"):
                with Vertical(id="runs-list-pane"):
                    yield Label("Run History", id="runs-list-title")
                    yield ListView(id="runs-list")
                with Vertical(id="runs-detail-pane"):
                    yield Label("Run Details", id="runs-detail-title")
                    yield Static("Select a run to view details.", id="runs-detail")
            yield Label("", id="runs-status")
        except Exception as e:
            # This is critical - never let a pane crash the shell
            try:
                yield Label(f"[RED]Error:[/RED] Failed to compose RunsPane: {str(e)}", id="error-label")
            except Exception:
                # If even the error display fails, yield a simple static
                yield Static("RunsPane failed to load")

    async def refresh_data(self) -> None:
        """Refresh run history data and UI."""
        try:
            # Load run summaries
            self.runs = list_runs()

            # Set default selection if none exists and we have runs
            if self.runs and not self.selected_run_id:
                self.selected_run_id = self.runs[0].run_id

        except Exception as exc:
            await self._show_error(exc, "loading run history")
            # Still render empty state
            self.runs = []
            return

        self._render_list()
        await self._load_details_for_selection()

        # Show status
        self.notify_status(f"Run history loaded: {len(self.runs)} runs")

        self.request_menu_refresh()

    def _render_list(self) -> None:
        """Render the ListView from run data."""
        try:
            list_view = self.query_one("#runs-list", ListView)
            list_view.clear()

            if not self.runs:
                list_view.append(ListItem(Label("No runs found [RO]")))
                list_view.index = 0
                self.selected_run_id = None
                self.request_menu_refresh()
                return

            for run in self.runs:
                # Format status with icon and color
                status_icons = {
                    "ok": "✓",
                    "drift": "⚠",
                    "blocked": "✗"
                }
                
                status_colors = {
                    "ok": "run-status-ok",
                    "drift": "run-status-drift",
                    "blocked": "run-status-blocked"
                }

                mode_classes = {
                    "normal": "run-mode-normal",
                    "rehearse": "run-mode-rehearse",
                    "replay": "run-mode-replay"
                }

                status_icon = status_icons.get(run.status, "?")
                status_class = status_colors.get(run.status, "")
                mode_class = mode_classes.get(run.mode, "")

                # Format the run item
                short_id = run.run_id.split('_')[-1] if '_' in run.run_id else run.run_id[:8]
                timestamp_str = run.timestamp.strftime("%m/%d %H:%M") if run.timestamp else "Unknown"
                baseline_label = f" [BASELINE: {run.baseline_tag}]" if run.baseline_tag else ""
                
                label = f"[{status_class}]{status_icon}[/] [{mode_class}]{run.mode.upper()}[/] {short_id} - {timestamp_str}{baseline_label}"
                list_view.append(ListItem(Label(label), id=f"run-{run.run_id}"))

            # Restore selection if possible
            if self.selected_run_id:
                run_ids = [f"run-{run.run_id}" for run in self.runs]
                if f"run-{self.selected_run_id}" in run_ids:
                    list_view.index = run_ids.index(f"run-{self.selected_run_id}")

            self.request_menu_refresh()
        except Exception as e:
            # Add error to the list view if possible
            try:
                list_view = self.query_one("#runs-list", ListView)
                list_view.clear()
                list_view.append(ListItem(Label(f"[RED]Error updating list: {str(e)}[/]")))
            except Exception:
                # If we can't update the list, just pass
                pass

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected run."""
        detail_widget = self.query_one("#runs-detail", Static)

        if not self.selected_run_id:
            detail_widget.update("No run selected.")
            return

        try:
            # Get run details
            run_detail = get_run(self.selected_run_id)
            if not run_detail:
                detail_widget.update(f"Run '{self.selected_run_id}' details not available.")
                return

            # Format detail information
            detail_lines = [
                f"[b]Run ID:[/b] {run_detail.run_id}",
                f"[b]Timestamp:[/b] {run_detail.timestamp}",
                f"[b]Mode:[/b] {run_detail.mode}",
                f"[b]Status:[/b] {run_detail.status}",
            ]

            if run_detail.baseline_tag:
                detail_lines.append(f"[b]Baseline:[/b] {run_detail.baseline_tag}")
            if run_detail.plan_revision:
                detail_lines.append(f"[b]Plan Revision:[/b] {run_detail.plan_revision}")
            if run_detail.decision_fingerprint:
                detail_lines.append(f"[b]Decision Fingerprint:[/b] {run_detail.decision_fingerprint[:12]}...")
            if run_detail.playbook_hash:
                detail_lines.append(f"[b]Playbook Hash:[/b] {run_detail.playbook_hash[:12]}...")

            if run_detail.engines_used:
                detail_lines.append(f"[b]Engines Used:[/b] {', '.join(run_detail.engines_used)}")

            detail_lines.append(f"[b]Checkpoints Hit:[/b] {run_detail.checkpoints_hit or 0}")
            detail_lines.append(f"[b]Semantic Warnings:[/b] {run_detail.semantic_warnings_count or 0}")
            detail_lines.append(f"[b]Arbitration Usage:[/b] {run_detail.arbitration_usage_count or 0}")

            # Try to get run manifest for more detailed info
            try:
                manifest = get_run_manifest(self.selected_run_id)
                if manifest and manifest.metadata:
                    detail_lines.append("")
                    detail_lines.append("[b]Additional Metadata:[/b]")
                    for key, value in manifest.metadata.items():
                        if key not in ['timestamp', 'mode', 'status']:  # Skip duplicates
                            detail_lines.append(f"  • {key}: {value}")
            except Exception:
                # If manifest isn't available, just continue without it
                pass

            detail_widget.update("\n".join(detail_lines))

        except Exception as exc:
            await self._show_error(exc, "loading run details")
            detail_widget.update(f"Error loading details for run '{self.selected_run_id}'")

    def _sync_selection_from_list(self) -> None:
        """Update selected_run_id from ListView and refresh details."""
        try:
            list_view = self.query_one("#runs-list", ListView)
            if list_view.index is None or not self.runs:
                return

            # Get the run ID from the list
            if 0 <= list_view.index < len(self.runs):
                self.selected_run_id = self.runs[list_view.index].run_id

                # Refresh the details panel
                self.call_after_refresh(self._load_details_for_selection)
            self.request_menu_refresh()
        except Exception as e:
            # Log error but don't crash the pane
            pass

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#runs-list", ListView)
        list_view.action_cursor_up()
        self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#runs-list", ListView)
        list_view.action_cursor_down()
        self._sync_selection_from_list()

    async def action_select_item(self) -> None:
        """Select the current item (equivalent to enter key)."""
        self._sync_selection_from_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "runs-list":
            return
        self._sync_selection_from_list()

    def action_focus_left(self) -> None:
        """Tab returns focus to the left navigation."""
        self.request_focus_left()

    def action_open_menu(self) -> None:
        """Expose menubar toggle from inside the pane."""
        try:
            if hasattr(self.app, "screen") and hasattr(self.app.screen, "action_toggle_menu"):
                self.app.screen.action_toggle_menu()  # type: ignore
        except Exception:
            pass

    def notify_status(self, message: str) -> None:
        """Update local status and inform shell."""
        try:
            self.query_one("#runs-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)
        self.request_menu_refresh()

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))

    # Action methods for menu items
    def replay_run_action(self) -> None:
        """Action to replay the selected run."""
        if not self.selected_run_id:
            self.notify_status("No run selected for replay")
            return

        try:
            result = replay_run(self.selected_run_id, apply=False)  # Dry run by default
            if result.get("success"):
                self.notify_status(f"Replay completed: {result.get('message', 'Unknown result')}")
            else:
                self.notify_status(f"Replay failed: {result.get('message', 'Unknown error')}")
        except Exception as e:
            self.notify_status(f"Error during replay: {str(e)}")

    def create_baseline_action(self) -> None:
        """Action to create a baseline from the selected run."""
        if not self.selected_run_id:
            self.notify_status("No run selected for baseline")
            return

        try:
            result = set_baseline(self.selected_run_id)
            if result.get("success"):
                self.notify_status(f"Baseline created: {result.get('message', 'Run marked as baseline')}")
                # Refresh to show the baseline tag
                self.call_after_refresh(self._refresh_data_async)
            else:
                self.notify_status(f"Failed to create baseline")
        except Exception as e:
            self.notify_status(f"Error creating baseline: {str(e)}")

    def compare_runs_action(self) -> None:
        """Action to compare runs (will need to select two runs)."""
        # For now, we'll just show a message; in a full implementation, this would 
        # allow the user to select a second run for comparison
        if not self.selected_run_id:
            self.notify_status("No run selected for comparison")
            return

        # In a real implementation, this would open a dialog to select a second run
        # For now, just show the first 3 runs as potential comparison targets
        if len(self.runs) > 1:
            other_runs = [r for r in self.runs if r.run_id != self.selected_run_id][:3]
            other_ids = [r.run_id.split('_')[-1] for r in other_runs]
            self.notify_status(f"Selected run for comparison: {self.selected_run_id.split('_')[-1]}. Other available: {', '.join(other_ids)}")
        else:
            self.notify_status("Not enough runs for comparison")

    def menu_action(self) -> None:
        """Action for menu."""
        self.action_open_menu()


# Register with the global pane registry
register_pane("runs", lambda: RunsPane())

# IMPORT-SAFE: no side effects allowed