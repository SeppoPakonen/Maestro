"""
Progressive Disclosure Widget for Maestro TUI

Provides expandable sections for advanced concepts
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from textual import on
from typing import Dict, Optional


class ExpandableSection(Vertical):
    """An expandable section for progressive disclosure of advanced concepts."""
    
    # Reactive property to track expanded state
    expanded = reactive(False)
    
    def __init__(self, 
                 title: str, 
                 content: str, 
                 section_id: str = "",
                 classes: str = "expandable-section"):
        super().__init__(classes=classes)
        self.title = title
        self.content = content
        self.section_id = section_id
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the expandable section."""
        # Header with toggle button
        with Horizontal(id=f"section-{self.section_id}-header", classes="section-header"):
            arrow = "▶" if not self.expanded else "▼"
            yield Label(f"{arrow} {self.title}", id=f"section-{self.section_id}-title")
            yield Button("Why am I seeing this?", variant="default", id=f"toggle-{self.section_id}", classes="toggle-button")
        
        # Content container (visible only when expanded)
        with Vertical(id=f"section-{self.section_id}-content", classes="section-content" + (" hidden" if not self.expanded else "")):
            yield Static(self.content, id=f"section-{self.section_id}-text")
    
    def toggle_expanded(self) -> None:
        """Toggle the expanded state."""
        self.expanded = not self.expanded
        self._update_display()
        
    def _update_display(self) -> None:
        """Update the UI based on expanded state."""
        # Update the toggle button text
        toggle_button = self.query_one(f"#toggle-{self.section_id}", Button)
        toggle_button.label = "Hide details" if self.expanded else "Why am I seeing this?"
        
        # Update the arrow in the title
        arrow = "▶" if not self.expanded else "▼"
        title_label = self.query_one(f"#section-{self.section_id}-title", Label)
        title_label.update(f"{arrow} {self.title}")
        
        # Update content visibility
        content_container = self.query_one(f"#section-{self.section_id}-content", Vertical)
        if not self.expanded:
            content_container.add_class("hidden")
        else:
            content_container.remove_class("hidden")
    
    @on(Button.Pressed, "#toggle-{self.section_id}")
    def on_toggle_button_pressed(self, event: Button.Pressed) -> None:
        """Handle toggle button press."""
        self.toggle_expanded()


class AdvancedConcepts:
    """Provides content for advanced concepts sections."""
    
    @staticmethod
    def get_arbitration_explanation() -> str:
        """Get explanation for arbitration concept."""
        return """**Arbitration Explained**

Arbitration is the process of comparing multiple implementations of the same task and selecting the best one. This happens when different AI engines produce different solutions to the same problem.

**How it works:**
• Multiple AI engines work on the same task independently
• Each produces a different implementation
• A judge engine evaluates all implementations
• The best solution is selected based on correctness, efficiency, and style

**When you'll see this:**
• When multiple engines are configured
• When confidence is low for a single solution
• When semantic integrity requires verification

**What you can do:**
• Review all candidate implementations
• Check semantic equivalence
• Select the winning solution manually if needed"""
    
    @staticmethod
    def get_checkpoints_explanation() -> str:
        """Get explanation for checkpoints concept."""
        return """**Checkpoints Explained**

Checkpoints are verification points in the conversion process where you can approve or reject changes before they propagate further.

**How they work:**
• Conversion pipeline pauses at predetermined points
• Changes are presented for human review
• You can approve, reject, or modify changes
• Process continues based on your decision

**When you'll see this:**
• During format conversion processes
• When semantic integrity checks flag issues
• At critical transformation points

**What you can do:**
• Review pending changes
• Approve to continue conversion
• Reject to stop and reconsider"""
    
    @staticmethod 
    def get_semantic_drift_explanation() -> str:
        """Get explanation for semantic drift concept."""
        return """**Semantic Drift Explained**

Semantic drift detection monitors whether code changes maintain their intended meaning and behavior over time.

**How it works:**
• Code and behavior are compared across versions
• Semantic differences are identified
• Confidence scores are adjusted based on drift
• Significant drift triggers alerts

**When you'll see this:**
• During replay operations
• When comparing runs to baselines
• During arbitration processes
• In confidence scoring

**What you can do:**
• Review semantic differences
• Acknowledge acceptable changes
• Address problematic drift"""
    
    @staticmethod
    def get_replay_vs_baseline_explanation() -> str:
        """Get explanation for replay vs baseline concept."""
        return """**Replay vs Baseline Explained**

Replay compares current execution to a baseline to identify differences in behavior, output, and performance.

**How it works:**
• A baseline run is established as reference
• New runs are compared against this baseline
• Differences in files, behavior, and output are detected
• Changes are categorized as safe or concerning

**When you'll see this:**
• After running tasks multiple times
• During quality verification
• In CI/CD pipelines
• When troubleshooting issues

**What you can do:**
• Compare run outputs
• Set new baselines
• Investigate differences"""
    
    @staticmethod
    def get_confidence_scoring_explanation() -> str:
        """Get explanation for confidence scoring concept."""
        return """**Confidence Scoring Explained**

Confidence scores measure the reliability and quality of AI-generated changes and decisions.

**How it works:**
• Multiple factors contribute to confidence:
  - Code correctness validation
  - Semantic integrity checks
  - Historical success rates
  - Consistency across engines
• Scores are aggregated at different levels
• Low scores trigger additional verification

**When you'll see this:**
• In task execution reports
• During arbitration decisions
• In quality gates
• In replay comparisons

**What you can do:**
• Review confidence factors
• Override low-confidence decisions
• Tune confidence thresholds"""