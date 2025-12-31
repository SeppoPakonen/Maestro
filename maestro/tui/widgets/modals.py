"""
Reusable Modal Widgets for Maestro TUI
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, TextArea
from textual.containers import Vertical, Horizontal
from textual import events


class ConfirmDialog(ModalScreen[bool]):
    """A confirmation dialog modal."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("left", "focus_prev_button", "Prev button"),
        Binding("right", "focus_next_button", "Next button"),
        Binding("tab", "focus_next_button", "Next button"),
        Binding("shift+tab", "focus_prev_button", "Prev button"),
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

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation."""
        # Arrow keys for button selection
        if event.key in ["left", "right"]:
            current = self.focused
            buttons = self.query("Button").results()
            if current in buttons and len(buttons) > 1:
                idx = buttons.index(current)
                if event.key == "right":
                    next_idx = (idx + 1) % len(buttons)
                else:  # left
                    next_idx = (idx - 1) % len(buttons)
                buttons[next_idx].focus()
                event.stop()

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

    def action_focus_next_button(self) -> None:
        """Move focus to next button."""
        current = self.focused
        buttons = self.query("Button").results()
        if current in buttons and len(buttons) > 1:
            idx = buttons.index(current)
            next_idx = (idx + 1) % len(buttons)
            buttons[next_idx].focus()
        elif buttons:
            buttons[0].focus()

    def action_focus_prev_button(self) -> None:
        """Move focus to previous button."""
        current = self.focused
        buttons = self.query("Button").results()
        if current in buttons and len(buttons) > 1:
            idx = buttons.index(current)
            prev_idx = (idx - 1) % len(buttons)
            buttons[prev_idx].focus()
        elif buttons:
            buttons[-1].focus()


class InputDialog(ModalScreen[str]):
    """An input dialog modal."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Submit"),
        ("tab", "focus_next_field", "Next field"),
        ("shift+tab", "focus_prev_field", "Prev field"),
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

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation."""
        # Handle Tab navigation between input and buttons
        if event.key in ["tab"]:
            if not event.shift:
                self.action_focus_next_field()
            else:
                self.action_focus_prev_field()
            event.stop()

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

    def action_focus_next_field(self) -> None:
        """Move focus to next field."""
        current = self.focused
        input_field = self.query_one("#input-field", Input)
        buttons = self.query("Button").results()

        if current == input_field and buttons:
            buttons[0].focus()  # Focus first button
        elif current in buttons and current != buttons[-1]:
            # Move to next button if exists
            idx = buttons.index(current)
            if idx + 1 < len(buttons):
                buttons[idx + 1].focus()
        else:
            # If at last button or no other elements, go back to first
            input_field.focus()

    def action_focus_prev_field(self) -> None:
        """Move focus to previous field."""
        current = self.focused
        input_field = self.query_one("#input-field", Input)
        buttons = self.query("Button").results()

        if current in buttons and current != buttons[0]:
            # Move to previous button if exists
            idx = buttons.index(current)
            if idx - 1 >= 0:
                buttons[idx - 1].focus()
        elif current in buttons and current == buttons[0]:
            # If at first button, go back to input
            input_field.focus()
        else:
            # If at input field or no other elements, go to last button
            if buttons:
                buttons[-1].focus()


class DecisionOverrideWizard(ModalScreen[dict]):
    """A 3-step wizard for overriding conversion decisions."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("tab", "focus_next_field", "Next field"),
        ("shift+tab", "focus_prev_field", "Prev field"),
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
        container = Vertical(id="decision-override-wizard-container")
        self._populate_wizard_content(container)
        yield container

    def _populate_wizard_content(self, container: Vertical) -> None:
        """Populate the wizard container based on the current step."""
        container.remove_children()

        # Step indicator
        container.mount(Label(f"Step {self.step} of 3", id="step-indicator"))

        # Content based on current step
        if self.step == 1:
            container.mount(Label(f"Decision ID: {self.decision['id']}", id="decision-id"))
            container.mount(Label(f"Title: {self.decision['title']}", id="decision-title"))

            current_value = self.decision.get('value', self.decision.get('reason', 'No description available'))
            container.mount(Label("Current Value:", id="current-value-label"))
            container.mount(Label(current_value, id="current-value", classes="decision-content"))

            container.mount(Label("WARNING: Overrides supersede, never delete", id="warning-label", classes="warning"))
            container.mount(Label("Proceed with override?", id="confirm-prompt"))

            buttons = Horizontal(id="step1-buttons")
            buttons.mount(Button("Cancel", variant="default", id="cancel-button"))
            buttons.mount(Button("No", variant="default", id="no-button"))
            buttons.mount(Button("Yes, Proceed", variant="primary", id="yes-button"))
            container.mount(buttons)

        elif self.step == 2:
            container.mount(Label(f"Editing Decision: {self.decision['id']}", id="edit-title"))
            container.mount(Label("New Decision Content:", id="new-value-label"))

            container.mount(Input(placeholder="Enter the new decision content/value", id="new-value-input"))

            container.mount(Label("Reason for Override (required):", id="reason-label"))
            container.mount(Input(placeholder="Provide a reason for this override", id="reason-input"))

            container.mount(Label("Auto Replan After Override:", id="replan-label"))
            replan_text = "ON" if self.auto_replan else "OFF"
            container.mount(Button(f"Auto Replan: {replan_text}", variant="success" if self.auto_replan else "default", id="replan-toggle"))

            buttons = Horizontal(id="step2-buttons")
            buttons.mount(Button("Back", variant="default", id="back-button"))
            buttons.mount(Button("Continue", variant="primary", id="continue-button"))
            container.mount(buttons)

        elif self.step == 3:
            container.mount(Label("Review Override", id="review-title"))
            container.mount(Label(f"Decision: {self.decision['id']}", id="review-decision-id"))
            container.mount(Label(f"Old Value: {self.decision.get('value', self.decision.get('reason', 'No description'))}", id="old-value"))
            container.mount(Label(f"New Value: {self.new_value}", id="new-value"))
            container.mount(Label(f"Reason: {self.reason}", id="reason-review"))
            container.mount(Label(f"Auto Replan: {'YES' if self.auto_replan else 'NO'}", id="replan-review"))

            buttons = Horizontal(id="step3-buttons")
            buttons.mount(Button("Back", variant="default", id="review-back-button"))
            buttons.mount(Button("Cancel", variant="default", id="review-cancel-button"))
            buttons.mount(Button("Apply Override", variant="warning", id="apply-button"))
            container.mount(buttons)

        # Navigation indicators
        indicators = Horizontal(id="wizard-nav-indicators")
        for step_idx in (1, 2, 3):
            step_class = "active" if self.step == step_idx else "inactive"
            indicators.mount(Label("●", classes=step_class, id=f"nav-step{step_idx}"))
        container.mount(indicators)

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
        container = self.query_one("#decision-override-wizard-container", Vertical)
        self._populate_wizard_content(container)

        # Reset focus as needed
        if self.step == 2:
            self.call_after_refresh(lambda: self.query_one("#new-value-input", Input).focus())
        elif self.step == 3:
            self.call_after_refresh(lambda: self.query_one("#apply-button", Button).focus())

    def action_focus_next_field(self) -> None:
        """Move focus to next field based on current step."""
        if self.step == 1:
            # Step 1: Only buttons available
            current = self.focused
            buttons = self.query("Button").results()
            if current in buttons and len(buttons) > 1:
                idx = buttons.index(current)
                next_idx = (idx + 1) % len(buttons)
                buttons[next_idx].focus()
            elif buttons:
                buttons[0].focus()
        elif self.step == 2:
            # Step 2: Input fields and buttons
            current = self.focused
            new_value_input = self.query_one("#new-value-input", Input) if self.query("#new-value-input") else None
            reason_input = self.query_one("#reason-input", Input) if self.query("#reason-input") else None
            replan_button = self.query_one("#replan-toggle", Button) if self.query("#replan-toggle") else None
            back_button = self.query_one("#back-button", Button) if self.query("#back-button") else None
            continue_button = self.query_one("#continue-button", Button) if self.query("#continue-button") else None

            all_widgets = [w for w in [new_value_input, reason_input, replan_button, back_button, continue_button] if w is not None]
            if current in all_widgets:
                idx = all_widgets.index(current)
                next_idx = (idx + 1) % len(all_widgets)
                all_widgets[next_idx].focus()
            elif all_widgets:
                all_widgets[0].focus()
        elif self.step == 3:
            # Step 3: Buttons only
            current = self.focused
            buttons = self.query("Button").results()
            if current in buttons and len(buttons) > 1:
                idx = buttons.index(current)
                next_idx = (idx + 1) % len(buttons)
                buttons[next_idx].focus()
            elif buttons:
                buttons[0].focus()

    def action_focus_prev_field(self) -> None:
        """Move focus to previous field based on current step."""
        if self.step == 1:
            # Step 1: Only buttons available
            current = self.focused
            buttons = self.query("Button").results()
            if current in buttons and len(buttons) > 1:
                idx = buttons.index(current)
                prev_idx = (idx - 1) % len(buttons)
                buttons[prev_idx].focus()
            elif buttons:
                buttons[-1].focus()  # Last button
        elif self.step == 2:
            # Step 2: Input fields and buttons
            current = self.focused
            new_value_input = self.query_one("#new-value-input", Input) if self.query("#new-value-input") else None
            reason_input = self.query_one("#reason-input", Input) if self.query("#reason-input") else None
            replan_button = self.query_one("#replan-toggle", Button) if self.query("#replan-toggle") else None
            back_button = self.query_one("#back-button", Button) if self.query("#back-button") else None
            continue_button = self.query_one("#continue-button", Button) if self.query("#continue-button") else None

            all_widgets = [w for w in [new_value_input, reason_input, replan_button, back_button, continue_button] if w is not None]
            if current in all_widgets:
                idx = all_widgets.index(current)
                prev_idx = (idx - 1) % len(all_widgets)
                all_widgets[prev_idx].focus()
            elif all_widgets:
                all_widgets[-1].focus()  # Last widget
        elif self.step == 3:
            # Step 3: Buttons only
            current = self.focused
            buttons = self.query("Button").results()
            if current in buttons and len(buttons) > 1:
                idx = buttons.index(current)
                prev_idx = (idx - 1) % len(buttons)
                buttons[prev_idx].focus()
            elif buttons:
                buttons[-1].focus()  # Last button
