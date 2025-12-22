#!/usr/bin/env python3
"""
Test script that uses the existing Qwen configuration to connect to the service
"""
import sys
import os
import json
import time

# Add the maestro/qwen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.qwen.main import QwenManager


def test_with_existing_config():
    """Test the QwenManager using existing configuration in ~/.qwen"""
    print("Testing QwenManager with existing configuration...")
    
    # Create a manager instance with environment that includes HOME
    # This should allow the qwen service to find the config in ~/.qwen
    env = os.environ.copy()
    env['HOME'] = os.path.expanduser('~')  # Ensure HOME is set properly
    
    manager = QwenManager(env=env)
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager")
        return False
    
    print("Manager started with existing configuration. Waiting for init message...")
    
    # Wait a bit for initialization
    time.sleep(3)
    
    print("QwenManager is running with OAuth configuration from ~/.qwen")
    print("Send JSON commands to stdin, for example:")
    print('{"type":"user_input","content":"Hello, Qwen!"}')
    print()
    print("Press Ctrl+C to stop.")
    
    try:
        while manager.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping manager...")
    
    manager.stop()
    return True


def test_hello_world():
    """Test by sending a simple hello world command through stdin"""
    print("This test requires manual input.")
    print("After starting, send a JSON command like:")
    print('{"type":"user_input","content":"Hello, Qwen!"}')
    print()
    
    # Create a manager instance with environment that includes HOME
    env = os.environ.copy()
    env['HOME'] = os.path.expanduser('~')
    
    manager = QwenManager(qwen_executable="npx qwen-code", env=env)
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager")
        return False
    
    print("QwenManager started in stdin mode with OAuth config.")
    print("You can now send JSON commands to this process's stdin.")
    print("For example, you can run in another terminal:")
    print('echo \'{"type":"user_input","content":"Hello, Qwen!"}\' | python3 -c "import sys; import time; [print(line, end=\'\') for line in sys.stdin]; time.sleep(10)"')
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Qwen with existing configuration")
    parser.add_argument("test", choices=['config', 'hello'], nargs='?', default='config',
                        help="Which test to run (default: config)")
    
    args = parser.parse_args()
    
    if args.test == 'config':
        test_with_existing_config()
    elif args.test == 'hello':
        test_hello_world()