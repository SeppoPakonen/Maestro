"""
Semantic Integrity Panel for Maestro TUI
This screen displays semantic risks and allows human judgment on findings.
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, Static, DataTable, ListView, ListItem
from textual.containers import Horizontal, Vertical, ScrollableContainer
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class SemanticFinding:
    """Represents a semantic finding from code conversion analysis."""
    id: str
    task_id: str
    files: List[str]
    equivalence_level: str  # high, medium, low, unknown
    risk_flags: List[str]  # [icon or tag names]
    status: str  # pending, accepted, rejected, blocking
    description: str
    evidence_before: str
    evidence_after: str
    decision_reason: Optional[str] = None
    checkpoint_id: Optional[str] = None
    blocks_pipeline: bool = False


@dataclass
class SemanticSummary:
    """Summary of semantic risks across all findings."""
    total_findings: int
    high_risk: int
    medium_risk: int
    low_risk: int
    accepted: int
    rejected: int
    blocking: int
    overall_health_score: float  # 0.0 to 1.0


class RiskSummaryPanel(Vertical):
    """Left region: Shows overall risk summary and health."""
    
    def __init__(self, summary: SemanticSummary = None):
        super().__init__()
        self.summary = summary or SemanticSummary(
            total_findings=0,
            high_risk=0,
            medium_risk=0, 
            low_risk=0,
            accepted=0,
            rejected=0,
            blocking=0,
            overall_health_score=0.0
        )

    def compose(self) -> ComposeResult:
        """Create child widgets for the risk summary panel."""
        # Overall health score
        health_color = "green" if self.summary.overall_health_score >= 0.8 else "yellow" if self.summary.overall_health_score >= 0.5 else "red"
        yield Label(f"[b]Semantic Health Score:[/b] [{health_color}]{self.summary.overall_health_score*100:.1f}%[/]", classes="summary-item")

        yield Label("\n[b]Risk Counts:[/b]", classes="section-title")
        
        # High risk
        yield Label(f"[red]🔴 High Risk: {self.summary.high_risk}[/]", classes="risk-high")
        
        # Medium risk  
        yield Label(f"[yellow]🟡 Medium Risk: {self.summary.medium_risk}[/]", classes="risk-medium")
        
        # Low risk
        yield Label(f"[blue]🔵 Low Risk: {self.summary.low_risk}[/]", classes="risk-low")
        
        # Status counts
        yield Label(f"[green]✅ Accepted: {self.summary.accepted}[/]", classes="status-accepted")
        yield Label(f"[red]❌ Rejected: {self.summary.rejected}[/]", classes="status-rejected")
        yield Label(f"[orange]🚧 Blocking: {self.summary.blocking}[/]", classes="status-blocking")
        
        # Total findings
        yield Label(f"[b]Total Findings: {self.summary.total_findings}[/]", classes="total-findings")
        
        # Active gates/checkpoints (if any)
        if self.summary.blocking > 0:
            yield Label("\n[b]Active Gates/Checkpoints:[/b]", classes="checkpoints-title")
            yield Label(f"[orange]⚠ {self.summary.blocking} findings require human review[/]", classes="active-gates")


class FindingsListPanel(Vertical):
    """Center region: Shows list of semantic findings."""
    
    def __init__(self, findings: List[SemanticFinding] = None):
        super().__init__()
        self.findings = findings or []
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the findings list panel."""
        if self.findings:
            yield Label("[b]Semantic Findings List[/b]", classes="list-title")
            
            for i, finding in enumerate(self.findings):
                # Determine color and icon based on equivalence level and status
                equiv_colors = {
                    "high": "green",
                    "medium": "yellow", 
                    "low": "red",
                    "unknown": "dim"
                }
                
                status_icons = {
                    "pending": "⏳",
                    "accepted": "✅",
                    "rejected": "❌", 
                    "blocking": "⚠️"
                }
                
                equiv_color = equiv_colors.get(finding.equivalence_level, "dim")
                status_icon = status_icons.get(finding.status, "❓")
                
                # Format files for display (show first few if many)
                files_text = ", ".join(finding.files[:2])
                if len(finding.files) > 2:
                    files_text += f" (+{len(finding.files)-2} more)"
                
                # Risk flags as tags
                risk_tags = " ".join([f"[{flag}]" for flag in finding.risk_flags]) if finding.risk_flags else ""
                
                # Highlight selected item
                css_class = "selected" if i == 0 else ""
                
                item_content = f"{status_icon} [{equiv_color}]{finding.id}[/] | {finding.task_id} | {files_text} | {finding.equivalence_level} | {risk_tags} | {finding.status}"
                
                yield Label(
                    item_content,
                    id=f"finding-{i}",
                    classes=f"finding-item {css_class}",
                    tooltip=finding.description
                )
        else:
            yield Label("No semantic findings detected", classes="placeholder")


class FindingDetailsPanel(Vertical):
    """Right region: Shows details for selected finding."""
    
    def __init__(self, finding: SemanticFinding = None):
        super().__init__()
        self.finding = finding

    def compose(self) -> ComposeResult:
        """Create child widgets for the finding details panel."""
        if self.finding:
            # Finding ID and status
            status_text = f"[{self.finding.status}]"
            status_colors = {
                "pending": "yellow",
                "accepted": "green", 
                "rejected": "red",
                "blocking": "orange"
            }
            status_color = status_colors.get(self.finding.status, "dim")
            
            yield Label(f"[b]Finding ID:[/b] {self.finding.id}", classes="finding-id")
            yield Label(f"[b]Status:[/b] [{status_color}]{status_text}[/]", classes="finding-status")
            
            # Task ID
            yield Label(f"[b]Task ID:[/b] {self.finding.task_id}", classes="task-id")
            
            # Files
            yield Label("\n[b]Affected Files:[/b]", classes="files-title")
            for file in self.finding.files:
                yield Label(f"• {file}", classes="file-item")
            
            # Equivalence level
            equiv_colors = {
                "high": "green",
                "medium": "yellow", 
                "low": "red",
                "unknown": "dim"
            }
            equiv_color = equiv_colors.get(self.finding.equivalence_level, "dim")
            yield Label(f"\n[b]Equivalence Level:[/b] [{equiv_color}]{self.finding.equivalence_level.title()}[/]", classes="equivalence-level")
            
            # Risk flags
            if self.finding.risk_flags:
                yield Label("\n[b]Risk Flags:[/b]", classes="risk-flags-title")
                for flag in self.finding.risk_flags:
                    yield Label(f"• {flag}", classes="risk-flag")
            
            # Detailed explanation
            yield Label("\n[b]Explanation:[/b]", classes="explanation-title")
            yield Static(self.finding.description, classes="explanation-text", shrink=False)
            
            # Evidence
            yield Label("\n[b]Evidence:[/b]", classes="evidence-title")
            yield Label("[i]Before conversion:[/i]", classes="evidence-before-title")
            yield Static(self.finding.evidence_before[:200] + ("..." if len(self.finding.evidence_before) > 200 else ""), classes="evidence-before", shrink=False)
            
            yield Label("\n[i]After conversion:[/i]", classes="evidence-after-title")
            yield Static(self.finding.evidence_after[:200] + ("..." if len(self.finding.evidence_after) > 200 else ""), classes="evidence-after", shrink=False)
            
            # Current disposition
            if self.finding.decision_reason:
                yield Label("\n[b]Decision Reason:[/b]", classes="decision-title")
                yield Static(self.finding.decision_reason, classes="decision-reason", shrink=False)
            
            # Impact section
            yield Label("\n[b]Impact:[/b]", classes="impact-title")
            blocks_text = "Yes" if self.finding.blocks_pipeline else "No"
            blocks_color = "red" if self.finding.blocks_pipeline else "green"
            yield Label(f"[b]Blocks Pipeline:[/b] [{blocks_color}]{blocks_text}[/]", classes="blocks-pipeline")
            
            if self.finding.checkpoint_id:
                yield Label(f"[b]Checkpoint ID:[/b] {self.finding.checkpoint_id}", classes="checkpoint-id")
        else:
            yield Label("Select a finding to view details", classes="placeholder")


class SemanticScreen(Screen):
    """Semantic Integrity Panel screen for reviewing semantic risks."""

    BINDINGS = [
        ("a", "accept_finding", "Accept"),
        ("r", "reject_finding", "Reject"),
        ("d", "defer_finding", "Defer"),
        ("e", "explain_finding", "Explain"),
        ("escape", "app.pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("up", "move_selection_up", "Up"),
        ("down", "move_selection_down", "Down"),
    ]

    def __init__(self, pipeline_id: str = None):
        super().__init__()
        self.pipeline_id = pipeline_id
        self.findings = []  # Will be populated on mount
        self.selected_finding_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the semantic screen."""
        yield Header(show_clock=True)
        
        # Main layout with three panels
        with Horizontal(id="semantic-dashboard"):
            # Left: Risk Summary
            with Vertical(id="risk-summary-container", classes="panel"):
                yield RiskSummaryPanel()
            
            # Center: Findings List
            with Vertical(id="findings-list-container", classes="panel"):
                yield FindingsListPanel()
            
            # Right: Finding Details
            with Vertical(id="finding-details-container", classes="panel"):
                yield FindingDetailsPanel()

        # Action buttons
        with Horizontal(id="action-buttons"):
            yield Button("Accept (A)", id="accept-btn", variant="success")
            yield Button("Reject (R)", id="reject-btn", variant="error")
            yield Button("Defer (D)", id="defer-btn", variant="warning") 
            yield Button("Explain (E)", id="explain-btn", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load semantic findings from facade
        self.load_semantic_data()

    def load_semantic_data(self) -> None:
        """Load semantic findings and summary from the facade."""
        try:
            from maestro.ui_facade.semantic import list_semantic_findings, get_semantic_summary
            # If we have a pipeline ID, pass it; otherwise, let the facade use default
            if self.pipeline_id:
                self.findings = list_semantic_findings(pipeline_id=self.pipeline_id)
                summary = get_semantic_summary(pipeline_id=self.pipeline_id)
            else:
                self.findings = list_semantic_findings()
                summary = get_semantic_summary()

            # Update all panels with new data
            self.update_risk_summary(summary)
            self.update_findings_list(self.findings)
            self.update_finding_details(self.findings[0] if self.findings else None)

        except ImportError:
            # For now, use placeholder data if facade doesn't exist yet
            self.load_placeholder_data()

    def load_placeholder_data(self) -> None:
        """Load placeholder data for development."""
        from random import choice, randint
        
        risk_levels = ["high", "medium", "low", "unknown"]
        statuses = ["pending", "accepted", "rejected", "blocking"]
        risk_flags = ["logic-change", "performance", "interface", "dependency", "api"]
        
        # Create mock findings
        self.findings = []
        for i in range(8):
            finding_id = f"sem_{i:03d}"
            task_id = f"task_{i:02d}"
            num_files = randint(1, 3)
            files = [f"src/file_{j}.cpp" for j in range(num_files)]
            equiv_level = choice(risk_levels)
            num_flags = randint(0, 2)
            flags = [choice(risk_flags) for _ in range(num_flags)]
            status = choice(statuses)
            
            finding = SemanticFinding(
                id=finding_id,
                task_id=task_id,
                files=files,
                equivalence_level=equiv_level,
                risk_flags=flags,
                status=status,
                description=f"This semantic finding identifies a potential issue where the conversion might have altered the original logic. Specifically, the conversion from U++ Vector to Python list may not maintain the same performance characteristics.",
                evidence_before="Upp::Vector<int> v; v.Add(42); int val = v[0];",
                evidence_after="v = []\nv.append(42)\nval = v[0]",
                decision_reason="Reviewed and accepted - performance impact is acceptable for this use case" if status == "accepted" else None,
                checkpoint_id=f"chk_{finding_id}" if status == "blocking" else None,
                blocks_pipeline=(status == "blocking")
            )
            self.findings.append(finding)
        
        # Create mock summary
        summary = SemanticSummary(
            total_findings=len(self.findings),
            high_risk=len([f for f in self.findings if f.equivalence_level == "high"]),
            medium_risk=len([f for f in self.findings if f.equivalence_level == "medium"]),
            low_risk=len([f for f in self.findings if f.equivalence_level == "low"]),
            accepted=len([f for f in self.findings if f.status == "accepted"]),
            rejected=len([f for f in self.findings if f.status == "rejected"]),
            blocking=len([f for f in self.findings if f.status == "blocking"]),
            overall_health_score=0.7
        )
        
        # Update all panels with mock data
        self.update_risk_summary(summary)
        self.update_findings_list(self.findings)
        self.update_finding_details(self.findings[0] if self.findings else None)

    def update_risk_summary(self, summary: SemanticSummary) -> None:
        """Update the risk summary panel."""
        summary_container = self.query_one("#risk-summary-container", expect_type=Vertical)
        summary_container.remove_children()
        risk_panel = RiskSummaryPanel(summary)
        risk_panel.mount_all(list(risk_panel.compose()))

    def update_findings_list(self, findings: List[SemanticFinding]) -> None:
        """Update the findings list panel."""
        list_container = self.query_one("#findings-list-container", expect_type=Vertical)
        list_container.remove_children()
        findings_panel = FindingsListPanel(findings)
        findings_panel.mount_all(list(findings_panel.compose()))

        # Set up click handlers for findings
        for i in range(len(findings)):
            try:
                label = self.query_one(f"#finding-{i}", expect_type=Label)
                label.can_focus = True
                label.styles.cursor = "pointer"
            except:
                continue  # Skip if label doesn't exist

    def update_finding_details(self, finding: SemanticFinding) -> None:
        """Update the finding details panel."""
        details_container = self.query_one("#finding-details-container", expect_type=Vertical)
        details_container.remove_children()
        details_panel = FindingDetailsPanel(finding)
        details_panel.mount_all(list(details_panel.compose()))

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a finding in the list."""
        if event.label.id and event.label.id.startswith("finding-"):
            try:
                index = int(event.label.id.split("-")[1])
                self.selected_finding_index = index
                
                # Update selection display
                for i in range(len(self.findings)):
                    try:
                        label = self.query_one(f"#finding-{i}", expect_type=Label)
                        if i == index:
                            label.add_class("selected")
                        else:
                            label.remove_class("selected")
                    except:
                        continue  # Skip if label doesn't exist
                
                # Update the details panel
                if index < len(self.findings):
                    selected_finding = self.findings[index]
                    self.update_finding_details(selected_finding)
                
            except ValueError:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "accept-btn":
            self.action_accept_finding()
        elif button_id == "reject-btn":
            self.action_reject_finding()
        elif button_id == "defer-btn":
            self.action_defer_finding()
        elif button_id == "explain-btn":
            self.action_explain_finding()

    def action_accept_finding(self) -> None:
        """Action to accept the selected finding."""
        if not self.findings or self.selected_finding_index >= len(self.findings):
            self.app.notify("No finding selected", timeout=2)
            return

        finding = self.findings[self.selected_finding_index]

        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    from maestro.ui_facade.semantic import accept_semantic_finding
                    accept_semantic_finding(finding.id)
                    self.app.notify(f"Finding {finding.id} accepted", timeout=3)

                    # Reload data to reflect the change
                    self.load_semantic_data()

                    # If the finding was blocking a pipeline stage, refresh the conversion dashboard
                    if finding.blocks_pipeline or finding.status == "blocking":
                        # Emit an event to notify other parts of the app about the change
                        self.app.post_message("semantic_finding_updated")

                except ImportError:
                    # For now, simulate the action with placeholder
                    self.app.notify(f"Finding {finding.id} accepted (simulated)", timeout=3)
                    finding.status = "accepted"
                    self.load_semantic_data()

                    # Emit an event to notify other parts of the app about the change
                    self.app.post_message("semantic_finding_updated")

                except Exception as e:
                    self.app.notify(f"Error accepting finding: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Accept cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Accept semantic finding {finding.id}?\n\nThis will mark the finding as reviewed and accepted.",
            title="Confirm Accept Finding"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_reject_finding(self) -> None:
        """Action to reject the selected finding."""
        if not self.findings or self.selected_finding_index >= len(self.findings):
            self.app.notify("No finding selected", timeout=2)
            return

        finding = self.findings[self.selected_finding_index]

        def on_reason_entered(reason: str):
            if reason:
                try:
                    from maestro.ui_facade.semantic import reject_semantic_finding
                    reject_semantic_finding(finding.id, reason)
                    self.app.notify(f"Finding {finding.id} rejected", timeout=3)

                    # Reload data to reflect the change
                    self.load_semantic_data()

                    # If the finding was blocking a pipeline stage, refresh the conversion dashboard
                    if finding.blocks_pipeline or finding.status == "blocking":
                        # Emit an event to notify other parts of the app about the change
                        self.app.post_message("semantic_finding_updated")

                except ImportError:
                    # For now, simulate the action with placeholder
                    self.app.notify(f"Finding {finding.id} rejected (simulated)", timeout=3)
                    finding.status = "rejected"
                    self.load_semantic_data()

                    # Emit an event to notify other parts of the app about the change
                    self.app.post_message("semantic_finding_updated")

                except Exception as e:
                    self.app.notify(f"Error rejecting finding: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Reject cancelled - reason required", timeout=2)

        from maestro.tui.widgets.modals import InputDialog
        input_dialog = InputDialog(
            message=f"Enter reason for rejecting finding {finding.id}:",
            title="Reject Finding"
        )
        self.app.push_screen(input_dialog, callback=on_reason_entered)

    def action_defer_finding(self) -> None:
        """Action to defer the selected finding."""
        if not self.findings or self.selected_finding_index >= len(self.findings):
            self.app.notify("No finding selected", timeout=2)
            return

        finding = self.findings[self.selected_finding_index]

        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    from maestro.ui_facade.semantic import defer_semantic_finding
                    defer_semantic_finding(finding.id)
                    self.app.notify(f"Finding {finding.id} deferred", timeout=3)

                    # Reload data to reflect the change
                    self.load_semantic_data()

                    # If the finding was blocking a pipeline stage, refresh the conversion dashboard
                    if finding.blocks_pipeline or finding.status == "blocking":
                        # Emit an event to notify other parts of the app about the change
                        self.app.post_message("semantic_finding_updated")

                except ImportError:
                    # For now, simulate the action with placeholder
                    self.app.notify(f"Finding {finding.id} deferred (simulated)", timeout=3)
                    self.load_semantic_data()

                    # Emit an event to notify other parts of the app about the change
                    self.app.post_message("semantic_finding_updated")

                except Exception as e:
                    self.app.notify(f"Error deferring finding: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Defer cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Defer semantic finding {finding.id}?\n\nThis will leave the finding unresolved.",
            title="Confirm Defer Finding"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_explain_finding(self) -> None:
        """Action to show detailed explanation of the selected finding."""
        if not self.findings or self.selected_finding_index >= len(self.findings):
            self.app.notify("No finding selected", timeout=2)
            return
            
        finding = self.findings[self.selected_finding_index]
        
        # Show detailed explanation in a modal or new screen
        explanation = f"""
        Rationale History for Finding {finding.id}

        Status: {finding.status}
        Task ID: {finding.task_id}
        Affected Files: {', '.join(finding.files)}
        Equivalence Level: {finding.equivalence_level}
        Risk Flags: {', '.join(finding.risk_flags) if finding.risk_flags else 'None'}

        Description:
        {finding.description}

        Evidence (Before):
        {finding.evidence_before}

        Evidence (After):
        {finding.evidence_after}

        Decision Reason (if any):
        {finding.decision_reason or 'No decision made yet'}

        Impact:
        - Blocks pipeline: {'Yes' if finding.blocks_pipeline else 'No'}
        - Checkpoint ID: {finding.checkpoint_id or 'None'}
        """
        
        from maestro.tui.widgets.modals import InfoDialog
        info_dialog = InfoDialog(
            message=explanation,
            title=f"Rationale History - {finding.id}"
        )
        self.app.push_screen(info_dialog)

    def action_move_selection_up(self) -> None:
        """Move selection up in the findings list."""
        if self.selected_finding_index > 0:
            self.selected_finding_index -= 1
            self.update_selection_display()

    def action_move_selection_down(self) -> None:
        """Move selection down in the findings list."""
        if self.selected_finding_index < len(self.findings) - 1:
            self.selected_finding_index += 1
            self.update_selection_display()

    def update_selection_display(self) -> None:
        """Update the visual selection in the findings list."""
        # Update selection display
        for i in range(len(self.findings)):
            try:
                label = self.query_one(f"#finding-{i}", expect_type=Label)
                if i == self.selected_finding_index:
                    label.add_class("selected")
                else:
                    label.remove_class("selected")
            except:
                continue  # Skip if label doesn't exist
        
        # Update the details panel
        if self.selected_finding_index < len(self.findings):
            selected_finding = self.findings[self.selected_finding_index]
            self.update_finding_details(selected_finding)