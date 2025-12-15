"""
Reusable Modal Widgets for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, TextArea
from textual.containers import Vertical, Horizontal
from textual import events


class ConfirmDialog(ModalScreen[bool]):
    """A confirmation dialog modal."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(self, message: str = "Are you sure?", title: str = "Confirmation"):
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        """Create child widgets for the confirmation dialog."""
        with Vertical(id="confirm-dialog-container"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", variant="default", id="cancel-button")
                yield Button("Confirm", variant="error", id="confirm-button")

    def on_mount(self) -> None:
        """Focus the cancel button by default."""
        self.query_one("#cancel-button").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-button":
            self.dismiss(True)
        elif event.button.id == "cancel-button":
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Action to cancel the confirmation."""
        self.dismiss(False)

    def action_confirm(self) -> None:
        """Action to confirm the action."""
        self.dismiss(True)


class InputDialog(ModalScreen[str]):
    """An input dialog modal."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Submit"),
    ]

    def __init__(self, message: str = "Enter value:", title: str = "Input", initial_value: str = ""):
        super().__init__()
        self.message = message
        self.title = title
        self.initial_value = initial_value

    def compose(self) -> ComposeResult:
        """Create child widgets for the input dialog."""
        with Vertical(id="input-dialog-container"):
            yield Label(self.message, id="input-message")
            yield Input(value=self.initial_value, id="input-field")
            with Horizontal(id="input-buttons"):
                yield Button("Cancel", variant="default", id="cancel-button")
                yield Button("Submit", variant="primary", id="submit-button")

    def on_mount(self) -> None:
        """Focus the input field when mounted."""
        self.query_one("#input-field").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-button":
            self.action_submit()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submitted event."""
        self.action_submit()

    def action_cancel(self) -> None:
        """Action to cancel the input."""
        self.dismiss(None)

    def action_submit(self) -> None:
        """Action to submit the input."""
        input_widget = self.query_one("#input-field", Input)
        self.dismiss(input_widget.value)


class DecisionOverrideWizard(ModalScreen[dict]):
    """A 3-step wizard for overriding conversion decisions."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, decision: dict, title: str = "Decision Override Wizard"):
        super().__init__()
        self.decision = decision
        self.title = title
        self.step = 1  # Start at step 1
        self.new_value = ""
        self.reason = ""
        self.auto_replan = True

    def compose(self) -> ComposeResult:
        """Create child widgets for the wizard."""
        with Vertical(id="decision-override-wizard-container"):
            # Step indicator
            yield Label(f"Step {self.step} of 3", id="step-indicator")

            # Content based on current step
            if self.step == 1:
                yield Label(f"Decision ID: {self.decision['id']}", id="decision-id")
                yield Label(f"Title: {self.decision['title']}", id="decision-title")

                # Show current decision value if available
                current_value = self.decision.get('value', self.decision.get('reason', 'No description available'))
                yield Label(f"Current Value:", id="current-value-label")
                yield Label(current_value, id="current-value", classes="decision-content")

                yield Label("WARNING: Overrides supersede, never delete", id="warning-label", classes="warning")
                yield Label("Proceed with override?", id="confirm-prompt")

                with Horizontal(id="step1-buttons"):
                    yield Button("Cancel", variant="default", id="cancel-button")
                    yield Button("No", variant="default", id="no-button")
                    yield Button("Yes, Proceed", variant="primary", id="yes-button")

            elif self.step == 2:
                yield Label(f"Editing Decision: {self.decision['id']}", id="edit-title")
                yield Label("New Decision Content:", id="new-value-label")

                # Using a text input for now, might need TextArea later
                yield Input(placeholder="Enter the new decision content/value", id="new-value-input")

                yield Label("Reason for Override (required):", id="reason-label")
                yield Input(placeholder="Provide a reason for this override", id="reason-input")

                yield Label("Auto Replan After Override:", id="replan-label")
                # Using a button as a toggle since Textual doesn't have a native checkbox in this project
                replan_text = "ON" if self.auto_replan else "OFF"
                yield Button(f"Auto Replan: {replan_text}", variant="success" if self.auto_replan else "default", id="replan-toggle")

                with Horizontal(id="step2-buttons"):
                    yield Button("Back", variant="default", id="back-button")
                    yield Button("Continue", variant="primary", id="continue-button")

            elif self.step == 3:
                yield Label("Review Override", id="review-title")
                yield Label(f"Decision: {self.decision['id']}", id="review-decision-id")
                yield Label(f"Old Value: {self.decision.get('value', self.decision.get('reason', 'No description'))}", id="old-value")
                yield Label(f"New Value: {self.new_value}", id="new-value")
                yield Label(f"Reason: {self.reason}", id="reason-review")
                yield Label(f"Auto Replan: {'YES' if self.auto_replan else 'NO'}", id="replan-review")

                with Horizontal(id="step3-buttons"):
                    yield Button("Back", variant="default", id="review-back-button")
                    yield Button("Cancel", variant="default", id="review-cancel-button")
                    yield Button("Apply Override", variant="warning", id="apply-button")

            # Navigation indicators
            with Horizontal(id="wizard-nav-indicators"):
                step_class = "active" if self.step == 1 else "inactive"
                yield Label("●", classes=step_class, id="nav-step1")
                step_class = "active" if self.step == 2 else "inactive"
                yield Label("●", classes=step_class, id="nav-step2")
                step_class = "active" if self.step == 3 else "inactive"
                yield Label("●", classes=step_class, id="nav-step3")

    def on_mount(self) -> None:
        """Set up the wizard when mounted."""
        if self.step == 2:
            # Focus the new value input for step 2
            self.query_one("#new-value-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the wizard."""
        button_id = event.button.id

        if button_id == "yes-button":
            self.step = 2
            self.refresh_wizard()
        elif button_id == "no-button" or button_id == "cancel-button":
            self.dismiss({"cancelled": True})
        elif button_id == "back-button":
            self.step = 1
            self.refresh_wizard()
        elif button_id == "continue-button":
            # Get values from the input fields
            new_value_widget = self.query_one("#new-value-input", Input)
            reason_widget = self.query_one("#reason-input", Input)

            self.new_value = new_value_widget.value.strip()
            self.reason = reason_widget.value.strip()

            # Validate that fields are not empty
            if not self.new_value:
                self.app.notify("New decision content cannot be empty", timeout=3, severity="error")
                return
            if not self.reason:
                self.app.notify("Reason for override cannot be empty", timeout=3, severity="error")
                return

            self.step = 3
            self.refresh_wizard()
        elif button_id == "replan-toggle":
            self.auto_replan = not self.auto_replan
            # Update button text and appearance
            replan_text = "Auto Replan: ON" if self.auto_replan else "Auto Replan: OFF"
            event.button.label = replan_text
            event.button.variant = "success" if self.auto_replan else "default"
        elif button_id == "review-back-button":
            self.step = 2
            self.refresh_wizard()
        elif button_id == "review-cancel-button":
            self.dismiss({"cancelled": True})
        elif button_id == "apply-button":
            # Apply the override
            result = {
                "old_decision_id": self.decision['id'],
                "new_value": self.new_value,
                "reason": self.reason,
                "auto_replan": self.auto_replan,
                "action": "apply_override"
            }
            self.dismiss(result)

    def refresh_wizard(self) -> None:
        """Refresh the wizard UI to reflect the current step."""
        # Remove current content and rebuild
        container = self.query_one("#decision-override-wizard-container", Vertical)
        container.remove_children()
        # Re-compose the content
        self.compose()
        # Reset focus as needed
        if self.step == 2:
            self.call_after_refresh(lambda: self.query_one("#new-value-input", Input).focus())
        elif self.step == 3:
            self.call_after_refresh(lambda: self.query_one("#apply-button", Button).focus())