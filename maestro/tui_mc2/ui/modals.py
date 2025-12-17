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
        except Exception:
            self.result = None
        
        # Clean up - delete the modal window
        del modal_win
        
        return self.result


class ConfirmModal:
    def __init__(self, parent_window, title: str, message_lines: List[str], default_yes: bool = True):
        self.parent_window = parent_window
        self.title = title
        self.message_lines = message_lines
        self.default_yes = default_yes
        self.result: Optional[bool] = None

    def show(self) -> bool:
        """Show confirm modal and return True if confirmed."""
        parent_height, parent_width = self.parent_window.getmaxyx()
        content_width = max([len(self.title)] + [len(line) for line in self.message_lines] + [12])
        modal_width = min(parent_width - 2, max(content_width + 4, 36))
        modal_height = min(parent_height - 2, len(self.message_lines) + 6)

        start_y = (parent_height - modal_height) // 2
        start_x = (parent_width - modal_width) // 2

        modal_win = curses.newwin(modal_height, modal_width, start_y, start_x)
        modal_win.keypad(True)
        if curses.has_colors():
            modal_win.bkgd(' ', curses.color_pair(3))

        modal_win.border()
        title_x = (modal_width - len(self.title)) // 2
        if 0 < title_x < modal_width - 1:
            try:
                modal_win.addstr(1, title_x, self.title, curses.A_BOLD)
            except Exception:
                pass

        for idx, line in enumerate(self.message_lines):
            row = 2 + idx
            if row >= modal_height - 2:
                break
            try:
                modal_win.addstr(row, 2, line[: modal_width - 4])
            except Exception:
                pass

        button_row = modal_height - 2
        buttons = " Yes / No "
        try:
            modal_win.addstr(button_row, max(1, (modal_width - len(buttons)) // 2), buttons, curses.A_BOLD)
        except Exception:
            pass

        modal_win.noutrefresh()
        self.parent_window.noutrefresh()
        curses.doupdate()

        while True:
            try:
                key = modal_win.getch()
            except Exception:
                self.result = False
                break

            if key in (27,):  # ESC
                self.result = False
                break
            if key in (10, 13):  # Enter
                self.result = True if self.default_yes else False
                break
            if key in (ord('y'), ord('Y')):
                self.result = True
                break
            if key in (ord('n'), ord('N')):
                self.result = False
                break

        del modal_win
        return bool(self.result)


class InputModal:
    def __init__(self, parent_window, title: str, prompt: str, default: str = ""):
        self.parent_window = parent_window
        self.title = title
        self.prompt = prompt
        self.default = default
        self.result: Optional[str] = None

    def show(self) -> Optional[str]:
        """Show input modal and return the entered text."""
        parent_height, parent_width = self.parent_window.getmaxyx()

        modal_height = 7
        modal_width = max(len(self.prompt) + 10, len(self.title) + 10, 40)
        modal_width = min(modal_width, parent_width - 2)

        start_y = (parent_height - modal_height) // 2
        start_x = (parent_width - modal_width) // 2

        modal_win = curses.newwin(modal_height, modal_width, start_y, start_x)
        modal_win.keypad(True)

        if curses.has_colors():
            modal_win.bkgd(' ', curses.color_pair(3))

        modal_win.border()

        title_x = (modal_width - len(self.title)) // 2
        if 0 < title_x < modal_width - 1:
            try:
                modal_win.addstr(1, title_x, self.title, curses.A_BOLD)
            except Exception:
                pass

        try:
            modal_win.addstr(2, 2, self.prompt[: modal_width - 4])
        except Exception:
            pass

        input_x = 2
        input_y = 3
        input_width = modal_width - 4
        input_value = self.default or ""

        def _draw_input(value: str) -> None:
            try:
                modal_win.addstr(input_y, input_x, " " * input_width, curses.A_REVERSE)
                modal_win.addstr(input_y, input_x, value[:input_width], curses.A_REVERSE)
            except Exception:
                pass

        _draw_input(input_value)

        try:
            curses.curs_set(1)
        except Exception:
            pass

        modal_win.noutrefresh()
        self.parent_window.noutrefresh()
        curses.doupdate()

        while True:
            try:
                modal_win.move(input_y, min(input_x + len(input_value), input_x + input_width - 1))
            except Exception:
                pass

            try:
                key = modal_win.getch()
            except Exception:
                self.result = None
                break

            if key in (27,):  # ESC
                self.result = None
                break
            if key in (10, 13):  # Enter
                self.result = input_value
                break
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if input_value:
                    input_value = input_value[:-1]
                    _draw_input(input_value)
                continue
            if 0 <= key <= 255:
                ch = chr(key)
                if ch.isprintable():
                    if len(input_value) < input_width:
                        input_value += ch
                        _draw_input(input_value)
                continue

        try:
            curses.curs_set(0)
        except Exception:
            pass

        del modal_win
        return self.result
