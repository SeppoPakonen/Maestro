"""Tests for the mapping module."""

import subprocess
import tempfile
import os
import yaml
import json
from pathlib import Path


def test_demo_mapping_outputs_interface(tmp_path):
    """Test that 'python -m blindfold demo' outputs the demo interface YAML."""
    # Set up temporary directories for XDG environment
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state" 
    cache_dir = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    
    # Run the command
    result = subprocess.run(
        ["python", "-m", "blindfold", "demo"],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Assert exit code is 0
    assert result.returncode == 0
    
    # Assert stderr is empty
    assert result.stderr == ""
    
    # Parse stdout as YAML and check content
    try:
        output_data = yaml.safe_load(result.stdout)
        assert output_data["api_version"] == 1
        assert "Demo" in output_data["name"]
    except yaml.YAMLError:
        assert False, f"stdout is not valid YAML: {result.stdout}"


def test_nonmatching_command_still_cookie(tmp_path):
    """Test that non-matching commands still generate error cookies."""
    # Set up temporary directories for XDG environment
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    
    # Run the command
    result = subprocess.run(
        ["python", "-m", "blindfold", "notdemo"],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Assert exit code is 2
    assert result.returncode == 2
    
    # Assert stderr contains error cookie
    assert "error-cookie-id=" in result.stderr


def test_bootstrap_copies_defaults(tmp_path):
    """Test that defaults are bootstrapped into XDG data_dir on first run."""
    # Set up empty data directory
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    cache_dir = tmp_path / "cache"
    
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_dir)
    env["XDG_STATE_HOME"] = str(state_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    
    # Ensure data_dir is empty before run
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Run the command
    result = subprocess.run(
        ["python", "-m", "blindfold", "demo"],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Check that files exist in the expected locations
    interfaces_dir = data_dir / "blindfold" / "interfaces"
    mappings_dir = data_dir / "blindfold" / "mappings"
    
    assert (interfaces_dir / "demo.yaml").exists(), f"File does not exist: {interfaces_dir / 'demo.yaml'}"
    assert (mappings_dir / "mappings.yaml").exists(), f"File does not exist: {mappings_dir / 'mappings.yaml'}"
    
    # Verify the content of the files
    with open(interfaces_dir / "demo.yaml", 'r') as f:
        demo_content = f.read()
        assert "Blindfold Demo Interface" in demo_content
    
    with open(mappings_dir / "mappings.yaml", 'r') as f:
        mappings_content = f.read()
        assert "demo.yaml" in mappings_content