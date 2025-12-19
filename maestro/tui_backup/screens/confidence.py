"""
Confidence Screen for Maestro TUI - Confidence Scoreboard
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button, Static, DataTable
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from maestro.ui_facade.confidence import get_confidence, get_confidence_components, get_confidence_gates, get_confidence_trend, explain_confidence, simulate_promotion_gate, ConfidenceTier
from datetime import datetime


class ScopeSelector(Vertical):
    """Left region: Allows selecting the scope for confidence evaluation."""
    
    def __init__(self):
        super().__init__()
        self.scope_options = ["repo", "run", "baseline", "batch"]
        self.current_scope = "repo"
        self.entity_id = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the scope selector."""
        yield Label("[b]Scope Selection[/b]", classes="category-title")
        
        # Scope selection buttons
        for option in self.scope_options:
            btn = Button(option.title(), id=f"scope-{option}", variant="default")
            if option == self.current_scope:
                btn.variant = "primary"
            yield btn
        
        # Show identifier based on current scope
        yield Label("\n[b]Identifiers:[/b]", classes="category-title")
        yield Label(f"Scope: {self.current_scope.title()}", classes="category-item")
        
        if self.entity_id:
            yield Label(f"Entity ID: {self.entity_id[:8]}...", classes="category-item")
        else:
            yield Label(f"Entity ID: current", classes="category-item")
            
        # Simulation controls
        yield Label("\n[b]CI Simulation:[/b]", classes="category-title")
        yield Button("Simulate Promotion", id="simulate-promotion", variant="success")


class ScoreBreakdown(Vertical):
    """Center region: Shows confidence score breakdown by component."""
    
    def __init__(self, scope: str = "repo", entity_id: str = None):
        super().__init__()
        self.scope = scope
        self.entity_id = entity_id
        self.components = []
        self.load_data()

    def load_data(self):
        """Load confidence components data."""
        try:
            self.components = get_confidence_components(self.scope, self.entity_id)
        except Exception as e:
            self.components = []
            self.mount(Label(f"Error loading data: {str(e)}", classes="error"))

    def compose(self) -> ComposeResult:
        """Create child widgets for the score breakdown."""
        if not self.components:
            yield Label("Loading confidence components...", classes="placeholder")
            return

        yield Label("[b]Confidence Components[/b]", classes="category-title")

        for i, component in enumerate(self.components):
            # Calculate score percentage
            score_pct = int(component.score * 100)

            # Determine trend icon
            trend_icons = {
                'up': '↑',
                'down': '↓',
                'stable': '→',
                'new': 'NEW'
            }
            trend_icon = trend_icons.get(component.trend, '?')

            # Determine color based on score
            if component.score >= 0.8:
                score_color = "green"
            elif component.score >= 0.6:
                score_color = "yellow"
            else:
                score_color = "red"

            # Create a clickable container for each component with unique ID
            with Horizontal(classes="category-item", id=f"component-{component.id}"):
                yield Label(f"{component.name}:", classes="component-name")
                yield Label(f"[{score_color}]{score_pct}% {trend_icon}[/]", classes="component-score")

            # Show description
            yield Label(f"  {component.description}", classes="entry-meta")

            # Show evidence link
            yield Label(f"  [link={component.evidence_link}]Evidence >>[/link]", classes="entry-meta")

            # Show explanation
            yield Label(f"  {component.explanation}", classes="entry-meta")


class HistoricalTrend(Vertical):
    """Widget to show historical confidence trend."""

    def __init__(self, scope: str = "repo", entity_id: str = None):
        super().__init__()
        self.scope = scope
        self.entity_id = entity_id
        self.trend_data = []

    def on_mount(self):
        """Load trend data when mounted."""
        try:
            self.trend_data = get_confidence_trend(self.scope, self.entity_id)
        except Exception as e:
            self.trend_data = []
            self.mount(Label(f"Error loading trend data: {str(e)}", classes="error"))

    def compose(self) -> ComposeResult:
        """Create child widgets for historical trend."""
        if not self.trend_data:
            yield Label("Loading trend data...", classes="placeholder")
            return

        yield Label("[b]Confidence Trend[/b]", classes="category-title")

        # Create a simple text-based chart
        max_score = max(item['score'] for item in self.trend_data) if self.trend_data else 1.0
        min_score = min(item['score'] for item in self.trend_data) if self.trend_data else 0.0
        score_range = max_score - min_score if max_score != min_score else 1.0

        # Show recent trend
        if len(self.trend_data) >= 2:
            first_score = self.trend_data[0]['score']
            last_score = self.trend_data[-1]['score']

            if last_score > first_score:
                trend_indicator = "📈 [green]Improving[/green]"
            elif last_score < first_score:
                trend_indicator = "📉 [red]Declining[/red]"
            else:
                trend_indicator = "➡️ [yellow]Stable[/yellow]"

            yield Label(f"Trend: {trend_indicator} ({int(first_score*100)}% → {int(last_score*100)}%)", classes="entry-meta")

        # Show last few data points
        yield Label("\n[b]Recent Scores:[/b]", classes="detail-section-title")
        for item in self.trend_data[-5:]:  # Show last 5 points
            score_pct = int(item['score'] * 100)
            if item['score'] >= 0.8:
                score_color = "green"
            elif item['score'] >= 0.6:
                score_color = "yellow"
            else:
                score_color = "red"

            yield Label(f"  [{score_color}]{item['label']}: {score_pct}%[/]", classes="entry-item")


class GatesAndPromotion(Vertical):
    """Right region: Shows promotion gates and readiness status."""

    def __init__(self, scope: str = "repo", entity_id: str = None):
        super().__init__()
        self.scope = scope
        self.entity_id = entity_id
        self.report = None
        self.load_data()

    def load_data(self):
        """Load confidence report data."""
        try:
            self.report = get_confidence(self.scope, self.entity_id)
        except Exception as e:
            self.report = None
            self.mount(Label(f"Error loading data: {str(e)}", classes="error"))

    def compose(self) -> ComposeResult:
        """Create child widgets for gates and promotion status."""
        if not self.report:
            yield Label("Loading confidence report...", classes="placeholder")
            return

        # Overall confidence tier
        tier_symbol = {
            ConfidenceTier.GREEN: "🟢",
            ConfidenceTier.YELLOW: "🟡",
            ConfidenceTier.RED: "🔴"
        }[self.report.tier]

        yield Label(f"[b]Overall Confidence:[/b] {tier_symbol} {int(self.report.overall_score * 100)}%", classes="detail-title")

        # Promition readiness
        ready_symbols = {
            "safe": "✓",
            "review_needed": "⚠",
            "blocked": "✗"
        }
        ready_symbol = ready_symbols.get(self.report.promotion_ready, "?")

        ready_labels = {
            "safe": "[green]Safe to promote[/green]",
            "review_needed": "[yellow]Requires review[/yellow]",
            "blocked": "[red]Blocked[/red]"
        }
        ready_label = ready_labels.get(self.report.promotion_ready, "Unknown")

        yield Label(f"\n[b]Promotion Ready:[/b] {ready_symbol} {ready_label}", classes="detail-status")

        # Blocking reasons if any
        if self.report.blocking_reasons:
            yield Label(f"\n[b]Blocking Reasons:[/b]", classes="blocking-title")
            for reason in self.report.blocking_reasons[:5]:  # Show first 5 reasons
                yield Label(f"• {reason}", classes="blocking-reason")

        # Show gates
        yield Label(f"\n[b]Gates Status:[/b]", classes="detail-section-title")
        gates = get_confidence_gates(self.scope, self.entity_id)

        for gate in gates:
            status_symbol = "✅" if gate.status else "❌"
            color = "green" if gate.status else "red"
            priority_symbol = "🚨" if gate.priority == 0 else "⚠️"  # Critical vs warning

            yield Label(f"{priority_symbol} [{color}]{status_symbol} {gate.name}[/]", classes="entry-item")
            yield Label(f"  {gate.reason}", classes="entry-meta")

        # Add historical trend
        yield Label(f"\n[b]Historical Comparison:[/b]", classes="detail-section-title")
        yield HistoricalTrend(self.scope, self.entity_id)


class ConfidenceScreen(Screen):
    """Confidence screen of the Maestro TUI - Confidence Scoreboard."""

    # Reactive variables to track state
    scope = reactive("repo")
    entity_id = reactive(None)

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("s", "toggle_scope_menu", "Change Scope"),
        ("e", "show_explanation", "Explain Component"),
        ("h", "show_history", "Show History"),
        ("escape", "app.pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the confidence screen."""
        yield Header(show_clock=True)

        # Create the main dashboard layout with three regions
        with Horizontal(id="confidence-container"):
            # Left: Scope Selector
            with Vertical(id="scope-selector-container", classes="dashboard-panel"):
                yield ScopeSelector()

            # Center: Score Breakdown
            with Vertical(id="score-breakdown-container", classes="dashboard-panel"):
                yield ScoreBreakdown(self.scope, self.entity_id)

            # Right: Gates & Promotion Status
            with Vertical(id="gates-promotion-container", classes="dashboard-panel"):
                yield GatesAndPromotion(self.scope, self.entity_id)

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Set initial title
        self.title = f"Maestro TUI - Confidence Scoreboard ({self.scope})"

    def watch_scope(self, new_scope: str) -> None:
        """Called when the scope changes."""
        # Update the screen title to reflect current scope
        self.title = f"Maestro TUI - Confidence Scoreboard ({new_scope})"
        
        # Refresh the data displays
        self.refresh_display()

    def refresh_display(self):
        """Refresh all confidence displays."""
        # Update scope selector
        scope_selector = self.query_one("#scope-selector-container", expect_type=Vertical)
        scope_selector.remove_children()
        scope_selector.mount_all(list(ScopeSelector().compose()))
        
        # Update score breakdown
        score_panel = self.query_one("#score-breakdown-container", expect_type=Vertical)
        score_panel.remove_children()
        score_panel.mount_all(list(ScoreBreakdown(self.scope, self.entity_id).compose()))
        
        # Update gates and promotion
        gates_panel = self.query_one("#gates-promotion-container", expect_type=Vertical)
        gates_panel.remove_children()
        gates_panel.mount_all(list(GatesAndPromotion(self.scope, self.entity_id).compose()))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id and button_id.startswith("scope-"):
            # Change scope
            new_scope = button_id.replace("scope-", "")
            self.scope = new_scope

            # Update button variants to show selection
            for opt in ["repo", "run", "baseline", "batch"]:
                btn = self.query(f"#scope-{opt}")
                if btn:
                    btn_variant = "primary" if opt == new_scope else "default"
                    for b in btn:
                        b.variant = btn_variant

        elif button_id == "simulate-promotion":
            # Show simulation results
            self.show_promotion_simulation()

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a component to show evidence or explanation."""
        # Check if the clicked label is part of a component row
        if event.label.id and event.label.id.startswith("component-"):
            # Extract component ID from the container ID
            component_id = event.label.id.replace("component-", "")

            # Find the corresponding component
            selected_component = None
            for comp in self.components:
                if comp.id == component_id:
                    selected_component = comp
                    break

            if selected_component:
                # Show explanation in a notification or modal
                explanation = explain_confidence(component_id)
                self.app.notify(f"[b]{selected_component.name}[/b]\n{explanation}", timeout=6)

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Set initial title
        self.title = f"Maestro TUI - Confidence Scoreboard ({self.scope})"

        # Bind click events to component containers
        self.call_after_refresh(self._bind_component_clicks)

    def _bind_component_clicks(self) -> None:
        """Bind click events for component containers."""
        # Iterate through all component containers and bind click events
        for comp in self.components:
            try:
                container = self.query_one(f"#component-{comp.id}", expect_type=Horizontal)
                # Make the container clickable
                container.styles.cursor = "pointer"
            except:
                # If element doesn't exist yet, try again later
                continue
        
    def show_promotion_simulation(self):
        """Show promotion gate simulation results."""
        try:
            simulation = simulate_promotion_gate(self.scope, self.entity_id)
            
            # Create modal or display results in a new screen
            results_text = f"""Promotion Gate Simulation Results:

Standard CI: {'[green]PASS[/green]' if simulation['would_pass_standard'] else '[red]FAIL[/red]'}
Strict Mode: {'[green]PASS[/green]' if simulation['would_pass_strict'] else '[red]FAIL[/red]'}
Permissive: {'[green]PASS[/green]' if simulation['would_pass_permissive'] else '[red]FAIL[/red]'}

Critical Failures: {len(simulation['critical_failures'])}
Warnings: {len(simulation['warnings'])}

Recommendation: {simulation['recommendation'].title()}
"""
            # For now, just show a notification
            self.app.notify(results_text, timeout=8)
        except Exception as e:
            self.app.notify(f"Error running simulation: {str(e)}", timeout=3, severity="error")

    def action_refresh(self) -> None:
        """Action to refresh the confidence display."""
        self.refresh_display()
        self.app.notify("Confidence data refreshed", timeout=2)

    def action_toggle_scope_menu(self) -> None:
        """Action to toggle scope menu."""
        from maestro.tui.widgets.command_palette import CommandPaletteScreen
        self.app.push_screen(CommandPaletteScreen(session_id=self.app.active_session.id if self.app.active_session else None))

    def action_show_explanation(self) -> None:
        """Action to show explanation for a component."""
        # In a real implementation, this would prompt for component selection
        self.app.notify("Press 'e' then select a component to explain", timeout=3)

    def action_show_history(self) -> None:
        """Action to show historical comparison."""
        # For now, just show a notification with trend summary
        try:
            trend_data = get_confidence_trend(self.scope, self.entity_id)
            if trend_data:
                first_score = trend_data[0]['score']
                last_score = trend_data[-1]['score']

                if last_score > first_score:
                    trend_desc = "[green]Improving[/green]"
                elif last_score < first_score:
                    trend_desc = "[red]Declining[/red]"
                else:
                    trend_desc = "[yellow]Stable[/yellow]"

                self.app.notify(f"Confidence trend: {trend_desc} ({int(first_score*100)}% → {int(last_score*100)}%)", timeout=4)
            else:
                self.app.notify("No historical data available", timeout=2)
        except Exception as e:
            self.app.notify(f"Error loading history: {str(e)}", timeout=3, severity="error")