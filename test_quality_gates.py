#!/usr/bin/env python3
"""
Test suite for quality gates: drift detection, write policies, merge safety, and idempotency
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add the project root to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent))

import realize_worker
import convert_orchestrator
import inventory_generator
import planner
import execution_engine


def test_target_hash_tracking():
    """Test that target hash tracking works correctly."""
    print("Testing target hash tracking...")
    
    with tempfile.TemporaryDirectory() as temp_target:
        # Create test file
        test_file_path = os.path.join(temp_target, "test_file.txt")
        test_content = "Initial content of the test file"
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        # Compute initial hash
        initial_hash = realize_worker.compute_file_hash(test_file_path)
        assert initial_hash is not None, "Should compute hash for existing file"
        
        # Load target hashes
        hashes = realize_worker.load_target_hashes()
        assert isinstance(hashes, dict), "Should return dict"
        
        # Update target hash
        task_id = "test_task_1"
        realize_worker.update_target_hash("test_file.txt", task_id, initial_hash)
        
        # Verify it was saved
        hashes = realize_worker.load_target_hashes()
        assert "test_file.txt" in hashes, "Should contain the test file"
        assert hashes["test_file.txt"]["hash"] == initial_hash, "Hash should match"
        assert hashes["test_file.txt"]["task_id"] == task_id, "Task ID should match"
        
        print("✓ Target hash tracking test passed")
        return True


def test_write_policy_enforcement():
    """Test that write policies are enforced correctly."""
    print("Testing write policy enforcement...")
    
    with tempfile.TemporaryDirectory() as temp_target:
        # Create a file in target to test 'skip_if_exists' policy
        existing_file_path = os.path.join(temp_target, "existing_file.txt")
        with open(existing_file_path, 'w') as f:
            f.write("existing content")
        
        # Test skip_if_exists policy
        write_result = realize_worker.safe_write_file(
            "existing_file.txt",
            "new content",
            temp_target,
            task_id="test_task",
            write_policy="skip_if_exists"
        )
        
        assert write_result["success"], "Should succeed (just skip)"
        assert write_result["action"] == "skipped", "Should be skipped"
        
        # Verify content was not changed
        with open(existing_file_path, 'r') as f:
            content = f.read()
            assert content == "existing content", "Content should not have changed"
        
        # Test overwrite policy
        write_result = realize_worker.safe_write_file(
            "overwrite_file.txt",
            "new content",
            temp_target,
            task_id="test_task",
            write_policy="overwrite"
        )
        
        assert write_result["success"], "Should succeed to write"
        assert write_result["changed"], "Content should have changed"
        
        # Verify new content was written
        with open(os.path.join(temp_target, "overwrite_file.txt"), 'r') as f:
            content = f.read()
            assert content == "new content", "Content should match"
        
        print("✓ Write policy enforcement test passed")
        return True


def test_merge_strategies():
    """Test that merge strategies work correctly."""
    print("Testing merge strategies...")

    # Test append_section strategy
    existing_content = "Initial content"
    new_content = "Appended content"
    result = realize_worker.merge_content(
        existing_content,
        new_content,
        "append_section"
    )
    expected = "Initial content\nAppended content"
    assert result == expected, f"Expected '{expected}', got '{result}'"

    # Test replace_section_by_marker strategy
    existing_content = "Start\n# BEGIN SECTION\nOld content\n# END SECTION\nEnd"
    new_content = "New content"
    markers = {
        "begin_marker": "# BEGIN SECTION",
        "end_marker": "# END SECTION"
    }
    result = realize_worker.merge_content(
        existing_content,
        new_content,
        "replace_section_by_marker",
        markers
    )
    expected = "Start\n# BEGIN SECTION\nNew content\n# END SECTION\nEnd"
    assert result == expected, f"Expected '{expected}', got '{result}'"

    print("✓ Merge strategies test passed")
    return True


def test_default_write_policy():
    """Test that default write policies are applied correctly."""
    print("Testing default write policies...")
    
    # Test scaffold task (should default to skip_if_exists)
    scaffold_task = {"phase": "scaffold", "write_policy": None}
    policy = realize_worker.get_write_policy_for_task(scaffold_task)
    assert policy == "skip_if_exists", f"Expected skip_if_exists, got {policy}"
    
    # Test file task (should default to overwrite)
    file_task = {"phase": "file", "write_policy": None}
    policy = realize_worker.get_write_policy_for_task(file_task)
    assert policy == "overwrite", f"Expected overwrite, got {policy}"
    
    # Test sweep task (should default to skip_if_exists)
    sweep_task = {"phase": "sweep", "write_policy": None}
    policy = realize_worker.get_write_policy_for_task(sweep_task)
    assert policy == "skip_if_exists", f"Expected skip_if_exists, got {policy}"
    
    # Test explicit policy override
    task_with_explicit_policy = {"phase": "file", "write_policy": "merge"}
    policy = realize_worker.get_write_policy_for_task(task_with_explicit_policy)
    assert policy == "merge", f"Expected merge, got {policy}"
    
    print("✓ Default write policies test passed")
    return True


def run_all_tests():
    """Run all quality gate tests."""
    print("Running quality gate tests...\n")
    
    tests = [
        test_target_hash_tracking,
        test_write_policy_enforcement,
        test_merge_strategies,
        test_default_write_policy
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTest results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✓ All quality gate tests passed!")
        return True
    else:
        print("✗ Some tests failed.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)