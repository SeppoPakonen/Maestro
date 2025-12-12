#!/usr/bin/env python3
"""
Test to verify the --force-replan flag works correctly with legacy plans.
"""
import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_model import Session, Subtask, save_session, load_session
from orchestrator_cli import handle_plan_session


def create_session_with_legacy_tasks():
    """Create a test session with the legacy 3 hard-coded subtasks."""
    session = Session(
        id='test-force-replan-session',
        created_at='2023-01-01T00:00:00',
        updated_at='2023-01-01T00:00:00',
        root_task='Test root task with legacy subtasks for force-replan',
        subtasks=[
            Subtask(
                id='legacy-1',
                title='Analysis and Research',
                description='Analyze the requirements',
                status='pending',
                planner_model='legacy',
                worker_model='qwen',
                summary_file=''
            ),
            Subtask(
                id='legacy-2', 
                title='Implementation',
                description='Implement the solution',
                status='pending',
                planner_model='legacy',
                worker_model='qwen',
                summary_file=''
            ),
            Subtask(
                id='legacy-3',
                title='Testing and Integration',
                description='Test the implemented solution',
                status='pending', 
                planner_model='legacy',
                worker_model='qwen',
                summary_file=''
            )
        ],
        rules_path=None,
        status='planned'
    )
    return session


def test_force_replan_clears_legacy_tasks():
    """Test that --force-replan clears legacy tasks and allows new planning."""
    print("Testing that --force-replan clears legacy tasks...")
    
    # Create a session with legacy tasks
    session = create_session_with_legacy_tasks()
    original_task_count = len(session.subtasks)
    
    # Save the session to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        save_session(session, f.name)
        session_path = f.name
    
    try:
        # Mock the planner engine to return known JSON
        mock_json_response = {
            "planner_model": "codex",
            "version": 1,
            "subtasks": [
                {
                    "id": "S1",
                    "title": "New Dummy Task",
                    "description": "A new task from force-replan.",
                    "kind": "code",
                    "complexity": "trivial",
                    "preferred_worker": "qwen",
                    "allowed_workers": ["qwen", "gemini"],
                    "planner_notes": "",
                    "depends_on": []
                }
            ]
        }
        
        # Patch the get_engine function in engines module to return a mock engine
        mock_engine = MagicMock()
        mock_engine.generate.return_value = json.dumps(mock_json_response)
        
        with patch('engines.get_engine', return_value=mock_engine):
            # Mock user input to accept the plan
            with patch('builtins.input', return_value='y'):
                # Call handle_plan_session with force_replan=True
                handle_plan_session(session_path, verbose=False, force_replan=True)
    
        # Reload the session to check if legacy tasks were cleared and new ones added
        updated_session = load_session(session_path)
        
        # Check that the original legacy tasks were cleared
        if len(updated_session.subtasks) != 1:
            print(f"✗ Expected 1 new task after force-replan, got {len(updated_session.subtasks)}")
            return False
        
        # Check that the new task from JSON planner is present
        new_task = updated_session.subtasks[0]
        if new_task.title != "New Dummy Task":
            print(f"✗ Expected new task title 'New Dummy Task', got '{new_task.title}'")
            return False
        
        if new_task.description != "A new task from force-replan.":
            print(f"✗ Expected new task description 'A new task from force-replan.', got '{new_task.description}'")
            return False
        
        print(f"✓ Legacy tasks cleared (was {original_task_count}, now 0 initial tasks)")
        print(f"✓ New task added from JSON planner: '{new_task.title}'")
        print(f"✓ Force re-plan functionality working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_force_replan_with_normal_session():
    """Test that --force-replan works with normal sessions too."""
    print("\nTesting that --force-replan works with normal sessions...")
    
    # Create a session with normal tasks
    session = Session(
        id='test-normal-force-replan-session',
        created_at='2023-01-01T00:00:00',
        updated_at='2023-01-01T00:00:00',
        root_task='Test root task with normal subtasks for force-replan',
        subtasks=[
            Subtask(
                id='normal-1',
                title='Normal Task 1',
                description='A normal task',
                status='pending',
                planner_model='codex',
                worker_model='qwen',
                summary_file=''
            ),
            Subtask(
                id='normal-2', 
                title='Normal Task 2',
                description='Another normal task',
                status='pending',
                planner_model='claude',
                worker_model='gemini',
                summary_file=''
            )
        ],
        rules_path=None,
        status='planned'
    )
    
    original_task_count = len(session.subtasks)
    
    # Save the session to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        save_session(session, f.name)
        session_path = f.name
    
    try:
        # Mock the planner engine to return known JSON
        mock_json_response = {
            "planner_model": "codex",
            "version": 1,
            "subtasks": [
                {
                    "id": "S1",
                    "title": "Fresh New Task",
                    "description": "A fresh task from force-replan.",
                    "kind": "documentation",
                    "complexity": "simple",
                    "preferred_worker": "qwen",
                    "allowed_workers": ["qwen"],
                    "planner_notes": "",
                    "depends_on": []
                }
            ]
        }
        
        # Patch the get_engine function in engines module to return a mock engine
        mock_engine = MagicMock()
        mock_engine.generate.return_value = json.dumps(mock_json_response)
        
        with patch('engines.get_engine', return_value=mock_engine):
            # Mock user input to accept the plan
            with patch('builtins.input', return_value='y'):
                # Call handle_plan_session with force_replan=True
                handle_plan_session(session_path, verbose=False, force_replan=True)
    
        # Reload the session to check if all tasks were cleared and new ones added
        updated_session = load_session(session_path)
        
        # Check that the original tasks were cleared
        if len(updated_session.subtasks) != 1:
            print(f"✗ Expected 1 new task after force-replan, got {len(updated_session.subtasks)}")
            return False
        
        # Check that the new task from JSON planner is present
        new_task = updated_session.subtasks[0]
        if new_task.title != "Fresh New Task":
            print(f"✗ Expected new task title 'Fresh New Task', got '{new_task.title}'")
            return False
        
        print(f"✓ Normal tasks cleared (was {original_task_count}, now 0 initial tasks)")
        print(f"✓ New task added from JSON planner: '{new_task.title}'")
        print(f"✓ Force re-plan works with normal sessions too")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


if __name__ == "__main__":
    success1 = test_force_replan_clears_legacy_tasks()
    success2 = test_force_replan_with_normal_session()
    
    if success1 and success2:
        print("\n✓ All --force-replan tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some --force-replan tests failed!")
        sys.exit(1)