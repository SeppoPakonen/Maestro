"""
Help Index & Mental Model Map Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from ..widgets.progressive_disclosure import AdvancedConcepts, ExpandableSection
from ..widgets.help_panel import HelpPanel, ScreenSpecificHelpData


class HelpIndexScreen(Screen):
    """Help Index & Mental Model Map screen - the 'score legend' of the orchestra."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("h", "toggle_help_panel", "Toggle Help"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the help index screen."""
        yield Header()

        with Vertical(id="help-index-container"):
            # Title and description
            yield Label("[b]Help Index & Mental Model Map[/b]", classes="title")
            yield Label("The 'score legend' of the Maestro orchestra", classes="subtitle")
            
            # Overview section
            with Vertical(classes="overview-section"):
                yield Label("[b]System Overview[/b]", classes="section-title")
                yield Static(
                    "Maestro orchestrates AI agents to perform complex software development tasks.\n"
                    "The system follows a hierarchical flow: [i]Session → Phase → Tasks → Runs → Replay → Confidence[/i]\n"
                    "Each level builds on the previous and feeds into verification systems.",
                    classes="overview-content"
                )
            
            # Core concepts with progressive disclosure
            with ScrollableContainer(id="concepts-container"):
                # Session concept
                yield Label("[b]Sessions[/b]", classes="concept-title")
                yield Static(
                    "Sessions maintain state across runs and provide a workspace for related tasks.\n"
                    "Each session can contain multiple phases for different approaches to the same task.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for sessions
                session_explanation = (
                    "**Sessions Explained**\n\n"
                    "Sessions are the top-level organizational unit in Maestro.\n\n"
                    "**How they work:**\n"
                    "• Each session represents a complete work effort\n"
                    "• Sessions maintain history and artifact storage\n"
                    "• Multiple phases can exist within one session\n"
                    "• Sessions can be paused and resumed\n\n"
                    "**When to use:**\n"
                    "• Starting a new project or feature\n"
                    "• Maintaining state across multiple attempts\n"
                    "• Organizing related work efforts"
                )
                yield ExpandableSection(
                    title="Why am I seeing sessions?",
                    content=session_explanation,
                    section_id="sessions"
                )
                
                # Phase concept
                yield Label("\n[b]Phases[/b]", classes="concept-title")
                yield Static(
                    "Phases represent structured approaches to completing the session's goal.\n"
                    "Each phase contains a hierarchy of subtasks that break down the work.",
                    classes="concept-description"
                )

                # Add progressive disclosure for phases
                phase_explanation = (
                    "**Phases Explained**\n\n"
                    "Phases are detailed breakdowns of how to achieve the session's objective.\n\n"
                    "**How they work:**\n"
                    "• Phases are derived from the session's root task\n"
                    "• Each phase contains a tree of subtasks\n"
                    "• Multiple phase branches can exist for different approaches\n"
                    "• Phases can be killed or activated\n\n"
                    "**When to use:**\n"
                    "• When you need different approaches to the same problem\n"
                    "• When you want to experiment with different strategies\n"
                    "• When work needs to be organized hierarchically"
                )
                yield ExpandableSection(
                    title="Why am I seeing phases?",
                    content=phase_explanation,
                    section_id="phases"
                )
                
                # Tasks concept
                yield Label("\n[b]Tasks[/b]", classes="concept-title")
                yield Static(
                    "Tasks are the smallest units of work that can be executed by AI agents.\n"
                    "They represent specific, actionable work items within a phase.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for tasks
                task_explanation = (
                    "**Tasks Explained**\n\n"
                    "Tasks are the fundamental units of execution in Maestro.\n\n"
                    "**How they work:**\n"
                    "• Tasks are atomic units of work\n"
                    "• Each task has a specific goal and description\n"
                    "• Tasks can be executed in sequence or parallel\n"
                    "• Task results feed into verification systems\n\n"
                    "**When to use:**\n"
                    "• When you need to break down complex work\n"
                    "• When you want verifiable, incremental progress\n"
                    "• When you need to track individual work units"
                )
                yield ExpandableSection(
                    title="Why am I seeing tasks?",
                    content=task_explanation,
                    section_id="tasks"
                )
                
                # Runs concept
                yield Label("\n[b]Runs[/b]", classes="concept-title")
                yield Static(
                    "Runs represent complete executions of phases and tasks.\n"
                    "They capture all outputs, artifacts, and results for verification.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for runs
                run_explanation = (
                    "**Runs Explained**\n\n"
                    "Runs capture complete execution sessions and their outcomes.\n\n"
                    "**How they work:**\n"
                    "• Runs record complete execution history\n"
                    "• They capture all artifacts and outputs\n"
                    "• Runs can be replayed for verification\n"
                    "• Baselines are established from successful runs\n\n"
                    "**When to use:**\n"
                    "• When you want to verify execution results\n"
                    "• When comparing different execution approaches\n"
                    "• When establishing new baselines"
                )
                yield ExpandableSection(
                    title="Why am I seeing runs?",
                    content=run_explanation,
                    section_id="runs"
                )
                
                # Replay concept
                yield Label("\n[b]Replay & Baselines[/b]", classes="concept-title")
                yield Static(
                    "Replay systems verify consistency by re-executing runs against baselines.\n"
                    "This ensures semantic integrity and detects unexpected changes.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for replay/baselines
                replay_explanation = AdvancedConcepts.get_replay_vs_baseline_explanation()
                yield ExpandableSection(
                    title="Why am I seeing replay vs baseline?",
                    content=replay_explanation,
                    section_id="replay"
                )
                
                # Confidence concept
                yield Label("\n[b]Confidence Scoring[/b]", classes="concept-title")
                yield Static(
                    "Confidence scores measure the reliability of AI-generated changes.\n"
                    "They aggregate multiple verification signals to assess quality.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for confidence
                confidence_explanation = AdvancedConcepts.get_confidence_scoring_explanation()
                yield ExpandableSection(
                    title="Why am I seeing confidence scores?",
                    content=confidence_explanation,
                    section_id="confidence"
                )
                
                # Arbitration concept
                yield Label("\n[b]Arbitration Arena[/b]", classes="concept-title")
                yield Static(
                    "Arbitration compares multiple implementations to select the best solution.\n"
                    "This is used when multiple AI engines produce different approaches.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for arbitration
                arbitration_explanation = AdvancedConcepts.get_arbitration_explanation()
                yield ExpandableSection(
                    title="Why am I seeing arbitration?",
                    content=arbitration_explanation,
                    section_id="arbitration"
                )
                
                # Semantic Integrity concept
                yield Label("\n[b]Semantic Integrity[/b]", classes="concept-title")
                yield Static(
                    "Semantic integrity systems detect unintended changes to code behavior.\n"
                    "They ensure transformations preserve the original meaning and functionality.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for semantic integrity
                semantic_explanation = AdvancedConcepts.get_semantic_drift_explanation()
                yield ExpandableSection(
                    title="Why am I seeing semantic integrity checks?",
                    content=semantic_explanation,
                    section_id="semantic"
                )
                
                # Checkpoints concept
                yield Label("\n[b]Checkpoints[/b]", classes="concept-title")
                yield Static(
                    "Checkpoints are verification points in conversion processes.\n"
                    "They allow human review before changes propagate further.",
                    classes="concept-description"
                )
                
                # Add progressive disclosure for checkpoints
                checkpoint_explanation = AdvancedConcepts.get_checkpoints_explanation()
                yield ExpandableSection(
                    title="Why am I seeing checkpoints?",
                    content=checkpoint_explanation,
                    section_id="checkpoints"
                )
            
            # Add the help panel
            help_content = ScreenSpecificHelpData.get_help_content("help")
            yield HelpPanel(
                title="Help Index Help", 
                help_content=help_content, 
                screen_name="help",
                id="help-panel"
            )

        yield Footer()

    def action_toggle_help_panel(self) -> None:
        """Toggle the help panel visibility."""
        try:
            help_panel = self.query_one("#help-panel")
            if hasattr(help_panel, 'toggle_collapsed'):
                help_panel.toggle_collapsed()
        except:
            # If no help panel exists on current screen, do nothing
            pass