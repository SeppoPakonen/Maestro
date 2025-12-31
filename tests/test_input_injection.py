#!/usr/bin/env python3
"""
Test script to validate input injection during active qwen sessions for the AI CLI Live Tool Protocol.
"""
import json
import subprocess
import sys
import time
import os
import shutil
from threading import Thread
from queue import Queue

import pytest


def run_qwen_session_with_injection():
    """
    This test demonstrates the concept of input injection during an active qwen session.
    Since qwen runs as a subprocess, we need to handle input injection through
    its API or by using the structured server mode.
    """
    print("Testing input injection during active qwen session...")
    
    # First, let's run qwen in server mode to allow for input injection
    # This approach uses qwen's server mode to allow external input injection
    cmd = [
        "qwen",
        "--yolo",  # Auto-approve all permissions
        "--output-format", "stream-json",  # Use stream-json for detailed events
        "--prompt-interactive"  # Start interactive mode after processing initial prompt
    ]
    
    # The initial prompt will request a long-running operation to allow for injection
    initial_input = "List the files in the current directory and then wait for further instructions."
    
    try:
        # Start the qwen process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Send the initial prompt
        process.stdin.write(initial_input + "\n")
        process.stdin.flush()
        
        # Read and process the initial response
        print("Reading initial response from qwen...")
        for line in process.stdout:
            event = json.loads(line.strip())
            print(f"Event: {event['type']}")
            
            # If we see that the directory listing is complete, we'll inject more input
            if event['type'] == 'assistant' and 'content' in event['message']:
                content = event['message']['content']
                # Check if this is the final response (not requiring more tools)
                if any(isinstance(item, dict) and item.get('type') == 'text' for item in content):
                    print("Detected final response. Injecting additional input...")
                    
                    # Inject additional input into the session
                    additional_input = "Now create a new test file named 'input_injection_test.txt' with the content 'Input injection successful'."
                    process.stdin.write(additional_input + "\n")
                    process.stdin.flush()
                    
                    # Continue reading responses
                    break
        
        # Continue reading the response to the injected input
        print("Reading response to injected input...")
        for line in process.stdout:
            event = json.loads(line.strip())
            print(f"Event: {event['type']}")
            
            # Look for tool use events related to file creation
            if event['type'] == 'assistant' and 'content' in event['message']:
                content = event['message']['content']
                if any(isinstance(item, dict) and item.get('type') == 'tool_use' and item.get('name') == 'write_file' for item in content):
                    print("Detected write_file tool use - input injection successful!")
                    break
            
            # Check if session is ending
            if event['type'] == 'result':
                print("Session ended.")
                break
        
        # Close the process
        process.stdin.close()
        stderr_output = process.stderr.read()
        if stderr_output:
            print(f"Stderr: {stderr_output}")
        
        return_code = process.wait()
        print(f"Process completed with return code: {return_code}")
        
    except Exception as e:
        print(f"Error during input injection test: {e}")
        return False
    
    return True


def test_direct_input_injection():
    """
    Test direct input injection using qwen's server mode capabilities.
    This method uses qwen in server mode which allows external input injection.
    """
    if os.environ.get("MAESTRO_RUN_QWEN_TESTS") != "1" or not shutil.which("qwen"):
        pytest.skip("qwen integration test disabled or qwen binary not available")

    print("\nTesting direct input injection via server mode...")
    
    # Run qwen in server mode with stdin communication
    cmd = [
        "qwen",
        "--yolo",
        "--channel", "SDK",
        "--input-format", "text",
        "--output-format", "stream-json"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send first input
        first_input = "What files are in the current directory?"
        process.stdin.write(first_input + "\n")
        process.stdin.flush()
        
        # Read response to first input
        print("Reading response to first input...")
        response_count = 0
        for line in process.stdout:
            event = json.loads(line.strip())
            print(f"Event: {event['type']}")
            response_count += 1
            if response_count > 5:  # Limit to first few events
                break
        
        # Inject second input while session is active
        second_input = "Create a test file with some content."
        process.stdin.write(second_input + "\n")
        process.stdin.flush()
        
        # Read response to second input
        print("Reading response to injected input...")
        response_count = 0
        for line in process.stdout:
            event = json.loads(line.strip())
            print(f"Event: {event['type']}")
            response_count += 1
            if response_count > 5 or event['type'] == 'result':  # Stop at result or after 5 events
                break
        
        process.stdin.close()
        process.terminate()
        process.wait()
        
        print("Direct input injection test completed.")
        return True
        
    except Exception as e:
        print(f"Error during direct input injection test: {e}")
        return False


if __name__ == "__main__":
    print("Starting input injection validation tests for AI CLI Live Tool Protocol...")
    
    success1 = run_qwen_session_with_injection()
    success2 = test_direct_input_injection()
    
    if success1 or success2:
        print("\nInput injection validation tests completed successfully.")
        sys.exit(0)
    else:
        print("\nInput injection validation tests failed.")
        sys.exit(1)
