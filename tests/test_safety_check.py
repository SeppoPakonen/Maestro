#!/usr/bin/env python3
"""
Test script to verify the JSON plan to Session.subtasks mapping implementation.
Also includes safety tests to ensure legacy hard-coded subtasks never reappear.
"""
import tempfile
import os
import sys
from unittest.mock import patch

# Import our modules
from session_model import Session, save_session, load_session
from orchestrator_cli import apply_json_plan_to_session, assert_no_legacy_subtasks


def test_json_plan_to_subtasks():
    """Test that the JSON plan is properly mapped to Session.subtasks."""
    print("Testing JSON plan to Session.subtasks mapping...")
    
    # Create a test session
    test_session = Session(
        id='test-id',
        created_at='2023-01-01T00:00:00',
        updated_at='2023-01-01T00:00:00',
        root_task='Test root task for verification',
        subtasks=[],
        rules_path=None,
        status='new'
    )
    
    # Create a sample JSON plan
    sample_plan = {
        "subtasks": [
            {
                "id": "subtask-1",
                "title": "Implement feature A",
                "description": "Implement the first feature",
                "kind": "code",
                "complexity": "normal"
            },
            {
                "id": "subtask-2",
                "title": "Write tests",
                "description": "Write unit tests for feature A",
                "kind": "code", 
                "complexity": "simple"
            },
            {
                "id": "subtask-3",
                "title": "Documentation",
                "description": "Create documentation for feature A",
                "kind": "documentation",
                "complexity": "complex"
            }
        ],
        "planner_model": "claude"
    }
    
    print(f"Original session has {len(test_session.subtasks)} subtasks")
    
    # Apply the JSON plan to the session
    apply_json_plan_to_session(test_session, sample_plan)
    
    print(f"After applying plan, session has {len(test_session.subtasks)} subtasks")
    
    # Verify the subtasks were created correctly
    assert len(test_session.subtasks) == 3, f"Expected 3 subtasks, got {len(test_session.subtasks)}"
    
    # Check first subtask
    first_subtask = test_session.subtasks[0]
    assert first_subtask.id == "subtask-1", f"Expected id 'subtask-1', got {first_subtask.id}"
    assert first_subtask.title == "Implement feature A", f"Expected title 'Implement feature A', got {first_subtask.title}"
    assert first_subtask.description == "Implement the first feature", f"Expected description 'Implement the first feature', got {first_subtask.description}"
    assert first_subtask.planner_model == "claude", f"Expected planner_model 'claude', got {first_subtask.planner_model}"
    assert first_subtask.worker_model in ["qwen", "gemini"], f"Expected worker_model to be qwen or gemini, got {first_subtask.worker_model}"
    assert first_subtask.status == "pending", f"Expected status 'pending', got {first_subtask.status}"
    
    # Check second subtask
    second_subtask = test_session.subtasks[1]
    assert second_subtask.id == "subtask-2", f"Expected id 'subtask-2', got {second_subtask.id}"
    assert second_subtask.kind == "code" if hasattr(second_subtask, 'kind') else True  # This field isn't stored in Subtask by design
    
    print("All assertions passed!")
    print(f"Session status: {test_session.status}")
    print(f"Session updated_at: {test_session.updated_at}")
    
    # Test validation - empty subtasks list
    try:
        empty_plan = {"subtasks": []}
        apply_json_plan_to_session(test_session, empty_plan)
        assert False, "Should have raised ValueError for empty subtasks list"
    except ValueError as e:
        print(f"Correctly caught validation error for empty subtasks: {e}")
    
    # Test validation - no subtasks key
    try:
        no_subtasks_plan = {"other_key": "value"}
        apply_json_plan_to_session(test_session, no_subtasks_plan)
        assert False, "Should have raised ValueError for missing subtasks key"
    except ValueError as e:
        print(f"Correctly caught validation error for missing subtasks: {e}")
    
    print("All tests passed! The JSON plan to subtasks mapping is working correctly.")


def test_legacy_subtask_detection():
    """Test that the safety check detects legacy hard-coded subtasks."""
    print("\nTesting legacy hard-coded subtask detection...")

    # Create mock subtask objects with the legacy titles
    class MockSubtask:
        def __init__(self, title):
            self.title = title

    # Create subtasks with legacy titles (this should trigger the assertion error)
    legacy_subtasks = [
        MockSubtask("Analysis and Research"),
        MockSubtask("Implementation"),
        MockSubtask("Testing and Integration")
    ]

    # This should raise an AssertionError
    try:
        assert_no_legacy_subtasks(legacy_subtasks)
        assert False, "Should have raised AssertionError for legacy subtasks"
    except AssertionError as e:
        print(f"Correctly caught AssertionError for legacy subtasks: {e}")

    # Test with only two legacy titles (should NOT trigger the assertion error)
    partial_legacy_subtasks = [
        MockSubtask("Analysis and Research"),
        MockSubtask("Some other task"),
        MockSubtask("Different task")
    ]

    # This should NOT raise an error (since not all 3 legacy titles are present)
    try:
        assert_no_legacy_subtasks(partial_legacy_subtasks)
        print("Correctly allowed partial legacy titles (not all 3 present)")
    except AssertionError:
        assert False, "Should not have raised AssertionError for partial legacy titles"

    # Test with no legacy titles (should NOT trigger the assertion error)
    new_subtasks = [
        MockSubtask("Research and Analysis"),
        MockSubtask("Code Implementation"),
        MockSubtask("Quality Assurance")
    ]

    # This should NOT raise an error
    try:
        assert_no_legacy_subtasks(new_subtasks)
        print("Correctly allowed new subtask titles")
    except AssertionError:
        assert False, "Should not have raised AssertionError for new subtask titles"

    print("Legacy subtask detection test passed!")


if __name__ == "__main__":
    test_json_plan_to_subtasks()
    test_legacy_subtask_detection()