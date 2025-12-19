"""
Single-line status line widget for MC shell footer.
"""
from __future__ import annotations

import time
from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class StatusLine(Widget):
    """A single-line status footer for MC shell."""

    DEFAULT_CSS = """
    StatusLine {
        height: 1;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
        content-align: left middle;
    }
    
    #status-hints {
        width: 60%;
        content-align: left middle;
    }
    
    #status-focus {
        width: 20%;
        content-align: center middle;
        text-style: bold;
    }
    
    #status-message {
        width: 20%;
        content-align: right middle;
        color: $text 80%;
    }
    """

    # Reactive attributes
    message: reactive[str] = reactive("")
    focus_indicator: reactive[str] = reactive("FOCUS: LEFT")
    hints: reactive[str] = reactive("")
    sticky_status: reactive[str] = reactive("")
    
    def __init__(
        self, 
        initial_message: str = "Ready", 
        initial_hints: str = "", 
        initial_focus: str = "FOCUS: LEFT",
        initial_sticky_status: str = "",
        id: Optional[str] = None
    ) -> None:
        super().__init__(id=id)
        self.message = initial_message
        self.hints = initial_hints
        self.focus_indicator = initial_focus
        self.sticky_status = initial_sticky_status
        self._message_ttl: Optional[float] = None
        self._original_sticky_status: str = initial_sticky_status
        
    def compose(self) -> ComposeResult:
        """Compose the status line."""
        with Horizontal():
            yield Label(self.hints or "F9 Menu | Tab Switch | Enter Open", id="status-hints")
            yield Label(self.focus_indicator, id="status-focus")
            yield Label(self._current_message(), id="status-message")
            
    def set_message(self, text: str, kind: str = "info", ttl: Optional[float] = None) -> None:
        """Set a transient message with optional TTL.
        
        Args:
            text: The message text to display
            kind: Type of message (info, warning, error) - affects styling
            ttl: Time to live in seconds before auto-clearing (None = no auto-clear)
        """
        self.message = text
        if ttl is not None:
            self._message_ttl = time.time() + ttl
        else:
            self._message_ttl = None
            
        # Update the message label
        if self.is_mounted:
            msg_label = self.query_one("#status-message", Label)
            msg_label.update(self._current_message())
            
    def set_sticky_status(self, text: str) -> None:
        """Set the persistent status text (like session/plan/build info)."""
        self.sticky_status = text
        self._original_sticky_status = text
        if self.is_mounted:
            msg_label = self.query_one("#status-message", Label)
            msg_label.update(self._current_message())
    
    def set_hints(self, text: str) -> None:
        """Set the hints portion of the status line."""
        self.hints = text
        if self.is_mounted:
            hints_label = self.query_one("#status-hints", Label)
            hints_label.update(text or "F9 Menu | Tab Switch | Enter Open")
    
    def set_focus_indicator(self, text: str) -> None:
        """Set the focus indicator portion."""
        self.focus_indicator = text
        if self.is_mounted:
            focus_label = self.query_one("#status-focus", Label)
            focus_label.update(text)
    
    def _current_message(self) -> str:
        """Get the current effective message (transient takes priority)."""
        if self.message and self._message_ttl is not None:
            if time.time() > self._message_ttl:
                # TTL expired, clear message and return sticky status
                self.message = ""
                self._message_ttl = None
                return self.sticky_status or "Ready"
            return self.message
        elif self.message:
            return self.message
        else:
            return self.sticky_status or "Ready"
    
    def update_displays(self) -> None:
        """Manually update all status line components."""
        if not self.is_mounted:
            return
            
        hints_label = self.query_one("#status-hints", Label)
        focus_label = self.query_one("#status-focus", Label)
        msg_label = self.query_one("#status-message", Label)
        
        hints_label.update(self.hints or "F9 Menu | Tab Switch | Enter Open")
        focus_label.update(self.focus_indicator)
        msg_label.update(self._current_message())
    
    def on_mount(self) -> None:
        """Initialize the status line displays."""
        self.update_displays()
    
    def tick(self) -> None:
        """Call this periodically to handle message TTL expiration."""
        if self._message_ttl is not None and time.time() > self._message_ttl:
            self.message = ""
            self._message_ttl = None
            if self.is_mounted:
                msg_label = self.query_one("#status-message", Label)
                msg_label.update(self._current_message())
                
    def clear_transient_message(self) -> None:
        """Clear any current transient message, revealing the sticky status."""
        self.message = ""
        self._message_ttl = None
        if self.is_mounted:
            msg_label = self.query_one("#status-message", Label)
            msg_label.update(self._current_message())