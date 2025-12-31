"""
NCurses TUI Implementation for Qwen

This module implements the NCurses-based Terminal User Interface that was originally
in the C++ CmdQwen.cpp file. It provides an interactive chat interface with features
like scrollable history, tool approval, permission modes, and status bar.
"""
import curses
import curses.textpad
import threading
import time
import json
import os
import socket
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from maestro.qwen.main import QwenManager
from maestro.qwen.server import QwenInitMessage, QwenConversationMessage, QwenToolGroup, QwenStatusUpdate, QwenInfoMessage, QwenErrorMessage, QwenCompletionStats


@dataclass
class OutputLine:
    """Helper class to store colored output lines"""
    text: str
    color_pair: int = 0
    is_box_content: bool = False


class PermissionMode:
    """Permission modes for tool execution"""
    PLAN_MODE = "PLAN"
    NORMAL = "NORMAL"
    AUTO_ACCEPT_EDITS = "AUTO-EDIT"
    YOLO = "YOLO"


class UIState:
    """UI state for state machine"""
    NORMAL = "Normal"
    TOOL_APPROVAL = "ToolApproval"
    DISCUSS = "Discuss"


class QwenTUI:
    """NCurses-based Terminal User Interface for Qwen"""

    def __init__(self, manager: QwenManager):
        self.manager = manager
        self.output_buffer: List[OutputLine] = []
        self.scroll_offset = 0
        self.input_buffer = ""
        self.cursor_pos = 0
        self.ui_state = UIState.NORMAL
        self.permission_mode = PermissionMode.NORMAL
        self.pending_tool_group = None
        self.has_pending_tool_group = False
        self.context_usage_percent = 0
        self.should_exit = False
        self.streaming_in_progress = False
        self.streaming_buffer = ""

        # Message handlers for ncurses mode
        self.setup_handlers()

    def setup_handlers(self):
        """Setup message handlers for ncurses mode"""
        from maestro.qwen.client import MessageHandlers
        handlers = MessageHandlers()

        handlers.on_init = self._handle_init
        handlers.on_conversation = self._handle_conversation
        handlers.on_tool_group = self._handle_tool_group
        handlers.on_status = self._handle_status
        handlers.on_info = self._handle_info
        handlers.on_error = self._handle_error
        handlers.on_completion_stats = self._handle_completion_stats

        self.manager.client.set_handlers(handlers)

    def _handle_init(self, msg: QwenInitMessage):
        """Handle initialization message"""
        self.add_output_line("[Connected to qwen-code]", 5)
        if msg.version:
            self.add_output_line(f"[Version: {msg.version}]", 5)
        if msg.model:
            # Update session model from server
            self.add_output_line(f"[Model: {msg.model}]", 5)

    def _handle_conversation(self, msg: QwenConversationMessage):
        """Handle conversation messages"""
        if msg.role == 'user':
            self.streaming_in_progress = False
            self.streaming_buffer = ""
            self.add_output_line(f"You: {msg.content}", 1)
        elif msg.role == 'assistant':
            # Handle streaming messages
            if msg.isStreaming:
                if not self.streaming_in_progress:
                    self.streaming_in_progress = True
                    self.streaming_buffer = "AI: "
                self.streaming_buffer += msg.content

                # Update the last line in the buffer (or add if empty)
                if (self.output_buffer and
                    self.output_buffer[-1].text.startswith("AI: ")):
                    self.output_buffer[-1].text = self.streaming_buffer
                else:
                    self.add_output_line(self.streaming_buffer, 2)
            else:
                # End of streaming or non-streaming message
                if self.streaming_in_progress:
                    self.streaming_in_progress = False
                    self.streaming_buffer = ""
                elif msg.content:
                    # Add the AI response as box content for distinction
                    self.output_buffer.append(OutputLine("", 0))  # Empty line to separate
                    self.output_buffer.append(OutputLine(msg.content, 2, True))  # Mark as box content
        else:
            # For system messages, add as box content for distinction
            self.output_buffer.append(OutputLine(f"[system]: {msg.content}", 3, True))

    def _handle_tool_group(self, group: QwenToolGroup):
        """Handle tool group messages"""
        # Check permission mode for auto-approval
        auto_approve = False
        if self.permission_mode == PermissionMode.YOLO:
            auto_approve = True
        elif self.permission_mode == PermissionMode.AUTO_ACCEPT_EDITS:
            # Check if all tools are edit-related (simplified check)
            auto_approve = True  # For now, we'll always ask for approval in this simplified version

        # Display tool group in a box
        self.output_buffer.append(OutputLine("", 0))  # Empty line to separate
        self.output_buffer.append(OutputLine("[Tool Execution Request:]", 6, True))
        self.output_buffer.append(OutputLine(f"  Group ID: {group.id}", 6, True))

        for tool in group.tools:
            self.output_buffer.append(OutputLine(f"    - {tool.tool_name} (ID: {tool.tool_id})", 6, True))

            if tool.confirmation_details:
                self.output_buffer.append(OutputLine(
                    f"      Details: {tool.confirmation_details.get('message', '')}", 6, True))

            if tool.args:
                self.output_buffer.append(OutputLine("      Arguments:", 6, True))
                for key, value in tool.args.items():
                    self.output_buffer.append(OutputLine(f"        {key}: {value}", 6, True))

        if auto_approve:
            self.add_output_line("[Auto-approving tools based on permission mode]", 5)
            # Send approval for all tools
            for tool in group.tools:
                if self.manager.client:
                    self.manager.client.send_tool_approval(tool.tool_id, True)
        else:
            # Store for approval request
            self.pending_tool_group = group
            self.has_pending_tool_group = True
            self.ui_state = UIState.TOOL_APPROVAL

    def _handle_status(self, msg: QwenStatusUpdate):
        """Handle status updates"""
        status_line = f"[Status: {msg.state}"
        if msg.message:
            status_line += f" - {msg.message}"
        status_line += "]"
        self.output_buffer.append(OutputLine(status_line, 3, True))

    def _handle_info(self, msg: QwenInfoMessage):
        """Handle info messages"""
        info_line = f"[Info: {msg.message}]"
        self.output_buffer.append(OutputLine(info_line, 5, True))

    def _handle_error(self, msg: QwenErrorMessage):
        """Handle error messages"""
        error_line = f"[Error: {msg.message}]"
        self.output_buffer.append(OutputLine(error_line, 4, True))

    def _handle_completion_stats(self, stats: QwenCompletionStats):
        """Handle completion stats"""
        stats_line = "[Stats"
        if stats.prompt_tokens is not None:
            stats_line += f" - Prompt: {stats.prompt_tokens}"
        if stats.completion_tokens is not None:
            stats_line += f", Completion: {stats.completion_tokens}"
        if stats.duration:
            stats_line += f", Duration: {stats.duration}"
        stats_line += "]"
        self.output_buffer.append(OutputLine(stats_line, 3, True))

    def add_output_line(self, text: str, color: int = 0, box_content: bool = False):
        """Add a line to output buffer"""
        self.output_buffer.append(OutputLine(text, color, box_content))
        self.scroll_offset = 0  # Auto-scroll to bottom on new output

    def draw_rounded_box(self, win, y, x, height, width, color_pair, title=""):
        """Draw rounded bordered boxes with color"""
        if height < 2 or width < 4:
            return  # Minimum size to draw a box

        # Set color if available
        if curses.has_colors() and color_pair > 0:
            win.attron(curses.color_pair(color_pair))

        # Draw top border
        win.addch(y, x, curses.ACS_ULCORNER)  # ╭ or ┌
        win.addch(y, x + width - 1, curses.ACS_URCORNER)  # ╮ or ┐

        # Draw top horizontal line with optional title
        for i in range(1, width - 1):
            win.addch(y, x + i, curses.ACS_HLINE)  # ─

        # Add title if provided
        if title and len(title) + 4 < width:
            title_str = f" {title} "
            win.addstr(y, x + 2, title_str)

        # Draw sides and content area
        for i in range(1, height - 1):
            win.addch(y + i, x, curses.ACS_VLINE)  # │
            win.addch(y + i, x + width - 1, curses.ACS_VLINE)  # │

            # Clear the content area
            for j in range(1, width - 1):
                win.addch(y + i, x + j, ord(' '))

        # Draw bottom border
        win.addch(y + height - 1, x, curses.ACS_LLCORNER)  # ╰ or └
        win.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)  # ╯ or ┘

        for i in range(1, width - 1):
            win.addch(y + height - 1, x + i, curses.ACS_HLINE)  # ─

        # Reset attributes
        if curses.has_colors() and color_pair > 0:
            win.attroff(curses.color_pair(color_pair))

    def redraw_output(self, stdscr):
        """Redraw output window"""
        max_y, max_x = stdscr.getmaxyx()
        output_height = max_y - 4  # Leave room for input, status bar, and separator

        # Clear the output area
        for y in range(output_height):
            stdscr.move(y, 0)
            stdscr.clrtoeol()

        # Calculate which lines to display
        total_lines = len(self.output_buffer)
        start_line = max(0, total_lines - output_height - self.scroll_offset)
        end_line = min(total_lines, start_line + output_height)

        # Draw visible lines
        y_pos = 0
        current_line = start_line

        while y_pos < output_height and current_line < end_line:
            if current_line >= len(self.output_buffer):
                break

            line = self.output_buffer[current_line]

            if line.is_box_content:
                # Find the complete box by collecting all lines that belong to the same box
                box_lines = []
                box_start_line = current_line

                # Collect all consecutive box content lines
                while (current_line < end_line and
                       current_line < len(self.output_buffer) and
                       self.output_buffer[current_line].is_box_content):
                    text = self.output_buffer[current_line].text
                    max_line_width = max_x - 6  # Account for borders and margin

                    if len(text) <= max_line_width:
                        box_lines.append(text)
                    else:
                        # Wrap the line if it's too long
                        pos = 0
                        while pos < len(text):
                            length = min(max_line_width, len(text) - pos)
                            box_lines.append(text[pos:pos + length])
                            pos += length
                    current_line += 1

                # Calculate box dimensions
                box_height = len(box_lines) + 2  # +2 for top and bottom borders
                box_width = max_x - 2  # Leave margin

                # Adjust if box is too large
                if box_height > output_height - y_pos:
                    box_height = output_height - y_pos

                # Find the title for the box - look for context in previous lines
                title = "Response"
                if box_start_line > 0:
                    # Look back for context that would determine the title
                    search_back = min(5, box_start_line)
                    for i in range(box_start_line - 1, max(box_start_line - search_back, 0) - 1, -1):
                        prev_text = self.output_buffer[i].text
                        if "Tool Execution Request:" in prev_text:
                            title = "Tool Request"
                            break
                        elif "[Info:" in prev_text:
                            title = "Info"
                            break
                        elif "[Error:" in prev_text:
                            title = "Error"
                            break
                        elif "[Status:" in prev_text:
                            title = "Status"
                            break
                        # Check content type from the line itself
                        elif box_start_line < len(self.output_buffer):
                            if self.output_buffer[box_start_line].text.startswith("You:"):
                                title = "User Input"
                            elif self.output_buffer[box_start_line].text.startswith("AI:"):
                                title = "AI Response"
                            elif "[system]:" in self.output_buffer[box_start_line].text:
                                title = "System"

                # Draw the box with appropriate color based on content type
                box_color = line.color_pair
                if title == "Error":
                    box_color = 4  # Red for errors
                elif title == "Tool Request":
                    box_color = 6  # Magenta for tools
                elif title == "Info":
                    box_color = 5  # Blue for info
                elif title == "User Input":
                    box_color = 1  # Green for user
                elif title == "AI Response":
                    box_color = 2  # Cyan for AI

                # Draw the box
                self.draw_rounded_box(stdscr, y_pos, 1, box_height, box_width, box_color, title)

                # Add the box content lines inside the box
                for i, box_line in enumerate(box_lines):
                    if i + 1 >= box_height:
                        break
                    if curses.has_colors() and box_color > 0:
                        stdscr.attron(curses.color_pair(box_color))
                        stdscr.addstr(y_pos + 1 + i, 3, box_line)
                        stdscr.attroff(curses.color_pair(box_color))
                    else:
                        stdscr.addstr(y_pos + 1 + i, 3, box_line)

                y_pos += box_height
            else:
                # Regular line (not in a box)
                if curses.has_colors() and line.color_pair > 0:
                    stdscr.attron(curses.color_pair(line.color_pair))
                    stdscr.addstr(y_pos, 0, line.text[:max_x])
                    stdscr.attroff(curses.color_pair(line.color_pair))
                else:
                    stdscr.addstr(y_pos, 0, line.text[:max_x])
                y_pos += 1
                current_line += 1

    def redraw_status(self, stdscr, extra=""):
        """Redraw status bar"""
        max_y, max_x = stdscr.getmaxyx()
        status_line = max_y - 3  # Position of status bar

        # Clear the status line
        stdscr.move(status_line, 0)
        stdscr.clrtoeol()

        # Set reverse video attribute
        stdscr.attron(curses.A_REVERSE)

        # Left side: Model and session
        left_text = f"Model: {self.manager.client.config.get('model', 'unknown') if self.manager.client else 'unknown'} | Session: demo-session"

        # Right side: Permission mode, context usage, scroll indicator
        right_text = self.permission_mode
        right_text += f" | Ctx: {self.context_usage_percent}%"

        if self.scroll_offset > 0:
            right_text += f" | ↑{self.scroll_offset}"

        if extra:
            right_text = extra + " | " + right_text

        # Calculate spacing
        total_len = len(left_text) + len(right_text)
        spaces = max_x - total_len - 2
        if spaces < 1:
            spaces = 1

        # Draw status bar
        stdscr.addstr(status_line, 0, left_text)
        stdscr.addstr(status_line, len(left_text), " " * spaces)
        stdscr.addstr(status_line, len(left_text) + spaces, right_text)

        # Reset attributes
        stdscr.attroff(curses.A_REVERSE)

    def redraw_input(self, stdscr):
        """Redraw input window"""
        max_y, max_x = stdscr.getmaxyx()
        input_start = max_y - 2  # Position of input window

        # Clear the input area
        stdscr.move(input_start, 0)
        stdscr.clrtoeol()
        stdscr.move(input_start + 1, 0)
        stdscr.clrtoeol()

        # Draw input box
        stdscr.addch(input_start, 0, curses.ACS_ULCORNER)
        stdscr.addch(input_start, max_x - 1, curses.ACS_URCORNER)
        for x in range(1, max_x - 1):
            stdscr.addch(input_start, x, curses.ACS_HLINE)

        stdscr.addch(input_start + 1, 0, curses.ACS_VLINE)
        stdscr.addch(input_start + 1, max_x - 1, curses.ACS_VLINE)

        stdscr.addch(input_start + 2, 0, curses.ACS_LLCORNER)
        stdscr.addch(input_start + 2, max_x - 1, curses.ACS_LRCORNER)
        for x in range(1, max_x - 1):
            stdscr.addch(input_start + 2, x, curses.ACS_HLINE)

        # Display input text (handle text longer than window width)
        visible_width = max_x - 4  # Account for box borders and "> " prompt
        display_start = 0

        if self.cursor_pos > visible_width - 1:
            display_start = self.cursor_pos - visible_width + 1

        visible_text = self.input_buffer[display_start:display_start + visible_width]
        stdscr.addstr(input_start + 1, 2, f"> {visible_text}")

        # Position cursor
        cursor_x = 4 + (self.cursor_pos - display_start)
        stdscr.move(input_start + 1, min(cursor_x, max_x - 1))

    def handle_command(self, cmd: str) -> bool:
        """Handle special commands (return True if command was handled)"""
        if cmd == "/exit":
            self.add_output_line("Exiting and closing session...", 3)
            if self.manager.client:
                self.manager.client.stop()
            self.should_exit = True
            return True
        elif cmd == "/detach":
            self.add_output_line("Detaching from session (saving state)...", 3)
            self.add_output_line("Session saved. Use 'qwen --attach session_id' to reconnect.", 1)
            self.should_exit = True
            return True
        elif cmd == "/save":
            self.add_output_line("Saving session...", 3)
            self.add_output_line("Session saved successfully.", 1)
            return True
        elif cmd == "/clear":
            self.add_output_line("Conversation history cleared.", 1)
            # Also clear the output buffer to reflect the clean slate
            self.output_buffer.clear()
            self.scroll_offset = 0
            self.add_output_line("Type /help for commands, /exit to quit, Shift+Tab to cycle permission modes", 3)
            return True
        elif cmd == "/status":
            self.add_output_line("Session Status:", 2)
            self.add_output_line("  Session ID: demo-session", 0)
            self.add_output_line(f"  Model: {self.manager.client.config.get('model', 'unknown') if self.manager.client else 'unknown'}", 0)
            self.add_output_line("  Message count: 0", 0)
            self.add_output_line("  Workspace: .", 0)
            self.add_output_line(f"  Client running: {self.manager.client.is_running() if self.manager.client else False}", 0)
            return True
        elif cmd == "/help":
            self.add_output_line("Interactive Commands:", 2)
            self.add_output_line("  /detach   - Detach from session (keeps it running)", 0)
            self.add_output_line("  /exit     - Exit and close session", 0)
            self.add_output_line("  /save     - Save session immediately", 0)
            self.add_output_line("  /clear    - Clear conversation history", 0)
            self.add_output_line("  /status   - Show session status", 0)
            self.add_output_line("  /help     - Show this help", 0)
            return True
        else:
            self.add_output_line(f"Unknown command: {cmd}", 4)
            self.add_output_line("Type /help for available commands.", 0)
            return True

    def run_ncurses(self, stdscr):
        """Main NCurses UI loop"""
        # Initialize colors if supported
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # User messages
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)    # AI messages
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # System/status messages
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)     # Error messages
            curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Info messages
            curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Tool messages

        # Set up non-blocking input
        stdscr.nodelay(True)
        
        # Add initial info to output buffer
        self.add_output_line("qwen - AI Assistant (NCurses Mode)", 2)
        self.add_output_line("Active Session: demo-session", 5)
        self.add_output_line(f"Model: {self.manager.client.config.get('model', 'unknown') if self.manager.client else 'unknown'}", 5)
        self.add_output_line("Type /help for commands, /exit to quit, Shift+Tab to cycle permission modes", 3)
        self.add_output_line("Use Page Up/Down or Ctrl+U/D to scroll", 3)
        self.add_output_line("")

        # Initial draw
        self.redraw_output(stdscr)
        self.redraw_status(stdscr)
        self.redraw_input(stdscr)
        stdscr.refresh()
        
        # Main event loop
        while not self.should_exit:
            try:
                ch = stdscr.getch()
                
                if ch != -1:  # If a key was pressed
                    # Handle special keys
                    if ch == curses.KEY_RESIZE:
                        # Handle window resize
                        stdscr.clear()
                        self.redraw_output(stdscr)
                        self.redraw_status(stdscr)
                        self.redraw_input(stdscr)
                        stdscr.refresh()
                        continue
                    
                    # Handle tool approval state - BLOCKS all other input!
                    if self.ui_state == UIState.TOOL_APPROVAL and self.has_pending_tool_group:
                        handled = False
                        approved = False

                        if ch == ord('y') or ch == ord('Y'):
                            approved = True
                            handled = True
                        elif ch == ord('n') or ch == ord('N'):
                            approved = False
                            handled = True
                        elif ch == ord('d') or ch == ord('D'):
                            # Enter discuss mode
                            self.add_output_line("=== Entering Discuss Mode ===", 3)
                            self.add_output_line("Explain your concerns or ask questions about the tools:", 3)
                            self.add_output_line("(Type your message and press Enter, or 'y'/'n' to approve/reject)", 3)
                            self.ui_state = UIState.DISCUSS
                            self.redraw_status(stdscr, "Discuss mode")
                            self.redraw_output(stdscr)
                            self.redraw_input(stdscr)
                            stdscr.refresh()
                            continue
                        else:
                            # In ToolApproval state but got a different key - ignore it completely
                            continue

                        if handled:
                            # Send approval/rejection for all tools
                            if self.pending_tool_group:
                                for tool in self.pending_tool_group.tools:
                                    if self.manager.client:
                                        self.manager.client.send_tool_approval(tool.tool_id, approved)

                                    if approved:
                                        self.add_output_line(f"  ✓ Approved: {tool.tool_name}", 1)
                                    else:
                                        self.add_output_line(f"  ✗ Rejected: {tool.tool_name}", 4)

                            self.has_pending_tool_group = False
                            self.ui_state = UIState.NORMAL
                            self.redraw_output(stdscr)
                            self.redraw_status(stdscr)
                            self.redraw_input(stdscr)
                            stdscr.refresh()
                            continue

                    # Handle discuss mode input
                    if self.ui_state == UIState.DISCUSS:
                        if ch == ord('y') or ch == ord('Y'):
                            # Approve and exit discuss mode
                            if self.pending_tool_group and self.manager.client:
                                for tool in self.pending_tool_group.tools:
                                    self.manager.client.send_tool_approval(tool.tool_id, True)
                                    self.add_output_line(f"  ✓ Approved: {tool.tool_name}", 1)
                                self.has_pending_tool_group = False
                            self.ui_state = UIState.NORMAL
                            self.redraw_output(stdscr)
                            self.redraw_status(stdscr)
                            self.redraw_input(stdscr)
                            stdscr.refresh()
                            continue
                        elif ch == ord('n') or ch == ord('N'):
                            # Reject and exit discuss mode
                            if self.pending_tool_group and self.manager.client:
                                for tool in self.pending_tool_group.tools:
                                    self.manager.client.send_tool_approval(tool.tool_id, False)
                                    self.add_output_line(f"  ✗ Rejected: {tool.tool_name}", 4)
                                self.has_pending_tool_group = False
                            self.ui_state = UIState.NORMAL
                            self.redraw_output(stdscr)
                            self.redraw_status(stdscr)
                            self.redraw_input(stdscr)
                            stdscr.refresh()
                            continue
                        # Otherwise fall through to normal input handling for discuss messages
                    # Handle permission mode cycling (Shift+Tab)
                    # Note: curses doesn't directly support Shift+Tab, so we'll use Ctrl+P for cycling
                    if ch == 16:  # Ctrl+P
                        # Cycle through permission modes
                        if self.permission_mode == PermissionMode.PLAN_MODE:
                            self.permission_mode = PermissionMode.NORMAL
                        elif self.permission_mode == PermissionMode.NORMAL:
                            self.permission_mode = PermissionMode.AUTO_ACCEPT_EDITS
                        elif self.permission_mode == PermissionMode.AUTO_ACCEPT_EDITS:
                            self.permission_mode = PermissionMode.YOLO
                        elif self.permission_mode == PermissionMode.YOLO:
                            self.permission_mode = PermissionMode.PLAN_MODE
                        self.add_output_line(f"Permission mode: {self.permission_mode}", 3)
                        self.redraw_output(stdscr)
                        self.redraw_status(stdscr)
                        self.redraw_input(stdscr)
                        stdscr.refresh()
                        continue

                    # Normal input processing
                    if ch == ord('\n') or ch == ord('\r') or ch == curses.KEY_ENTER:
                        # Enter key - submit input
                        if self.input_buffer:
                            # Handle special commands
                            if self.input_buffer.startswith('/'):
                                self.handle_command(self.input_buffer)
                            else:
                                # Send to AI
                                if self.manager.client and self.manager.client.send_user_input(self.input_buffer):
                                    # Input sent successfully (will appear via message handler)
                                    if self.ui_state == UIState.DISCUSS:
                                        self.add_output_line("(AI will respond to your question. Press 'y' to approve or 'n' to reject after.)", 3)
                                else:
                                    self.add_output_line("Failed to send message.", 4)

                            # Clear input buffer
                            self.input_buffer = ""
                            self.cursor_pos = 0
                            self.redraw_input(stdscr)
                    elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                        # Backspace
                        if self.cursor_pos > 0:
                            self.input_buffer = (self.input_buffer[:self.cursor_pos-1] + 
                                               self.input_buffer[self.cursor_pos:])
                            self.cursor_pos -= 1
                            self.redraw_input(stdscr)
                    elif ch == curses.KEY_DC:  # Delete key
                        if self.cursor_pos < len(self.input_buffer):
                            self.input_buffer = (self.input_buffer[:self.cursor_pos] + 
                                               self.input_buffer[self.cursor_pos+1:])
                            self.redraw_input(stdscr)
                    elif ch == curses.KEY_LEFT:
                        if self.cursor_pos > 0:
                            self.cursor_pos -= 1
                            self.redraw_input(stdscr)
                    elif ch == curses.KEY_RIGHT:
                        if self.cursor_pos < len(self.input_buffer):
                            self.cursor_pos += 1
                            self.redraw_input(stdscr)
                    elif ch == curses.KEY_UP:  # For scrolling through history
                        # This would implement command history in a full implementation
                        pass
                    elif ch == curses.KEY_DOWN:  # For scrolling through history
                        # This would implement command history in a full implementation
                        pass
                    elif ch == curses.KEY_PPAGE:  # Page Up
                        # Scroll up
                        max_y, max_x = stdscr.getmaxyx()
                        output_height = max_y - 4
                        self.scroll_offset = min(self.scroll_offset + 5, 
                                               len(self.output_buffer) - output_height)
                        self.redraw_output(stdscr)
                        self.redraw_status(stdscr)
                        self.redraw_input(stdscr)
                        stdscr.refresh()
                    elif ch == curses.KEY_NPAGE:  # Page Down
                        # Scroll down
                        self.scroll_offset = max(self.scroll_offset - 5, 0)
                        self.redraw_output(stdscr)
                        self.redraw_status(stdscr)
                        self.redraw_input(stdscr)
                        stdscr.refresh()
                    elif ch == 4:  # Ctrl+D
                        # Scroll down
                        self.scroll_offset = max(self.scroll_offset - 5, 0)
                        self.redraw_output(stdscr)
                        self.redraw_status(stdscr)
                        self.redraw_input(stdscr)
                        stdscr.refresh()
                    elif ch == 21:  # Ctrl+U
                        # Scroll up if input is empty, otherwise clear input
                        if not self.input_buffer:
                            max_y, max_x = stdscr.getmaxyx()
                            output_height = max_y - 4
                            self.scroll_offset = min(self.scroll_offset + 5, 
                                                   len(self.output_buffer) - output_height)
                            self.redraw_output(stdscr)
                            self.redraw_status(stdscr)
                            self.redraw_input(stdscr)
                            stdscr.refresh()
                        else:
                            # Clear entire line
                            self.input_buffer = ""
                            self.cursor_pos = 0
                            self.redraw_input(stdscr)
                    elif ch == 3:  # Ctrl+C
                        # Exit
                        self.add_output_line("^C (received interrupt signal, exiting qwen...)", 3)
                        self.redraw_output(stdscr)
                        self.should_exit = True
                    elif 32 <= ch <= 126 and ch != 127:  # Printable ASCII characters
                        # Add character to input buffer
                        char = chr(ch)
                        self.input_buffer = (self.input_buffer[:self.cursor_pos] + 
                                           char + 
                                           self.input_buffer[self.cursor_pos:])
                        self.cursor_pos += 1
                        self.redraw_input(stdscr)

                # Poll for incoming messages (non-blocking)
                if self.manager.client:
                    self.manager.client.poll_messages(0)

                # Refresh the screen
                stdscr.refresh()
                
                # Small delay to avoid busy-waiting
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                self.should_exit = True
                break

        # End NCurses mode
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


def run_qwen_ncurses(manager: QwenManager):
    """Run the Qwen NCurses UI"""
    tui = QwenTUI(manager)
    
    # Start the client
    if not manager.client or not manager.client.start():
        print("Failed to start qwen-code subprocess.")
        if manager.client:
            print(f"Error: {manager.client.get_last_error()}")
        print("\nMake sure qwen-code is installed and accessible.")
        print("Set QWEN_CODE_PATH environment variable if needed.")
        print("Falling back to stdio mode.")
        return False
    
    print("Connected! Switching to ncurses mode...")
    
    try:
        curses.wrapper(tui.run_ncurses)
    except Exception as e:
        print(f"Error in NCurses UI: {e}")
        import traceback
        traceback.print_exc()
    
    # Save session before exiting
    print("Saving session...")
    print("Session saved.")

    return True


def run_tui(
    host: str = "127.0.0.1",
    port: int = 7777,
    prompt: Optional[str] = None,
    *,
    exit_after_prompt: bool = False,
) -> int:
    """Simple TUI client for the Qwen TCP server."""
    try:
        import threading
        import json
        from typing import Optional

        sock = socket.create_connection((host, port), timeout=5)
    except OSError as exc:
        print(f"Error: failed to connect to Qwen server at {host}:{port}: {exc}")
        return 1

    stop_event = threading.Event()
    got_conversation_event = threading.Event()

    def _reader() -> None:
        buffer = ""
        try:
            while not stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if _print_message(line):
                        got_conversation_event.set()
        except OSError:
            pass
        finally:
            stop_event.set()

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    if prompt:
        _send_command(sock, {"type": "user_input", "content": prompt})
        if exit_after_prompt:
            # Wait briefly for at least one conversation message so `-p` is useful
            # in non-interactive scripting (e.g. `timeout 10 ...`).
            got_conversation_event.wait(timeout=8.0)
            stop_event.set()

    try:
        while not stop_event.is_set():
            try:
                user_input = input("> ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input in ("/exit", "/quit"):
                break
            _send_command(sock, {"type": "user_input", "content": user_input})
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        reader_thread.join(timeout=1)

    return 0


def _send_command(sock, cmd: dict) -> None:
    """Send a command to the Qwen server."""
    import json
    payload = json.dumps(cmd) + "\n"
    sock.sendall(payload.encode("utf-8"))


def _print_message(raw_line: str) -> bool:
    """Print a message from the Qwen server."""
    import json
    try:
        msg = json.loads(raw_line)
    except json.JSONDecodeError:
        print(raw_line)
        return False

    msg_type = msg.get("type")
    if msg_type == "conversation":
        role = msg.get("role", "assistant").upper()
        content = msg.get("content", "")
        print(f"{role}: {content}")
        return role == "ASSISTANT"

    if msg_type == "status":
        state = msg.get("state", "")
        message = msg.get("message")
        if message:
            print(f"[status:{state}] {message}")
        else:
            print(f"[status:{state}]")
        return False

    if msg_type == "tool_group":
        tool_id = msg.get("id", "")
        tools = msg.get("tools") or []
        tool_names = [tool.get("tool_name", "tool") for tool in tools if isinstance(tool, dict)]
        summary = ", ".join(tool_names) if tool_names else "tools"
        print(f"[tools:{tool_id}] {summary}")
        return False

    if msg_type == "error":
        print(f"[error] {msg.get('message', '')}")
        return False

    if msg_type == "info":
        print(f"[info] {msg.get('message', '')}")
        return False

    if msg_type == "completion_stats":
        duration = msg.get("duration", "")
        prompt_tokens = msg.get("prompt_tokens")
        completion_tokens = msg.get("completion_tokens")
        stats = [duration] if duration else []
        if prompt_tokens is not None:
            stats.append(f"prompt={prompt_tokens}")
        if completion_tokens is not None:
            stats.append(f"completion={completion_tokens}")
        stat_line = " ".join(stats)
        print(f"[stats] {stat_line}".strip())
        return False

    print(raw_line)
    return False


def main() -> int:
    """Main entry point for the NCurses TUI"""
    import argparse
    from maestro.qwen.main import QwenManager

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Qwen TUI client (TCP)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--tcp-port", type=int, default=7777, help="Server TCP port (default: 7777)")
    parser.add_argument("--simple", action="store_true", help="Use simple line-based TUI instead of NCurses")
    args = parser.parse_args()

    if args.simple:
        return run_tui(host=args.host, port=args.tcp_port)

    # Create a QwenManager instance
    manager = QwenManager()

    # Run the NCurses UI
    success = run_qwen_ncurses(manager)

    if not success:
        # Fallback to simple TUI if NCurses fails
        print("NCurses UI failed to start, falling back to simple TUI...")
        return run_tui(host=args.host, port=args.tcp_port)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
