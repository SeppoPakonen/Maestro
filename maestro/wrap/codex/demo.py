"""
Demonstration script for the Codex wrapper.

This script shows how to use the Codex wrapper to interact with the codex CLI.
"""
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import CodexWrapper


def demo_basic_usage():
    """Demonstrate basic usage of the Codex wrapper."""
    print("=== Codex Wrapper Demo ===")
    print("This demo shows the basic usage of the Codex wrapper.")
    print()
    
    # Create a temporary socket path for this demo
    socket_path = "/tmp/codex_demo.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)
    
    print(f"1. Creating wrapper with socket at: {socket_path}")
    wrapper = CodexWrapper(width=240, height=60, socket_path=socket_path)
    
    print("2. Starting codex wrapper (this would start the actual codex process)")
    try:
        # Note: This will fail if codex binary is not installed, but that's expected in demo
        wrapper.start()
        print("   Codex process started successfully")

        # Briefly wait and then stop
        time.sleep(1)
        wrapper.quit()
    except Exception as e:
        print(f"   Expected error (codex may not be installed): {e}")
        print("   This is normal if the codex binary is not available")
        print("   The wrapper would work if codex was installed")
    
    print()
    print("3. Turing Machine State Analysis:")
    print(f"   Initial state: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate some state transitions
    wrapper.turing_machine.transition("prompt_start")
    print(f"   After prompt_start: {wrapper.turing_machine.get_current_state().value}")
    
    wrapper.turing_machine.transition("input_complete")
    print(f"   After input_complete: {wrapper.turing_machine.get_current_state().value}")
    
    wrapper.turing_machine.transition("response_start")
    print(f"   After response_start: {wrapper.turing_machine.get_current_state().value}")
    
    wrapper.turing_machine.transition("tool_detected")
    print(f"   After tool_detected: {wrapper.turing_machine.get_current_state().value}")
    
    print()
    print("4. Parser Demonstration:")
    from maestro.wrap.codex.parser import CodexParser
    parser = CodexParser()
    
    # Parse an input
    input_text = "What is 2+2?"
    parsed_input = parser.parse_input(input_text)
    print(f"   Input: '{input_text}' -> Parsed type: {parsed_input.metadata['type']}")
    
    # Parse an output with tool usage
    output_text = "The answer is 4.\n[EXEC: echo 'Math confirmed']"
    parsed_output = parser.parse_output(output_text)
    print(f"   Output: '{output_text[:30]}...' -> Has tools: {parsed_output.metadata['has_tools']}")
    print(f"   Tool detected: {parsed_output.tools[0].tool_name} with args: {parsed_output.tools[0].arguments}")
    
    print()
    print("5. JSON Encoding:")
    json_result = parser.encode_as_json(parsed_input, parsed_output)
    print(f"   Encoded as JSON (first 100 chars): {json_result[:100]}...")
    
    print()
    print("6. Command Handling:")
    commands = ["/compact", "/new", "/quit", "/model"]
    for cmd in commands:
        parsed_cmd = parser.parse_input(cmd)
        print(f"   Command '{cmd}' -> Type: {parsed_cmd.metadata['type']}, Command: {parsed_cmd.metadata['command']}")
    
    print()
    print("Demo completed!")


if __name__ == "__main__":
    demo_basic_usage()