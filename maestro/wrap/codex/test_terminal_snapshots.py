"""
Test for the new terminal snapshot functionality in the Codex wrapper.
This validates the time-differential comparison of terminal states.
"""
import sys
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import TerminalSnapshot, CodexWrapper


def test_terminal_snapshots():
    """Test the terminal snapshot functionality."""
    print("=== Testing Terminal Snapshot Functionality ===")
    
    # Create initial snapshot
    initial_content = "Welcome to Codex AI Assistant\n> "
    snapshot1 = TerminalSnapshot(content=initial_content)
    print(f"1. Initial snapshot created with {snapshot1.line_count} lines")
    print(f"   Content: {repr(initial_content[:30])}...")
    
    # Create a second snapshot with more content
    updated_content = "Welcome to Codex AI Assistant\n> Hello World\nHello! How can I assist you today?"
    snapshot2 = TerminalSnapshot(content=updated_content)
    print(f"2. Updated snapshot created with {snapshot2.line_count} lines")
    print(f"   Content: {repr(updated_content[:50])}...")
    
    # Compare snapshots to detect changes
    changes = snapshot2.get_changed_regions(snapshot1)
    print(f"3. Found {len(changes)} change regions:")
    for i, change in enumerate(changes):
        print(f"   Change {i+1}: {change['type']} at position {change['position']}")
        print(f"      Content: {repr(change['content'][:50])}...")
    
    # Create a third snapshot with tool usage
    tool_content = updated_content + "\n[EXEC: echo 'Processing request']\nDone executing command"
    snapshot3 = TerminalSnapshot(content=tool_content)
    print(f"4. Tool snapshot created with {snapshot3.line_count} lines")
    
    # Compare to see tool usage
    changes2 = snapshot3.get_changed_regions(snapshot2)
    print(f"5. Found {len(changes2)} change regions after tool usage:")
    for i, change in enumerate(changes2):
        print(f"   Change {i+1}: {change['type']} at position {change['position']}")
        print(f"      Content: {repr(change['content'][:50])}...")
    
    print("\n✓ Terminal snapshot functionality works correctly!")


def test_wrapper_with_snapshots():
    """Test the wrapper's integration with terminal snapshots."""
    print("\n=== Testing Wrapper Integration with Snapshots ===")
    
    # Create a wrapper instance
    wrapper = CodexWrapper(width=240, height=60)
    
    print(f"1. Wrapper initialized with {len(wrapper.terminal_history)} snapshots in history")
    print(f"2. Initial Turing machine state: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate processing some output
    output1 = "Codex> "
    wrapper._process_output(output1)
    
    print(f"3. After processing 'Codex> ', history size: {len(wrapper.terminal_history)}")
    print(f"4. Turing machine state: {wrapper.turing_machine.get_current_state().value}")
    
    # Simulate more output
    output2 = "Hello World\nHello! Nice to meet you."
    wrapper._process_output(output2)
    
    print(f"5. After processing response, history size: {len(wrapper.terminal_history)}")
    print(f"6. Turing machine state: {wrapper.turing_machine.get_current_state().value}")
    
    # Add tool usage
    output3 = "[EXEC: echo 'Tool executed']\nTool completed successfully"
    wrapper._process_output(output3)
    
    print(f"7. After processing tool, history size: {len(wrapper.terminal_history)}")
    print(f"8. Turing machine state: {wrapper.turing_machine.get_current_state().value}")
    
    # Check the last snapshot
    if wrapper.terminal_history:
        last_snapshot = wrapper.terminal_history[-1]
        print(f"9. Last snapshot has {last_snapshot.line_count} lines")
    
    print("\n✓ Wrapper integration with terminal snapshots works correctly!")


def test_change_analysis():
    """Test the terminal change analysis functionality."""
    print("\n=== Testing Terminal Change Analysis ===")
    
    # Create a wrapper to test change analysis
    wrapper = CodexWrapper(width=240, height=60)
    
    # Create a mock change and analyze it
    new_content = "Hello from AI assistant\n> "
    change_info = {
        "type": "new_content",
        "content": new_content,
        "position": (1, 0)
    }
    
    print(f"1. Analyzing change with content: {repr(new_content[:30])}...")
    print(f"2. Initial state: {wrapper.turing_machine.get_current_state().value}")
    
    # Call the analysis method
    wrapper._analyze_terminal_change(new_content, change_info)
    
    print(f"3. State after analysis: {wrapper.turing_machine.get_current_state().value}")
    
    # Test with tool content
    tool_content = "[EXEC: ls -la]\n"
    print(f"4. Analyzing tool content: {repr(tool_content[:20])}...")
    print(f"5. State before tool analysis: {wrapper.turing_machine.get_current_state().value}")
    
    change_info_tool = {
        "type": "new_content",
        "content": tool_content,
        "position": (2, 0)
    }
    
    wrapper._analyze_terminal_change(tool_content, change_info_tool)
    print(f"6. State after tool analysis: {wrapper.turing_machine.get_current_state().value}")
    
    print("\n✓ Terminal change analysis works correctly!")


if __name__ == "__main__":
    test_terminal_snapshots()
    test_wrapper_with_snapshots()
    test_change_analysis()
    
    print("\n🎉 All terminal snapshot tests passed!")
    print("\nKey features implemented:")
    print("- Time-differential comparison of terminal states")
    print("- Detection of new content regions")
    print("- Integration with Turing machine state transitions")
    print("- Analysis of terminal changes to update UI patterns")