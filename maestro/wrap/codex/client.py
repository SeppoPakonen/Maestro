"""
Client module for the Codex wrapper.

This module provides a client interface to communicate with the codex wrapper
via the Unix domain socket.
"""
import json
import socket
from typing import Dict, Any, Optional


class CodexClient:
    """
    Client for communicating with the Codex wrapper.
    
    This class provides methods to send commands and receive responses
    from the codex wrapper process.
    """
    
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.socket: Optional[socket.socket] = None
    
    def connect(self):
        """Connect to the codex wrapper socket."""
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(self.socket_path)
    
    def disconnect(self):
        """Disconnect from the codex wrapper."""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_input(self, input_text: str) -> Dict[str, Any]:
        """Send an input prompt to the codex wrapper."""
        if not self.socket:
            raise ConnectionError("Not connected to codex wrapper")
        
        message = {
            "type": "input",
            "content": input_text
        }
        
        self.socket.send(json.dumps(message).encode('utf-8'))
        
        # Receive response
        response_data = self.socket.recv(4096).decode('utf-8')
        return json.loads(response_data)
    
    def send_command(self, command: str) -> Dict[str, Any]:
        """Send a command to the codex wrapper."""
        if not self.socket:
            raise ConnectionError("Not connected to codex wrapper")
        
        message = {
            "type": "command",
            "content": command
        }
        
        self.socket.send(json.dumps(message).encode('utf-8'))
        
        # Receive response
        response_data = self.socket.recv(4096).decode('utf-8')
        return json.loads(response_data)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the codex wrapper."""
        if not self.socket:
            raise ConnectionError("Not connected to codex wrapper")
        
        message = {
            "type": "status"
        }
        
        self.socket.send(json.dumps(message).encode('utf-8'))
        
        # Receive response
        response_data = self.socket.recv(4096).decode('utf-8')
        return json.loads(response_data)


def main():
    """Example usage of the CodexClient."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Codex Client')
    parser.add_argument('--socket-path', type=str, default='/tmp/codex_wrapper.sock',
                        help='Unix socket path for client communication')
    
    args = parser.parse_args()
    
    client = CodexClient(args.socket_path)
    
    try:
        client.connect()
        print("Connected to codex wrapper. Type 'quit' to exit.")
        
        while True:
            user_input = input('> ')
            if user_input.lower() == 'quit':
                break
            
            # Send input to codex wrapper
            response = client.send_input(user_input)
            print(f"Response: {response}")
            
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()