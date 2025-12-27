#!/usr/bin/env python3
"""
Test to verify the legacy plan migration check works correctly.
"""
import os
import sys
import tempfile
import json

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_model import Session, Subtask, save_session


def create_session_with_legacy_tasks():
    """Create a test session with the legacy 3 hard-coded subtasks."""
    session = Session(
        id='test-migration-session',
        created_at='2023-01-01T00:00:00',
        updated_at='2023-01-01T00:00:00',
        root_task='Test root task with legacy subtasks',
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


def test_legacy_detection():
    """Test that legacy plan detection works correctly."""
    print("Testing legacy plan detection...")
    
    # Create a session with legacy tasks
    session = create_session_with_legacy_tasks()
    
    # Save the session to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        save_session(session, f.name)
        session_path = f.name
    
    try:
        # Import the detection function
        from orchestrator_cli import has_legacy_plan
        
        # Test the detection function
        result = has_legacy_plan(session.subtasks)
        if result:
            print("✓ Legacy plan correctly detected")
        else:
            print("✗ Legacy plan detection failed")
            return False
            
        # Test with non-legacy tasks
        non_legacy_session = Session(
            id='test',
            created_at='2023-01-01T00:00:00',
            updated_at='2023-01-01T00:00:00',
            root_task='Test',
            subtasks=[
                Subtask(
                    id='task-1',
                    title='Some other task',
                    description='Test',
                    status='pending',
                    planner_model='codex',
                    worker_model='qwen',
                    summary_file=''
                )
            ],
            rules_path=None, 
            status='new'
        )
        
        result2 = has_legacy_plan(non_legacy_session.subtasks)
        if not result2:
            print("✓ Non-legacy plan correctly not detected as legacy")
        else:
            print("✗ Non-legacy plan incorrectly detected as legacy")
            return False
            
        print("✓ All legacy detection tests passed!")
        return True
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


if __name__ == "__main__":
    success = test_legacy_detection()
    if success:
        print("\n✓ Legacy plan migration check test passed!")
        sys.exit(0)
    else:
        print("\n✗ Legacy plan migration check test failed!")
        sys.exit(1)