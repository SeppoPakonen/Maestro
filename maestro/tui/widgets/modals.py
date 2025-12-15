"""
Reusable Modal Widgets for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input
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