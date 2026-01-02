"""Tests for error cookie and ledger functionality."""

import subprocess
import sys
import json
import os
from pathlib import Path


def test_invalid_command_creates_ledger(monkeypatch, tmp_path):
    """Test that invalid blind commands create an error ledger entry."""
    # Set up temporary directories for XDG paths
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"

    # Create the blindfold subdirectories
    state_blindfold_dir = state_dir / "blindfold"
    state_blindfold_dir.mkdir(parents=True)

    # Monkeypatch the XDG environment variables
    monkeypatch.setenv('XDG_DATA_HOME', str(data_dir))
    monkeypatch.setenv('XDG_STATE_HOME', str(state_dir))
    monkeypatch.setenv('XDG_CACHE_HOME', str(cache_dir))

    # Run blindfold with an invalid command
    result = subprocess.run(
        [sys.executable, "-m", "blindfold", "foobar"],
        capture_output=True,
        text=True,
        env=os.environ.copy()  # Use a copy of environment with our XDG vars
    )

    # Check that it returns exit code 2
    assert result.returncode == 2

    # Extract cookie from stderr
    import re
    match = re.search(r'error-cookie-id=(0x[a-f0-9]{8})', result.stderr)
    assert match is not None, f"Could not find cookie in stderr: {result.stderr}"
    cookie = match.group(1)

    # Check that the error file exists
    error_file_path = state_blindfold_dir / "errors" / f"{cookie}.json"
    assert error_file_path.exists(), f"Error file does not exist: {error_file_path}"

    # Load and validate the JSON content
    with open(error_file_path, 'r', encoding='utf-8') as f:
        error_data = json.load(f)

    # Check required keys exist
    required_keys = {
        "cookie", "argv", "cwd", "stdin_snippet", "stdin_truncated",
        "timestamp_utc", "blindfold_version", "python_version"
    }
    for key in required_keys:
        assert key in error_data, f"Missing required key '{key}' in error record"

    # Check that cookie matches
    assert error_data["cookie"] == cookie

    # Check that argv contains the command
    assert "foobar" in error_data["argv"]

    # Check that stdin_snippet is a string and stdin_truncated is a bool
    assert isinstance(error_data["stdin_snippet"], str)
    assert isinstance(error_data["stdin_truncated"], bool)