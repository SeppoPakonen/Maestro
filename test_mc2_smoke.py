"""
Smoke test for MC2 mode
Tests that the --mc2 --smoke command works and prints the success marker
"""
import subprocess
import sys
import time


def test_mc2_smoke():
    """Test that MC2 smoke mode runs successfully"""
    try:
        # Run the MC2 smoke test
        result = subprocess.run([
            sys.executable, "-m", "maestro.tui", 
            "--mc2", "--smoke", "--smoke-seconds", "0.1"
        ], capture_output=True, text=True, timeout=5)
        
        # Check that it exited successfully
        assert result.returncode == 0, f"Command failed with return code {result.returncode}"
        
        # Check that the success marker was printed
        output = result.stdout + result.stderr
        assert "MAESTRO_TUI_SMOKE_OK" in output, f"Success marker not found in output: {output}"
        
        print("✓ MC2 smoke test passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ MC2 smoke test timed out")
        return False
    except Exception as e:
        print(f"✗ MC2 smoke test failed with error: {e}")
        return False


def test_mc2_smoke_with_file():
    """Test that MC2 smoke mode works with output file"""
    import tempfile
    import os
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
            
        # Run the MC2 smoke test with output file
        result = subprocess.run([
            sys.executable, "-m", "maestro.tui",
            "--mc2", "--smoke", "--smoke-seconds", "0.1",
            "--smoke-out", temp_file
        ], capture_output=True, text=True, timeout=5)
        
        # Check that it exited successfully
        assert result.returncode == 0, f"Command failed with return code {result.returncode}"
        
        # Check that the success marker was printed
        output = result.stdout + result.stderr
        assert "MAESTRO_TUI_SMOKE_OK" in output, f"Success marker not found in output: {output}"
        
        # Check that the file contains the success marker
        with open(temp_file, 'r') as f:
            file_content = f.read()
            assert "MAESTRO_TUI_SMOKE_OK" in file_content, f"Success marker not found in file: {file_content}"
        
        # Clean up
        os.unlink(temp_file)
        
        print("✓ MC2 smoke test with file output passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ MC2 smoke test with file timed out")
        return False
    except Exception as e:
        print(f"✗ MC2 smoke test with file failed with error: {e}")
        return False


if __name__ == "__main__":
    print("Running MC2 smoke tests...")
    
    success = True
    success &= test_mc2_smoke()
    success &= test_mc2_smoke_with_file()
    
    if success:
        print("\n✓ All MC2 smoke tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some MC2 smoke tests failed!")
        sys.exit(1)