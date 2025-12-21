#!/usr/bin/env python3
"""
Simple test to make sure the TU6 CLI command is properly integrated.
"""
import subprocess
import sys
import os

def test_cli_integration():
    """Test that the CLI command is properly integrated."""
    try:
        # Test that the help command works for tu transform
        result = subprocess.run([
            sys.executable, "-m", "maestro", "tu", "transform", "--help"
        ], capture_output=True, text=True, cwd="/common/active/sblo/Dev/Maestro")
        
        if result.returncode == 0:
            print("✓ CLI command 'maestro tu transform --help' works")
            print("Output snippet:", result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
        else:
            print("✗ CLI command 'maestro tu transform --help' failed")
            print("Error:", result.stderr)
            return False
            
        return True
    except Exception as e:
        print(f"Error testing CLI integration: {e}")
        return False

if __name__ == "__main__":
    print("Testing TU6 CLI integration...")
    success = test_cli_integration()
    
    if success:
        print("\n✓ TU6 CLI integration test passed!")
    else:
        print("\n✗ TU6 CLI integration test failed!")
        sys.exit(1)