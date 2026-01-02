"""Tests for session injection functionality."""

import os
import tempfile
import subprocess
import sys
import yaml
from pathlib import Path


def test_session_injection_with_default_session():
    """Test that session vars are injected into interface YAML output with default session."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up environment variables to use the temporary directory
        env = os.environ.copy()
        env["XDG_STATE_HOME"] = tmp_dir

        # Set up the default session with a variable
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set",
            "--session", "default", "--key", "project", "--value", "alpha"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Var set failed: {result.stderr}"

        # Run the demo command (which has a built-in mapping)
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "demo"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Demo command failed: {result.stderr}"

        # Parse the output YAML
        output_data = yaml.safe_load(result.stdout)

        # Verify session name is injected
        assert output_data["session"]["name"] == "default"

        # Verify context vars are injected
        assert output_data["fields"]["context"]["vars"]["project"] == "alpha"

        print("Test A passed: Injection with default session")


def test_env_overrides_stored_active_session():
    """Test that environment variable overrides stored active session."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up environment variables to use the temporary directory
        env = os.environ.copy()
        env["XDG_STATE_HOME"] = tmp_dir

        # Create session "s1" and set a variable
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set",
            "--session", "s1", "--key", "project", "--value", "beta"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Var set failed: {result.stderr}"

        # Set active session to s1
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "session", "set-active", "s1"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Set active session failed: {result.stderr}"

        # Run demo with no env var (should use stored active session s1)
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "demo"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Demo command failed: {result.stderr}"

        # Parse the output YAML
        output_data = yaml.safe_load(result.stdout)

        # Verify session name is s1 and project is beta
        assert output_data["session"]["name"] == "s1"
        assert output_data["fields"]["context"]["vars"]["project"] == "beta"

        # Now run with env var BLINDFOLD_SESSION=default
        env_with_session = env.copy()
        env_with_session["BLINDFOLD_SESSION"] = "default"

        # Set a variable in the default session
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set",
            "--session", "default", "--key", "project", "--value", "alpha"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Var set failed: {result.stderr}"

        result = subprocess.run([
            sys.executable, "-m", "blindfold", "demo"
        ], capture_output=True, text=True, env=env_with_session)
        assert result.returncode == 0, f"Demo command with env failed: {result.stderr}"

        # Parse the output YAML
        output_data = yaml.safe_load(result.stdout)

        # Verify session name is default and project is alpha (from env override)
        assert output_data["session"]["name"] == "default"
        assert output_data["fields"]["context"]["vars"]["project"] == "alpha"

        print("Test B passed: Env overrides stored active session")


def test_overwrite_behavior():
    """Test that DB vars overwrite interface vars."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up environment variables to use the temporary directory
        env = os.environ.copy()
        env["XDG_STATE_HOME"] = tmp_dir

        # Set a variable in the default session
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set",
            "--session", "default", "--key", "project", "--value", "from_db"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Var set failed: {result.stderr}"

        # Also set a different variable
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "--HIDDEN", "var", "set",
            "--session", "default", "--key", "new_var", "--value", "new_value"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Var set failed: {result.stderr}"

        # Run the demo command
        result = subprocess.run([
            sys.executable, "-m", "blindfold", "demo"
        ], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"Demo command failed: {result.stderr}"

        # Parse the output YAML
        output_data = yaml.safe_load(result.stdout)

        # Verify that DB value is present
        assert output_data["fields"]["context"]["vars"]["project"] == "from_db"

        # Verify that new DB vars are added
        assert output_data["fields"]["context"]["vars"]["new_var"] == "new_value"

        print("Test C passed: Overwrite behavior")


if __name__ == "__main__":
    test_session_injection_with_default_session()
    test_env_overrides_stored_active_session()
    test_overwrite_behavior()
    print("All tests passed!")