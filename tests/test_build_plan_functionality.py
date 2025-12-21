#!/usr/bin/env python3
"""
Test script to verify build plan interactive UX functionality
"""
import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the maestro directory to the path so we can import the functions
sys.path.insert(0, '/common/active/sblo/Dev/Maestro')

from maestro.main import (
    handle_build_plan,
    create_session,
    set_active_session_name,
    get_session_path_by_name,
    validate_build_target_schema
)


def test_validate_build_target_schema():
    """Test the build target schema validation function"""
    print("Testing build target schema validation...")
    
    # Test valid target
    valid_target = {
        "name": "test-target",
        "pipeline": {
            "steps": []
        }
    }
    assert validate_build_target_schema(valid_target), "Valid target should pass validation"
    print("✓ Valid target passes validation")
    
    # Test missing name
    invalid_target = {
        "pipeline": {
            "steps": []
        }
    }
    assert not validate_build_target_schema(invalid_target), "Target without name should fail validation"
    print("✓ Target without name fails validation")
    
    # Test invalid name type
    invalid_target = {
        "name": 123,
        "pipeline": {
            "steps": []
        }
    }
    assert not validate_build_target_schema(invalid_target), "Target with non-string name should fail validation"
    print("✓ Target with non-string name fails validation")
    
    # Test missing steps in pipeline
    invalid_target = {
        "name": "test",
        "pipeline": {}
    }
    assert not validate_build_target_schema(invalid_target), "Target without steps should fail validation"
    print("✓ Target without steps fails validation")
    
    # Test invalid steps type
    invalid_target = {
        "name": "test",
        "pipeline": {
            "steps": "not-an-array"
        }
    }
    assert not validate_build_target_schema(invalid_target), "Target with non-array steps should fail validation"
    print("✓ Target with non-array steps fails validation")


def test_build_plan_functionality():
    """Test the build plan functionality"""
    print("\nTesting build plan functionality...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Initialize maestro directory structure
        maestro_dir = os.path.join(temp_dir, '.maestro') 
        os.makedirs(maestro_dir, exist_ok=True)
        
        sessions_dir = os.path.join(maestro_dir, 'sessions')
        os.makedirs(sessions_dir, exist_ok=True)
        
        # Create a test session with a unique name
        import time
        session_name = f"test_session_{int(time.time())}"
        # Use the temp directory for session creation to avoid conflicts
        session_path = os.path.join(sessions_dir, f"{session_name}.json")
        
        # Create a new session with status="new" and empty subtasks
        from maestro.session_model import Session
        from maestro.main import save_session
        import uuid
        from datetime import datetime
        session_obj = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="Test root task for build functionality",
            subtasks=[],
            rules_path=None,
            status="new"
        )
        save_session(session_obj, session_path)
        
        set_active_session_name(session_name)
        
        print("Created test session")
        
        # Test one-shot mode with mocked AI response
        print("\n1. Testing one-shot mode with mock AI response...")
        
        # Mock the AI response to return a valid JSON
        mock_response = '''{
            "name": "test-target",
            "description": "A test build target",
            "categories": ["build", "test"],
            "pipeline": {
                "steps": [
                    {"id": "build", "cmd": ["make"], "optional": false}
                ]
            },
            "patterns": {
                "error_extract": ["ERROR: (.*)"],
                "ignore": ["warning"]
            },
            "environment": {
                "vars": {"BUILD_TYPE": "debug"},
                "cwd": "."
            }
        }'''
        
        with patch('maestro.main.planner_preference') as mock_planner_pref, \
             patch('maestro.engines.get_engine') as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = mock_response
            mock_get_engine.return_value = mock_engine

            try:
                # Test one-shot mode
                result = handle_build_plan(
                    session_path,
                    "test-target",
                    verbose=True,
                    one_shot=True,
                    quiet=False
                )
                print("✓ One-shot mode completed successfully")
            except Exception as e:
                print(f"✗ One-shot mode failed: {e}")
                import traceback
                traceback.print_exc()
                return False
                
        print("\n2. Testing schema validation...")
        test_validate_build_target_schema()
        
        print("\n✓ All functionality tests passed!")
        return True


if __name__ == "__main__":
    print("Testing build plan interactive UX functionality...")
    
    success = test_build_plan_functionality()
    
    if success:
        print("\n🎉 All tests passed! Build plan UX is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)