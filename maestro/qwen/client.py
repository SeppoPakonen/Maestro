"""
Qwen Client Implementation in Python

This module implements the client functionality that connects to the actual Qwen service
and handles communication between the server and the AI service.
"""
import json
import subprocess
import threading
import time
import select
import sys
import os
from typing import Optional, Dict, Any, Callable, List
from queue import Queue, Empty
from .server import (
    QwenUserInput, QwenToolApproval, QwenInterrupt, QwenModelSwitch,
    QwenInitMessage, QwenConversationMessage, QwenToolGroup,
    QwenStatusUpdate, QwenInfoMessage, QwenErrorMessage, QwenCompletionStats
)


class QwenClientConfig:
    """Configuration for the Qwen client"""
    
    def __init__(self):
        self.qwen_executable = "npx qwen-code"  # Default to npx command
        self.qwen_args = ["--server-mode", "stdin"]  # Default args for server mode
        self.auto_restart = True
        self.verbose = True
        self.max_restarts = 5


class MessageHandlers:
    """Container for message handlers"""
    
    def __init__(self):
        self.on_init: Optional[Callable[[QwenInitMessage], None]] = None
        self.on_conversation: Optional[Callable[[QwenConversationMessage], None]] = None
        self.on_tool_group: Optional[Callable[[QwenToolGroup], None]] = None
        self.on_status: Optional[Callable[[QwenStatusUpdate], None]] = None
        self.on_info: Optional[Callable[[QwenInfoMessage], None]] = None
        self.on_error: Optional[Callable[[QwenErrorMessage], None]] = None
        self.on_completion_stats: Optional[Callable[[QwenCompletionStats], None]] = None


class QwenClient:
    """Client to communicate with the Qwen service"""
    
    def __init__(self, config: QwenClientConfig):
        self.config = config
        self.process = None
        self.running = False
        self.handlers = MessageHandlers()
        self.stdin_queue = Queue()
        self.read_buffer = ""
        self.restart_count = 0
        self.last_error = ""
        self.stdin_thread = None
        self.stdout_thread = None
    
    def start(self) -> bool:
        """Start the Qwen subprocess"""
        try:
            # Build command
            cmd_parts = self.config.qwen_executable.split()
            cmd = cmd_parts + self.config.qwen_args
            
            if self.config.verbose:
                print(f"[QwenClient] Starting subprocess: {' '.join(cmd)}", file=sys.stderr)
            
            # Start the subprocess
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            self.running = True
            
            # Start threads for stdin and stdout handling
            self.stdin_thread = threading.Thread(target=self._write_stdin, daemon=True)
            self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            
            self.stdin_thread.start()
            self.stdout_thread.start()
            
            if self.config.verbose:
                print(f"[QwenClient] Subprocess started with PID {self.process.pid}", file=sys.stderr)
            
            return True
            
        except Exception as e:
            self.last_error = f"Failed to start subprocess: {str(e)}"
            print(f"[QwenClient] Error starting subprocess: {e}", file=sys.stderr)
            return False
    
    def stop(self):
        """Stop the Qwen subprocess"""
        if not self.running:
            return
        
        if self.config.verbose:
            print(f"[QwenClient] Stopping subprocess PID={self.process.pid if self.process else 'None'}", file=sys.stderr)
        
        self.running = False
        
        if self.process:
            try:
                # Terminate the process
                self.process.terminate()
                try:
                    # Wait for process to exit (with timeout)
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    if self.config.verbose:
                        print("[QwenClient] Process didn't respond to terminate, sending kill", file=sys.stderr)
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                print(f"[QwenClient] Error stopping subprocess: {e}", file=sys.stderr)
            
            self.process = None
        
        # Wait for threads to finish
        if self.stdin_thread and self.stdin_thread.is_alive():
            self.stdin_thread.join(timeout=1)
        if self.stdout_thread and self.stdout_thread.is_alive():
            self.stdout_thread.join(timeout=1)
        
        if self.config.verbose:
            print("[QwenClient] Client stopped", file=sys.stderr)
    
    def restart(self) -> bool:
        """Restart the client"""
        if self.config.verbose:
            print(f"[QwenClient] Restarting (attempt {self.restart_count + 1})", file=sys.stderr)
        
        self.stop()
        
        if self.restart_count >= self.config.max_restarts:
            self.last_error = "Maximum restart attempts exceeded"
            return False
        
        self.restart_count += 1
        return self.start()
    
    def is_running(self) -> bool:
        """Check if client is running"""
        if not self.running or not self.process:
            return False
        
        # Check if process is still alive
        return self.process.poll() is None
    
    def set_handlers(self, handlers: MessageHandlers):
        """Set message handlers"""
        self.handlers = handlers
    
    def poll_messages(self, timeout_ms: int = 0) -> int:
        """Poll for messages from the subprocess"""
        # In Python, we're using threads to read messages continuously
        # So this is mainly for compatibility with the interface
        # The actual message processing happens in the stdout thread
        time.sleep(timeout_ms / 1000.0)  # Convert ms to seconds
        return 0  # We don't have a count since we process messages continuously
    
    def send_user_input(self, content: str) -> bool:
        """Send user input to the Qwen service"""
        return self._send_command({
            "type": "user_input",
            "content": content
        })
    
    def send_tool_approval(self, tool_id: str, approved: bool) -> bool:
        """Send tool approval to the Qwen service"""
        return self._send_command({
            "type": "tool_approval",
            "tool_id": tool_id,
            "approved": approved
        })
    
    def send_interrupt(self) -> bool:
        """Send interrupt command to the Qwen service"""
        return self._send_command({
            "type": "interrupt"
        })
    
    def send_model_switch(self, model_id: str) -> bool:
        """Send model switch command to the Qwen service"""
        return self._send_command({
            "type": "model_switch",
            "model_id": model_id
        })
    
    def _send_command(self, cmd: Dict[str, Any]) -> bool:
        """Send a command to the subprocess"""
        if not self.running or not self.process or self.process.stdin is None:
            self.last_error = "Client not running"
            if self.config.verbose:
                print("[QwenClient] send_command failed: client not running", file=sys.stderr)
            return False
        
        try:
            json_str = json.dumps(cmd)
            if self.config.verbose:
                log_json = json_str if len(json_str) <= 200 else json_str[:197] + "..."
                print(f"[QwenClient] Sending: {log_json}", file=sys.stderr)
            
            self.process.stdin.write(json_str + '\n')
            self.process.stdin.flush()
            
            return True
        except Exception as e:
            self.last_error = f"Failed to send command: {str(e)}"
            print(f"[QwenClient] Failed to send command: {e}", file=sys.stderr)
            return False
    
    def _write_stdin(self):
        """Thread function to write to subprocess stdin"""
        while self.running and self.process and self.process.stdin:
            try:
                # Get command from queue (with timeout to allow checking running flag)
                try:
                    cmd = self.stdin_queue.get(timeout=0.1)
                    self._send_command(cmd)
                except Empty:
                    continue
            except Exception as e:
                if self.running:
                    print(f"[QwenClient] Error writing to stdin: {e}", file=sys.stderr)
                break
    
    def _read_stdout(self):
        """Thread function to read from subprocess stdout"""
        while self.running and self.process and self.process.stdout:
            try:
                # Try to read with timeout
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline()
                    if line:
                        self._process_message(line.strip())
                    else:
                        # EOF - subprocess closed stdout
                        if self.config.verbose:
                            print(f"[QwenClient] EOF: Subprocess closed stdout (PID={self.process.pid})", file=sys.stderr)
                        
                        if self.config.auto_restart:
                            if self.config.verbose:
                                print("[QwenClient] Auto-restart enabled, restarting subprocess", file=sys.stderr)
                            self.restart()
                        break
                elif not self.running:
                    break
            except Exception as e:
                if self.running:
                    print(f"[QwenClient] Error reading from stdout: {e}", file=sys.stderr)
                break
    
    def _process_message(self, json_line: str):
        """Process a message from the subprocess"""
        if not json_line.strip():
            return
        
        # Log received message (truncate if too long)
        log_line = json_line if len(json_line) <= 200 else json_line[:197] + "..."
        if self.config.verbose:
            print(f"[QwenClient] Received: {log_line}", file=sys.stderr)
        
        try:
            data = json.loads(json_line)
            msg_type = data.get('type')
            
            if msg_type == 'init':
                if self.handlers.on_init:
                    msg = QwenInitMessage(
                        type=data.get('type', 'init'),
                        version=data.get('version', ''),
                        workspace_root=data.get('workspace_root', ''),
                        model=data.get('model', '')
                    )
                    self.handlers.on_init(msg)
            
            elif msg_type == 'conversation':
                if self.handlers.on_conversation:
                    msg = QwenConversationMessage(
                        type=data.get('type', 'conversation'),
                        role=data.get('role', ''),
                        content=data.get('content', ''),
                        id=data.get('id', 0),
                        timestamp=data.get('timestamp'),
                        isStreaming=data.get('isStreaming')
                    )
                    self.handlers.on_conversation(msg)
            
            elif msg_type == 'tool_group':
                if self.handlers.on_tool_group:
                    tools_data = data.get('tools', [])
                    tools = []
                    for tool_data in tools_data:
                        tool = QwenToolCall(
                            type=tool_data.get('type', 'tool_call'),
                            tool_id=tool_data.get('tool_id', ''),
                            tool_name=tool_data.get('tool_name', ''),
                            status=tool_data.get('status', ''),
                            args=tool_data.get('args', {}),
                            result=tool_data.get('result'),
                            error=tool_data.get('error'),
                            confirmation_details=tool_data.get('confirmation_details')
                        )
                        tools.append(tool)
                    
                    msg = QwenToolGroup(
                        type=data.get('type', 'tool_group'),
                        id=data.get('id', 0),
                        tools=tools
                    )
                    self.handlers.on_tool_group(msg)
            
            elif msg_type == 'status':
                if self.handlers.on_status:
                    msg = QwenStatusUpdate(
                        type=data.get('type', 'status'),
                        state=data.get('state', 'idle'),
                        message=data.get('message'),
                        thought=data.get('thought')
                    )
                    self.handlers.on_status(msg)
            
            elif msg_type == 'info':
                if self.handlers.on_info:
                    msg = QwenInfoMessage(
                        type=data.get('type', 'info'),
                        message=data.get('message', ''),
                        id=data.get('id', 0)
                    )
                    self.handlers.on_info(msg)
            
            elif msg_type == 'error':
                if self.handlers.on_error:
                    msg = QwenErrorMessage(
                        type=data.get('type', 'error'),
                        message=data.get('message', ''),
                        id=data.get('id', 0)
                    )
                    self.handlers.on_error(msg)
            
            elif msg_type == 'completion_stats':
                if self.handlers.on_completion_stats:
                    msg = QwenCompletionStats(
                        type=data.get('type', 'completion_stats'),
                        duration=data.get('duration', ''),
                        prompt_tokens=data.get('prompt_tokens'),
                        completion_tokens=data.get('completion_tokens')
                    )
                    self.handlers.on_completion_stats(msg)
            
            else:
                if self.config.verbose:
                    print(f"[QwenClient] Unknown message type: {msg_type}", file=sys.stderr)
        
        except json.JSONDecodeError as e:
            self.last_error = f"Failed to parse message: {json_line} - Error: {e}"
            print(f"[QwenClient] Failed to parse message: {e}", file=sys.stderr)
        except Exception as e:
            self.last_error = f"Error processing message: {e}"
            print(f"[QwenClient] Error processing message: {e}", file=sys.stderr)
    
    def get_last_error(self) -> str:
        """Get the last error message"""
        return self.last_error
    
    def get_restart_count(self) -> int:
        """Get the restart count"""
        return self.restart_count
    
    def get_process_id(self) -> Optional[int]:
        """Get the process ID"""
        return self.process.pid if self.process else None