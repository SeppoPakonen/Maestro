#!/usr/bin/env python3
"""
Test script for Qwen Python Implementation

This script tests the Python implementation of Qwen functionality
"""
import sys
import os
import time
import threading
import subprocess
from typing import Optional

# Add the maestro/qwen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.qwen.server import create_qwen_server, QwenUserInput
from maestro.qwen.client import QwenClient, QwenClientConfig, MessageHandlers
from maestro.qwen.main import QwenManager


def test_server_only():
    """Test the server functionality without connecting to a real qwen service"""
    print("Testing server functionality...")
    
    # Create a stdin server
    server = create_qwen_server('stdin')
    server.start()
    
    # Send a test message
    from maestro.qwen.server import QwenInfoMessage
    test_msg = QwenInfoMessage(type="info", message="Test message", id=1)
    server.send_message(test_msg)
    
    # Wait a bit and then stop
    time.sleep(0.1)
    server.stop()
    
    print("Server test completed.")


def test_client_creation():
    """Test creating a client (without starting it necessarily)"""
    print("Testing client creation...")
    
    config = QwenClientConfig()
    config.qwen_executable = "npx qwen-code"
    config.qwen_args = ["--help"]  # Just to test if command works
    config.verbose = True
    
    client = QwenClient(config)
    
    # Set up basic handlers
    handlers = MessageHandlers()
    client.set_handlers(handlers)
    
    print("Client creation test completed.")


def test_manager():
    """Test the QwenManager (without actually starting the service)"""
    print("Testing QwenManager...")
    
    manager = QwenManager()
    
    # We won't actually start it since we need qwen-code to be available
    # Instead, let's just check that the class can be instantiated
    print(f"QwenManager created: {manager}")
    
    print("QwenManager test completed.")


def test_imports():
    """Test that all modules can be imported without errors"""
    print("Testing imports...")
    
    try:
        from maestro.qwen import server
        from maestro.qwen import client
        from maestro.qwen import main
        print("All modules imported successfully.")
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    
    return True


def run_tests():
    """Run all tests"""
    print("Starting tests for Qwen Python Implementation...\n")
    
    success = True
    
    try:
        if not test_imports():
            success = False
        
        test_server_only()
        test_client_creation()
        test_manager()
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print(f"\nTests completed. Success: {success}")
    return success


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)