"""
Status line for MC2 Curses TUI
"""
import curses
import time
from typing import Optional


class StatusLine:
    def __init__(self, window, context):
        self.window = window
        self.context = context
        self.default_ttl = 3.0  # seconds
        self.message_expires_at = None
        self.current_message = ""
        self.debug_enabled = False
        self.debug_info = ""
        self.default_hints = "Tab=Switch | Enter=Open | Esc=Back | F1=Help | F5=Refresh | F7=New | F8=Delete | F9=Menu | F10=Quit"

    def set_window(self, window):
        """Update the curses window for the status line."""
        self.window = window
    
    def set_message(self, message: str, ttl: Optional[float] = None):
        """Set a status message with optional timeout"""
        self.current_message = message or ""
        if ttl is not None:
            self.message_expires_at = time.time() + ttl
        else:
            self.message_expires_at = None

    def set_debug_info(self, enabled: bool, info: str):
        """Set debug text for render diagnostics."""
        self.debug_enabled = enabled
        self.debug_info = info

    def has_active_ttl(self) -> bool:
        """Return True if there's an active expiring status message."""
        return self.message_expires_at is not None and bool(self.current_message)

    def time_until_expire(self, now: float) -> Optional[float]:
        """Return seconds until expiry for active message, else None."""
        if not self.has_active_ttl():
            return None
        return max(0.0, self.message_expires_at - now)

    def maybe_expire(self, now: float) -> bool:
        """Expire the current message if its TTL has elapsed."""
        if self.message_expires_at is None:
            return False
        if now >= self.message_expires_at and self.current_message:
            self.current_message = ""
            self.message_expires_at = None
            return True
        return False
    
    def render(self):
        """Render the status line"""
        self.window.erase()
        height, width = self.window.getmaxyx()
        
        # Initialize color pair for status line
        if curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(2))
        
        # Prepare the status text
        status_text = self.current_message
        if not status_text and self.debug_enabled and self.debug_info:
            status_text = self.debug_info
        if not status_text:
            filter_text = getattr(self.context, "sessions_filter_text", "")
            visible = getattr(self.context, "sessions_filter_visible", 0)
            total = getattr(self.context, "sessions_filter_total", 0)
            if filter_text or total:
                status_text = f'Filter: "{filter_text}" | {visible} shown / {total} total'
        
        # Add focus indicator
        focus_indicator = f"FOCUS: {self.context.focus_pane.upper()}"
        
        # Add active session info
        session_info = f"Session: {self.context.active_session_id or 'None'}"
        
        # Combine all elements
        left_part = f"{status_text}"
        right_part = f"{focus_indicator} | {session_info}"
        
        # Calculate available space
        total_len = len(left_part) + len(right_part) + 3  # 3 for separator
        if total_len <= width:
            # Enough space for both parts
            try:
                self.window.addstr(0, 0, left_part)
                self.window.addstr(0, max(0, width - len(right_part)), right_part)
            except:
                pass
        else:
            # Not enough space, prioritize left part (status message)
            available = max(0, width - len(right_part) - 3)
            if available > 0:
                try:
                    self.window.addstr(0, 0, left_part[:available])
                    self.window.addstr(0, max(0, width - len(right_part)), right_part)
                except:
                    pass
            else:
                # Only show right part if no space for left
                try:
                    self.window.addstr(0, max(0, width - len(right_part)), right_part)
                except:
                    pass
        
        # Add default hints if no message/debug info/filter is shown
        if not status_text:
            hints = self.default_hints
            if len(hints) <= width:
                try:
                    self.window.addstr(0, 0, hints[:width])
                except:
                    pass
            else:
                try:
                    self.window.addstr(0, 0, hints[:width])
                except:
                    pass
        
        self.window.noutrefresh()
