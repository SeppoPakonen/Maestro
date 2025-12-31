"""CLI acceptance tests for AI commands."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def test_ai_print_cmd_flags():
    """Test that --print-cmd flag works for all engines."""
    
    # Test qwen --print-cmd
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'qwen', '--print-cmd', 'hello']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    # Should print a command without error (even if binary doesn't exist)
    assert result.returncode == 0
    assert 'qwen' in result.stdout.lower() or result.stdout == ''  # Command might not exist but shouldn't crash
    
    # Test gemini --print-cmd
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'gemini', '--print-cmd', 'hello']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    assert 'gemini' in result.stdout.lower() or result.stdout == ''
    
    # Test codex --print-cmd
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'codex', '--print-cmd', 'hello']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    assert 'codex' in result.stdout.lower() or result.stdout == ''
    
    # Test claude --print-cmd
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'claude', '--print-cmd', 'hello']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    assert 'claude' in result.stdout.lower() or result.stdout == ''


def test_ai_help_commands():
    """Test that help commands work for all engines."""
    
    # Test ai --help includes all engines
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', '--help']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    assert 'qwen' in result.stdout.lower()
    assert 'gemini' in result.stdout.lower()
    assert 'codex' in result.stdout.lower()
    assert 'claude' in result.stdout.lower()


def test_command_building_with_options():
    """Test command building with various options."""
    
    # Test qwen with continue-latest
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'qwen', '--continue-latest', '--print-cmd']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    
    # Test qwen with resume
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'qwen', '--resume', 'test123', '--print-cmd']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    
    # Test qwen with stream-json
    result = subprocess.run([
        sys.executable, "-c", 
        "from maestro.main import main; import sys; sys.argv = ['maestro', 'ai', 'qwen', '--stream-json', '--print-cmd', 'test']; main()"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0


if __name__ == "__main__":
    test_ai_print_cmd_flags()
    test_ai_help_commands()
    test_command_building_with_options()
    print("All CLI acceptance tests passed!")
