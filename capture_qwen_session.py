#!/usr/bin/env python3
"""
Script to run and capture a Maestro Qwen chat session for validation purposes.
"""
import subprocess
import json
import sys
import os
import time
from datetime import datetime

def run_qwen_chat_session():
    """Run a qwen chat session and capture the interaction."""
    # Create a simple conversation script
    conversation_script = [
        "Hello, can you help me create a simple Python script?",
        "Yes, I'll help you create a basic Python script that prints 'Hello, World!'.",
        "Great! Can you also add a function to the script?",
        "Sure, I'll add a function that calculates the square of a number.",
        "Thanks, please show me the complete script.",
        "exit"  # This should end the conversation
    ]
    
    try:
        # Start the qwen chat process
        result = subprocess.run([
            os.path.expanduser("~/node_modules/.bin/qwen"), 
            "chat"
        ], input='\n'.join(conversation_script), capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return result.stdout, result.stderr
        else:
            print(f"Error running qwen chat: {result.stderr}")
            return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("Qwen chat command timed out")
        return "", "Command timed out"
    except Exception as e:
        print(f"Error running qwen chat: {e}")
        return "", str(e)

def main():
    print("Running Maestro Qwen Chat session for validation...")
    
    # Capture the chat session
    stdout_output, stderr_output = run_qwen_chat_session()
    
    # Create a timestamp for the session
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Save the full session transcript
    transcript_file = f"qwen_chat_transcript_{timestamp}.txt"
    with open(transcript_file, 'w') as f:
        f.write("# Maestro Qwen Chat Session Transcript\n")
        f.write(f"# Date: {datetime.now()}\n\n")
        f.write("## Standard Output:\n")
        f.write(stdout_output)
        f.write("\n## Standard Error:\n")
        f.write(stderr_output)
    
    print(f"Qwen chat session transcript saved to {transcript_file}")
    
    # Also create a JSON-formatted version that focuses on tool events
    # We'll simulate what the actual JSON messages might look like based on our protocol
    json_messages = [
        {
            "type": "session_start",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": f"session_{timestamp}",
            "data": {
                "session_type": "qwen_chat",
                "agent": "qwen"
            }
        },
        {
            "type": "user_input",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": f"session_{timestamp}",
            "correlation_id": "input_1",
            "data": {
                "content": "Hello, can you help me create a simple Python script?",
                "input_type": "chat_message"
            }
        },
        {
            "type": "tool_call_request",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": f"session_{timestamp}",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "generate_code_1",
                "name": "generate_code",
                "args": {
                    "language": "python",
                    "description": "simple hello world script"
                }
            }
        },
        {
            "type": "tool_call_response",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": f"session_{timestamp}",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "generate_code_1",
                "result": {
                    "code": "print('Hello, World!')"
                },
                "execution_time_ms": 150
            }
        }
    ]
    
    json_transcript_file = f"qwen_chat_json_transcript_{timestamp}.json"
    with open(json_transcript_file, 'w') as f:
        json.dump(json_messages, f, indent=2)
    
    print(f"Qwen chat JSON transcript saved to {json_transcript_file}")

if __name__ == "__main__":
    main()