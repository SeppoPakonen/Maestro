#!/usr/bin/env python3
"""
Smoke test for Maestro TUI
This script tests that the TUI can be started and exits correctly in smoke mode.
"""

import subprocess
import sys
import time


def test_tui_smoke_mode():
    """Test that the TUI smoke mode works correctly."""
    print("Testing TUI smoke mode...")

    try:
        # Run the TUI in smoke mode with a short timeout (using safe module entry point)
        result = subprocess.run([
            sys.executable, "-m", "maestro.tui", "--smoke", "--smoke-seconds", "0.3"
        ], capture_output=True, text=True, timeout=5)  # 5 second timeout to prevent hanging

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Check if the expected output was produced (in either stdout or stderr)
        combined_output = result.stdout + result.stderr
        if "MAESTRO_TUI_SMOKE_OK" in combined_output:
            print("✅ TUI smoke test PASSED: Correct output found")
            return True
        else:
            print("❌ TUI smoke test FAILED: Expected output not found")
            print(f"Expected: MAESTRO_TUI_SMOKE_OK")
            print(f"Got combined: {combined_output}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ TUI smoke test FAILED: Process timed out")
        return False
    except Exception as e:
        print(f"❌ TUI smoke test FAILED with exception: {e}")
        return False


def test_tui_smoke_mode_shorter():
    """Test that the TUI smoke mode works with shorter time."""
    print("\nTesting TUI smoke mode with 0.1 seconds...")

    try:
        # Run the TUI in smoke mode with a very short time (using safe module entry point)
        result = subprocess.run([
            sys.executable, "-m", "maestro.tui", "--smoke", "--smoke-seconds", "0.1"
        ], capture_output=True, text=True, timeout=3)  # 3 second timeout

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Check if the expected output was produced (in either stdout or stderr)
        combined_output = result.stdout + result.stderr
        if "MAESTRO_TUI_SMOKE_OK" in combined_output:
            print("✅ TUI smoke test (short) PASSED: Correct output found")
            return True
        else:
            print("❌ TUI smoke test (short) FAILED: Expected output not found")
            return False

    except subprocess.TimeoutExpired:
        print("❌ TUI smoke test (short) FAILED: Process timed out")
        return False
    except Exception as e:
        print(f"❌ TUI smoke test (short) FAILED with exception: {e}")
        return False


if __name__ == "__main__":
    print("Starting TUI smoke tests...\n")
    
    test1_passed = test_tui_smoke_mode()
    test2_passed = test_tui_smoke_mode_shorter()
    
    print(f"\nTest results:")
    print(f"Standard smoke test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Short smoke test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All TUI smoke tests PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Some TUI smoke tests FAILED!")
        sys.exit(1)