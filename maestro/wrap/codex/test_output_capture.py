"""
Direct test of the wrapper's ability to capture and process output from a real CLI.
"""
import sys
import time
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import CodexWrapper


def test_output_capture():
    """Test that the wrapper properly captures output from a real CLI."""
    print("=== Testing Output Capture from Real CLI ===")
    
    # Create a wrapper without socket for this test
    wrapper = CodexWrapper(width=240, height=60)
    
    try:
        # Start a simple interactive process
        import pexpect
        print("Starting 'bash' process...")
        wrapper.child = pexpect.spawn('bash', ['-i'], timeout=5, dimensions=(60, 240))
        
        print("Waiting for bash prompt...")
        # Wait for the prompt to appear
        wrapper.child.expect(r'\$', timeout=5)
        print(f"✓ Received initial prompt: {repr(wrapper.child.after)}")
        
        # Send a command
        print("Sending 'echo hello' command...")
        wrapper.child.sendline('echo hello')
        
        # Wait for the response
        wrapper.child.expect(r'hello', timeout=5)
        print(f"✓ Received expected output: {repr(wrapper.child.after)}")
        
        # Now let's see if our background thread captured anything
        print(f"✓ Terminal history size after interaction: {len(wrapper.terminal_history)}")
        
        # Wait a bit more to allow background processing
        time.sleep(2)
        print(f"✓ Terminal history size after waiting: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            for i, snapshot in enumerate(wrapper.terminal_history):
                print(f"  Snapshot {i+1}: {snapshot.line_count} lines, content preview: {repr(snapshot.content[-50:])}")
        
        # Send another command to see if it's captured
        print("Sending 'pwd' command...")
        wrapper.child.sendline('pwd')
        wrapper.child.expect(r'\n', timeout=3)  # Expect a newline after pwd
        
        time.sleep(1)
        print(f"✓ Terminal history size after second command: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            last_snapshot = wrapper.terminal_history[-1]
            print(f"  Last snapshot: {last_snapshot.line_count} lines, content preview: {repr(last_snapshot.content[-100:])}")
        
        # Try to send exit command
        wrapper.child.sendline('exit')
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    if wrapper.child and wrapper.child.isalive():
        wrapper.child.terminate()


def test_manual_snapshot_creation():
    """Test the snapshot functionality manually."""
    print("\n=== Testing Manual Snapshot Creation ===")
    
    wrapper = CodexWrapper(width=240, height=60)
    
    # Manually process content to test snapshot creation
    content1 = "Welcome to the system\n$ "
    wrapper._process_output(content1)
    
    print(f"✓ After content1, history size: {len(wrapper.terminal_history)}")
    print(f"  Content: {repr(content1)}")
    
    content2 = "hello world\nHello to you too!\n$ "
    wrapper._process_output(content2)
    
    print(f"✓ After content2, history size: {len(wrapper.terminal_history)}")
    print(f"  Content: {repr(content2)}")
    
    # Check differences
    if len(wrapper.terminal_history) >= 2:
        changes = wrapper.terminal_history[-1].get_changed_regions(wrapper.terminal_history[-2])
        print(f"✓ Differences detected: {len(changes)}")
        for i, change in enumerate(changes):
            print(f"  Change {i+1}: {change}")
    
    print(f"✓ Final Turing machine state: {wrapper.turing_machine.get_current_state().value}")


if __name__ == "__main__":
    test_output_capture()
    test_manual_snapshot_creation()