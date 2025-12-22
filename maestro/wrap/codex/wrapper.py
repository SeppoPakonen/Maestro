"""
Codex CLI Loop wrapper for Maestro.

This module provides an automated wrapper around the codex CLI application,
running it in a virtual terminal with wide display (200+ chars), analyzing
UI usage patterns through a Turing machine model, and handling specific
commands like /compact, /new, /quit, /model.

The wrapper captures input prompts, parses AI outputs, separates tool usage,
encodes results as JSON, and communicates with connected clients.
"""
import json
import logging
import os
import pexpect
import re
import socket
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from queue import Queue

from .parser import CodexParser


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class State(Enum):
    """States for the Turing machine representing UI usage patterns."""
    IDLE = "idle"
    PROMPTING = "prompting"
    AWAITING_RESPONSE = "awaiting_response"
    PROCESSING_TOOLS = "processing_tools"
    COMMAND_MODE = "command_mode"
    QUITTING = "quitting"


@dataclass
class TuringMachineTransition:
    """Represents a transition in the Turing machine."""
    current_state: State
    input_char: str
    next_state: State
    action: Optional[str] = None  # Optional action to perform during transition


class CodexTuringMachine:
    """
    Turing machine implementation to model UI usage patterns.
    
    This machine tracks the state of the codex CLI session and manages
    transitions based on input/output patterns.
    """
    
    def __init__(self):
        self.state = State.IDLE
        self.transitions = self._build_transitions()
        self.history = []
    
    def _build_transitions(self) -> Dict[Tuple[State, str], TuringMachineTransition]:
        """Build the state transition table."""
        # This is a simplified model - in practice, this would be more complex
        transitions = {}

        # From IDLE state
        transitions[(State.IDLE, "prompt_start")] = TuringMachineTransition(
            State.IDLE, "prompt_start", State.PROMPTING, "start_prompt_capture"
        )
        transitions[(State.IDLE, "command_start")] = TuringMachineTransition(
            State.IDLE, "command_start", State.COMMAND_MODE, "start_command_mode"
        )
        transitions[(State.IDLE, "idle")] = TuringMachineTransition(
            State.IDLE, "idle", State.IDLE, "maintain_idle"
        )

        # From PROMPTING state
        transitions[(State.PROMPTING, "input_complete")] = TuringMachineTransition(
            State.PROMPTING, "input_complete", State.AWAITING_RESPONSE, "send_input"
        )
        transitions[(State.PROMPTING, "idle")] = TuringMachineTransition(
            State.PROMPTING, "idle", State.PROMPTING, "continue_prompting"
        )

        # From AWAITING_RESPONSE state
        transitions[(State.AWAITING_RESPONSE, "response_start")] = TuringMachineTransition(
            State.AWAITING_RESPONSE, "response_start", State.AWAITING_RESPONSE, "start_response_capture"
        )
        transitions[(State.AWAITING_RESPONSE, "response_end")] = TuringMachineTransition(
            State.AWAITING_RESPONSE, "response_end", State.IDLE, "process_response"
        )
        transitions[(State.AWAITING_RESPONSE, "tool_detected")] = TuringMachineTransition(
            State.AWAITING_RESPONSE, "tool_detected", State.PROCESSING_TOOLS, "process_tools"
        )
        transitions[(State.AWAITING_RESPONSE, "response_continue")] = TuringMachineTransition(
            State.AWAITING_RESPONSE, "response_continue", State.AWAITING_RESPONSE, "continue_response_capture"
        )

        # From PROCESSING_TOOLS state
        transitions[(State.PROCESSING_TOOLS, "tool_complete")] = TuringMachineTransition(
            State.PROCESSING_TOOLS, "tool_complete", State.AWAITING_RESPONSE, "continue_response"
        )
        transitions[(State.PROCESSING_TOOLS, "response_end")] = TuringMachineTransition(
            State.PROCESSING_TOOLS, "response_end", State.IDLE, "process_response"
        )

        # From COMMAND_MODE state
        transitions[(State.COMMAND_MODE, "quit_command")] = TuringMachineTransition(
            State.COMMAND_MODE, "quit_command", State.QUITTING, "quit_application"
        )
        transitions[(State.COMMAND_MODE, "other_command")] = TuringMachineTransition(
            State.COMMAND_MODE, "other_command", State.IDLE, "execute_command"
        )
        transitions[(State.COMMAND_MODE, "idle")] = TuringMachineTransition(
            State.COMMAND_MODE, "idle", State.COMMAND_MODE, "maintain_command_mode"
        )

        # From QUITTING state
        transitions[(State.QUITTING, "quit_application")] = TuringMachineTransition(
            State.QUITTING, "quit_application", State.QUITTING, "terminate_process"
        )

        return transitions
    
    def transition(self, input_char: str) -> Optional[str]:
        """Process an input character and return any action to take."""
        key = (self.state, input_char)
        if key in self.transitions:
            transition = self.transitions[key]
            self.state = transition.next_state
            self.history.append(transition)
            return transition.action
        return None
    
    def get_current_state(self) -> State:
        """Get the current state of the machine."""
        return self.state


class TerminalSnapshot:
    """Represents a snapshot of the terminal state at a specific time."""

    def __init__(self, content: str, cursor_position: Optional[tuple] = None, timestamp: Optional[float] = None):
        self.content = content
        self.cursor_position = cursor_position
        self.timestamp = timestamp or time.time()
        self.line_count = len(content.split('\n')) if content else 0

    def get_changed_regions(self, previous_snapshot: 'TerminalSnapshot') -> List[Dict[str, Any]]:
        """Compare with a previous snapshot and return the changed regions."""
        if not previous_snapshot:
            return [{"type": "initial", "content": self.content, "position": (0, 0)}]

        # Split content into lines for comparison
        prev_lines = previous_snapshot.content.split('\n')
        curr_lines = self.content.split('\n')

        changes = []

        # Find where content starts to differ
        min_lines = min(len(prev_lines), len(curr_lines))
        start_diff = 0
        for i in range(min_lines):
            if prev_lines[i] != curr_lines[i]:
                start_diff = i
                break
        else:
            # If all compared lines are the same, check if one has more lines
            if len(prev_lines) != len(curr_lines):
                start_diff = min_lines

        # Capture the changed content
        if start_diff < len(curr_lines):
            changed_content = '\n'.join(curr_lines[start_diff:])
            changes.append({
                "type": "new_content",
                "content": changed_content,
                "position": (start_diff, 0),  # (line, column)
                "previous_line_count": len(prev_lines),
                "new_line_count": len(curr_lines)
            })

        return changes


class CodexWrapper:
    """
    Wrapper for the codex CLI application with virtual terminal.

    This class manages the codex process in a pty with wide display (200+ chars),
    handles input/output parsing, command processing, and client communication.
    """

    def __init__(self, width: int = 240, height: int = 60, socket_path: Optional[str] = None):
        self.width = width
        self.height = height
        self.socket_path = socket_path
        self.child = None
        self.turing_machine = CodexTuringMachine()
        self.parser = CodexParser()
        self.input_buffer = ""
        self.output_buffer = ""
        self.tool_buffer = ""
        self.is_capturing_tools = False
        self.client_socket = None
        self.output_queue = Queue()
        self.should_stop = False

        # Terminal state tracking
        self.terminal_history = []  # List of TerminalSnapshot objects
        self.last_snapshot = None

        # Initialize socket for client communication
        if self.socket_path:
            self._setup_socket()
    
    def _setup_socket(self):
        """Set up Unix domain socket for client communication."""
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        
        self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client_socket.bind(self.socket_path)
        self.client_socket.listen(1)
        logger.info(f"Socket listening at {self.socket_path}")
    
    def start(self):
        """Start the codex process in a virtual terminal."""
        try:
            # Start codex in a pty with specified dimensions
            self.child = pexpect.spawn('codex', timeout=None, dimensions=(self.height, self.width))
            logger.info(f"Started codex process with dimensions {self.height}x{self.width}")
            
            # Start output reading thread
            output_thread = threading.Thread(target=self._read_output, daemon=True)
            output_thread.start()
            
            # Start client handling thread if socket is configured
            if self.client_socket:
                client_thread = threading.Thread(target=self._handle_clients, daemon=True)
                client_thread.start()
                
        except Exception as e:
            logger.error(f"Failed to start codex process: {e}")
            raise
    
    def _read_output(self):
        """Read output from the codex process and process it."""
        try:
            while not self.should_stop:
                try:
                    # Use pexpect's expect with a short timeout to avoid blocking
                    index = self.child.expect([pexpect.TIMEOUT, pexpect.EOF, r'.'], timeout=0.1)

                    if index == 0:  # TIMEOUT
                        continue
                    elif index == 1:  # EOF
                        logger.info("Codex process ended")
                        break
                    elif index == 2:  # Got output
                        output = self.child.after
                        if output:
                            # Ensure output is a string
                            if isinstance(output, bytes):
                                output = output.decode('utf-8')

                            self._process_output(output)
                except pexpect.exceptions.TIMEOUT:
                    continue
                except pexpect.exceptions.EOF:
                    logger.info("Codex process ended")
                    break
        except Exception as e:
            logger.error(f"Error reading codex output: {e}")


    def _is_prompt(self, text: str) -> bool:
        """Check if the text indicates a prompt is ready."""
        # Check if the text ends with a prompt character, but only if it's a standalone prompt
        # (appears after a newline or the entire text is just the prompt)
        text_stripped = text.rstrip()

        # Common prompt endings
        prompt_endings = [
            'codex>',       # Codex prompt
            '>',            # Generic prompt
            ':',            # Colon prompt
            '>>>',          # Python-style prompt
            '$',            # Shell-style prompt
        ]

        for ending in prompt_endings:
            if text_stripped.endswith(ending):
                # Check if the prompt appears after a newline or is the entire text
                # This prevents matching prompts that are part of AI responses
                if '\n' + ending in text or text_stripped == ending:
                    return True
        return False

    def _is_command(self, text: str) -> bool:
        """Check if the text contains a command."""
        # Commands start with / in our system
        return text.strip().startswith('/')

    def _is_response_start(self, text: str) -> bool:
        """Check if the text indicates the start of a response."""
        # Simple heuristic - AI responses often start with capitalized text
        # after a newline or after a prompt
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('/') and not self._is_prompt(stripped):
                # Check if it looks like an AI response (starts with capital letter)
                if re.match(r'^[A-Z][a-z]', stripped):
                    return True
        return False

    def _is_response_end(self, text: str) -> bool:
        """Check if the text indicates the end of a response."""
        # This is a simplified check - in practice, this would be more sophisticated
        # For now, we'll consider it ends when we see a prompt again
        return self._is_prompt(text)

    def _is_tool_detected(self, text: str) -> bool:
        """Check if the text contains tool usage."""
        return self.parser.parse_output(text).metadata.get('has_tools', False)
    
    def _process_output(self, output):
        """Process output from the codex process."""
        # Ensure output is a string
        if isinstance(output, bytes):
            output = output.decode('utf-8')

        # Store the new output segment
        new_output_segment = output

        # Update the full output buffer
        self.output_buffer += output

        # Create a new terminal snapshot of the full content
        current_snapshot = TerminalSnapshot(content=self.output_buffer)

        # Compare with the last snapshot to detect changes
        changes = []
        if self.last_snapshot:
            changes = current_snapshot.get_changed_regions(self.last_snapshot)
        else:
            # For the first snapshot, treat all content as new
            changes = [{"type": "initial", "content": self.output_buffer, "position": (0, 0)}]

        # Update the last snapshot
        self.last_snapshot = current_snapshot
        self.terminal_history.append(current_snapshot)

        # Process the changes to update Turing machine
        for change in changes:
            if change["type"] in ["new_content", "initial"]:
                self._analyze_terminal_change(change["content"], change)

        # Parse the new output segment (not the full buffer to avoid reparsing)
        parsed_output = self.parser.parse_output(new_output_segment)

        # Look for tool usage patterns in the new output segment
        if parsed_output.metadata.get('has_tools', False):
            self.is_capturing_tools = True
            action = self.turing_machine.transition("tool_detected")
            if action:
                logger.debug(f"Turing machine action: {action}")

        # Process and send output to client
        json_data = self.parser.encode_as_json(parsed_output=parsed_output)
        self._send_to_client({
            "type": "output",
            "content": new_output_segment,  # Send only the new segment
            "parsed_data": json.loads(json_data),
            "state": self.turing_machine.get_current_state().value,
            "terminal_changes": changes
        })

    def _analyze_terminal_change(self, new_content: str, change_info: Dict[str, Any]):
        """Analyze terminal changes to update the Turing machine appropriately."""
        # Check for prompt indicators in the new content
        if self._is_prompt(new_content):
            action = self.turing_machine.transition("prompt_start")
        elif self._is_command(new_content):
            action = self.turing_machine.transition("command_start")
        elif self._is_response_start(new_content):
            action = self.turing_machine.transition("response_start")
        elif self._is_response_end(new_content):
            action = self.turing_machine.transition("response_end")
        elif self._is_tool_detected(new_content):
            action = self.turing_machine.transition("tool_detected")
        else:
            # Default transition based on current state
            if self.turing_machine.get_current_state() == State.AWAITING_RESPONSE:
                action = self.turing_machine.transition("response_continue")
            else:
                action = self.turing_machine.transition("idle")

        if action:
            logger.debug(f"Turing machine action from terminal change: {action}")
    
    
    def send_input(self, input_text: str):
        """Send input to the codex process."""
        if not self.child or not self.child.isalive():
            raise RuntimeError("Codex process is not running")

        # Parse the input
        parsed_input = self.parser.parse_input(input_text)

        # Check if this is a command
        if input_text.strip().startswith('/'):
            self._handle_command(input_text.strip())
        else:
            # Regular input - send to codex
            self.child.send(input_text + '\n')

            # Process through Turing machine
            action = self.turing_machine.transition("input_complete")
            if action:
                logger.debug(f"Turing machine action: {action}")

        # Send parsed input to client
        json_data = self.parser.encode_as_json(parsed_input=parsed_input)
        self._send_to_client({
            "type": "input",
            "content": input_text,
            "parsed_data": json.loads(json_data),
            "state": self.turing_machine.get_current_state().value
        })
    
    def _handle_command(self, command: str):
        """Handle special commands like /compact, /new, /quit, /model."""
        cmd = command.split()[0].lower()
        
        if cmd == '/quit':
            action = self.turing_machine.transition("quit_command")
            if action:
                logger.debug(f"Turing machine action: {action}")
            self.quit()
        elif cmd == '/new':
            action = self.turing_machine.transition("other_command")
            if action:
                logger.debug(f"Turing machine action: {action}")
            # For /new, we just pass it to codex
            self.child.send(command + '\n')
        elif cmd == '/compact' or cmd == '/model':
            action = self.turing_machine.transition("other_command")
            if action:
                logger.debug(f"Turing machine action: {action}")
            # For these commands, pass to codex
            self.child.send(command + '\n')
        else:
            # Unknown command - pass to codex
            self.child.send(command + '\n')
    
    def _handle_clients(self):
        """Handle incoming client connections."""
        while not self.should_stop:
            try:
                if self.client_socket:
                    conn, addr = self.client_socket.accept()
                    client_handler = threading.Thread(
                        target=self._serve_client, 
                        args=(conn,), 
                        daemon=True
                    )
                    client_handler.start()
            except OSError:
                # Socket might have been closed
                break
            except Exception as e:
                logger.error(f"Error accepting client connection: {e}")
    
    def _serve_client(self, conn):
        """Serve a single client connection."""
        try:
            while not self.should_stop:
                data = conn.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._handle_client_message(message, conn)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from client")
        except Exception as e:
            logger.error(f"Error serving client: {e}")
        finally:
            conn.close()
    
    def _handle_client_message(self, message: Dict[str, Any], conn):
        """Handle a message from the connected client."""
        msg_type = message.get('type')
        
        if msg_type == 'input':
            input_text = message.get('content', '')
            try:
                self.send_input(input_text)
            except Exception as e:
                error_response = {
                    "type": "error",
                    "content": str(e)
                }
                conn.send(json.dumps(error_response).encode('utf-8'))
        elif msg_type == 'command':
            command = message.get('content', '')
            try:
                self.send_input(command)
            except Exception as e:
                error_response = {
                    "type": "error",
                    "content": str(e)
                }
                conn.send(json.dumps(error_response).encode('utf-8'))
        elif msg_type == 'status':
            # Send current status
            status = {
                "type": "status",
                "state": self.turing_machine.get_current_state().value,
                "is_alive": self.child.isalive() if self.child else False
            }
            conn.send(json.dumps(status).encode('utf-8'))
    
    def _send_to_client(self, data: Dict[str, Any]):
        """Send data to the connected client."""
        # For now, just log the data. In a real implementation, 
        # this would send to active client connections.
        logger.debug(f"Sending to client: {data}")
        
        # Put on queue for potential processing
        self.output_queue.put(data)
    
    def quit(self):
        """Quit the codex process and clean up."""
        self.should_stop = True
        if self.child and self.child.isalive():
            self.child.terminate()
        if self.client_socket:
            self.client_socket.close()
        logger.info("Codex wrapper stopped")
    
    def is_alive(self) -> bool:
        """Check if the codex process is still running."""
        return self.child and self.child.isalive()


def main():
    """Main function to run the codex wrapper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Codex CLI Loop Wrapper')
    parser.add_argument('--socket-path', type=str, default='/tmp/codex_wrapper.sock',
                        help='Unix socket path for client communication')
    parser.add_argument('--width', type=int, default=240, help='Terminal width (default: 240)')
    parser.add_argument('--height', type=int, default=60, help='Terminal height (default: 60)')
    
    args = parser.parse_args()
    
    wrapper = CodexWrapper(width=args.width, height=args.height, socket_path=args.socket_path)
    
    try:
        wrapper.start()
        logger.info("Codex wrapper started. Press Ctrl+C to quit.")
        
        # Keep the main thread alive
        while wrapper.is_alive():
            try:
                # Simple input handling for direct interaction
                # In a real implementation, this would be handled via the socket
                import time
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
    
    except Exception as e:
        logger.error(f"Error running codex wrapper: {e}")
    finally:
        wrapper.quit()


if __name__ == "__main__":
    main()