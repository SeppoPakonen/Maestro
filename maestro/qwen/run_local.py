#!/usr/bin/env python3
"""
Run Qwen Manager with the local built version of qwen-code
"""
import sys
import os
import time

# Add the maestro/qwen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.qwen.main import QwenManager


def run_local_qwen():
    """Run QwenManager with the local built version"""
    print("Starting QwenManager with local built qwen-code...")
    
    # Set up environment to include HOME and use the local built version
    env = os.environ.copy()
    env['HOME'] = os.path.expanduser('~')
    
    # Path to the locally built qwen-code
    qwen_executable = "/common/active/sblo/Dev/Maestro/external/ai-agents/qwen-code/node packages/cli/dist/index.js"
    
    manager = QwenManager(qwen_executable=qwen_executable, env=env)
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager with local built version")
        return False
    
    print("QwenManager started with local built qwen-code.")
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


def run_with_npx():
    """Run QwenManager with npx (may not have server-mode)"""
    print("Starting QwenManager with npx qwen-code...")
    
    # Set up environment to include HOME
    env = os.environ.copy()
    env['HOME'] = os.path.expanduser('~')
    
    manager = QwenManager(qwen_executable="npx qwen-code", env=env)
    
    # Start in stdin mode
    success = manager.start(mode='stdin')
    if not success:
        print("Failed to start manager with npx")
        return False
    
    print("QwenManager started with npx qwen-code.")
    print("Note: This may not work if npx version doesn't have --server-mode option.")
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Qwen Manager with proper configuration")
    parser.add_argument("--local", action="store_true", 
                        help="Use local built version instead of npx")
    
    args = parser.parse_args()
    
    if args.local:
        run_local_qwen()
    else:
        run_with_npx()