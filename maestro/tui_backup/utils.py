"""
Utilities for Maestro TUI - Loading states, Error handling, Performance, and UX Trust Signals
"""
import os
import sys
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from textual.widgets import Label, Button, Static, Switch, Input
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import on
from maestro.ui_facade.utils import (
    GlobalStatusManager,
    LoadingIndicator,
    global_status_manager,
    memoization_cache,
    memoize_for,
    track_facade_call,
)


class ErrorSeverity(Enum):
    """Severity levels for error presentation."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class ErrorMessage:
    """Normalized error message structure."""
    title: str
    severity: ErrorSeverity
    message: str
    technical_details: Optional[str] = None
    actionable_hint: Optional[str] = None


def write_smoke_success(smoke_out: Optional[str] = None) -> None:
    """Persist and print a consistent smoke-test success marker."""
    smoke_success_file = smoke_out or os.environ.get("MAESTRO_SMOKE_SUCCESS_FILE", "/tmp/maestro_tui_smoke_success")
    try:
        with open(smoke_success_file, "w") as file_handle:
            file_handle.write("MAESTRO_TUI_SMOKE_OK\n")
    except Exception:
        # File writes may fail in restricted environments; stdout still carries the marker.
        pass

    print("MAESTRO_TUI_SMOKE_OK", flush=True)
    sys.stdout.flush()


class ErrorModal(ModalScreen[bool]):
    """A modal for displaying normalized error messages."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("enter", "dismiss", "Close"),
        ("tab", "focus_next_field", "Next field"),
        ("shift+tab", "focus_prev_field", "Prev field"),
    ]

    def __init__(self, error_msg: ErrorMessage):
        super().__init__()
        self.error_msg = error_msg
        # Track whether technical details should be shown
        self.show_technical_details = False

    def compose(self) -> "ComposeResult":
        """Create child widgets for the error modal."""
        with Vertical(id="error-modal-container"):
            # Header with severity-appropriate styling
            title_text = f"{self.error_msg.severity.value.upper()}: {self.error_msg.title}"
            yield Label(title_text, id="error-title")
            yield Label(self.error_msg.message, id="error-message")

            # Add actionable hint if available
            if self.error_msg.actionable_hint:
                yield Label(f"[bold]Hint:[/bold] {self.error_msg.actionable_hint}", id="actionable-hint")

            # Button to show technical details
            if self.error_msg.technical_details:
                with Horizontal(id="details-controls"):
                    yield Button("Show Technical Details", variant="default", id="toggle-details")

            # Technical details section (initially hidden)
            if self.error_msg.technical_details:
                details = Static(self.error_msg.technical_details, id="technical-details")
                details.display = False
                yield details

            with Horizontal(id="error-buttons"):
                yield Button("OK", variant="primary", id="ok-button")

    def on_mount(self) -> None:
        """Focus the OK button when mounted."""
        self.query_one("#ok-button").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "ok-button":
            self.dismiss(True)
        elif event.button.id == "toggle-details":
            self.toggle_technical_details()

    def toggle_technical_details(self):
        """Toggle the visibility of technical details."""
        details_container = self.query_one("#technical-details", Static)
        toggle_button = self.query_one("#toggle-details", Button)

        self.show_technical_details = not self.show_technical_details
        details_container.visible = self.show_technical_details

        if self.show_technical_details:
            toggle_button.label = "Hide Technical Details"
        else:
            toggle_button.label = "Show Technical Details"

    def action_dismiss(self) -> None:
        """Action to dismiss the modal."""
        self.dismiss(True)

    def action_focus_next_field(self) -> None:
        """Move focus to next field."""
        current = self.focused
        ok_button = self.query_one("#ok-button", Button)
        toggle_button = self.query_one("#toggle-details", Button) if self.query("#toggle-details") else None

        all_buttons = [b for b in [toggle_button, ok_button] if b is not None]

        if current in all_buttons:
            idx = all_buttons.index(current)
            next_idx = (idx + 1) % len(all_buttons)
            all_buttons[next_idx].focus()
        elif all_buttons:
            all_buttons[0].focus()  # Focus first available button

    def action_focus_prev_field(self) -> None:
        """Move focus to previous field."""
        current = self.focused
        ok_button = self.query_one("#ok-button", Button)
        toggle_button = self.query_one("#toggle-details", Button) if self.query("#toggle-details") else None

        all_buttons = [b for b in [toggle_button, ok_button] if b is not None]

        if current in all_buttons:
            idx = all_buttons.index(current)
            prev_idx = (idx - 1) % len(all_buttons)
            all_buttons[prev_idx].focus()
        elif all_buttons:
            all_buttons[-1].focus()  # Focus last available button


class ErrorNormalizer:
    """Normalizes errors from various facade calls."""

    @staticmethod
    def normalize_exception(exc: Exception, context: str = "") -> ErrorMessage:
        """Convert an exception to a normalized ErrorMessage."""
        # Map specific exception types to appropriate severities and messages
        if isinstance(exc, FileNotFoundError):
            return ErrorMessage(
                title="File Not Found",
                severity=ErrorSeverity.BLOCKED,
                message=f"The required file could not be found: {str(exc)}",
                actionable_hint="Check that the specified file exists and is accessible."
            )
        elif isinstance(exc, PermissionError):
            return ErrorMessage(
                title="Permission Denied",
                severity=ErrorSeverity.BLOCKED,
                message=f"Access to the required resource was denied: {str(exc)}",
                actionable_hint="Verify that you have the necessary permissions to access this resource."
            )
        elif isinstance(exc, ValueError):
            return ErrorMessage(
                title="Invalid Value",
                severity=ErrorSeverity.WARNING,
                message=str(exc),
                actionable_hint="Check the input values and try again."
            )
        elif isinstance(exc, ConnectionError):
            return ErrorMessage(
                title="Connection Error",
                severity=ErrorSeverity.ERROR,
                message="Failed to connect to the required service.",
                actionable_hint="Check your network connection and try again."
            )
        else:
            # Default error message for unknown exceptions
            return ErrorMessage(
                title="Operation Failed",
                severity=ErrorSeverity.ERROR,
                message=str(exc) or f"An error occurred during {context}.",
                technical_details=str(type(exc).__name__),
                actionable_hint="Try again or check logs for more details."
            )


class InputModal(ModalScreen[str]):
    """A modal for getting text input from the user."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Submit"),
        ("tab", "focus_next_field", "Next field"),
        ("shift+tab", "focus_prev_field", "Prev field"),
    ]

    def __init__(self, title: str = "Input", prompt: str = "Enter value:", submit_label: str = "Submit", cancel_label: str = "Cancel"):
        super().__init__()
        self.title_text = title
        self.prompt_text = prompt
        self.submit_label = submit_label
        self.cancel_label = cancel_label
        self.submitted_value = ""

    def compose(self) -> "ComposeResult":
        """Create child widgets for the input modal."""
        with Vertical(id="input-modal-container"):
            yield Label(self.title_text, id="input-title")
            yield Label(self.prompt_text, id="input-prompt")

            yield Input(placeholder="Type your response...", id="input-field")

            with Horizontal(id="input-buttons"):
                yield Button(self.submit_label, variant="primary", id="submit-button")
                yield Button(self.cancel_label, variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Focus the input field when mounted."""
        self.query_one("#input-field", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-button":
            self.action_submit()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.action_submit()

    def action_submit(self) -> None:
        """Action to submit the input."""
        input_widget = self.query_one("#input-field", Input)
        self.submitted_value = input_widget.value.strip()
        if self.submitted_value:
            self.dismiss(self.submitted_value)
        else:
            # If no value, still dismiss but with empty string
            self.dismiss(self.submitted_value)

    def action_cancel(self) -> None:
        """Action to cancel the input."""
        self.dismiss(None)  # Return None to indicate cancellation

    def action_focus_next_field(self) -> None:
        """Move focus to next field."""
        current = self.focused
        input_field = self.query_one("#input-field", Input)
        submit_button = self.query_one("#submit-button", Button)
        cancel_button = self.query_one("#cancel-button", Button)

        all_widgets = [input_field, submit_button, cancel_button]

        if current in all_widgets:
            idx = all_widgets.index(current)
            next_idx = (idx + 1) % len(all_widgets)
            all_widgets[next_idx].focus()
        else:
            input_field.focus()  # Focus input field if no match

    def action_focus_prev_field(self) -> None:
        """Move focus to previous field."""
        current = self.focused
        input_field = self.query_one("#input-field", Input)
        submit_button = self.query_one("#submit-button", Button)
        cancel_button = self.query_one("#cancel-button", Button)

        all_widgets = [input_field, submit_button, cancel_button]

        if current in all_widgets:
            idx = all_widgets.index(current)
            prev_idx = (idx - 1) % len(all_widgets)
            all_widgets[prev_idx].focus()
        else:
            cancel_button.focus()  # Focus last field if no match

