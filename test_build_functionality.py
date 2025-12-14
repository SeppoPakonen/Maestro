#!/usr/bin/env python3
"""
Test script to verify build target lifecycle functionality
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the maestro directory to the path so we can import the functions
sys.path.insert(0, '/common/active/sblo/Dev/Maestro')

from maestro.main import (
    handle_build_new,
    handle_build_list,
    handle_build_set,
    handle_build_get,
    handle_build_show,
    create_session,
    set_active_session_name,
    get_session_path_by_name
)


def test_build_lifecycle():
    """Test the build target lifecycle functionality"""
    print("Testing build target lifecycle functionality...")
    
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
            rules_path=None,  # Point to rules file if it exists
            status="new"
        )
        save_session(session_obj, session_path)

        set_active_session_name(session_name)
        
        print("Created test session")
        
        # Test build new command
        print("\n1. Testing build new command...")
        try:
            handle_build_new(session_path, "debug-default", verbose=True)
            print("✓ Build new command executed successfully")
        except Exception as e:
            print(f"✗ Build new command failed: {e}")
            return False
            
        # Test build list command
        print("\n2. Testing build list command...")
        try:
            handle_build_list(session_path, verbose=True)
            print("✓ Build list command executed successfully")
        except Exception as e:
            print(f"✗ Build list command failed: {e}")  
            return False
            
        # Test build set command
        print("\n3. Testing build set command...")
        try:
            handle_build_set(session_path, "debug-default", verbose=True)
            print("✓ Build set command executed successfully")
        except Exception as e:
            print(f"✗ Build set command failed: {e}")
            return False
            
        # Test build get command
        print("\n4. Testing build get command...")
        try:
            handle_build_get(session_path, verbose=True)
            print("✓ Build get command executed successfully")
        except Exception as e:
            print(f"✗ Build get command failed: {e}")
            return False
            
        # Test build show command
        print("\n5. Testing build show command...")
        try:
            handle_build_show(session_path, "debug-default", verbose=True)
            print("✓ Build show command executed successfully")
        except Exception as e:
            print(f"✗ Build show command failed: {e}")
            return False
            
        print("\n✓ All build target lifecycle tests passed!")
        return True


if __name__ == "__main__":
    success = test_build_lifecycle()
    if success:
        print("\n🎉 All tests passed! Build target lifecycle is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)