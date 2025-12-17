"""
Status line for MC2 Curses TUI
"""
import curses
from typing import Optional


class StatusLine:
    def __init__(self, window, context):
        self.window = window
        self.context = context
        self.message_timeout = 3.0  # seconds
        self.message_start_time = 0
        self.current_message = ""
        self.default_hints = "Tab=Switch | Enter=Open | Esc=Back | F1=Help | F5=Refresh | F7=New | F8=Delete | F9=Menu | F10=Quit"
    
    def set_message(self, message: str, ttl: Optional[float] = None):
        """Set a status message with optional timeout"""
        self.current_message = message
        if ttl is not None:
            self.message_timeout = ttl
            self.message_start_time = __import__('time').time()
        else:
            # Don't auto-clear if no TTL specified
            self.message_start_time = 0
    
    def render(self):
        """Render the status line"""
        self.window.clear()
        height, width = self.window.getmaxyx()
        
        # Initialize color pair for status line
        if curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(2))
        
        # Prepare the status text
        current_time = __import__('time').time()
        elapsed = current_time - self.message_start_time if self.message_start_time > 0 else float('inf')
        
        # Use custom message if it's still active, otherwise use default
        if elapsed < self.message_timeout:
            status_text = self.current_message
        else:
            status_text = self.current_message  # Keep showing the last message even after TTL
            # Reset to empty to show default hints again
            if elapsed >= self.message_timeout:
                status_text = ""
        
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
        
        # Add default hints at the bottom if no message or space allows
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
        
        self.window.refresh()