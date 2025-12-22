"""
Main Qwen Implementation Module

This module implements the main functionality that was in the C++ QwenTCPServer,
combining both server and client functionality to create a bridge between
the frontend and the actual Qwen service.
"""
import sys
import threading
import time
from typing import Optional, Dict, Any, List
from .server import create_qwen_server, BaseQwenServer, QwenInitMessage, QwenConversationMessage, QwenToolGroup, QwenStatusUpdate, QwenInfoMessage, QwenErrorMessage, QwenCompletionStats
from .client import QwenClient, QwenClientConfig, MessageHandlers


class QwenManager:
    """Main manager class that combines server and client functionality"""

    def __init__(self, qwen_executable: str = "npx qwen-code", env: Optional[Dict[str, str]] = None):
        self.qwen_executable = qwen_executable
        self.env = env
        self.server: Optional[BaseQwenServer] = None
        self.client: Optional[QwenClient] = None
        self.running = False
        self.main_thread: Optional[threading.Thread] = None
    
    def start(
        self,
        mode: str = 'stdin',
        pipe_path: Optional[str] = None,
        tcp_port: Optional[int] = None,
        tcp_host: Optional[str] = None,
    ):
        """Start the Qwen manager with specified communication mode"""
        self.running = True
        
        # Create server based on mode
        try:
            self.server = create_qwen_server(mode, pipe_path, tcp_port, tcp_host)
            self.server.start()
        except Exception as e:
            print(f"[QwenManager] Failed to start server: {e}", file=sys.stderr)
            return False
        
        # Create and configure client
        client_config = QwenClientConfig()
        client_config.qwen_executable = self.qwen_executable
        client_config.qwen_args = ["--server-mode", "stdin"]
        client_config.verbose = True
        client_config.env = self.env
        
        self.client = QwenClient(client_config)
        
        # Set up message handlers to forward responses from qwen-code to the server
        handlers = MessageHandlers()
        
        # When we get a conversation response from qwen-code, forward it to the server
        handlers.on_conversation = self._handle_conversation
        handlers.on_tool_group = self._handle_tool_group
        handlers.on_status = self._handle_status
        handlers.on_info = self._handle_info
        handlers.on_error = self._handle_error
        handlers.on_init = self._handle_init
        handlers.on_completion_stats = self._handle_completion_stats
        
        self.client.set_handlers(handlers)
        
        # Start the qwen-code client
        if not self.client.start():
            print(f"[QwenManager] Warning: Failed to start qwen-code client: {self.client.get_last_error()}", file=sys.stderr)
            print("[QwenManager] Continuing with server functionality only.", file=sys.stderr)
        
        # Start main processing loop
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        print(f"[QwenManager] Started in {mode} mode", file=sys.stderr)
        return True
    
    def _handle_conversation(self, msg: QwenConversationMessage):
        """Handle conversation messages from the client and forward to server"""
        if msg.role == 'assistant':
            print(f"[QwenManager] Forwarding assistant response to server: {msg.content[:100]}...", file=sys.stderr)
        self.server.send_message(msg)
    
    def _handle_tool_group(self, msg: QwenToolGroup):
        """Handle tool group messages from the client and forward to server"""
        print(f"[QwenManager] Forwarding tool_group id {msg.id} to server", file=sys.stderr)
        self.server.send_message(msg)
    
    def _handle_status(self, msg: QwenStatusUpdate):
        """Handle status messages from the client and forward to server"""
        self.server.send_message(msg)
    
    def _handle_info(self, msg: QwenInfoMessage):
        """Handle info messages from the client and forward to server"""
        self.server.send_message(msg)
    
    def _handle_error(self, msg: QwenErrorMessage):
        """Handle error messages from the client and forward to server"""
        self.server.send_message(msg)
    
    def _handle_init(self, msg: QwenInitMessage):
        """Handle init messages from the client and forward to server"""
        self.server.send_message(msg)
    
    def _handle_completion_stats(self, msg: QwenCompletionStats):
        """Handle completion stats from the client and forward to server"""
        self.server.send_message(msg)
    
    def _main_loop(self):
        """Main processing loop that handles communication between server and client"""
        while self.running:
            if self.server and self.client and self.client.is_running():
                # Check for commands from the server and forward to client
                try:
                    cmd = self.server.receive_command()
                    if cmd:
                        if cmd.type == 'user_input':
                            print(f"[QwenManager] Forwarding user input to qwen-code: {cmd.content[:100]}...", file=sys.stderr)
                            self.client.send_user_input(cmd.content)
                        elif cmd.type == 'tool_approval':
                            print(f"[QwenManager] Forwarding tool approval for {cmd.tool_id} (approved={cmd.approved})", file=sys.stderr)
                            self.client.send_tool_approval(cmd.tool_id, cmd.approved)
                        elif cmd.type == 'interrupt':
                            self.client.send_interrupt()
                        elif cmd.type == 'model_switch':
                            self.client.send_model_switch(cmd.model_id)
                except Exception as e:
                    print(f"[QwenManager] Error processing server command: {e}", file=sys.stderr)
            
            # Small delay to prevent busy-waiting
            time.sleep(0.01)
    
    def stop(self):
        """Stop the Qwen manager"""
        self.running = False
        
        if self.client:
            self.client.stop()
            self.client = None
        
        if self.server:
            self.server.stop()
            self.server = None
        
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=1)
        
        print("[QwenManager] Stopped", file=sys.stderr)
    
    def is_running(self) -> bool:
        """Check if the manager is running"""
        return self.running


def run_qwen_server(
    mode: str = 'stdin',
    pipe_path: Optional[str] = None,
    tcp_port: Optional[int] = None,
    tcp_host: Optional[str] = None,
    qwen_executable: Optional[str] = None,
):
    """Run the Qwen server with the specified mode"""
    manager = QwenManager(qwen_executable=qwen_executable or "npx qwen-code")
    
    try:
        success = manager.start(mode, pipe_path, tcp_port, tcp_host)
        if not success:
            print("[QwenManager] Failed to start Qwen manager", file=sys.stderr)
            return False
        
        print(f"[QwenManager] Qwen server running in {mode} mode. Press Ctrl+C to stop.", file=sys.stderr)
        
        # Keep running until interrupted
        try:
            while manager.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[QwenManager] Received interrupt signal, stopping...", file=sys.stderr)
        
        manager.stop()
        return True
        
    except Exception as e:
        print(f"[QwenManager] Error running Qwen server: {e}", file=sys.stderr)
        if manager:
            manager.stop()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Qwen Server Implementation")
    parser.add_argument("--mode", choices=['stdin', 'pipe', 'tcp'], default='stdin',
                        help="Communication mode (default: stdin)")
    parser.add_argument("--pipe-path", type=str, help="Named pipe path for pipe mode")
    parser.add_argument("--tcp-host", type=str, default="127.0.0.1", help="TCP host (default: 127.0.0.1)")
    parser.add_argument("--tcp-port", type=int, default=7777, help="TCP port for tcp mode (default: 7777)")
    parser.add_argument(
        "--qwen-executable",
        type=str,
        help="Path to qwen-code.sh or a qwen-code executable",
    )
    
    args = parser.parse_args()
    
    run_qwen_server(
        args.mode,
        args.pipe_path,
        args.tcp_port,
        args.tcp_host,
        args.qwen_executable,
    )
