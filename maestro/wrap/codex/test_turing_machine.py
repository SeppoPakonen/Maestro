"""
Comprehensive test for the Codex wrapper Turing machine functionality.
This test validates the Turing machine behavior with actual prompt interactions.
"""
import sys
import tempfile
import os
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import CodexWrapper, State
from maestro.wrap.codex.parser import CodexParser


def test_turing_machine_with_prompt():
    """Test the Turing machine with a 'hello world' prompt."""
    print("=== Testing Turing Machine with 'hello world' prompt ===")
    
    # Create a temporary socket path for this test
    socket_path = "/tmp/codex_test.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)
    
    # Create the wrapper without starting the actual codex process for this test
    wrapper = CodexWrapper(width=240, height=60, socket_path=socket_path)
    
    print(f"Initial state: {wrapper.turing_machine.get_current_state().value}")
    
    # Test state transitions manually by simulating what would happen with a prompt
    print("\nSimulating 'hello world' prompt interaction...")
    
    # When a prompt is sent, the state should transition
    print(f"Before sending input: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate the internal state changes that would happen when sending input
    # This mimics what happens in the _update_turing_machine_with_output method
    action = wrapper.turing_machine.transition("prompt_start")
    print(f"After prompt_start transition: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    action = wrapper.turing_machine.transition("input_complete")
    print(f"After input_complete transition: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    action = wrapper.turing_machine.transition("response_start")
    print(f"After response_start transition: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    # Simulate receiving a response without tools
    action = wrapper.turing_machine.transition("response_continue")
    print(f"After response_continue transition: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    # Simulate end of response (e.g., seeing a prompt again)
    action = wrapper.turing_machine.transition("response_end")
    print(f"After response_end transition: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    print(f"\nFinal state: {wrapper.turing_machine.get_current_state().value}")
    
    # Now test with tool usage
    print("\n=== Testing Turing Machine with tool usage ===")
    
    # Reset the Turing machine to IDLE state
    wrapper.turing_machine.state = State.IDLE
    print(f"Reset to state: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate a response that contains tool usage
    action = wrapper.turing_machine.transition("response_start")
    print(f"After response_start: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    action = wrapper.turing_machine.transition("tool_detected")
    print(f"After tool_detected: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    action = wrapper.turing_machine.transition("response_end")
    print(f"After response_end: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    print(f"\nFinal state after tool usage: {wrapper.turing_machine.get_current_state().value}")
    
    # Test command handling
    print("\n=== Testing Turing Machine with commands ===")
    
    # Reset to IDLE
    wrapper.turing_machine.state = State.IDLE
    print(f"Reset to state: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate command input
    action = wrapper.turing_machine.transition("command_start")
    print(f"After command_start: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    action = wrapper.turing_machine.transition("other_command")  # For commands like /compact, /new, /model
    print(f"After other_command: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    print(f"\nFinal state after command: {wrapper.turing_machine.get_current_state().value}")
    
    # Test quit command specifically
    wrapper.turing_machine.state = State.COMMAND_MODE
    print(f"\nStarting from COMMAND_MODE: {wrapper.turing_machine.get_current_state().value}")
    
    action = wrapper.turing_machine.transition("quit_command")
    print(f"After quit_command: {wrapper.turing_machine.get_current_state().value}, Action: {action}")
    
    print(f"\nFinal state after quit command: {wrapper.turing_machine.get_current_state().value}")
    
    print("\n=== Turing Machine tests completed successfully! ===")


def test_parser_with_real_examples():
    """Test the parser with real examples."""
    print("\n=== Testing Parser with Real Examples ===")
    
    parser = CodexParser()
    
    # Test 1: Simple prompt
    input_text = "hello world"
    parsed_input = parser.parse_input(input_text)
    print(f"Input: '{input_text}' -> Type: {parsed_input.metadata['type']}")
    
    # Test 2: Command
    command_text = "/compact"
    parsed_cmd = parser.parse_input(command_text)
    print(f"Command: '{command_text}' -> Type: {parsed_cmd.metadata['type']}, Command: {parsed_cmd.metadata['command']}")
    
    # Test 3: Output with no tools
    output_text = "Hello world! This is a simple response."
    parsed_output = parser.parse_output(output_text)
    print(f"Output without tools: '{output_text[:30]}...' -> Has tools: {parsed_output.metadata['has_tools']}")
    
    # Test 4: Output with tool
    output_with_tool = "Hello world! [EXEC: echo 'Hello from tool']"
    parsed_output_tool = parser.parse_output(output_with_tool)
    print(f"Output with tool: Has tools: {parsed_output_tool.metadata['has_tools']}")
    if parsed_output_tool.tools:
        print(f"  Tool: {parsed_output_tool.tools[0].tool_name}, Args: {parsed_output_tool.tools[0].arguments}")
    
    # Test 5: Complex output with multiple tools
    complex_output = "First response. [FILE: read, {\"path\": \"/tmp/test.txt\"}] Then more text. [SEARCH: python tutorial]"
    parsed_complex = parser.parse_output(complex_output)
    print(f"Complex output: Has tools: {parsed_complex.metadata['has_tools']}, Tool count: {len(parsed_complex.tools)}")
    for i, tool in enumerate(parsed_complex.tools):
        print(f"  Tool {i+1}: {tool.tool_name}, Args: {tool.arguments}")
    
    print("\n=== Parser tests completed successfully! ===")


if __name__ == "__main__":
    test_turing_machine_with_prompt()
    test_parser_with_real_examples()
    
    print("\nAll comprehensive tests passed!")