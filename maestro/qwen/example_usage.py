"""
Example usage of the Qwen Python Implementation

This demonstrates how to use the Python implementation of Qwen functionality.
"""
import sys
import os
import threading
import time

# Add the maestro/qwen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.qwen.main import QwenManager


def example_stdin_mode():
    """Example using stdin/stdout mode"""
    print("=== Example: Stdin/Stdout Mode ===")
    
    # Create a manager instance
    manager = QwenManager()
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager in stdin mode")
        return
    
    print("Manager started in stdin mode. You can now send commands to stdin.")
    print("For example, try echoing a command:")
    print("echo '{\"type\":\"user_input\",\"content\":\"Hello\"}' | python3 example_usage.py")
    
    # Keep running for a few seconds to demonstrate
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping manager...")
    
    manager.stop()


def example_tcp_mode():
    """Example using TCP mode (would require a client to connect)"""
    print("=== Example: TCP Mode ===")
    
    # Create a manager instance
    manager = QwenManager()
    
    # Start in TCP mode on port 8080
    success = manager.start(mode='tcp', tcp_port=8080)
    if not success:
        print("Failed to start manager in TCP mode")
        return
    
    print("Manager started in TCP mode on port 8080")
    print("A TCP server is now listening for connections...")
    
    # Keep running for demonstration
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("\nStopping manager...")
    
    manager.stop()


def example_pipe_mode():
    """Example using named pipe mode (would require pipes to exist)"""
    print("=== Example: Named Pipe Mode ===")
    
    # Note: For this to work, you would need to create the named pipes first:
    # mkfifo /tmp/qwen_pipe.in /tmp/qwen_pipe.out
    
    # Create a manager instance
    manager = QwenManager()
    
    try:
        # Start in pipe mode
        success = manager.start(mode='pipe', pipe_path='/tmp/qwen_pipe')
        if not success:
            print("Failed to start manager in pipe mode")
            return
        
        print("Manager started in pipe mode using /tmp/qwen_pipe")
        print("Ready to read from /tmp/qwen_pipe.in and write to /tmp/qwen_pipe.out")
        
        # Keep running for demonstration
        time.sleep(5)
        
    except FileNotFoundError as e:
        print(f"Named pipe not found. Create with: mkfifo /tmp/qwen_pipe.in /tmp/qwen_pipe.out")
        print(f"Error: {e}")
    
    finally:
        manager.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Example usage of Qwen Python Implementation")
    parser.add_argument("mode", choices=['stdin', 'tcp', 'pipe'], nargs='?', default='stdin',
                        help="Mode to run example (default: stdin)")
    
    args = parser.parse_args()
    
    if args.mode == 'stdin':
        example_stdin_mode()
    elif args.mode == 'tcp':
        example_tcp_mode()
    elif args.mode == 'pipe':
        example_pipe_mode()