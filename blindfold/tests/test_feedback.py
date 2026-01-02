"""Tests for feedback functionality."""

import os
import subprocess
import tempfile
import yaml
import json
from pathlib import Path


def test_feedback_success(tmp_path):
    """Test successful feedback submission."""
    # Set up environment with temporary directories
    xdg_data_home = tmp_path / "data"
    xdg_state_home = tmp_path / "state"
    xdg_cache_home = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_STATE_HOME"] = str(xdg_state_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    
    # First create an error cookie by running blindfold with a command
    result = subprocess.run([
        "python", "-m", "blindfold", "foobar"
    ], capture_output=True, text=True, env=env)
    
    assert result.returncode == 2
    # Extract cookie from stderr
    stderr_lines = result.stderr.strip().split('\n')
    cookie_line = [line for line in stderr_lines if "error-cookie-id=" in line][0]
    cookie = cookie_line.split("error-cookie-id=")[1]
    
    # Prepare feedback YAML
    feedback_yaml = """expectation:
  input: "user prompt"
  context: "some vars"
  process: "should do X"
  output: "expected Y"
"""
    
    # Submit feedback
    result = subprocess.run([
        "python", "-m", "blindfold", "--FEEDBACK", cookie
    ], input=feedback_yaml, capture_output=True, text=True, env=env)
    
    assert result.returncode == 0
    assert result.stdout == f"feedback stored for {cookie}\n"
    
    # Check that feedback file was created
    feedback_file = xdg_state_home / "blindfold" / "feedback" / f"{cookie}.yaml"
    assert feedback_file.exists()
    
    # Load and verify content
    with open(feedback_file, 'r', encoding='utf-8') as f:
        loaded = yaml.safe_load(f)
    
    assert loaded["cookie"] == cookie
    assert "expectation" in loaded
    assert loaded["expectation"]["input"] == "user prompt"


def test_feedback_unknown_cookie(tmp_path):
    """Test feedback with unknown cookie."""
    # Set up environment with temporary directories
    xdg_data_home = tmp_path / "data"
    xdg_state_home = tmp_path / "state"
    xdg_cache_home = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_STATE_HOME"] = str(xdg_state_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    
    # Try to submit feedback for a non-existent cookie
    fake_cookie = "0x1234abcd"
    feedback_yaml = """expectation:
  input: "user prompt"
  context: "some vars"
  process: "should do X"
  output: "expected Y"
"""
    
    result = subprocess.run([
        "python", "-m", "blindfold", "--FEEDBACK", fake_cookie
    ], input=feedback_yaml, capture_output=True, text=True, env=env)
    
    assert result.returncode == 3
    assert "unknown error cookie" in result.stderr


def test_feedback_invalid_cookie_format(tmp_path):
    """Test feedback with invalid cookie format."""
    # Set up environment with temporary directories
    xdg_data_home = tmp_path / "data"
    xdg_state_home = tmp_path / "state"
    xdg_cache_home = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_STATE_HOME"] = str(xdg_state_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    
    # Try to submit feedback with invalid cookie format
    invalid_cookie = "not_a_cookie"
    feedback_yaml = """expectation:
  input: "user prompt"
  context: "some vars"
  process: "should do X"
  output: "expected Y"
"""
    
    result = subprocess.run([
        "python", "-m", "blindfold", "--FEEDBACK", invalid_cookie
    ], input=feedback_yaml, capture_output=True, text=True, env=env)
    
    assert result.returncode == 3
    assert "invalid cookie format" in result.stderr


def test_feedback_empty_payload(tmp_path):
    """Test feedback with empty payload."""
    # Set up environment with temporary directories
    xdg_data_home = tmp_path / "data"
    xdg_state_home = tmp_path / "state"
    xdg_cache_home = tmp_path / "cache"

    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_STATE_HOME"] = str(xdg_state_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)

    # First create an error cookie by running blindfold with a command
    result = subprocess.run([
        "python", "-m", "blindfold", "foobar"
    ], capture_output=True, text=True, env=env)

    assert result.returncode == 2
    # Extract cookie from stderr
    stderr_lines = result.stderr.strip().split('\n')
    cookie_line = [line for line in stderr_lines if "error-cookie-id=" in line][0]
    cookie = cookie_line.split("error-cookie-id=")[1]

    # Submit empty feedback
    result = subprocess.run([
        "python", "-m", "blindfold", "--FEEDBACK", cookie
    ], input="", capture_output=True, text=True, env=env)

    assert result.returncode == 3
    assert "invalid feedback payload" in result.stderr


def test_feedback_stores_expectation_gap(tmp_path):
    """Test that feedback can store expectation_gap content."""
    # Set up environment with temporary directories
    xdg_data_home = tmp_path / "data"
    xdg_state_home = tmp_path / "state"
    xdg_cache_home = tmp_path / "cache"

    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_STATE_HOME"] = str(xdg_state_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)

    # First create an error cookie by running blindfold with a command
    result = subprocess.run([
        "python", "-m", "blindfold", "foobar"
    ], capture_output=True, text=True, env=env)

    assert result.returncode == 2
    # Extract cookie from stderr
    stderr_lines = result.stderr.strip().split('\n')
    cookie_line = [line for line in stderr_lines if "error-cookie-id=" in line][0]
    cookie = cookie_line.split("error-cookie-id=")[1]

    # Prepare feedback YAML with expectation_gap
    feedback_yaml = """expectation_gap:
  missing:
    - "Need database schema name for table X"
    - "Need env var FOO to locate config"
  notes: "Without these I can't produce output Y."
"""

    # Submit feedback
    result = subprocess.run([
        "python", "-m", "blindfold", "--FEEDBACK", cookie
    ], input=feedback_yaml, capture_output=True, text=True, env=env)

    assert result.returncode == 0
    assert result.stdout == f"feedback stored for {cookie}\n"

    # Check that feedback file was created
    feedback_file = xdg_state_home / "blindfold" / "feedback" / f"{cookie}.yaml"
    assert feedback_file.exists()

    # Load and verify content
    with open(feedback_file, 'r', encoding='utf-8') as f:
        loaded = yaml.safe_load(f)

    assert loaded["cookie"] == cookie
    assert "expectation_gap" in loaded
    assert "missing" in loaded["expectation_gap"]
    assert len(loaded["expectation_gap"]["missing"]) == 2
    assert "Need database schema name for table X" in loaded["expectation_gap"]["missing"]
    assert "Need env var FOO to locate config" in loaded["expectation_gap"]["missing"]
    assert loaded["expectation_gap"]["notes"] == "Without these I can't produce output Y."