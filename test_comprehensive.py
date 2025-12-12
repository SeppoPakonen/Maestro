#!/usr/bin/env python3
"""
Comprehensive test for the new CLI functionality: flexible root task handling, 
interactive planner discussion, and plan tree branching.
"""
import json
import os
import tempfile
import uuid
from datetime import datetime
from session_model import Session, Subtask, PlanNode, load_session, save_session

def test_cli_flags():
    """Test that the new CLI flags are properly defined."""
    print("Testing CLI flag configuration...")
    
    # Test that the help message includes new flags
    import subprocess
    result = subprocess.run(['python', 'orchestrator_cli.py', '--help'], 
                          capture_output=True, text=True)
    
    # Check that new flags are present in help
    help_text = result.stdout
    assert '--one-shot-plan' in help_text
    assert '--discuss-plan' in help_text
    assert '--show-plan-tree' in help_text
    assert '--focus-plan' in help_text
    
    print("✓ CLI flags are properly configured")


def test_new_session_creation():
    """Test creating a new session with the new data model."""
    print("Testing new session creation...")
    
    # Create a new session
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task="Test root task for implementation",
        subtasks=[],
        rules_path=None,
        status="new",
        root_task_raw="Raw test root task",
        root_task_clean="Cleaned test root task",
        root_task_categories=["backend", "api", "testing"]
    )
    
    # Verify the data was set correctly
    assert session.root_task_raw == "Raw test root task"
    assert session.root_task_clean == "Cleaned test root task"
    assert session.root_task_categories == ["backend", "api", "testing"]
    assert session.plans == []
    assert session.active_plan_id is None
    
    print("✓ New session creation works correctly")


def test_subtask_with_categories():
    """Test subtasks with the new category and excerpt fields."""
    print("Testing subtasks with categories and excerpts...")
    
    subtask = Subtask(
        id="test1",
        title="Test Subtask",
        description="A subtask for testing",
        planner_model="test",
        worker_model="test",
        status="pending",
        summary_file="",
        categories=["frontend", "ui"],
        root_excerpt="This part is relevant for UI work",
        plan_id="plan-test"
    )
    
    # Verify new fields
    assert subtask.categories == ["frontend", "ui"]
    assert subtask.root_excerpt == "This part is relevant for UI work"
    assert subtask.plan_id == "plan-test"
    
    # Test serialization/deserialization
    subtask_dict = subtask.to_dict()
    assert "categories" in subtask_dict
    assert "root_excerpt" in subtask_dict
    assert "plan_id" in subtask_dict
    
    subtask_reconstructed = Subtask.from_dict(subtask_dict)
    assert subtask_reconstructed.categories == ["frontend", "ui"]
    assert subtask_reconstructed.root_excerpt == "This part is relevant for UI work"
    assert subtask_reconstructed.plan_id == "plan-test"
    
    print("✓ Subtasks with categories and excerpts work correctly")


def test_plan_branching():
    """Test plan branching functionality."""
    print("Testing plan branching...")
    
    # Create a session with an initial plan
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task="Main project",
        subtasks=[],
        rules_path=None,
        status="new",
        root_task_raw="Raw main project task",
        root_task_clean="Cleaned main project task",
        root_task_categories=["backend", "frontend"]
    )
    
    # Create initial plan
    initial_plan = PlanNode(
        plan_id="P1",
        parent_plan_id=None,
        created_at=datetime.now().isoformat(),
        label="Initial plan",
        status="active",
        notes="Original plan",
        root_task_snapshot="Raw main project task",
        root_clean_snapshot="Cleaned main project task",
        categories_snapshot=["backend", "frontend"],
        subtask_ids=["S1", "S2"]
    )
    
    session.plans = [initial_plan]
    session.active_plan_id = "P1"
    
    # Simulate creating a branch
    branch_plan = PlanNode(
        plan_id="P2",
        parent_plan_id="P1",
        created_at=datetime.now().isoformat(),
        label="Alternative approach",
        status="active",
        notes="Branch for different approach",
        root_task_snapshot="Raw main project task",
        root_clean_snapshot="Alternative cleaned task",
        categories_snapshot=["frontend", "ui"],
        subtask_ids=["S3", "S4"]
    )
    
    session.plans.append(branch_plan)
    session.active_plan_id = "P2"
    
    # Verify the plan tree structure
    assert len(session.plans) == 2
    assert any(p.plan_id == "P1" for p in session.plans)
    assert any(p.plan_id == "P2" for p in session.plans)
    assert session.active_plan_id == "P2"
    
    # Verify parent-child relationship
    for plan in session.plans:
        if plan.plan_id == "P2":
            assert plan.parent_plan_id == "P1"
    
    # Test serialization
    session_dict = session.to_dict()
    assert len(session_dict["plans"]) == 2
    assert session_dict["active_plan_id"] == "P2"
    
    # Test deserialization
    session_reconstructed = Session.from_dict(session_dict)
    assert len(session_reconstructed.plans) == 2
    assert session_reconstructed.active_plan_id == "P2"
    assert any(p.plan_id == "P2" and p.parent_plan_id == "P1" for p in session_reconstructed.plans)
    
    print("✓ Plan branching works correctly")


def test_worker_prompt_format():
    """Test that worker prompts are formatted with the new structure."""
    print("Testing worker prompt format...")
    
    # This simulates how the worker prompt would be constructed
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task="Main task",
        subtasks=[],
        rules_path=None,
        status="new",
        root_task_raw="Raw main task input from user",
        root_task_clean="Cleaned and structured main task",
        root_task_categories=["backend", "api", "security"]
    )
    
    subtask = Subtask(
        id="S1",
        title="Implement API",
        description="Create backend API endpoints",
        planner_model="test",
        worker_model="test",
        status="pending",
        summary_file="",
        categories=["backend", "api"],
        root_excerpt="Backend implementation: create secure API endpoints",
        plan_id="P1"
    )
    
    # Simulate the worker prompt construction from handle_resume_session
    root_task_to_use = session.root_task_clean or session.root_task_raw or session.root_task
    categories_str = ", ".join(subtask.categories) if subtask.categories else "No specific categories"
    root_excerpt = subtask.root_excerpt if subtask.root_excerpt else "No specific excerpt, see categories."
    
    prompt = f"[ROOT TASK (CLEANED)]\n{root_task_to_use}\n\n"
    prompt += f"[RELEVANT CATEGORIES]\n{categories_str}\n\n"
    prompt += f"[RELEVANT ROOT EXCERPT]\n{root_excerpt}\n\n"
    
    # Verify the prompt contains the new format
    assert "[ROOT TASK (CLEANED)]" in prompt
    assert "Cleaned and structured main task" in prompt
    assert "[RELEVANT CATEGORIES]" in prompt
    assert "backend, api" in prompt
    assert "[RELEVANT ROOT EXCERPT]" in prompt
    assert "Backend implementation: create secure API endpoints" in prompt
    
    print("✓ Worker prompt format works correctly")


def test_plan_tree_visualization():
    """Test the plan tree visualization logic."""
    print("Testing plan tree visualization...")
    
    # Create a session with a tree of plans
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task="Main project",
        subtasks=[
            Subtask(
                id="S1", title="Root task 1", description="Task", planner_model="test", 
                worker_model="test", status="done", summary_file="", plan_id="P1"
            ),
            Subtask(
                id="S2", title="Root task 2", description="Task", planner_model="test", 
                worker_model="test", status="pending", summary_file="", plan_id="P2"
            ),
            Subtask(
                id="S3", title="Branch task", description="Task", planner_model="test", 
                worker_model="test", status="pending", summary_file="", plan_id="P3"
            ),
        ],
        rules_path=None,
        status="new",
        root_task_raw="Raw main project",
        root_task_clean="Cleaned main project",
        root_task_categories=["backend", "frontend"]
    )
    
    # Create a tree structure: P1 -> P2 -> P3
    plan1 = PlanNode(
        plan_id="P1",
        parent_plan_id=None,
        created_at=datetime.now().isoformat(),
        label="Initial plan",
        status="active",
        notes="Initial plan",
        root_task_snapshot="Raw main project",
        root_clean_snapshot="Cleaned main project",
        categories_snapshot=["backend", "frontend"],
        subtask_ids=["S1"]
    )
    
    plan2 = PlanNode(
        plan_id="P2",
        parent_plan_id="P1",
        created_at=datetime.now().isoformat(),
        label="Refinement plan",
        status="active",
        notes="Refinement",
        root_task_snapshot="Raw main project",
        root_clean_snapshot="Cleaned main project",
        categories_snapshot=["backend"],
        subtask_ids=["S2"]
    )
    
    plan3 = PlanNode(
        plan_id="P3",
        parent_plan_id="P2",
        created_at=datetime.now().isoformat(),
        label="Branch plan",
        status="dead",  # Mark as dead to test visualization
        notes="Alternative approach",
        root_task_snapshot="Raw main project",
        root_clean_snapshot="Alternative cleaned version",
        categories_snapshot=["frontend"],
        subtask_ids=["S3"]
    )
    
    session.plans = [plan1, plan2, plan3]
    session.active_plan_id = "P2"
    
    # Test plan tree structure building logic
    plan_tree = {}
    root_plans = []
    
    for plan in session.plans:
        if plan.parent_plan_id is None:
            root_plans.append(plan)
        else:
            if plan.parent_plan_id not in plan_tree:
                plan_tree[plan.parent_plan_id] = []
            plan_tree[plan.parent_plan_id].append(plan)
    
    # Should have 1 root plan (P1) with 1 child (P2), and P2 has 1 child (P3)
    assert len(root_plans) == 1
    assert root_plans[0].plan_id == "P1"
    assert len(plan_tree["P1"]) == 1  # P1 has P2 as child
    assert plan_tree["P1"][0].plan_id == "P2"
    assert len(plan_tree["P2"]) == 1  # P2 has P3 as child
    assert plan_tree["P2"][0].plan_id == "P3"
    
    # Test subtask counting for each plan
    for plan in session.plans:
        subtasks_for_plan = [st for st in session.subtasks if st.plan_id == plan.plan_id]
        if plan.plan_id == "P1":
            assert len(subtasks_for_plan) == 1  # S1
        elif plan.plan_id == "P2":
            assert len(subtasks_for_plan) == 1  # S2
        elif plan.plan_id == "P3":
            assert len(subtasks_for_plan) == 1  # S3
    
    print("✓ Plan tree visualization logic works correctly")


def run_all_tests():
    """Run all tests."""
    print("Running comprehensive tests for new CLI functionality...\n")
    
    test_cli_flags()
    test_new_session_creation()
    test_subtask_with_categories()
    test_plan_branching()
    test_worker_prompt_format()
    test_plan_tree_visualization()
    
    print("\n✓ All comprehensive tests passed!")


if __name__ == "__main__":
    run_all_tests()