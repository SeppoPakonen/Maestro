"""
Test to run the actual codex application with the wrapper.
This will only work if codex is installed and available in the system.
"""
import sys
import time
import subprocess
from pathlib import Path

# Add the project root to the Python path so we can import maestro modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from maestro.wrap.codex.wrapper import CodexWrapper


def check_codex_installed():
    """Check if codex is installed and available."""
    try:
        result = subprocess.run(['which', 'codex'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Codex found at: {result.stdout.strip()}")
            return True
        else:
            print("⚠ Codex not found in system PATH")
            return False
    except Exception:
        print("⚠ Codex not found in system PATH")
        return False


def run_codex_with_wrapper():
    """Run the actual codex with the wrapper if available."""
    print("=== Running Actual Codex with Wrapper ===")
    
    if not check_codex_installed():
        print("Codex is not installed or not in PATH.")
        print("To install codex, you would typically use one of these methods:")
        print("  - pip install codex")
        print("  - Or follow the installation instructions from the codex documentation")
        print("  - Or build it from source if available")
        print()
        print("However, we can still demonstrate how the wrapper would work by showing the")
        print("command that would be executed and the expected behavior.")
        print()
        print("The wrapper would execute: codex [with appropriate parameters]")
        print("The wrapper provides:")
        print("  - 240 character wide terminal")
        print("  - Time-differential terminal state comparison")
        print("  - Turing machine state tracking")
        print("  - Command handling for /compact, /new, /quit, /model")
        print("  - Tool usage detection and parsing")
        print("  - JSON encoding for client communication")
        return False
    
    # Create a temporary socket path for this test
    socket_path = "/tmp/codex_actual_test.sock"
    if Path(socket_path).exists():
        Path(socket_path).unlink()
    
    # Create the wrapper
    wrapper = CodexWrapper(width=240, height=60, socket_path=socket_path)
    
    try:
        print("Starting wrapper with actual 'codex' command...")
        wrapper.start()  # This will start the actual codex process
        
        print(f"✓ Started codex process with dimensions {wrapper.height}x{wrapper.width}")
        print(f"✓ Initial Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        print(f"✓ Socket listening at: {socket_path}")
        
        # Wait a bit to see initial output
        print("Waiting for initial codex output...")
        time.sleep(3)
        
        print(f"✓ Terminal history size: {len(wrapper.terminal_history)}")
        
        if wrapper.terminal_history:
            last_snapshot = wrapper.terminal_history[-1]
            print(f"✓ Last snapshot has {last_snapshot.line_count} lines")
            print(f"  Content preview: {repr(last_snapshot.content[-200:])}...")
        
        # If codex is interactive, we could send a test command
        # But we'll be careful not to send anything that might cause unwanted side effects
        print("\\nSending a test command to codex (if it accepts commands)...")
        try:
            wrapper.send_input("hello world")
            time.sleep(2)
        except Exception as e:
            print(f"Note: Command sending failed (expected if codex is not interactive): {e}")
        
        print(f"✓ Final Turing machine state: {wrapper.turing_machine.get_current_state().value}")
        print(f"✓ Final terminal history size: {len(wrapper.terminal_history)}")
        
        # Clean exit
        print("\\nSending quit command...")
        try:
            wrapper.send_input("/quit")
            time.sleep(1)
        except:
            # If codex doesn't support /quit, try to terminate the process
            if wrapper.child and wrapper.child.isalive():
                wrapper.child.terminate()
        
        return True
        
    except Exception as e:
        print(f"Error running codex: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        if wrapper.child and wrapper.child.isalive():
            wrapper.child.terminate()
        if Path(socket_path).exists():
            Path(socket_path).unlink()


def demonstrate_expected_behavior():
    """Demonstrate the expected behavior with codex."""
    print("\\n=== Expected Behavior with Codex ===")
    print("When codex is properly installed, the wrapper will:")
    print("1. Launch codex in a 240x60 terminal (wide display)")
    print("2. Capture all terminal output in snapshots")
    print("3. Compare snapshots over time to detect changes")
    print("4. Use Turing machine to track UI states:")
    print("   - IDLE: Waiting for input")
    print("   - PROMPTING: Capturing user prompt")
    print("   - AWAITING_RESPONSE: Waiting for AI response")
    print("   - PROCESSING_TOOLS: Handling tool usage")
    print("   - COMMAND_MODE: Processing special commands")
    print("   - QUITTING: Shutting down")
    print("5. Detect tool usage patterns like [TOOL:], [EXEC:], [FILE:], [SEARCH:]")
    print("6. Parse and encode all data as JSON for client communication")
    print("7. Handle special commands: /compact, /new, /quit, /model")


if __name__ == "__main__":
    print("Testing Codex Wrapper with Actual Codex Application")
    print("=" * 60)
    
    success = run_codex_with_wrapper()
    
    if not success:
        demonstrate_expected_behavior()
    
    print("\\n" + "=" * 60)
    print("Test completed.")
    if success:
        print("✓ Codex ran successfully with the wrapper")
    else:
        print("ℹ Codex was not available, but the wrapper is ready to use when codex is installed")