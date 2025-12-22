#!/usr/bin/env python3
"""
Test script that sends valid commands to the Qwen service
"""
import sys
import os
import json
import time

# Add the maestro/qwen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.qwen.main import QwenManager


def test_with_valid_commands():
    """Test the QwenManager with valid JSON commands"""
    print("Testing QwenManager with valid commands...")
    
    # Create a manager instance
    manager = QwenManager()
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager")
        return False
    
    print("Manager started. Waiting for init message...")
    
    # Wait a bit for initialization
    time.sleep(2)
    
    # Send a test user input command (this should be done via stdin in real usage)
    # For testing, we'll just let the user interact via stdin
    print("\nYou can now send commands to the Qwen service:")
    print('Example: echo \'{"type":"user_input","content":"Hello, Qwen!"}\' | python3 -c "import sys; print(sys.stdin.read())"')
    print("Or interact directly with the stdin of this process.")
    print("Press Ctrl+C to stop.")
    
    try:
        while manager.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping manager...")
    
    manager.stop()
    return True


def test_manual_interaction():
    """Test by allowing manual interaction"""
    print("Starting QwenManager for manual interaction...")
    print("After starting, you can send JSON commands to stdin, for example:")
    print('{"type":"user_input","content":"Hello, Qwen!"}')
    print('{"type":"tool_approval","tool_id":"123","approved":true}')
    print()
    
    # Create a manager instance
    manager = QwenManager()
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager")
        return False
    
    print("QwenManager started in stdin mode. Send JSON commands to stdin.")
    print("Examples of valid commands:")
    print('  {"type":"user_input","content":"Hello"}')
    print('  {"type":"tool_approval","tool_id":"some_id","approved":true}')
    print('  {"type":"interrupt"}')
    print()
    print("Press Ctrl+C to stop.")
    
    try:
        while manager.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping manager...")
    
    manager.stop()
    return True


if __name__ == "__main__":
    test_manual_interaction()