#!/usr/bin/env python3
"""
Test to verify that the --plan command uses the JSON-based planner output.
"""
import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_model import Session, load_session, save_session
from orchestrator_cli import handle_plan_session, assert_no_legacy_subtasks


def test_plan_uses_json_planner():
    """Test that --plan command uses JSON-based planner output, not legacy code."""
    print("Testing that --plan uses JSON-based planner output...")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as session_file:
        session_path = session_file.name
        
        # Create a session with simple root_task and empty subtasks
        test_session = Session(
            id='test-session-id',
            created_at='2023-01-01T00:00:00',
            updated_at='2023-01-01T00:00:00',
            root_task='Test root task for JSON planner verification',
            subtasks=[],
            rules_path=None,
            status='new'
        )
        save_session(test_session, session_path)
    
    try:
        # Mock the planner engine to return known JSON
        mock_json_response = {
            "planner_model": "codex",
            "version": 1,
            "subtasks": [
                {
                    "id": "S1",
                    "title": "Dummy Task",
                    "description": "Do something trivial for testing.",
                    "kind": "code",
                    "complexity": "trivial",
                    "preferred_worker": "qwen",
                    "allowed_workers": ["qwen", "gemini"],
                    "planner_notes": "",
                    "depends_on": []
                }
            ]
        }
        
        # Patch the get_engine function to return a mock engine
        mock_engine = MagicMock()
        mock_engine.generate.return_value = json.dumps(mock_json_response)
        
        # Patch the get_engine function in engines module where it's imported from
        with patch('engines.get_engine', return_value=mock_engine):
            # Run the --plan functionality programmatically
            # Set up to bypass user input by mocking input() to return 'y' (yes)
            with patch('builtins.input', return_value='y'):
                # Call the handle_plan_session function directly
                handle_plan_session(session_path, verbose=True)
        
        # Reload the session file
        updated_session = load_session(session_path)
        
        # Assertions: check that the session contains data from mocked JSON, not legacy defaults
        assert len(updated_session.subtasks) == 1, f"Expected 1 subtask, got {len(updated_session.subtasks)}"
        
        subtask = updated_session.subtasks[0]
        assert subtask.title == "Dummy Task", f"Expected title 'Dummy Task', got '{subtask.title}'"
        assert subtask.description == "Do something trivial for testing.", f"Expected description 'Do something trivial for testing.', got '{subtask.description}'"
        assert subtask.planner_model == "codex", f"Expected planner_model 'codex', got '{subtask.planner_model}'"
        
        # Worker model should be selected based on the preferred_worker from the JSON, 
        # or the first in allowed_workers if worker selection logic selects from allowed_workers
        # According to the JSON, preferred_worker is "qwen", so worker_model is likely to be qwen/gemini
        assert subtask.worker_model in ["qwen", "gemini"], f"Expected worker_model to be qwen or gemini, got '{subtask.worker_model}'"
        
        print(f"✓ Session has {len(updated_session.subtasks)} subtask(s)")
        print(f"✓ Subtask title: '{subtask.title}'")
        print(f"✓ Subtask description: '{subtask.description}'")
        print(f"✓ Subtask planner_model: '{subtask.planner_model}'")
        print(f"✓ Subtask worker_model: '{subtask.worker_model}'")
        
        # Call the safety check from Task B to reinforce the guard
        assert_no_legacy_subtasks(updated_session.subtasks)
        print("✓ Safety check passed - no legacy subtasks detected")
        
        print("✓ All assertions passed! The --plan command is using JSON-based planner output.")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the temporary session file
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_plan_uses_json_planner_with_multiple_tasks():
    """Test that --plan correctly handles multiple subtasks from JSON."""
    print("\nTesting that --plan handles multiple subtasks from JSON...")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as session_file:
        session_path = session_file.name
        
        # Create a session with a different root_task and empty subtasks
        test_session = Session(
            id='test-session-id-2',
            created_at='2023-01-01T00:00:00',
            updated_at='2023-01-01T00:00:00',
            root_task='Test multiple subtasks for verification',
            subtasks=[],
            rules_path=None,
            status='new'
        )
        save_session(test_session, session_path)
    
    try:
        # Mock the planner engine to return JSON with multiple subtasks
        mock_json_response = {
            "planner_model": "claude",
            "version": 1,
            "subtasks": [
                {
                    "id": "S1",
                    "title": "First Test Task",
                    "description": "First task for testing.",
                    "kind": "documentation",
                    "complexity": "simple",
                    "preferred_worker": "qwen",
                    "allowed_workers": ["qwen"],
                    "planner_notes": "Initial setup task",
                    "depends_on": []
                },
                {
                    "id": "S2", 
                    "title": "Second Test Task",
                    "description": "Second task for testing.",
                    "kind": "code",
                    "complexity": "complex",
                    "preferred_worker": "gemini",
                    "allowed_workers": ["qwen", "gemini"],
                    "planner_notes": "Implementation task",
                    "depends_on": ["S1"]
                }
            ]
        }
        
        # Patch the get_engine function to return a mock engine
        mock_engine = MagicMock()
        mock_engine.generate.return_value = json.dumps(mock_json_response)
        
        # Patch the get_engine function in engines module where it's imported from
        with patch('engines.get_engine', return_value=mock_engine):
            # Set up to bypass user input by mocking input() to return 'y' (yes)
            with patch('builtins.input', return_value='y'):
                # Call the handle_plan_session function directly
                handle_plan_session(session_path, verbose=True)
        
        # Reload the session file
        updated_session = load_session(session_path)
        
        # Assertions: check that the session contains data from mocked JSON
        assert len(updated_session.subtasks) == 2, f"Expected 2 subtasks, got {len(updated_session.subtasks)}"
        
        # Check first subtask
        first_subtask = updated_session.subtasks[0]
        assert first_subtask.title == "First Test Task", f"Expected title 'First Test Task', got '{first_subtask.title}'"
        assert first_subtask.description == "First task for testing.", f"Expected description 'First task for testing.', got '{first_subtask.description}'"
        assert first_subtask.planner_model == "claude", f"Expected planner_model 'claude', got '{first_subtask.planner_model}'"
        
        # Check second subtask
        second_subtask = updated_session.subtasks[1]
        assert second_subtask.title == "Second Test Task", f"Expected title 'Second Test Task', got '{second_subtask.title}'"
        assert second_subtask.description == "Second task for testing.", f"Expected description 'Second Test Task', got '{second_subtask.description}'"
        assert second_subtask.planner_model == "claude", f"Expected planner_model 'claude', got '{second_subtask.planner_model}'"
        
        print(f"✓ Session has {len(updated_session.subtasks)} subtask(s)")
        print(f"✓ First subtask title: '{first_subtask.title}'")
        print(f"✓ Second subtask title: '{second_subtask.title}'")
        print(f"✓ Both have correct planner_model: '{first_subtask.planner_model}'")
        
        # Call the safety check from Task B to reinforce the guard
        assert_no_legacy_subtasks(updated_session.subtasks)
        print("✓ Safety check passed - no legacy subtasks detected")
        
        print("✓ Multiple subtask test passed! The --plan command correctly handles JSON-based planner output.")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the temporary session file
        if os.path.exists(session_path):
            os.unlink(session_path)


if __name__ == "__main__":
    success1 = test_plan_uses_json_planner()
    success2 = test_plan_uses_json_planner_with_multiple_tasks()
    
    if success1 and success2:
        print("\n✓ All --plan JSON planner tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)