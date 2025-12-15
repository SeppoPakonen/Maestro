"""
Arbitration Arena Screen for Multi-Engine Comparison & Human Verdict
"""
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, RichLog, DataTable
from textual.containers import Vertical, Horizontal, Container
from textual import on
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from maestro.ui_facade.arbitration import (
    list_arbitrated_tasks,
    get_arbitration,
    list_candidates,
    get_candidate,
    choose_winner,
    reject_candidate
)
from maestro.ui_facade.sessions import get_active_session
import asyncio


class TaskList(Widget):
    """Widget to display arbitrated tasks with status indicators."""

    # Reactive attribute to track selected task
    selected_task_id = reactive(None)

    def __init__(self, tasks=None, **kwargs):
        super().__init__(**kwargs)
        self.tasks = tasks or []

    def compose(self) -> ComposeResult:
        """Create child widgets for the task list."""
        if not self.tasks:
            yield Label("[No arbitrated tasks found]", classes="placeholder")
            return

        for i, task in enumerate(self.tasks):
            task_classes = ["task-item", "arbitration-task-item"]
            if task.id == self.selected_task_id:
                task_classes.append("selected")
            if task.status == "pending":
                task_classes.append("pending")
            elif task.status == "decided":
                task_classes.append("decided")
            elif task.status == "blocked":
                task_classes.append("blocked")

            winner_text = f" - Winner: {task.winner}" if task.winner else ""
            yield Label(
                f"{task.id[:8]}... | {task.phase.upper():>8} | {task.status.upper():>8}{winner_text}",
                id=f"task-{task.id}",
                classes=" ".join(task_classes)
            )

    def update_tasks(self, tasks):
        """Update the task list."""
        self.tasks = tasks
        self.refresh()

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a task to select it."""
        # Extract task ID from the label's ID
        if event.label.id and event.label.id.startswith("task-"):
            task_id = event.label.id[5:]  # Remove "task-" prefix
            self.selected_task_id = task_id
            # Notify parent screen about task selection
            self.post_message(TaskSelected(task_id))


class CandidateList(Widget):
    """Widget to display candidates for a selected task."""

    # Reactive attribute to track selected candidate
    selected_candidate_engine = reactive(None)

    def __init__(self, candidates=None, **kwargs):
        super().__init__(**kwargs)
        self.candidates = candidates or []

    def compose(self) -> ComposeResult:
        """Create child widgets for the candidate list."""
        if not self.candidates:
            yield Label("[No candidates for this task]", classes="placeholder")
            return

        for i, candidate in enumerate(self.candidates):
            candidate_classes = ["candidate-item"]
            if candidate.engine == self.selected_candidate_engine:
                candidate_classes.append("selected")

            score_text = f"{candidate.score:.2f}" if candidate.score is not None else "N/A"
            equiv_text = candidate.semantic_equivalence or "N/A"
            validation_text = "PASS" if candidate.validation_passed else "FAIL"
            flags_text = ", ".join(candidate.flags) if candidate.flags else "None"

            yield Label(
                f"{candidate.engine:>10} | {score_text:>6} | {equiv_text:>8} | {validation_text:>4} | {flags_text}",
                id=f"candidate-{candidate.engine}",
                classes=" ".join(candidate_classes)
            )

    def update_candidates(self, candidates):
        """Update the candidate list."""
        self.candidates = candidates
        self.refresh()

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a candidate to select it."""
        # Extract candidate engine from the label's ID
        if event.label.id and event.label.id.startswith("candidate-"):
            engine = event.label.id[10:]  # Remove "candidate-" prefix
            self.selected_candidate_engine = engine
            # Notify parent screen about candidate selection
            self.post_message(CandidateSelected(engine))


class SideBySideViewer(Widget):
    """Widget to display candidate details in a side-by-side format."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.candidate = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the candidate details viewer."""
        if not self.candidate:
            yield Label("[No candidate selected]", classes="placeholder")
            return

        # Structured summary section
        with Vertical(classes="candidate-details"):
            yield Label(f"[b]Engine:[/b] {self.candidate.engine}", classes="detail-field")
            yield Label(f"[b]Score:[/b] {self.candidate.score:.2f}" if self.candidate.score is not None else f"[b]Score:[/b] N/A", classes="detail-field")
            yield Label(f"[b]Semantic Equivalence:[/b] {self.candidate.semantic_equivalence or 'N/A'}", classes="detail-field")
            yield Label(f"[b]Validation Status:[/b] {'PASS' if self.candidate.validation_passed else 'FAIL'}", classes="detail-field")
            
            # Files written
            if self.candidate.files_written:
                yield Label("[b]Files Written:[/b]", classes="artifacts-title")
                for file_path in self.candidate.files_written:
                    yield Label(f"  • {file_path}", classes="artifact-item")
            
            # Policy used
            if self.candidate.policy_used:
                yield Label("[b]Policy Used:[/b]", classes="policy-title")
                yield Label(f"  {self.candidate.policy_used}", classes="policy-item")
            
            # Validation output (if any)
            if self.candidate.validation_output:
                yield Label("[b]Validation Output:[/b]", classes="validation-title")
                log_widget = RichLog(
                    max_lines=50,
                    markup=True,
                    wrap=True,
                    highlight=True,
                    id="validation-output"
                )
                log_widget.write(self.candidate.validation_output)
                yield log_widget

    def update_candidate(self, candidate):
        """Update the displayed candidate details."""
        self.candidate = candidate
        self.refresh()


class DecisionPanel(Widget):
    """Widget to display decision information and controls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.arbitration_data = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the decision panel."""
        if not self.arbitration_data:
            yield Label("[No arbitration data selected]", classes="placeholder")
            return

        with Vertical(classes="decision-panel-content"):
            # Current winner information
            if self.arbitration_data.current_winner:
                yield Label(f"[b]Current Winner:[/b] {self.arbitration_data.current_winner}", classes="current-winner")
            else:
                yield Label("[b]Current Winner:[/b] None", classes="no-winner")

            # Judge engine output (if used)
            if self.arbitration_data.judge_output:
                yield Label("[b]Judge Engine Output:[/b]", classes="judge-title")
                yield Label(self.arbitration_data.judge_output, classes="judge-output")

            # Decision rationale
            if self.arbitration_data.decision_rationale:
                yield Label("[b]Decision Rationale:[/b]", classes="rationale-title")
                yield Label(self.arbitration_data.decision_rationale, classes="rationale-text")

            # Confidence indicators
            if self.arbitration_data.confidence:
                yield Label("[b]Confidence Indicators:[/b]", classes="confidence-title")
                for indicator in self.arbitration_data.confidence:
                    yield Label(f"  • {indicator}", classes="confidence-item")

            # Action buttons would go here (handled by parent screen)

    def update_arbitration_data(self, arbitration_data):
        """Update the displayed arbitration data."""
        self.arbitration_data = arbitration_data
        self.refresh()


class ArbitrationScreen(Screen):
    """Arbitration Arena screen for comparing competing AI outputs."""

    BINDINGS = [
        ("w", "choose_winner", "Choose Winner"),
        ("x", "reject_candidate", "Reject Candidate"),
        ("r", "re_run_arbitration", "Re-run Arbitration"),
        ("e", "explain_decision", "Explain Decision"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the arbitration screen."""
        yield Header()

        # Main content with four regions
        with Horizontal(id="main-content"):
            # Left: Task List
            with Vertical(classes="task-list-container"):
                yield Label("[b]Arbitrated Tasks[/b]", classes="section-title")
                yield TaskList(id="task-list")

            # Center-Left: Candidate List
            with Vertical(classes="candidate-list-container"):
                yield Label("[b]Candidates[/b]", classes="section-title")
                yield CandidateList(id="candidate-list")

            # Center-Right: Side-by-Side Viewer
            with Vertical(classes="details-viewer-container"):
                yield Label("[b]Candidate Details[/b]", classes="section-title")
                yield SideBySideViewer(id="side-by-side-viewer")

            # Right: Decision Panel
            with Vertical(classes="decision-panel-container"):
                yield Label("[b]Decision Panel[/b]", classes="section-title")
                yield DecisionPanel(id="decision-panel")

        # Status message area
        yield Label("Ready - Select a task to begin arbitration review", id="status-message", classes="status-message")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load initial task list
        self.refresh_task_list()

        # Set up periodic refresh to update task statuses
        self.set_interval(2.0, self.refresh_task_list)

    def refresh_task_list(self) -> None:
        """Refresh the task list from the backend."""
        try:
            session = get_active_session()
            if session:
                tasks = list_arbitrated_tasks(session.id)
                # Use call_later to ensure UI is ready before updating
                self.call_later(lambda: self._update_task_list(tasks))
            else:
                # No active session
                self.call_later(lambda: self._update_task_list([]))
        except Exception as e:
            # If we can't load tasks, show empty list
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

    def on_task_selected(self, message: TaskSelected) -> None:
        """Handle when a task is selected to show its candidates."""
        task_id = message.task_id
        try:
            candidates = list_candidates(task_id)
            candidate_list = self.query_one("#candidate-list", CandidateList)
            candidate_list.update_candidates(candidates)
            
            # Clear previous candidate details
            viewer = self.query_one("#side-by-side-viewer", SideBySideViewer)
            viewer.update_candidate(None)
            
            # Update decision panel
            arbitration_data = get_arbitration(task_id)
            decision_panel = self.query_one("#decision-panel", DecisionPanel)
            decision_panel.update_arbitration_data(arbitration_data)
            
        except Exception:
            # Handle error if needed
            pass

    def on_candidate_selected(self, message: CandidateSelected) -> None:
        """Handle when a candidate is selected to show its details."""
        engine = message.engine
        # Get the currently selected task to pair with this candidate
        task_list = self.query_one("#task-list", TaskList)
        task_id = task_list.selected_task_id
        
        if task_id and engine:
            try:
                candidate = get_candidate(task_id, engine)
                viewer = self.query_one("#side-by-side-viewer", SideBySideViewer)
                viewer.update_candidate(candidate)
            except Exception:
                # Handle error if needed
                pass

    def action_choose_winner(self) -> None:
        """Choose the currently selected candidate as the winner."""
        # Get the current selections
        task_list = self.query_one("#task-list", TaskList)
        candidate_list = self.query_one("#candidate-list", CandidateList)
        
        task_id = task_list.selected_task_id
        engine = candidate_list.selected_candidate_engine
        
        if not task_id:
            self.notify("Please select a task first", severity="warning", timeout=3)
            return
            
        if not engine:
            self.notify("Please select a candidate first", severity="warning", timeout=3)
            return
        
        # Confirm the selection before proceeding
        def on_confirmed(confirmed: bool):
            if confirmed:
                def get_reason():
                    # Get reason for selection
                    reason = self.app.query_one("#reason-input").value if self.app.query_one("#reason-input", expect_type=None) else "Manual selection by human reviewer"
                    try:
                        choose_winner(task_id, engine, reason)
                        self.notify(f"Winner selected: {engine} for task {task_id[:8]}...", severity="success", timeout=3)
                        self.refresh_task_list()  # Refresh to show updated status
                    except Exception as e:
                        self.notify(f"Error selecting winner: {str(e)}", severity="error", timeout=5)
                
                # In a real implementation, we'd show a reason input dialog
                # For now, we'll use a default reason
                get_reason()
            else:
                self.notify("Winner selection cancelled", timeout=3)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Select {engine} as the winner for task {task_id[:8]}...?\n\nThis will mark the task as decided.",
            title="Confirm Winner Selection"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)

    def action_reject_candidate(self) -> None:
        """Reject the currently selected candidate."""
        # Get the current selections
        task_list = self.query_one("#task-list", TaskList)
        candidate_list = self.query_one("#candidate-list", CandidateList)
        
        task_id = task_list.selected_task_id
        engine = candidate_list.selected_candidate_engine
        
        if not task_id:
            self.notify("Please select a task first", severity="warning", timeout=3)
            return
            
        if not engine:
            self.notify("Please select a candidate first", severity="warning", timeout=3)
            return
        
        # Show input dialog for rejection reason
        def on_rejection_info_entered(rejection_info: str):
            if rejection_info:
                parts = rejection_info.strip().split('\n', 1)
                if len(parts) < 2:
                    reason = rejection_info.strip()
                else:
                    # First line should be the engine (should match selection), second is the reason
                    provided_engine = parts[0].strip()
                    reason = parts[1].strip()
                    
                    if provided_engine.lower() != engine.lower():
                        self.notify(f"Engine {provided_engine} doesn't match selection {engine}", severity="error", timeout=3)
                        return

                if not reason:
                    self.notify("Reason is required for rejection", severity="error", timeout=3)
                    return

                # Confirm rejection before proceeding
                def on_confirmed(confirmed: bool):
                    if confirmed:
                        try:
                            reject_candidate(task_id, engine, reason)
                            self.notify(f"Candidate {engine} rejected for task {task_id[:8]}...", timeout=3)
                            # Refresh candidate list to reflect changes
                            candidates = list_candidates(task_id)
                            candidate_list.update_candidates(candidates)
                        except Exception as e:
                            self.notify(f"Error rejecting candidate: {str(e)}", severity="error", timeout=5)
                    else:
                        self.notify("Rejection cancelled", timeout=3)

                from maestro.tui.widgets.modals import ConfirmDialog
                confirm_dialog = ConfirmDialog(
                    message=f"Reject candidate {engine} for task {task_id[:8]}...?\n\nReason: {reason}",
                    title="Confirm Candidate Rejection"
                )
                self.app.push_screen(confirm_dialog, callback=on_confirmed)
            else:
                self.notify("Rejection cancelled", timeout=3)

        from maestro.tui.widgets.modals import InputDialog
        input_dialog = InputDialog(
            message=f"Enter reason to reject {engine} for task {task_id[:8]}...:\n(separate with newline if needed)",
            title="Reject Candidate"
        )
        self.app.push_screen(input_dialog, callback=on_rejection_info_entered)

    def action_re_run_arbitration(self) -> None:
        """Re-run arbitration for the selected task."""
        task_list = self.query_one("#task-list", TaskList)
        task_id = task_list.selected_task_id
        
        if not task_id:
            self.notify("Please select a task first", severity="warning", timeout=3)
            return
        
        # Check if re-running is allowed by policy (would be checked in backend)
        # For now, just confirm and notify
        def on_confirmed(confirmed: bool):
            if confirmed:
                self.notify(f"Re-running arbitration for task {task_id[:8]}...", severity="warning", timeout=3)
                # In a real implementation, this would trigger a re-run
                # For now, we'll just show a notification
            else:
                self.notify("Re-run cancelled", timeout=3)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Re-run arbitration for task {task_id[:8]}...?\n\nThis may take some time.",
            title="Confirm Re-run Arbitration"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)

    def action_explain_decision(self) -> None:
        """Show the full decision trail for the selected task."""
        task_list = self.query_one("#task-list", TaskList)
        task_id = task_list.selected_task_id
        
        if not task_id:
            self.notify("Please select a task first", severity="warning", timeout=3)
            return
        
        try:
            arbitration_data = get_arbitration(task_id)
            explanation = f"""
            Arbitration Details for Task: {task_id}
            
            Task Phase: {arbitration_data.phase or 'N/A'}
            Status: {arbitration_data.status or 'N/A'}
            Current Winner: {arbitration_data.current_winner or 'None'}
            
            Decision Rationale: {arbitration_data.decision_rationale or 'No rationale provided'}
            
            Judge Output: {arbitration_data.judge_output or 'No judge output'}
            
            Confidence Indicators: {', '.join(arbitration_data.confidence) if arbitration_data.confidence else 'None'}
            
            Candidates:
            """
            for candidate in arbitration_data.candidates:
                explanation += f"\n  - Engine: {candidate.engine}"
                explanation += f"\n    Score: {candidate.score:.2f}" if candidate.score is not None else "\n    Score: N/A"
                explanation += f"\n    Semantic Equivalence: {candidate.semantic_equivalence or 'N/A'}"
                explanation += f"\n    Validation Passed: {'Yes' if candidate.validation_passed else 'No'}"
                explanation += f"\n    Flags: {', '.join(candidate.flags) if candidate.flags else 'None'}"
            
            from maestro.tui.widgets.modals import InfoDialog
            info_dialog = InfoDialog(
                message=explanation,
                title=f"Arbitration Decision Trail - {task_id[:8]}..."
            )
            self.app.push_screen(info_dialog)
        except Exception as e:
            self.notify(f"Error showing decision explanation: {str(e)}", severity="error", timeout=5)


class TaskSelected(Message):
    """Message sent when a task is selected in the task list."""

    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id


class CandidateSelected(Message):
    """Message sent when a candidate is selected in the candidate list."""

    def __init__(self, engine: str) -> None:
        super().__init__()
        self.engine = engine