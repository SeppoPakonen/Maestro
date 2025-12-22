"""
Qwen Server Implementation in Python

This module implements the server functionality that was originally in C++.
It supports three communication modes:
- stdin/stdout: Line-buffered JSON
- Named pipes: Bidirectional filesystem pipes  
- TCP: Network-based communication
"""
import json
import socket
import select
import threading
import time
import os
import subprocess
import sys
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from queue import Queue, Empty


@dataclass
class QwenInitMessage:
    type: str = "init"
    version: str = ""
    workspace_root: str = ""
    model: str = ""


@dataclass
class QwenConversationMessage:
    type: str = "conversation"
    role: str = ""  # 'user' | 'assistant' | 'system'
    content: str = ""
    id: int = 0
    timestamp: Optional[int] = None
    isStreaming: Optional[bool] = None


@dataclass
class QwenToolCall:
    type: str = "tool_call"
    tool_id: str = ""
    tool_name: str = ""
    status: str = ""  # 'pending' | 'confirming' | 'executing' | 'success' | 'error' | 'canceled'
    args: Dict[str, Any] = None
    result: Optional[str] = None
    error: Optional[str] = None
    confirmation_details: Optional[Dict[str, Any]] = None


@dataclass
class QwenToolGroup:
    type: str = "tool_group"
    id: int = 0
    tools: List[QwenToolCall] = None


@dataclass
class QwenStatusUpdate:
    type: str = "status"
    state: str = ""  # 'idle' | 'responding' | 'waiting_for_confirmation'
    message: Optional[str] = None
    thought: Optional[str] = None


@dataclass
class QwenInfoMessage:
    type: str = "info"
    message: str = ""
    id: int = 0


@dataclass
class QwenErrorMessage:
    type: str = "error"
    message: str = ""
    id: int = 0


@dataclass
class QwenCompletionStats:
    type: str = "completion_stats"
    duration: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


from typing import Union

QwenStateMessage = Union[
    QwenInitMessage, QwenConversationMessage, QwenToolGroup,
    QwenStatusUpdate, QwenInfoMessage, QwenErrorMessage, QwenCompletionStats
]


@dataclass
class QwenUserInput:
    type: str = "user_input"
    content: str = ""


@dataclass
class QwenToolApproval:
    type: str = "tool_approval"
    tool_id: str = ""
    approved: bool = False


@dataclass
class QwenInterrupt:
    type: str = "interrupt"


@dataclass
class QwenModelSwitch:
    type: str = "model_switch"
    model_id: str = ""


QwenCommand = Union[QwenUserInput, QwenToolApproval, QwenInterrupt, QwenModelSwitch]


class BaseQwenServer:
    """Base class for Qwen server implementations"""
    
    def __init__(self):
        self.running = False
        self.message_queue = Queue()
        self.handlers = {}
    
    def start(self):
        """Start the server"""
        raise NotImplementedError
    
    def stop(self):
        """Stop the server"""
        self.running = False
    
    def is_running(self):
        """Check if server is running"""
        return self.running
    
    def send_message(self, msg: QwenStateMessage):
        """Send a message to the client"""
        raise NotImplementedError
    
    def send_messages(self, messages: List[QwenStateMessage]):
        """Send multiple messages in batch (more efficient)"""
        for msg in messages:
            self.send_message(msg)
    
    def receive_command(self) -> Optional[QwenCommand]:
        """Receive command from client (non-blocking)"""
        try:
            return self.message_queue.get_nowait()
        except Empty:
            return None
    
    def wait_for_command(self, timeout: int = 60) -> Optional[QwenCommand]:
        """Wait for specific command type (blocking with timeout)"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                return self.message_queue.get(timeout=0.1)
            except Empty:
                continue
        
        return None
    
    def parse_command(self, line: str) -> Optional[QwenCommand]:
        """Parse incoming JSON command"""
        try:
            parsed = json.loads(line)
            cmd_type = parsed.get('type')
            
            if cmd_type == 'user_input':
                return QwenUserInput(
                    type='user_input',
                    content=parsed.get('content', '')
                )
            elif cmd_type == 'tool_approval':
                return QwenToolApproval(
                    type='tool_approval',
                    tool_id=parsed.get('tool_id', ''),
                    approved=parsed.get('approved', False)
                )
            elif cmd_type == 'interrupt':
                return QwenInterrupt(type='interrupt')
            elif cmd_type == 'model_switch':
                return QwenModelSwitch(
                    type='model_switch',
                    model_id=parsed.get('model_id', '')
                )
            else:
                print(f"[QwenServer] Invalid command type: {parsed}", file=sys.stderr)
                return None
        except json.JSONDecodeError as e:
            print(f"[QwenServer] Failed to parse command: {line}, error: {e}", file=sys.stderr)
            return None


class StdinStdoutServer(BaseQwenServer):
    """Stdin/Stdout server implementation"""
    
    def __init__(self):
        super().__init__()
        self.stdin_thread = None
    
    def start(self):
        self.running = True
        
        print("[QwenServer] Starting stdin/stdout mode", file=sys.stderr)
        
        # Make stdout unbuffered so messages are sent immediately
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)
        else:
            # For older Python versions
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        
        # Start thread to read from stdin
        self.stdin_thread = threading.Thread(target=self._read_stdin, daemon=True)
        self.stdin_thread.start()
    
    def _read_stdin(self):
        """Read commands from stdin"""
        try:
            for line in sys.stdin:
                line = line.strip()
                if line:
                    cmd = self.parse_command(line)
                    if cmd:
                        self.message_queue.put(cmd)
        except Exception as e:
            print(f"[QwenServer] Error reading from stdin: {e}", file=sys.stderr)
    
    def send_message(self, msg: QwenStateMessage):
        if not self.running:
            return
        
        try:
            # Convert dataclass to dict and write to stdout
            msg_dict = {}
            for field in msg.__dataclass_fields__:
                value = getattr(msg, field)
                if value is not None:
                    msg_dict[field] = value
            json_str = json.dumps(msg_dict)
            print(json_str, flush=True)
        except Exception as e:
            print(f"[QwenServer] Failed to send message: {e}", file=sys.stderr)
    
    def stop(self):
        super().stop()
        if self.stdin_thread and self.stdin_thread.is_alive():
            self.stdin_thread.join(timeout=1)


class NamedPipeServer(BaseQwenServer):
    """Named pipe server implementation"""
    
    def __init__(self, pipe_path: str):
        super().__init__()
        self.read_pipe = f"{pipe_path}.in"
        self.write_pipe = f"{pipe_path}.out"
        self.read_fd = None
        self.write_fd = None
        self.read_thread = None
    
    def start(self):
        self.running = True
        
        print(f"[QwenServer] Starting named pipe mode: {self.read_pipe} / {self.write_pipe}", file=sys.stderr)
        
        # Check if pipes exist
        if not os.path.exists(self.read_pipe):
            raise FileNotFoundError(f"Read pipe {self.read_pipe} does not exist. Create with: mkfifo {self.read_pipe}")
        if not os.path.exists(self.write_pipe):
            raise FileNotFoundError(f"Write pipe {self.write_pipe} does not exist. Create with: mkfifo {self.write_pipe}")
        
        # Open pipes
        self.read_fd = os.open(self.read_pipe, os.O_RDONLY | os.O_NONBLOCK)
        self.write_fd = os.open(self.write_pipe, os.O_WRONLY | os.O_NONBLOCK)
        
        # Start thread to read from pipe
        self.read_thread = threading.Thread(target=self._read_pipe, daemon=True)
        self.read_thread.start()
    
    def _read_pipe(self):
        """Read commands from named pipe"""
        buffer = b""
        
        while self.running:
            try:
                # Read available data
                data = os.read(self.read_fd, 4096)
                if data:
                    buffer += data
                    
                    # Process complete lines
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            cmd = self.parse_command(line_str)
                            if cmd:
                                self.message_queue.put(cmd)
                else:
                    # No data available, sleep briefly
                    time.sleep(0.01)
            except OSError:
                # No data available (EAGAIN), sleep briefly
                time.sleep(0.01)
            except Exception as e:
                print(f"[QwenServer] Error reading from pipe: {e}", file=sys.stderr)
                break
    
    def send_message(self, msg: QwenStateMessage):
        if not self.running or self.write_fd is None:
            return
        
        try:
            # Convert dataclass to dict and write to pipe
            msg_dict = {}
            for field in msg.__dataclass_fields__:
                value = getattr(msg, field)
                if value is not None:
                    msg_dict[field] = value
            json_str = json.dumps(msg_dict) + '\n'
            
            os.write(self.write_fd, json_str.encode('utf-8'))
        except Exception as e:
            print(f"[QwenServer] Failed to send to pipe: {e}", file=sys.stderr)
    
    def stop(self):
        super().stop()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1)
        
        if self.read_fd is not None:
            os.close(self.read_fd)
            self.read_fd = None
        if self.write_fd is not None:
            os.close(self.write_fd)
            self.write_fd = None


class TCPServer(BaseQwenServer):
    """TCP server implementation"""
    
    def __init__(self, port: int, host: str = "localhost"):
        super().__init__()
        self.port = port
        self.host = host
        self.server_socket = None
        self.client_socket = None
        self.buffer = ""
        self.server_thread = None
        self.client_thread = None
    
    def start(self):
        self.running = True
        
        print(f"[QwenServer] Starting TCP mode on {self.host}:{self.port}", file=sys.stderr)
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)  # Set timeout for accept to allow checking running flag
            
            print(f"[QwenServer] TCP server listening on {self.host}:{self.port}", file=sys.stderr)
            
            # Start server thread to accept connections
            self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self.server_thread.start()
            
        except Exception as e:
            print(f"[QwenServer] Failed to start TCP server: {e}", file=sys.stderr)
            self.running = False
            raise
    
    def _accept_connections(self):
        """Accept incoming TCP connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[QwenServer] Client connected from {addr[0]}:{addr[1]}", file=sys.stderr)
                
                # Close any existing client connection
                if self.client_socket:
                    self.client_socket.close()
                
                self.client_socket = client_socket
                self.client_socket.settimeout(0.1)  # Set timeout for recv to allow checking running flag
                
                # Start client handling thread
                self.client_thread = threading.Thread(target=self._handle_client, args=(client_socket,), daemon=True)
                self.client_thread.start()
                
            except socket.timeout:
                # This is expected, allows checking running flag
                continue
            except Exception as e:
                if self.running:  # Only report error if we're still supposed to be running
                    print(f"[QwenServer] Error accepting connection: {e}", file=sys.stderr)
                break
    
    def _handle_client(self, client_socket):
        """Handle communication with a TCP client"""
        buffer = ""
        
        while self.running:
            try:
                data = client_socket.recv(4096)
                if not data:
                    # Client disconnected
                    print("[QwenServer] Client disconnected", file=sys.stderr)
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        cmd = self.parse_command(line)
                        if cmd:
                            self.message_queue.put(cmd)
                            
            except socket.timeout:
                # This is expected, allows checking running flag
                continue
            except Exception as e:
                print(f"[QwenServer] Error handling client: {e}", file=sys.stderr)
                break
    
    def send_message(self, msg: QwenStateMessage):
        if not self.running or not self.client_socket:
            return
        
        try:
            # Convert dataclass to dict and send to client
            msg_dict = {}
            for field in msg.__dataclass_fields__:
                value = getattr(msg, field)
                if value is not None:
                    msg_dict[field] = value
            json_str = json.dumps(msg_dict) + '\n'
            
            self.client_socket.send(json_str.encode('utf-8'))
        except Exception as e:
            print(f"[QwenServer] Failed to send to TCP client: {e}", file=sys.stderr)
    
    def stop(self):
        super().stop()
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1)
        
        if self.client_thread and self.client_thread.is_alive():
            self.client_thread.join(timeout=1)


def create_qwen_server(
    mode: str,
    pipe_path: Optional[str] = None,
    tcp_port: Optional[int] = None,
    tcp_host: Optional[str] = None,
):
    """Factory function to create the appropriate server based on mode"""
    if mode == 'stdin':
        return StdinStdoutServer()
    elif mode == 'pipe':
        if not pipe_path:
            raise ValueError("pipe_path is required for pipe mode")
        return NamedPipeServer(pipe_path)
    elif mode == 'tcp':
        port = tcp_port or 7777
        host = tcp_host or "localhost"
        return TCPServer(port, host=host)
    else:
        raise ValueError(f"Unknown server mode: {mode}")
