"""Tests for redaction and garbage collection functionality."""

import os
import tempfile
import time
from pathlib import Path
import subprocess
import json
import yaml


def test_redaction_applies_to_error_ledger(tmp_path):
    """Test that redaction applies to error ledger stdin_snippet."""
    # Set up temporary directories
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"

    data_dir.mkdir()
    state_dir.mkdir()
    cache_dir.mkdir()

    # Set environment variables to use temporary directories
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)

    # Run an invalid command with sensitive data in stdin
    result = subprocess.run(
        ["python", "-m", "blindfold", "invalid-command"],
        input="hello token=SECRET123",
        text=True,
        capture_output=True,
        env=env
    )

    # Extract cookie from stderr (the error message is printed to stderr)
    stderr_output = result.stderr
    # Find the cookie in the format "error-cookie-id=0x..."
    import re
    match = re.search(r"error-cookie-id=(0x[0-9a-f]{8})", stderr_output)
    assert match, f"Could not find cookie in stderr: {stderr_output}"
    cookie = match.group(1)

    # Open JSON ledger file and assert redaction
    error_file = state_dir / "blindfold" / "errors" / f"{cookie}.json"
    assert error_file.exists(), f"Error file does not exist: {error_file}"

    with open(error_file, 'r') as f:
        error_data = json.load(f)

    stdin_snippet = error_data.get("stdin_snippet", "")
    # Check that the secret is not present
    assert "SECRET123" not in stdin_snippet
    # Check that the redacted form is present
    assert "token=***" in stdin_snippet


def test_redaction_applies_to_feedback(tmp_path):
    """Test that redaction applies to feedback storage."""
    # Set up temporary directories
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"

    data_dir.mkdir()
    state_dir.mkdir()
    cache_dir.mkdir()

    # Set environment variables to use temporary directories
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)

    # First, create an error cookie by running an invalid command
    result = subprocess.run(
        ["python", "-m", "blindfold", "invalid-command"],
        input="some input",
        text=True,
        capture_output=True,
        env=env
    )

    # Extract cookie from stderr
    stderr_output = result.stderr
    import re
    match = re.search(r"error-cookie-id=(0x[0-9a-f]{8})", stderr_output)
    assert match, f"Could not find cookie in stderr: {stderr_output}"
    cookie = match.group(1)

    # Submit feedback that contains sensitive data
    feedback_data = {
        "note": "This contains api_key=ABC",
        "other_field": "normal data"
    }

    feedback_yaml = yaml.dump(feedback_data)
    result = subprocess.run(
        ["python", "-m", "blindfold", "--FEEDBACK", cookie],
        input=feedback_yaml,
        text=True,
        capture_output=True,
        env=env
    )

    assert result.returncode == 0, f"Feedback submission failed: {result.stderr}"

    # Check the stored feedback file for redaction
    feedback_file = state_dir / "blindfold" / "feedback" / f"{cookie}.yaml"
    assert feedback_file.exists(), f"Feedback file does not exist: {feedback_file}"

    with open(feedback_file, 'r') as f:
        feedback_content = f.read()

    # Check that the secret is not present
    assert "api_key=ABC" not in feedback_content
    # Check that the redacted form is present
    assert "api_key=***" in feedback_content


def test_gc_deletes_old_files(tmp_path):
    """Test that GC deletes old error and feedback files."""
    # Set up temporary directories
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"

    data_dir.mkdir()
    state_dir.mkdir()
    cache_dir.mkdir()

    # Set environment variables to use temporary directories
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)

    # First, create an error cookie by running an invalid command
    result = subprocess.run(
        ["python", "-m", "blindfold", "invalid-command"],
        input="some input",
        text=True,
        capture_output=True,
        env=env
    )

    # Extract cookie from stderr
    stderr_output = result.stderr
    import re
    match = re.search(r"error-cookie-id=(0x[0-9a-f]{8})", stderr_output)
    assert match, f"Could not find cookie in stderr: {stderr_output}"
    cookie = match.group(1)

    # Submit feedback for this cookie
    feedback_data = {"note": "test feedback"}
    feedback_yaml = yaml.dump(feedback_data)
    result = subprocess.run(
        ["python", "-m", "blindfold", "--FEEDBACK", cookie],
        input=feedback_yaml,
        text=True,
        capture_output=True,
        env=env
    )

    assert result.returncode == 0, f"Feedback submission failed: {result.stderr}"

    # Verify files exist before GC
    error_file = state_dir / "blindfold" / "errors" / f"{cookie}.json"
    feedback_file = state_dir / "blindfold" / "feedback" / f"{cookie}.yaml"
    assert error_file.exists(), f"Error file should exist before GC: {error_file}"
    assert feedback_file.exists(), f"Feedback file should exist before GC: {feedback_file}"

    # Manually set their mtime to an old timestamp (10 days ago)
    old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
    os.utime(error_file, (old_time, old_time))
    os.utime(feedback_file, (old_time, old_time))

    # Run GC to delete files older than 1 day
    result = subprocess.run(
        ["python", "-m", "blindfold", "--HIDDEN", "gc", "--older-than", "1d"],
        text=True,
        capture_output=True,
        env=env
    )

    # Check that GC ran successfully
    assert result.returncode == 0, f"GC command failed: {result.stderr}"

    # Check that the output mentions the deletions
    assert "deleted 1 error logs, 1 feedback files" in result.stdout

    # Verify files are deleted after GC
    assert not error_file.exists(), f"Error file should be deleted after GC: {error_file}"
    assert not feedback_file.exists(), f"Feedback file should be deleted after GC: {feedback_file}"