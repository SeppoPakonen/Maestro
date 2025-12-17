"""
Modal dialogs for MC2 Curses TUI
"""
import curses
from typing import List, Optional, Union


class ModalDialog:
    def __init__(self, parent_window, title: str, content: Union[str, List[str]]):
        self.parent_window = parent_window
        self.title = title
        if isinstance(content, str):
            self.content = content.split('\n')
        else:
            self.content = content
        self.result: Optional[str] = None
    
    def show(self) -> Optional[str]:
        """Show the modal and return the result"""
        # Get parent window dimensions
        parent_height, parent_width = self.parent_window.getmaxyx()
        
        # Calculate modal dimensions (use 60% of parent size)
        modal_height = min(len(self.content) + 4, parent_height - 2)  # +4 for padding/title/border
        modal_width = min(max(len(self.title) + 4, max(len(line) for line in self.content) + 4), parent_width - 2)
        
        # Calculate position (centered)
        start_y = (parent_height - modal_height) // 2
        start_x = (parent_width - modal_width) // 2
        
        # Create modal window
        modal_win = curses.newwin(modal_height, modal_width, start_y, start_x)
        
        # Initialize color pair for modal
        if curses.has_colors():
            modal_win.bkgd(' ', curses.color_pair(3))
        
        # Draw border
        modal_win.border()
        
        # Add title
        title_x = (modal_width - len(self.title)) // 2
        if title_x > 0 and title_x + len(self.title) < modal_width - 1:
            try:
                modal_win.addstr(1, title_x, self.title, curses.A_BOLD)
            except:
                pass
        
        # Add content
        for i, line in enumerate(self.content):
            if 2 + i < modal_height - 1:  # Leave space for border
                line_x = 2  # Left padding
                try:
                    modal_win.addstr(2 + i, line_x, line[:modal_width - 4])  # -4 for borders
                except:
                    pass
        
        # Batch refresh to avoid flicker
        modal_win.noutrefresh()
        self.parent_window.noutrefresh()
        curses.doupdate()
        
        # Wait for user input
        try:
            key = modal_win.getch()
            self.result = chr(key) if 0 <= key <= 255 else str(key)
        except:
            self.result = None
        
        # Clean up - delete the modal window
        del modal_win
        
        return self.result


class InputModal:
    def __init__(self, parent_window, title: str, prompt: str, default: str = ""):
        self.parent_window = parent_window
        self.title = title
        self.prompt = prompt
        self.default = default
        self.result: Optional[str] = None
    
    def show(self) -> Optional[str]:
        """Show input modal and return the entered text"""
        # Get parent window dimensions
        parent_height, parent_width = self.parent_window.getmaxyx()
        
        # Calculate modal dimensions
        modal_height = 6  # Fixed height for input modal
        modal_width = max(len(self.prompt) + 10, len(self.title) + 10, 40)
        modal_width = min(modal_width, parent_width - 2)
        
        # Calculate position (centered)
        start_y = (parent_height - modal_height) // 2
        start_x = (parent_width - modal_width) // 2
        
        # Create modal window
        modal_win = curses.newwin(modal_height, modal_width, start_y, start_x)
        
        # Initialize color pair for modal
        if curses.has_colors():
            modal_win.bkgd(' ', curses.color_pair(3))
        
        # Draw border
        modal_win.border()
        
        # Add title
        title_x = (modal_width - len(self.title)) // 2
        if title_x > 0 and title_x + len(self.title) < modal_width - 1:
            try:
                modal_win.addstr(1, title_x, self.title, curses.A_BOLD)
            except:
                pass
        
        # Add prompt
        try:
            modal_win.addstr(2, 2, self.prompt)
        except:
            pass
        
        # Add input field
        input_x = 2
        input_y = 3
        input_width = modal_width - 4  # Leave space for borders
        
        # Show default value initially in reverse video
        input_value = self.default
        try:
            modal_win.addstr(input_y, input_x, input_value.ljust(input_width), curses.A_REVERSE)
        except:
            pass
            
        modal_win.noutrefresh()
        self.parent_window.noutrefresh()
        curses.doupdate()
        
        # Move cursor to input position and enable echoing
        modal_win.move(input_y, input_x)
        
        # Use nocbreak mode to enable line buffering
        curses.nocbreak()
        self.parent_window.keypad(False)
        curses.echo()
        
        try:
            # Get input from user
            input_value = modal_win.getstr(input_y, input_x, input_width - 1).decode('utf-8')
            self.result = input_value
        except:
            self.result = None
        finally:
            # Restore original settings
            curses.echo()
            curses.nocbreak()
            self.parent_window.keypad(True)
        
        # Clean up
        del modal_win
        
        return self.result
