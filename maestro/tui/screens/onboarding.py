"""
Onboarding Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label
from textual.containers import Vertical, Horizontal
from textual import on
from ..onboarding import onboarding_manager, OnboardingStep


class OnboardingScreen(ModalScreen):
    """Modal screen for first-run onboarding flow."""

    BINDINGS = [
        ("enter", "next_step", "Next"),
        ("escape", "skip_onboarding", "Skip"),
    ]

    def __init__(self):
        super().__init__()
        self.current_step_index = 0
        self.steps = onboarding_manager.steps

    def compose(self) -> ComposeResult:
        """Create child widgets for the onboarding screen."""
        with Vertical(id="onboarding-container", classes="onboarding-screen"):
            # Title
            yield Label("[b]Maestro TUI Onboarding[/b]", id="onboarding-title")

            # Step counter
            yield Label(f"Step {self.current_step_index + 1} of {len(self.steps)}", id="step-counter")

            # Current step content
            current_step = self.steps[self.current_step_index]
            with Vertical(id="step-content"):
                yield Label(f"[b]{current_step.title}[/b]", id="step-title")
                yield Static(current_step.description, id="step-description")

                if current_step.key_bindings:
                    with Horizontal(id="key-bindings"):
                        for key in current_step.key_bindings:
                            yield Label(f"  [yellow]{key}[/yellow]  ", classes="key-binding")

            # Next hint
            if current_step.next_hint:
                yield Label(current_step.next_hint, id="next-hint")

            # Action buttons
            with Horizontal(id="onboarding-buttons"):
                if self.current_step_index == len(self.steps) - 1:
                    # Final step - complete onboarding
                    yield Button("Complete Onboarding", variant="success", id="complete-btn")
                else:
                    # Regular next button
                    yield Button("Next", variant="primary", id="next-btn")

                yield Button("Skip", variant="default", id="skip-btn")

    def on_mount(self) -> None:
        """Focus the appropriate button when mounted."""
        if self.current_step_index == len(self.steps) - 1:
            self.query_one("#complete-btn").focus()
        else:
            self.query_one("#next-btn").focus()

    def action_next_step(self) -> None:
        """Move to the next step or complete onboarding."""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.refresh()  # Refresh the entire screen to update content
        else:
            # Complete the onboarding
            self._complete_onboarding()

    def action_skip_onboarding(self) -> None:
        """Skip the onboarding flow."""
        self.dismiss()

    def _complete_onboarding(self) -> None:
        """Complete the onboarding flow."""
        onboarding_manager.mark_onboarding_completed()
        self.dismiss()

    @on(Button.Pressed, "#next-btn")
    def on_next_pressed(self, event: Button.Pressed) -> None:
        """Handle next button press."""
        self.action_next_step()

    @on(Button.Pressed, "#complete-btn")
    def on_complete_pressed(self, event: Button.Pressed) -> None:
        """Handle complete button press."""
        self._complete_onboarding()

    @on(Button.Pressed, "#skip-btn")
    def on_skip_pressed(self, event: Button.Pressed) -> None:
        """Handle skip button press."""
        self.action_skip_onboarding()