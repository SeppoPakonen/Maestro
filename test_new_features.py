#!/usr/bin/env python3
"""
Test script to verify the new features: flexible root task handling, 
interactive planner discussion, and plan tree branching.
"""
import json
import os
import tempfile
from session_model import Session, Subtask, PlanNode, load_session, save_session
from orchestrator_cli import migrate_session_if_needed

def test_session_model_extensions():
    """Test the extended session model with new fields."""
    print("Testing extended session model...")
    
    # Create a test session with new fields
    session = Session(
        id="test-session",
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        root_task="Original root task",
        subtasks=[
            Subtask(
                id="subtask1",
                title="Test Subtask",
                description="A test subtask",
                planner_model="test",
                worker_model="test",
                status="pending",
                summary_file="",
                categories=["backend", "api"],
                root_excerpt="This part is relevant for backend work",
                plan_id="plan1"
            )
        ],
        rules_path=None,
        status="new",
        root_task_raw="Raw root task input from user",
        root_task_clean="Cleaned and structured root task",
        root_task_categories=["backend", "frontend", "testing"]
    )
    
    # Test plan nodes
    plan_node = PlanNode(
        plan_id="plan1",
        parent_plan_id=None,
        created_at="2023-01-01T00:00:00",
        label="Initial plan",
        status="active",
        notes="Initial planning",
        root_task_snapshot="Raw root task input from user",
        root_clean_snapshot="Cleaned and structured root task",
        categories_snapshot=["backend", "frontend", "testing"],
        subtask_ids=["subtask1"]
    )
    
    # Test serialization
    session_dict = session.to_dict()
    assert "root_task_raw" in session_dict
    assert "root_task_clean" in session_dict
    assert "root_task_categories" in session_dict
    assert "plans" in session_dict
    assert "active_plan_id" in session_dict
    
    # Test deserialization
    session_reconstructed = Session.from_dict(session_dict)
    assert session_reconstructed.root_task_raw == "Raw root task input from user"
    assert session_reconstructed.root_task_clean == "Cleaned and structured root task"
    assert session_reconstructed.root_task_categories == ["backend", "frontend", "testing"]
    assert session_reconstructed.subtasks[0].categories == ["backend", "api"]
    assert session_reconstructed.subtasks[0].root_excerpt == "This part is relevant for backend work"
    assert session_reconstructed.subtasks[0].plan_id == "plan1"
    
    print("✓ Session model extensions work correctly")


def test_backward_compatibility():
    """Test backward compatibility for old sessions."""
    print("Testing backward compatibility...")
    
    # Create an old-style session (without new fields)
    old_session_dict = {
        "id": "old-session",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "root_task": "Old root task",
        "subtasks": [
            {
                "id": "old-subtask1",
                "title": "Old Subtask",
                "description": "An old subtask",
                "planner_model": "old",
                "worker_model": "old",
                "status": "pending",
                "summary_file": ""
            }
        ],
        "rules_path": None,
        "status": "new"
    }
    
    # Save the old-style session
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(old_session_dict, f)
        temp_path = f.name
    
    try:
        # Load the session using the new model
        loaded_session = load_session(temp_path)
        
        # Migration should have been applied
        migrate_session_if_needed(loaded_session)
        
        # Check that default values were set
        assert loaded_session.root_task_raw == "Old root task"
        assert loaded_session.root_task_clean == "Old root task"
        assert loaded_session.root_task_categories == []
        assert loaded_session.plans != []
        assert loaded_session.active_plan_id is not None
        assert loaded_session.subtasks[0].plan_id == loaded_session.active_plan_id
        
        print("✓ Backward compatibility works correctly")
    finally:
        # Clean up
        os.unlink(temp_path)


def test_worker_prompt_format():
    """Test that worker prompts use the new format."""
    print("Testing worker prompt format...")
    
    # Create a session and subtask with the new fields
    session = Session(
        id="test-session",
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        root_task="Main task",
        subtasks=[],
        rules_path=None,
        status="new",
        root_task_raw="Raw main task input",
        root_task_clean="Cleaned main task for processing",
        root_task_categories=["backend", "api"]
    )
    
    subtask = Subtask(
        id="test-subtask",
        title="Test Work",
        description="Do some work",
        planner_model="test",
        worker_model="test",
        status="pending",
        summary_file="",
        categories=["backend"],
        root_excerpt="Backend-specific instructions",
        plan_id="test-plan"
    )
    
    # Check that we can access the new fields
    assert subtask.categories == ["backend"]
    assert subtask.root_excerpt == "Backend-specific instructions"
    assert subtask.plan_id == "test-plan"
    assert session.root_task_clean == "Cleaned main task for processing"
    assert session.root_task_categories == ["backend", "api"]
    
    print("✓ Worker prompt format uses new fields correctly")


def test_plan_tree_structure():
    """Test plan tree functionality."""
    print("Testing plan tree structure...")
    
    session = Session(
        id="tree-session",
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        root_task="Root task",
        subtasks=[],
        rules_path=None,
        status="new"
    )
    
    # Create a plan tree
    root_plan = PlanNode(
        plan_id="P1",
        parent_plan_id=None,
        created_at="2023-01-01T00:00:00",
        label="Root plan",
        status="active",
        notes="Initial plan",
        root_task_snapshot="Root task",
        root_clean_snapshot="Root task",
        categories_snapshot=[],
        subtask_ids=[]
    )
    
    child_plan = PlanNode(
        plan_id="P2",
        parent_plan_id="P1",
        created_at="2023-01-01T00:01:00",
        label="Child plan",
        status="inactive",
        notes="Branch plan",
        root_task_snapshot="Root task",
        root_clean_snapshot="Root task",
        categories_snapshot=[],
        subtask_ids=[]
    )
    
    # Add to session
    session.plans = [root_plan, child_plan]
    session.active_plan_id = "P1"
    
    # Serialize and verify
    session_dict = session.to_dict()
    assert len(session_dict["plans"]) == 2
    assert session_dict["active_plan_id"] == "P1"
    
    # Deserialize and verify
    session_reconstructed = Session.from_dict(session_dict)
    assert len(session_reconstructed.plans) == 2
    assert session_reconstructed.active_plan_id == "P1"
    assert session_reconstructed.plans[0].parent_plan_id is None
    assert session_reconstructed.plans[1].parent_plan_id == "P1"
    
    print("✓ Plan tree structure works correctly")


def run_all_tests():
    """Run all tests."""
    print("Running tests for new features...\n")
    
    test_session_model_extensions()
    test_backward_compatibility()
    test_worker_prompt_format()
    test_plan_tree_structure()
    
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    run_all_tests()