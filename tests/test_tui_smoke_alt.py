#!/usr/bin/env python3
"""
Simple smoke test for Maestro TUI using shell redirection to capture output
"""

import subprocess
import sys
import os
import tempfile


def test_tui_smoke_mode():
    """Test TUI smoke mode by redirecting output to files."""
    print("Testing TUI smoke mode with file redirection...")
    
    # Create temporary files for stdout and stderr
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as stdout_file:
        stdout_filename = stdout_file.name
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as stderr_file:
        stderr_filename = stderr_file.name
    
    try:
        # Run the command, redirecting output to our temp files (using safe module entry point)
        cmd = [sys.executable, "-m", "maestro.tui", "--smoke", "--smoke-seconds", "0.2"]

        # Use shell redirection to ensure output goes to the files
        full_cmd = f'{sys.executable} -m maestro.tui --smoke --smoke-seconds 0.2 > {stdout_filename} 2> {stderr_filename}'
        
        result = subprocess.run(full_cmd, shell=True, timeout=5)
        
        print(f"Return code: {result.returncode}")
        
        # Read the output files
        with open(stdout_filename, 'r') as f:
            stdout_content = f.read()
        with open(stderr_filename, 'r') as f:
            stderr_content = f.read()
        
        print(f"STDOUT file content: '{stdout_content}'")
        print(f"STDERR file content: '{stderr_content}'")
        
        # Check if the success message appears in either output
        combined_output = stdout_content + stderr_content
        if "MAESTRO_TUI_SMOKE_OK" in combined_output:
            print("✅ TUI smoke test PASSED: Success message found!")
            return True
        else:
            print("❌ TUI smoke test FAILED: Success message not found")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ TUI smoke test FAILED: Timeout")
        return False
    except Exception as e:
        print(f"❌ TUI smoke test FAILED: {e}")
        return False
    finally:
        # Clean up temp files
        try:
            os.unlink(stdout_filename)
            os.unlink(stderr_filename)
        except:
            pass


def test_tui_smoke_mode_alternative():
    """Alternative approach using pipe and checking process exit."""
    print("Testing TUI smoke mode - alternative approach...")
    
    try:
        # Try with pty to better handle terminal applications
        import pty
        import select
        import os
        
        pid, fd = pty.fork()
        
        if pid == 0:  # Child process
            os.execlp(sys.executable, sys.executable, "-m", "maestro.tui", "--smoke", "--smoke-seconds", "0.2")
        else:  # Parent process
            output = ""
            start_time = time.time()
            timeout = 5  # seconds
            
            while True:
                ready, _, _ = select.select([fd], [], [], 0.1)  # 0.1 second timeout on select
                if ready:
                    try:
                        data = os.read(fd, 1024).decode('utf-8', errors='ignore')
                        output += data
                        if "MAESTRO_TUI_SMOKE_OK" in output:
                            print("✅ Success message found in output!")
                            print(f"Full output: '{output}'")
                            os.waitpid(pid, 0)  # Wait for child to exit
                            return True
                    except OSError:
                        # FD closed, the process probably exited
                        break
                elif time.time() - start_time > timeout:
                    print("❌ Timeout waiting for output")
                    os.kill(pid, 9)  # Force kill if timeout
                    os.waitpid(pid, 0)
                    return False
                    
            # Process has ended, check the final output
            print(f"Process ended. Final output: '{output}'")
            if "MAESTRO_TUI_SMOKE_OK" in output:
                print("✅ TUI smoke test PASSED: Success message found!")
                return True
            else:
                print("❌ TUI smoke test FAILED: Success message not found in final output")
                return False
    except Exception as e:
        print(f"❌ Alternative test failed: {e}")
        return False


# Import time for the alternative function
import time

if __name__ == "__main__":
    print("Starting TUI smoke tests with alternative methods...\n")
    
    test1_result = test_tui_smoke_mode()
    print()
    test2_result = test_tui_smoke_mode_alternative()
    
    print(f"\nTest results:")
    print(f"File redirection test: {'PASSED' if test1_result else 'FAILED'}")
    print(f"PTY test: {'PASSED' if test2_result else 'FAILED'}")
    
    if test1_result or test2_result:  # If at least one passed
        print("\n🎉 At least one smoke mode test passed!")
        sys.exit(0)
    else:
        print("\n💥 All smoke mode tests failed!")
        sys.exit(1)