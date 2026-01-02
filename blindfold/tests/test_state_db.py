"""Tests for the state database functionality."""

import os
import tempfile
import subprocess
import sys
from pathlib import Path


def test_state_db_functionality():
    """Test the state database functionality using subprocess calls."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up environment variables to use the temporary directory
        env = os.environ.copy()
        env["XDG_STATE_HOME"] = tmp_dir
        
        # Define the state directory path
        state_dir = Path(tmp_dir) / "blindfold"
        db_path = state_dir / "blindfold.sqlite3"
        
        # Test 1: Create a session
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "session", "create", "default"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Session create failed: {result.stderr}"
        assert f"created session default" in result.stdout
        
        # Test 2: List sessions (should contain 'default')
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "session", "list"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Session list failed: {result.stderr}"
        assert "default" in result.stdout
        
        # Test 3: Set a variable in the session
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set", 
            "--session", "default", "--key", "foo", "--value", "bar"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Var set failed: {result.stderr}"
        assert "set default:foo" in result.stdout
        
        # Test 4: Get the variable (should return 'bar')
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "get",
            "--session", "default", "--key", "foo"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Var get failed: {result.stderr}"
        assert result.stdout.strip() == "bar"
        
        # Test 5: List variables in the session (should contain 'foo=bar')
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "list",
            "--session", "default"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Var list failed: {result.stderr}"
        assert "foo=bar" in result.stdout
        
        # Test 6: Delete the session
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "session", "delete", "default"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Session delete failed: {result.stderr}"
        assert "deleted session default" in result.stdout
        
        # Test 7: List sessions again (should NOT contain 'default')
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "session", "list"
        ], capture_output=True, text=True, env=env)
        
        assert result.returncode == 0, f"Session list after delete failed: {result.stderr}"
        assert "default" not in result.stdout
        
        # Test 8: Verify that the database file exists
        assert db_path.exists(), f"Database file does not exist at {db_path}"
        
        print("All tests passed!")


if __name__ == "__main__":
    test_state_db_functionality()