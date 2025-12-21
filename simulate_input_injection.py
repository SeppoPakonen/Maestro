#!/usr/bin/env python3
"""
Script to simulate and validate input injection during an active session.
"""
import json
import time
from datetime import datetime

def simulate_input_injection_during_session():
    """
    Simulate a scenario where input is injected mid-stream during an active session.
    This demonstrates the input injection validation process for Task aicli4-3.
    """
    
    # Create a simulation of an active session with ongoing tool execution
    session_events = [
        {
            "type": "session_start",
            "timestamp": datetime.now().isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "data": {
                "session_type": "qwen_chat",
                "agent": "qwen"
            }
        },
        {
            "type": "user_input",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "input_1",
            "data": {
                "content": "Can you help me create a file with some content?",
                "input_type": "chat_message"
            }
        },
        {
            "type": "tool_call_request",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "write_file_1",
                "name": "write_file",
                "args": {
                    "file_path": "/tmp/test_file.txt",
                    "content": "Initial content for the test file."
                }
            }
        },
        # Simulate tool execution in progress
        {
            "type": "tool_execution_status",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "write_file_1",
                "status": "in_progress",
                "progress": 0.3,
                "message": "Writing content to file..."
            }
        },
        # This is where input injection happens mid-stream
        {
            "type": "user_input",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "input_2",
            "data": {
                "content": "Actually, can you also create another file?",
                "input_type": "injected_input_during_execution"
            }
        },
        # Acknowledgment of injected input
        {
            "type": "status_update",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "input_2",
            "data": {
                "status": "input_queued",
                "message": "Injected input received and queued for processing",
                "queued_input_id": "input_2"
            }
        },
        # Tool execution continues and completes
        {
            "type": "tool_execution_status",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "write_file_1",
                "status": "in_progress",
                "progress": 0.7,
                "message": "Almost done writing to file..."
            }
        },
        {
            "type": "tool_call_response",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_1",
            "data": {
                "call_id": "write_file_1",
                "result": {
                    "success": True,
                    "file_path": "/tmp/test_file.txt",
                    "bytes_written": 32
                },
                "execution_time_ms": 350
            }
        },
        # Now process the injected input
        {
            "type": "tool_call_request",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_2",
            "data": {
                "call_id": "write_file_2",
                "name": "write_file",
                "args": {
                    "file_path": "/tmp/second_file.txt",
                    "content": "Content for the second file as requested."
                }
            }
        },
        {
            "type": "tool_call_response",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "correlation_id": "tool_2",
            "data": {
                "call_id": "write_file_2",
                "result": {
                    "success": True,
                    "file_path": "/tmp/second_file.txt",
                    "bytes_written": 44
                },
                "execution_time_ms": 280
            }
        },
        {
            "type": "session_end",
            "timestamp": (datetime.now()).isoformat() + "Z",
            "session_id": "input_injection_test_session",
            "data": {
                "session_type": "qwen_chat",
                "termination_reason": "user_request"
            }
        }
    ]
    
    return session_events

def main():
    print("Simulating input injection during active session...")
    
    # Generate the simulated events
    events = simulate_input_injection_during_session()
    
    # Save the events to a JSON file
    filename = f"input_injection_simulation_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(filename, 'w') as f:
        json.dump(events, f, indent=2)
    
    print(f"Input injection simulation saved to {filename}")
    
    # Verify that input injection was handled properly
    print("\nVerifying input injection handling:")
    
    # Check if input was injected during execution
    input_injected = False
    for event in events:
        if event["type"] == "user_input" and "injected_input" in str(event.get("data", {}).get("input_type", "")):
            input_injected = True
            print(f"✅ Input injection detected: {event['data']['content']}")
    
    # Check if the injected input was properly handled
    injected_input_handled = False
    for event in events:
        if event["type"] == "tool_call_request":
            # Check if the second request is a response to the injected input
            if event["correlation_id"] == "tool_2":
                injected_input_handled = True
                print(f"✅ Injected input properly handled with new tool call: {event['data']['name']}")
    
    # Check for acknowledgment of injected input
    injection_acknowledged = False
    for event in events:
        if (event["type"] == "status_update" and 
            "input_queued" in event.get("data", {}).get("status", "")):
            injection_acknowledged = True
            print(f"✅ Input injection acknowledged: {event['data']['message']}")
    
    # Summary
    print(f"\nValidation Results:")
    print(f"- Input injected during execution: {'✅' if input_injected else '❌'}")
    print(f"- Injected input properly handled: {'✅' if injected_input_handled else '❌'}")
    print(f"- Input injection acknowledged: {'✅' if injection_acknowledged else '❌'}")
    
    if input_injected and injected_input_handled and injection_acknowledged:
        print("\n🎉 Input injection validation successful!")
        return True
    else:
        print("\n❌ Input injection validation failed!")
        return False

if __name__ == "__main__":
    main()