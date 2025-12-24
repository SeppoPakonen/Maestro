"""
Tests for JSON parsing error handling in plan commands.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from maestro.commands.plan import handle_plan_discuss, handle_plan_explore


def test_plan_discuss_json_parse_error():
    """Test that plan discuss handles JSON parse errors gracefully."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid JSON
        invalid_response = '{"invalid": "json", "missing": "required_fields"'
        
        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create a temporary file with the invalid response
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(invalid_response)
                temp_response_path = f.name

            # Mock the run_once method to return our invalid response
            mock_result = Mock()
            mock_result.stdout_path = temp_response_path
            mock_result.stderr_path = None
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 0  # Success exit code but invalid JSON

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Mock()
                test_plan.title = "Test Plan"
                test_plan.items = [Mock()]
                test_plan.items[0].text = "Existing item"
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture stdout to check for error messages
                from io import StringIO
                import sys

                captured_stdout = StringIO()

                # Mock print functions to capture output
                with patch('sys.stdout', captured_stdout), \
                     pytest.raises(SystemExit):
                    # Call the function - should fail after max retries
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Get the output
                output = captured_stdout.getvalue()

                # Verify that the appropriate error message was shown for JSON parse errors
                assert 'PlanOpsResult JSON invalid' in output or 'JSON parse error' in output
                # Ensure old error message is NOT shown
                assert 'Expecting value: line 1 column 1' not in output, f"Old error message found in output: {output}"

                # Verify that raw response was shown in verbose mode
                assert 'Raw AI response' in output, f"Expected raw response message not found in output: {output}"

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_engine_execution_error():
    """Test that plan discuss handles engine execution errors properly."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create a temporary stderr file with error content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("Command not found: qwen\nError details here")
                temp_stderr_path = f.name

            # Mock the run_once method to return an execution failure
            mock_result = Mock()
            mock_result.stdout_path = None
            mock_result.stderr_path = temp_stderr_path
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 127  # Command not found

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Mock()
                test_plan.title = "Test Plan"
                test_plan.items = [Mock()]
                test_plan.items[0].text = "Existing item"
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture stdout to check for error messages
                from io import StringIO
                import sys

                captured_stdout = StringIO()

                # Mock print functions to capture output
                with patch('sys.stdout', captured_stdout), \
                     pytest.raises(SystemExit):
                    # Call the function with verbose mode
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Get the output
                output = captured_stdout.getvalue()

                # Verify that the appropriate error message was shown for engine failure
                assert 'engine failed' in output.lower()
                assert 'exit code 127' in output

                # Verify that stderr excerpt was shown in verbose mode
                assert 'Stderr excerpt' in output, f"Expected stderr excerpt not found in output: {output}"

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary stderr file
        Path(temp_stderr_path).unlink()


def test_plan_explore_json_parse_error():
    """Test that plan explore handles JSON parse errors gracefully."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid JSON
        invalid_response = '{"invalid": "json", "missing": "required_fields"'

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create a temporary file with the invalid response
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(invalid_response)
                temp_response_path = f.name

            # Mock the run_once method to return our invalid response
            mock_result = Mock()
            mock_result.stdout_path = temp_response_path
            mock_result.stderr_path = None
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 0  # Success exit code but invalid JSON

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Mock()
                test_plan.title = "Test Plan"
                test_plan.items = [Mock()]
                test_plan.items[0].text = "Task 1"
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture stdout to check for error messages
                from io import StringIO
                import sys

                captured_stdout = StringIO()

                # Mock print functions to capture output
                with patch('sys.stdout', captured_stdout):
                    # Call the function - should fail after max retries but not raise SystemExit
                    handle_plan_explore("Test Plan", temp_path, verbose=True, max_iterations=1)

                # Get the output
                output = captured_stdout.getvalue()

                # Verify that the appropriate error message was shown for JSON parse errors
                assert 'ProjectOpsResult JSON invalid' in output or 'JSON parse error' in output
                # Ensure old error message is NOT shown
                assert 'Expecting value: line 1 column 1' not in output, f"Old error message found in output: {output}"

                # Verify that raw response was shown in verbose mode
                assert 'Raw AI response' in output, f"Expected raw response message not found in output: {output}"

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()