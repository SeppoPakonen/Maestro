#!/usr/bin/env python3
"""
Test script for the interactive planner functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.main import get_fix_rulebooks_dir


def test_directories():
    print("Testing if fix directories are properly set up...")
    
    fix_dir = get_fix_rulebooks_dir()
    conversations_dir = os.path.join(fix_dir, 'conversations')
    outputs_dir = os.path.join(fix_dir, 'outputs')
    
    print(f"Base fix directory: {fix_dir}")
    print(f"Conversations directory: {conversations_dir}")
    print(f"Outputs directory: {outputs_dir}")
    
    # Create directories
    os.makedirs(conversations_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    
    print("✓ Directories created successfully")
    
    # Test if they exist
    assert os.path.exists(fix_dir), f"Fix directory doesn't exist: {fix_dir}"
    assert os.path.exists(conversations_dir), f"Conversations directory doesn't exist: {conversations_dir}"
    assert os.path.exists(outputs_dir), f"Outputs directory doesn't exist: {outputs_dir}"
    
    print("✓ All directories exist")
    return True


def test_function_import():
    print("\nTesting if functions can be imported without errors...")
    try:
        from maestro.main import handle_build_fix_plan
        print("✓ handle_build_fix_plan function imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error importing function: {e}")
        return False


if __name__ == "__main__":
    success1 = test_directories()
    success2 = test_function_import()
    
    if success1 and success2:
        print("\n✓ All basic tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)