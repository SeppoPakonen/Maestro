"""
Cross-Repo Semantic Diff Explorer for Maestro TUI
This screen allows humans to see what survived, what changed, and what was lost when comparing:
- source repo ↔ target repo
- current run ↔ baseline
- run ↔ run
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, Static, DataTable, ListView, ListItem, Select
from textual.containers import Horizontal, Vertical, ScrollableContainer
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SemanticDiffConcept:
    """Represents a concept from the glossary in a semantic diff."""
    id: str
    name: str
    source_file: str  # Source file path
    target_file: str  # Target file path (after conversion)
    status: str  # preserved, changed, degraded, lost
    equivalence_level: str  # high, medium, low, unknown
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    description: str
    evidence_links: List[str]  # Links to task summaries, diffs, snapshots


@dataclass
class SemanticDiffMapping:
    """Represents a file-to-file mapping in semantic diff."""
    id: str
    source_path: str
    target_path: str
    status: str  # preserved, changed, degraded, lost
    concepts: List[SemanticDiffConcept]
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    equivalence_level: str  # high, medium, low, unknown
    heuristics_used: List[str]  # identifier loss, api shrinkage, etc.


@dataclass
class SemanticDiffSummary:
    """Summary of semantic diff analysis."""
    total_concepts: int
    preserved_concepts: int
    changed_concepts: int
    degraded_concepts: int
    lost_concepts: int
    total_files: int
    preserved_files: int
    changed_files: int
    lost_files: int
    aggregated_risk_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    heuristics_used: List[str]
    drift_threshold_exceeded: bool
    checkpoint_required: bool


@dataclass
class CheckpointInfo:
    """Information about a checkpoint."""
    id: str
    reason: str
    threshold: float
    detected_drift: float
    created_at: str
    status: str  # pending, approved, rejected, overridden
    human_action: Optional[str] = None
    human_reason: Optional[str] = None


class ComparisonSelectorPanel(Vertical):
    """Left region: Selection of comparison mode and baseline/runs."""

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        """Create child widgets for comparison selector panel."""
        yield Label("[b]Comparison Mode[/b]", classes="section-title")
        
        # Comparison mode selector
        yield Select(
            options=[
                ("Current Run ↔ Baseline", "current_baseline"),
                ("Run ↔ Run", "run_run"),
                ("Source ↔ Target", "source_target")
            ],
            id="comparison-mode",
            value="current_baseline"
        )

        yield Label("\n[b]Available Baselines & Runs[/b]", classes="section-title")
        
        # Available baselines and runs
        yield Label("[b]Baselines:[/b]", classes="subsection-title")
        yield Label("• baseline_prod (v1.2.3)", id="baseline-prod")
        yield Label("• baseline_dev (v1.3.0)", id="baseline-dev")
        yield Label("• baseline_test (v1.1.9)", id="baseline-test")
        
        yield Label("\n[b]Runs:[/b]", classes="subsection-title")
        yield Label("• run_a1b2c3d4 (latest)", id="run-latest")
        yield Label("• run_e5f6g7h8", id="run-older")
        yield Label("• run_i9j0k1l2", id="run-oldest")
        
        yield Label("\n[b]Glossary & Concepts[/b]", classes="section-title")
        yield Label("• 42 concepts identified", id="concepts-count")
        yield Label("• 156 file mappings", id="mappings-count")


class ConceptFileMapPanel(Vertical):
    """Center-Left region: Tree/list of concepts and mapped source → target files."""
    
    def __init__(self, mappings: List[SemanticDiffMapping] = None):
        super().__init__()
        self.mappings = mappings or []
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        """Create child widgets for concept/file map panel."""
        yield Label("[b]Concepts & File Mappings[/b]", classes="section-title")
        
        if self.mappings:
            for i, mapping in enumerate(self.mappings):
                # Status icon based on mapping status
                status_icons = {
                    "preserved": "✓",
                    "changed": "~",
                    "degraded": "⚠",
                    "lost": "✗"
                }
                
                status_icon = status_icons.get(mapping.status, "?")
                status_colors = {
                    "preserved": "green",
                    "changed": "yellow", 
                    "degraded": "orange",
                    "lost": "red"
                }
                status_color = status_colors.get(mapping.status, "dim")
                
                # Create a clickable item for the mapping
                mapping_label = f"[{status_color}]{status_icon}[/] {mapping.source_path} → {mapping.target_path}"
                yield Label(
                    mapping_label,
                    id=f"mapping-{i}",
                    classes="mapping-item",
                    tooltip=f"Status: {mapping.status} | Risk: {mapping.risk_score:.2f} | Confidence: {mapping.confidence:.2f}"
                )
                
                # Show concepts within this mapping if expanded
                if i == self.selected_index:  # If this mapping is selected, show its concepts
                    for concept in mapping.concepts:
                        concept_status_icon = status_icons.get(concept.status, "?")
                        concept_status_color = status_colors.get(concept.status, "dim")
                        
                        concept_label = f"     [{concept_status_color}]{concept_status_icon}[/] {concept.name} ({concept.status})"
                        yield Label(
                            concept_label,
                            id=f"concept-{mapping.id}-{concept.id}",
                            classes="concept-item",
                            tooltip=f"Risk: {concept.risk_score:.2f} | Confidence: {concept.confidence:.2f}"
                        )
        else:
            yield Label("No semantic mappings detected", classes="placeholder")


class SemanticDiffDetailPanel(Vertical):
    """Center-Right region: Detailed semantic diff information for selected item."""
    
    def __init__(self, mapping: SemanticDiffMapping = None, concept: SemanticDiffConcept = None):
        super().__init__()
        self.mapping = mapping
        self.concept = concept
    
    def compose(self) -> ComposeResult:
        """Create child widgets for semantic diff detail panel."""
        if self.concept:
            # Show concept details
            yield Label(f"[b]Concept:[/b] {self.concept.name}", classes="detail-title")
            yield Label(f"[b]ID:[/b] {self.concept.id}", classes="detail-field")
            yield Label(f"[b]Status:[/b] {self.concept.status}", classes="detail-field")
            yield Label(f"[b]Equivalence Level:[/b] {self.concept.equivalence_level}", classes="detail-field")
            
            # Risk and confidence scores
            risk_color = "green" if self.concept.risk_score < 0.3 else "yellow" if self.concept.risk_score < 0.7 else "red"
            yield Label(f"[b]Risk Score:[/b] [{risk_color}]{self.concept.risk_score:.2f}[/]", classes="detail-field")
            yield Label(f"[b]Confidence Score:[/b] {self.concept.confidence:.2f}", classes="detail-field")
            
            # Description
            yield Label("\n[b]Description:[/b]", classes="section-title")
            yield Static(self.concept.description, classes="description-text", shrink=False)
            
            # Evidence links
            if self.concept.evidence_links:
                yield Label("\n[b]Evidence Links:[/b]", classes="section-title")
                for link in self.concept.evidence_links:
                    yield Label(f"• {link}", classes="evidence-link")
        
        elif self.mapping:
            # Show mapping details
            yield Label(f"[b]File Mapping:[/b] {self.mapping.source_path} → {self.mapping.target_path}", classes="detail-title")
            yield Label(f"[b]ID:[/b] {self.mapping.id}", classes="detail-field")
            yield Label(f"[b]Status:[/b] {self.mapping.status}", classes="detail-field")
            yield Label(f"[b]Equivalence Level:[/b] {self.mapping.equivalence_level}", classes="detail-field")
            
            # Risk and confidence scores
            risk_color = "green" if self.mapping.risk_score < 0.3 else "yellow" if self.mapping.risk_score < 0.7 else "red"
            yield Label(f"[b]Risk Score:[/b] [{risk_color}]{self.mapping.risk_score:.2f}[/]", classes="detail-field")
            yield Label(f"[b]Confidence Score:[/b] {self.mapping.confidence:.2f}", classes="detail-field")
            
            # Heuristics used
            if self.mapping.heuristics_used:
                yield Label("\n[b]Heuristics Used:[/b]", classes="section-title")
                for heuristic in self.mapping.heuristics_used:
                    yield Label(f"• {heuristic}", classes="heuristic-item")
        else:
            yield Label("Select a concept or file mapping to view details", classes="placeholder")


class RiskEscalationPanel(Vertical):
    """Right region: Risk metrics, thresholds, and human actions."""
    
    def __init__(self, summary: SemanticDiffSummary = None, checkpoint: CheckpointInfo = None):
        super().__init__()
        self.summary = summary
        self.checkpoint = checkpoint
    
    def compose(self) -> ComposeResult:
        """Create child widgets for risk & escalation panel."""
        yield Label("[b]Risk Metrics[/b]", classes="section-title")
        
        if self.summary:
            # Aggregated risk metrics
            risk_color = "green" if self.summary.aggregated_risk_score < 0.3 else "yellow" if self.summary.aggregated_risk_score < 0.7 else "red"
            yield Label(f"[b]Aggregated Risk Score:[/b] [{risk_color}]{self.summary.aggregated_risk_score:.2f}[/]", classes="risk-field")
            yield Label(f"[b]Confidence Score:[/b] {self.summary.confidence_score:.2f}", classes="risk-field")
            
            # Concept summary
            yield Label("\n[b]Concept Status:[/b]", classes="subsection-title")
            yield Label(f"[green]✓ Preserved:[/] {self.summary.preserved_concepts}", classes="risk-field")
            yield Label(f"[yellow]~ Changed:[/] {self.summary.changed_concepts}", classes="risk-field")
            yield Label(f"[orange]⚠ Degraded:[/] {self.summary.degraded_concepts}", classes="risk-field")
            yield Label(f"[red]✗ Lost:[/] {self.summary.lost_concepts}", classes="risk-field")
            
            # File summary
            yield Label("\n[b]File Status:[/b]", classes="subsection-title")
            yield Label(f"[green]✓ Preserved:[/] {self.summary.preserved_files}", classes="risk-field")
            yield Label(f"[yellow]~ Changed:[/] {self.summary.changed_files}", classes="risk-field")
            yield Label(f"[red]✗ Lost:[/] {self.summary.lost_files}", classes="risk-field")
        
        # Thresholds and checkpoint status
        yield Label("\n[b]Thresholds & Checkpoints[/b]", classes="section-title")
        
        if self.summary:
            drift_exceeded = self.summary.drift_threshold_exceeded
            exceeded_color = "red" if drift_exceeded else "green"
            drift_status = "EXCEEDED" if drift_exceeded else "OK"
            yield Label(f"[b]Drift Threshold:[/b] [{exceeded_color}]{drift_status}[/]", classes="threshold-field")
        
        if self.checkpoint:
            checkpoint_color = {
                "pending": "yellow",
                "approved": "green", 
                "rejected": "red",
                "overridden": "orange"
            }.get(self.checkpoint.status, "dim")
            
            yield Label(f"[b]Checkpoint Status:[/b] [{checkpoint_color}]{self.checkpoint.status.title()}[/]", classes="checkpoint-field")
            yield Label(f"[b]Reason:[/b] {self.checkpoint.reason}", classes="checkpoint-field")
            yield Label(f"[b]Threshold:[/b] {self.checkpoint.threshold:.2f}", classes="checkpoint-field")
            yield Label(f"[b]Detected Drift:[/b] {self.checkpoint.detected_drift:.2f}", classes="checkpoint-field")
            yield Label(f"[b]Created At:[/b] {self.checkpoint.created_at}", classes="checkpoint-field")
            
            if self.checkpoint.human_action:
                yield Label(f"\n[b]Human Action:[/b] {self.checkpoint.human_action}", classes="checkpoint-field")
                if self.checkpoint.human_reason:
                    yield Label(f"[b]Reason:[/b] {self.checkpoint.human_reason}", classes="checkpoint-field")
        
        # Human action buttons
        yield Label("\n[b]Human Actions[/b]", classes="section-title")
        yield Button("Acknowledge Loss", id="acknowledge-btn", variant="warning", classes="action-button")
        yield Button("Mark Acceptable", id="accept-btn", variant="success", classes="action-button")
        yield Button("Override (with reason)", id="override-btn", variant="error", classes="action-button")
        
        # Note about blocking conditions
        if self.summary and self.summary.checkpoint_required:
            yield Label("\n[i]⚠ This comparison is blocked until checkpoint is resolved[/i]", classes="blocking-note")


class SemanticDiffScreen(Screen):
    """Cross-Repo Semantic Diff Explorer screen for visual semantic comparison."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("up", "move_selection_up", "Up"),
        ("down", "move_selection_down", "Down"),
    ]
    
    def __init__(self):
        super().__init__()
        self.mappings = []  # Will be populated on mount
        self.selected_mapping_index = 0
        self.selected_concept = None
        self.summary = None  # Will be populated on mount
        self.checkpoint = None  # Will be populated on mount
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the semantic diff screen."""
        yield Header(show_clock=True)
        
        # Main layout with four panels
        with Horizontal(id="semantic-diff-layout"):
            # Left: Comparison Selector
            with Vertical(id="comparison-selector-container", classes="panel"):
                yield ComparisonSelectorPanel()
            
            # Center-Left: Concept & File Map
            with Vertical(id="concept-file-map-container", classes="panel"):
                yield ConceptFileMapPanel()
            
            # Center-Right: Semantic Diff Detail
            with Vertical(id="diff-detail-container", classes="panel"):
                yield SemanticDiffDetailPanel()
            
            # Right: Risk & Escalation Panel
            with Vertical(id="risk-escalation-container", classes="panel"):
                yield RiskEscalationPanel()
        
        # Action buttons
        with Horizontal(id="action-buttons"):
            yield Button("Acknowledge Loss (A)", id="acknowledge-btn", variant="warning")
            yield Button("Mark Acceptable (M)", id="accept-btn", variant="success")
            yield Button("Override (O)", id="override-btn", variant="error")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load semantic diff data from facade
        self.load_semantic_diff_data()
    
    def load_semantic_diff_data(self) -> None:
        """Load semantic diff data from the facade."""
        try:
            # Import the facade functions for semantic diff
            from maestro.ui_facade.semantic import (
                get_mapping_index,
                diff_semantics,
                get_semantic_coverage,
                get_semantic_hotspots
            )

            # Get the mapping index
            mappings_data = get_mapping_index()

            # Create SemanticDiffMapping objects from the data
            self.mappings = []
            for mapping_data in mappings_data:
                concepts = []
                for concept_data in mapping_data.get('concepts', []):
                    concept = SemanticDiffConcept(
                        id=concept_data['id'],
                        name=concept_data['name'],
                        source_file=concept_data['source_file'],
                        target_file=concept_data['target_file'],
                        status=concept_data['status'],
                        equivalence_level=concept_data['equivalence_level'],
                        risk_score=concept_data['risk_score'],
                        confidence=concept_data['confidence'],
                        description=concept_data['description'],
                        evidence_links=concept_data['evidence_links']
                    )
                    concepts.append(concept)

                mapping = SemanticDiffMapping(
                    id=mapping_data['id'],
                    source_path=mapping_data['source_path'],
                    target_path=mapping_data['target_path'],
                    status=mapping_data['status'],
                    concepts=concepts,
                    risk_score=mapping_data['risk_score'],
                    confidence=mapping_data['confidence'],
                    equivalence_level=mapping_data['equivalence_level'],
                    heuristics_used=mapping_data['heuristics_used']
                )
                self.mappings.append(mapping)

            # Get semantic diff summary
            diff_result = diff_semantics("source_target", "source_repo", "target_repo")  # Example mode
            summary_data = diff_result.get('summary', {})
            self.summary = SemanticDiffSummary(
                total_concepts=summary_data.get('total_concepts', 0),
                preserved_concepts=summary_data.get('preserved_concepts', 0),
                changed_concepts=summary_data.get('changed_concepts', 0),
                degraded_concepts=summary_data.get('degraded_concepts', 0),
                lost_concepts=summary_data.get('lost_concepts', 0),
                total_files=summary_data.get('total_files', 0),
                preserved_files=summary_data.get('preserved_files', 0),
                changed_files=summary_data.get('changed_files', 0),
                lost_files=summary_data.get('lost_files', 0),
                aggregated_risk_score=summary_data.get('aggregated_risk_score', 0.0),
                confidence_score=summary_data.get('confidence_score', 0.0),
                heuristics_used=summary_data.get('heuristics_used', []),
                drift_threshold_exceeded=summary_data.get('drift_threshold_exceeded', False),
                checkpoint_required=summary_data.get('checkpoint_required', False)
            )

            # Create a dummy checkpoint based on the summary
            if self.summary.checkpoint_required:
                self.checkpoint = CheckpointInfo(
                    id="chk_semantic_auto",
                    reason="Semantic drift threshold exceeded",
                    threshold=0.5,
                    detected_drift=self.summary.aggregated_risk_score,
                    created_at=datetime.now().isoformat(),
                    status="pending"
                )

            # Update all panels with new data
            self.update_concept_file_map(self.mappings)
            self.update_diff_detail_panel(self.mappings[0] if self.mappings else None, None)
            self.update_risk_escalation_panel(self.summary, self.checkpoint)

        except ImportError:
            # For now, use placeholder data if facade doesn't exist yet
            self.load_placeholder_data()
        except Exception as e:
            # If there's an error loading data, fall back to placeholder
            self.app.notify(f"Error loading semantic diff data: {str(e)}", severity="error", timeout=5)
            self.load_placeholder_data()
    
    def load_placeholder_data(self) -> None:
        """Load placeholder data for development."""
        from random import choice, random
        
        statuses = ["preserved", "changed", "degraded", "lost"]
        equivalence_levels = ["high", "medium", "low", "unknown"]
        heuristics = [
            "identifier_loss", 
            "api_shrinkage", 
            "size_delta", 
            "function_count_change",
            "interface_change",
            "dependency_modification"
        ]
        
        # Create mock mappings
        self.mappings = []
        for i in range(5):
            num_concepts = choice([1, 2, 3])
            concepts = []
            for j in range(num_concepts):
                concept = SemanticDiffConcept(
                    id=f"concept_{i}_{j}",
                    name=f"Concept {i}-{j}",
                    source_file=f"src/file_{i}.cpp",
                    target_file=f"target/file_{i}.py",
                    status=choice(statuses),
                    equivalence_level=choice(equivalence_levels),
                    risk_score=random(),
                    confidence=random(),
                    description=f"This concept represents a potential semantic change from the original source. The conversion may have altered the original behavior or meaning.",
                    evidence_links=[f"task_summary_{i}_{j}", f"snapshot_{i}_{j}"]
                )
                concepts.append(concept)
            
            mapping = SemanticDiffMapping(
                id=f"mapping_{i}",
                source_path=f"src/module_{i}",
                target_path=f"target/module_{i}",
                status=choice(statuses),
                concepts=concepts,
                risk_score=random(),
                confidence=random(),
                equivalence_level=choice(equivalence_levels),
                heuristics_used=[choice(heuristics) for _ in range(choice([1, 2, 3]))]
            )
            self.mappings.append(mapping)
        
        # Create mock summary
        total_concepts = sum(len(m.concepts) for m in self.mappings)
        self.summary = SemanticDiffSummary(
            total_concepts=total_concepts,
            preserved_concepts=int(total_concepts * 0.6),
            changed_concepts=int(total_concepts * 0.25),
            degraded_concepts=int(total_concepts * 0.1),
            lost_concepts=total_concepts - (int(total_concepts * 0.6) + int(total_concepts * 0.25) + int(total_concepts * 0.1)),
            total_files=len(self.mappings),
            preserved_files=3,
            changed_files=1,
            lost_files=1,
            aggregated_risk_score=random(),
            confidence_score=random(),
            heuristics_used=["identifier_loss", "api_shrinkage"],
            drift_threshold_exceeded=True,
            checkpoint_required=True
        )
        
        # Create mock checkpoint
        self.checkpoint = CheckpointInfo(
            id="chk_semantic_001",
            reason="Significant semantic drift detected in core module",
            threshold=0.5,
            detected_drift=0.75,
            created_at=datetime.now().isoformat(),
            status="pending"
        )
        
        # Update all panels with mock data
        self.update_concept_file_map(self.mappings)
        self.update_diff_detail_panel(self.mappings[0] if self.mappings else None, None)
        self.update_risk_escalation_panel(self.summary, self.checkpoint)
    
    def update_concept_file_map(self, mappings: List[SemanticDiffMapping]) -> None:
        """Update the concept/file map panel."""
        map_container = self.query_one("#concept-file-map-container", expect_type=Vertical)
        map_container.remove_children()
        map_panel = ConceptFileMapPanel(mappings)
        map_panel.mount_all(list(map_panel.compose()))
    
    def update_diff_detail_panel(self, mapping: SemanticDiffMapping, concept: SemanticDiffConcept) -> None:
        """Update the diff detail panel."""
        detail_container = self.query_one("#diff-detail-container", expect_type=Vertical)
        detail_container.remove_children()
        detail_panel = SemanticDiffDetailPanel(mapping, concept)
        detail_panel.mount_all(list(detail_panel.compose()))
    
    def update_risk_escalation_panel(self, summary: SemanticDiffSummary, checkpoint: CheckpointInfo) -> None:
        """Update the risk & escalation panel."""
        risk_container = self.query_one("#risk-escalation-container", expect_type=Vertical)
        risk_container.remove_children()
        risk_panel = RiskEscalationPanel(summary, checkpoint)
        risk_panel.mount_all(list(risk_panel.compose()))
    
    def on_label_clicked(self, event) -> None:
        """Handle clicking on a mapping or concept in the list."""
        if event.label.id:
            if event.label.id.startswith("mapping-"):
                try:
                    index = int(event.label.id.split("-")[1])
                    self.selected_mapping_index = index
                    mapping = self.mappings[index] if index < len(self.mappings) else None
                    
                    # Update selection display
                    for i in range(len(self.mappings)):
                        try:
                            label = self.query_one(f"#mapping-{i}", expect_type=Label)
                            if i == index:
                                label.add_class("selected")
                            else:
                                label.remove_class("selected")
                        except:
                            continue  # Skip if label doesn't exist
                    
                    # Update the detail panel
                    self.update_diff_detail_panel(mapping, None)
                    
                except ValueError:
                    pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "acknowledge-btn":
            self.action_acknowledge_loss()
        elif button_id == "accept-btn":
            self.action_mark_acceptable()
        elif button_id == "override-btn":
            self.action_override_with_reason()
    
    def action_acknowledge_loss(self) -> None:
        """Action to acknowledge loss."""
        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    from maestro.ui_facade.semantic import acknowledge_loss
                    # For now, using a mock ID - in a real implementation, this would be the actual loss ID
                    result = acknowledge_loss("loss_id_123", "Acknowledged by user")
                    self.app.notify("Loss acknowledged", timeout=3)

                    # Reload data to reflect changes
                    self.load_semantic_diff_data()
                except ImportError:
                    self.app.notify("Loss acknowledged (simulated)", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error acknowledging loss: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Acknowledgment cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Acknowledge loss in semantic comparison?\n\nThis will mark the detected loss as acknowledged but not necessarily resolved.",
            title="Confirm Acknowledge Loss"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_mark_acceptable(self) -> None:
        """Action to mark as acceptable."""
        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    from maestro.ui_facade.semantic import acknowledge_loss
                    # For now, using a mock ID - in a real implementation, this would be the actual loss ID
                    result = acknowledge_loss("loss_id_123", "Marked as acceptable by user")
                    self.app.notify("Marked as acceptable", timeout=3)

                    # Reload data to reflect changes
                    self.load_semantic_diff_data()
                except ImportError:
                    self.app.notify("Marked as acceptable (simulated)", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error marking as acceptable: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Marking as acceptable cancelled", timeout=2)

        from maestro.tui.widgets.modals import ConfirmDialog
        confirm_dialog = ConfirmDialog(
            message=f"Mark semantic changes as acceptable?\n\nThis will mark the semantic differences as acceptable and reduce the risk score.",
            title="Confirm Mark Acceptable"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirm)

    def action_override_with_reason(self) -> None:
        """Action to override with reason."""
        def on_reason_entered(reason: str):
            if reason:
                try:
                    from maestro.ui_facade.semantic import override_loss
                    # For now, using a mock ID - in a real implementation, this would be the actual loss ID
                    result = override_loss("loss_id_123", reason)
                    self.app.notify("Override completed", timeout=3)

                    # Reload data to reflect changes
                    self.load_semantic_diff_data()
                except ImportError:
                    self.app.notify("Override completed (simulated)", timeout=3)
                except Exception as e:
                    self.app.notify(f"Error during override: {str(e)}", timeout=3, severity="error")
            else:
                self.app.notify("Override cancelled - reason required", timeout=2)

        from maestro.tui.widgets.modals import InputDialog
        input_dialog = InputDialog(
            message="Enter reason for override:",
            title="Override Semantic Checkpoint"
        )
        self.app.push_screen(input_dialog, callback=on_reason_entered)
    
    def action_move_selection_up(self) -> None:
        """Move selection up in the mappings list."""
        if self.selected_mapping_index > 0:
            self.selected_mapping_index -= 1
            self.update_selection_display()
    
    def action_move_selection_down(self) -> None:
        """Move selection down in the mappings list."""
        if self.selected_mapping_index < len(self.mappings) - 1:
            self.selected_mapping_index += 1
            self.update_selection_display()
    
    def update_selection_display(self) -> None:
        """Update the visual selection in the mappings list."""
        # Update selection display
        for i in range(len(self.mappings)):
            try:
                label = self.query_one(f"#mapping-{i}", expect_type=Label)
                if i == self.selected_mapping_index:
                    label.add_class("selected")
                else:
                    label.remove_class("selected")
            except:
                continue  # Skip if label doesn't exist
        
        # Update the detail panel
        if self.selected_mapping_index < len(self.mappings):
            selected_mapping = self.mappings[self.selected_mapping_index]
            self.update_diff_detail_panel(selected_mapping, None)