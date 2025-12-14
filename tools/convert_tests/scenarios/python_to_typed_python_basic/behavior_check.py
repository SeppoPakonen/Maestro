#!/usr/bin/env python3
"""
Behavior preservation check for Python to Typed Python conversion.
This script tests that key behavior remains unchanged after conversion.
"""

import subprocess
import sys
import os
import hashlib

def run_python_code(file_path):
    """Run the Python code and capture output."""
    try:
        result = subprocess.run([sys.executable, file_path], 
                              capture_output=True, text=True, timeout=30)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout occurred", 1

def calculate_output_hash(output):
    """Calculate hash of output to compare behavior."""
    return hashlib.md5(output.encode()).hexdigest()

def test_python_behavior():
    """Test that Python code behavior is preserved."""
    print("Testing Python behavior preservation...")

    # Run the calculator module from source_repo
    stdout, stderr, returncode = run_python_code("source_repo/calculator.py")
    
    if returncode != 0:
        print(f"ERROR: Python code execution failed with return code {returncode}")
        print(f"STDERR: {stderr}")
        return False
    
    # Check for expected outputs in the calculator execution
    expected_outputs = [
        "Initial value: 10",
        "After adding 5: 15",
        "After subtracting 3: 12",
        "Sum of 5 and 3: 8",
        "Multiply 4 and 5: 20"
    ]
    
    missing_outputs = []
    for expected in expected_outputs:
        if expected not in stdout:
            missing_outputs.append(expected)
    
    if missing_outputs:
        print(f"ERROR: Missing expected outputs: {missing_outputs}")
        print(f"Actual output: {stdout}")
        return False
    
    # Calculate hash of the output to compare against baseline
    output_hash = calculate_output_hash(stdout)
    print(f"Output hash: {output_hash}")
    
    # For the preservation check, we just ensure the expected outputs are present
    print("Python behavior preservation test PASSED")
    return True

if __name__ == "__main__":
    success = test_python_behavior()
    sys.exit(0 if success else 1)