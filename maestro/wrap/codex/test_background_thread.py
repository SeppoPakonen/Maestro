"""
Test to verify that the background thread properly updates terminal history.
"""
import sys
import time
import threading
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import CodexWrapper


def test_background_thread_updates():
    """Test that the background thread properly updates terminal history."""
    print("=== Testing Background Thread Updates ===")
    
    # Create a wrapper without socket for this test
    wrapper = CodexWrapper(width=240, height=60)
    
    try:
        # Start a simple interactive process
        import pexpect
        print("Starting 'bash' process...")
        wrapper.child = pexpect.spawn('bash', ['-i'], timeout=5, dimensions=(60, 240))
        
        # Start the background thread to read output
        output_thread = threading.Thread(target=wrapper._read_output, daemon=True)
        output_thread.start()
        
        print(f"Initial terminal history size: {len(wrapper.terminal_history)}")
        print(f"Initial Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        
        # Wait a bit for initial output (prompt) to be captured
        time.sleep(1)
        print(f"After 1s - history size: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            print(f"  Latest snapshot: {wrapper.terminal_history[-1].line_count} lines")
            print(f"  Content preview: {repr(wrapper.terminal_history[-1].content[-50:])}")
        
        print(f"Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        
        # Send a command to bash
        print("Sending 'echo test' command...")
        wrapper.child.sendline('echo test')
        
        # Wait for the command output to be processed by background thread
        time.sleep(1)
        print(f"After command - history size: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            print(f"  Latest snapshot: {wrapper.terminal_history[-1].line_count} lines")
            print(f"  Content preview: {repr(wrapper.terminal_history[-1].content[-100:])}")
        
        print(f"Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        
        # Send another command
        print("Sending 'pwd' command...")
        wrapper.child.sendline('pwd')
        
        time.sleep(1)
        print(f"After second command - history size: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            print(f"  Latest snapshot: {wrapper.terminal_history[-1].line_count} lines")
            print(f"  Content preview: {repr(wrapper.terminal_history[-1].content[-100:])}")
        
        print(f"Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        
        # Send exit command
        wrapper.child.sendline('exit')
        wrapper.should_stop = True
        
        # Wait for thread to finish
        output_thread.join(timeout=2)
        
        print(f"Final history size: {len(wrapper.terminal_history)}")
        print(f"Final Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        
        # Print all snapshots
        for i, snapshot in enumerate(wrapper.terminal_history):
            print(f"  Snapshot {i+1}: {snapshot.line_count} lines")
            print(f"    Content: {repr(snapshot.content[-100:])}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    if wrapper.child and wrapper.child.isalive():
        wrapper.child.terminate()


def test_with_manual_content():
    """Test with manually added content to make sure functionality works."""
    print("\n=== Testing Manual Content Addition ===")
    
    wrapper = CodexWrapper(width=240, height=60)
    
    print(f"Initial history size: {len(wrapper.terminal_history)}")
    
    # Add content manually
    wrapper._process_output("Welcome to bash\n$ ")
    print(f"After welcome - history size: {len(wrapper.terminal_history)}")
    
    wrapper._process_output("echo test\n")
    print(f"After echo command - history size: {len(wrapper.terminal_history)}")
    
    wrapper._process_output("test\n$ ")
    print(f"After echo output - history size: {len(wrapper.terminal_history)}")
    
    print(f"Turing machine state: {wrapper.turing_machine.get_current_state().value}")
    
    # Show snapshots
    for i, snapshot in enumerate(wrapper.terminal_history):
        print(f"  Snapshot {i+1}: {snapshot.line_count} lines")
        print(f"    Content: {repr(snapshot.content)}")


if __name__ == "__main__":
    test_background_thread_updates()
    test_with_manual_content()