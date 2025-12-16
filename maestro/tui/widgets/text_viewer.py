"""
Simple text viewer modal for read-only content.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class TextViewerModal(ModalScreen[None]):
    """Minimal modal that renders read-only text content."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
        ("enter", "dismiss", "Close"),
    ]

    def __init__(self, title: str, body: str):
        super().__init__()
        self.title = title
        self.body = body

    def compose(self) -> ComposeResult:
        """Compose title, content, and close button."""
        with Vertical(id="text-viewer"):
            yield Label(f"[b]{self.title}[/b]")
            yield Static(self.body, id="text-viewer-body")
            yield Button("Close", id="text-viewer-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss the modal when the close button is pressed."""
        if event.button.id == "text-viewer-close":
            self.dismiss()

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.dismiss()
