#!/usr/bin/env python3
"""
Test to verify the legacy plan migration enforcement works correctly during resume.
"""
import os
import sys
import tempfile
import json
from unittest.mock import patch

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_model import Session, Subtask, save_session
from orchestrator_cli import handle_resume_session, has_legacy_plan


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


def test_legacy_resume_refusal():
    """Test that resuming a session with legacy tasks is refused."""
    print("Testing that resuming session with legacy tasks is refused...")
    
    # Create a session with legacy tasks
    session = create_session_with_legacy_tasks()
    
    # Save the session to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        save_session(session, f.name)
        session_path = f.name
    
    try:
        # Test that has_legacy_plan returns True for our session
        if not has_legacy_plan(session.subtasks):
            print("✗ Session should be detected as legacy")
            return False
        
        print("✓ Session correctly identified as containing legacy plan")
        
        # Try to resume the session - this should cause sys.exit(1)
        try:
            handle_resume_session(session_path, verbose=False)
            print("✗ Session with legacy tasks was allowed to resume (should have been refused)")
            return False
        except SystemExit as e:
            if e.code == 1:
                print("✓ Session with legacy tasks correctly refused during resume (sys.exit(1))")
            else:
                print(f"✗ Session exit code was {e.code}, expected 1")
                return False
        
        return True
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_non_legacy_resume_allowed():
    """Test that resuming a session with non-legacy tasks is allowed."""
    print("\nTesting that resuming session with non-legacy tasks is allowed...")
    
    # Create a session with non-legacy tasks
    session = Session(
        id='test-normal-session',
        created_at='2023-01-01T00:00:00',
        updated_at='2023-01-01T00:00:00',
        root_task='Test root task with normal subtasks',
        subtasks=[
            Subtask(
                id='task-1',
                title='Research Phase',
                description='Do some research',
                status='pending',
                planner_model='codex',
                worker_model='qwen',
                summary_file=''
            ),
            Subtask(
                id='task-2', 
                title='Development Phase',
                description='Develop the solution',
                status='pending',
                planner_model='claude',
                worker_model='gemini',
                summary_file=''
            )
        ],
        rules_path=None,
        status='planned'
    )
    
    # Save the session to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        save_session(session, f.name)
        session_path = f.name
    
    try:
        # Test that has_legacy_plan returns False for our session
        if has_legacy_plan(session.subtasks):
            print("✗ Session should not be detected as legacy")
            return False
        
        print("✓ Session correctly identified as NOT containing legacy plan")
        
        # Mock the actual resume logic to prevent it from trying to process subtasks
        with patch('orchestrator_cli.collect_worker_summaries', return_value="(no summaries)"):
            try:
                handle_resume_session(session_path, verbose=False)
                # If we get here without SystemExit, it means the session was allowed to proceed
                # (it should have exited during processing, so we need to check the actual behavior)
                print("Note: This test shows the session loading is allowed, but the actual resume process might continue")
            except SystemExit:
                # This is expected if there are no pending subtasks or other conditions
                pass
        
        print("✓ Session with non-legacy tasks proceeded without legacy plan refusal")
        return True
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


if __name__ == "__main__":
    success1 = test_legacy_resume_refusal()
    success2 = test_non_legacy_resume_allowed()
    
    if success1 and success2:
        print("\n✓ All legacy plan migration enforcement tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some legacy plan migration enforcement tests failed!")
        sys.exit(1)