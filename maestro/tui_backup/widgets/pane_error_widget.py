"""
Pane error widget for Maestro TUI.
"""
from __future__ import annotations

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Button
from textual.message import Message


class PaneRetryRequest(Message):
    """Message to request pane retry."""
    
    def __init__(self, pane_id: str) -> None:
        super().__init__()
        self.pane_id = pane_id


class PaneErrorWidget(Vertical):
    """Widget to display pane errors with retry option."""
    
    def __init__(self, error_message: str, error_exception: Optional[Exception] = None, pane_id: str = "unknown") -> None:
        super().__init__()
        self.error_message = error_message
        self.error_exception = error_exception
        self.pane_id = pane_id

    def compose(self) -> ComposeResult:
        yield Label(f"[RED]Pane Error:[/RED] {self.error_message}", id="error-message")
        yield Button("Retry", variant="primary", id="retry-button")

    def on_mount(self) -> None:
        """Set up event handlers after widget is mounted."""
        # Bind the retry button click
        retry_btn = self.query_one("#retry-button", Button)
        retry_btn.on_click = lambda _: self.post_message(PaneRetryRequest(self.pane_id))