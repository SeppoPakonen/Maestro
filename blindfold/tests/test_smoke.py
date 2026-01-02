"""Smoke tests for blindfold CLI."""

import subprocess
import yaml
import sys
import re

def test_version():
    """Test the --version flag."""
    result = subprocess.run(
        [sys.executable, "-m", "blindfold", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert result.stdout.strip() != ""

def test_default_yaml():
    """Test the default behavior outputs valid YAML with mode 'blind'."""
    result = subprocess.run(
        [sys.executable, "-m", "blindfold"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    data = yaml.safe_load(result.stdout)
    assert data["mode"] == "blind"

def test_unknown_arg():
    """Test that unknown arguments return exit code 2 and error message with cookie."""
    result = subprocess.run(
        [sys.executable, "-m", "blindfold", "--nope"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2
    assert "virheellinen komento." in result.stderr
    assert "error-cookie-id=0x" in result.stderr
    # Check that the cookie format is correct (0x followed by 8 hex digits)
    assert re.search(r'0x[a-f0-9]{8}', result.stderr) is not None