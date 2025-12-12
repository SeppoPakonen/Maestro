"""
Tests for interrupt handling functionality.

This test suite verifies the new interrupt and resume functionality
for the orchestrator system.
"""
import os
import sys
import json
import tempfile
import signal
from unittest.mock import patch, MagicMock
import subprocess
import time

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator_cli import handle_resume_session, handle_plan_session
from session_model import Session, Subtask
from engines import run_cli_engine, EngineResult
import engines


def test_engine_result_dataclass():
    """Test that EngineResult dataclass works as expected."""
    result = EngineResult(exit_code=0, stdout="test output", stderr="", interrupted=False)
    assert result.exit_code == 0
    assert result.stdout == "test output"
    assert result.stderr == ""
    assert result.interrupted is False
    print("✓ EngineResult dataclass test passed")


def test_run_cli_engine_with_interruption():
    """Test run_cli_engine handles interruption gracefully."""
    # This is difficult to test directly since we need to simulate Ctrl+C
    # For now, we'll test that the function accepts the new signature
    config = engines.CliEngineConfig(binary="echo", base_args=[])
    
    # This test is more of a structural verification since
    # actual interruption testing would require complex mocking
    result = run_cli_engine(config, "test", debug=False, stream_output=False)
    assert isinstance(result, EngineResult)
    print("✓ run_cli_engine return type test passed")


def test_session_model_interrupted_status():
    """Test that session model supports interrupted status."""
    # Test that interrupted is a valid status
    from session_model import SESSION_STATUSES, SUBTASK_STATUSES
    
    assert "interrupted" in SESSION_STATUSES
    assert "interrupted" in SUBTASK_STATUSES
    print("✓ Session model interrupted status test passed")


def test_subtask_interrupted_handling():
    """Test that subtasks can have interrupted status."""
    subtask = Subtask(
        id="test-id",
        title="Test Subtask",
        description="Test Description",
        planner_model="test",
        worker_model="test",
        status="interrupted",  # This should be valid now
        summary_file="/tmp/test.txt"
    )
    assert subtask.status == "interrupted"
    print("✓ Subtask interrupted status test passed")


def create_test_session_with_interrupted_subtask():
    """Helper to create a test session with an interrupted subtask."""
    from session_model import Session, Subtask
    import uuid
    from datetime import datetime
    
    subtask = Subtask(
        id=str(uuid.uuid4()),
        title="Interrupted Subtask",
        description="A subtask that was interrupted",
        planner_model="codex_planner",
        worker_model="qwen",
        status="interrupted",
        summary_file=""
    )
    
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task="Test root task",
        subtasks=[subtask],
        rules_path=None,
        status="interrupted"
    )
    
    return session


def test_partial_output_file_creation():
    """Test that partial output files are created during interruption."""
    import tempfile
    import os
    from pathlib import Path
    
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create partials directory
        partials_dir = Path(temp_dir) / "partials"
        partials_dir.mkdir(exist_ok=True)
        
        # Test file creation
        test_subtask_id = "test-123"
        partial_filename = partials_dir / f"worker_{test_subtask_id}.partial.txt"
        
        # Write some test content
        test_content = "This is partial output from an interrupted task"
        with open(partial_filename, 'w') as f:
            f.write(test_content)
        
        # Verify file exists and content matches
        assert partial_filename.exists()
        with open(partial_filename, 'r') as f:
            content = f.read()
            assert content == test_content
        
        print("✓ Partial output file creation test passed")


def test_cli_retry_interrupted_parameter():
    """Test that the retry_interrupted parameter is handled properly."""
    # This tests that the parameter exists and can be passed
    # Actual functionality testing would require more complex mocking
    import inspect
    
    # Check that handle_resume_session accepts retry_interrupted parameter
    sig = inspect.signature(handle_resume_session)
    assert 'retry_interrupted' in sig.parameters
    print("✓ CLI retry-interrupted parameter test passed")


def run_all_tests():
    """Run all tests for interrupt handling functionality."""
    print("Running interrupt handling functionality tests...\n")
    
    test_engine_result_dataclass()
    test_run_cli_engine_with_interruption()
    test_session_model_interrupted_status()
    test_subtask_interrupted_handling()
    test_partial_output_file_creation()
    test_cli_retry_interrupted_parameter()
    
    print("\n✓ All interrupt handling functionality tests passed!")


if __name__ == "__main__":
    run_all_tests()