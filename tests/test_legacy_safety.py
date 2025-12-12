#!/usr/bin/env python3
"""
Test to verify the legacy subtask safety mechanism works as expected.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator_cli import assert_no_legacy_subtasks

def test_legacy_detection():
    """Test that the legacy detection function works properly."""
    print("Testing legacy subtask detection function...")
    
    # Create mock objects with the legacy titles
    class MockSubtask:
        def __init__(self, title):
            self.title = title
    
    # Test 1: All three legacy titles present - should raise AssertionError
    legacy_subtasks = [
        MockSubtask("Analysis and Research"),
        MockSubtask("Implementation"),
        MockSubtask("Testing and Integration")
    ]
    
    try:
        assert_no_legacy_subtasks(legacy_subtasks)
        print("ERROR: Should have raised AssertionError for all 3 legacy titles")
        return False
    except AssertionError as e:
        print(f"✓ Correctly detected all 3 legacy titles: {e}")
    
    # Test 2: Only 2 legacy titles - should NOT raise AssertionError
    partial_legacy = [
        MockSubtask("Analysis and Research"),
        MockSubtask("Implementation"),
        MockSubtask("Some other task")
    ]
    
    try:
        assert_no_legacy_subtasks(partial_legacy)
        print("✓ Correctly allowed partial legacy titles (2 out of 3)")
    except AssertionError:
        print("ERROR: Should not have raised AssertionError for 2 out of 3 legacy titles")
        return False
    
    # Test 3: No legacy titles - should NOT raise AssertionError
    new_subtasks = [
        MockSubtask("Research Phase"),
        MockSubtask("Development Phase"),
        MockSubtask("Testing Phase")
    ]
    
    try:
        assert_no_legacy_subtasks(new_subtasks)
        print("✓ Correctly allowed new subtask titles")
    except AssertionError:
        print("ERROR: Should not have raised AssertionError for new subtask titles")
        return False
    
    print("All safety tests passed!")
    return True

if __name__ == "__main__":
    success = test_legacy_detection()
    if success:
        print("\n✓ Legacy safety mechanism is working correctly!")
    else:
        print("\n✗ Legacy safety mechanism has issues!")
        sys.exit(1)