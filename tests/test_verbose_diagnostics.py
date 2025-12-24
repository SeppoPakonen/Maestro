"""
Tests for verbose diagnostics in AI commands.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from maestro.commands.plan import handle_plan_discuss, handle_plan_explore


def test_plan_discuss_verbose_diagnostics():
    """Test that plan discuss shows verbose diagnostics when -v is enabled."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        # Mock AI response with valid PlanOpsResult
        valid_response = {
            "kind": "plan_ops",
            "version": 1,
            "scope": "plan",
            "actions": [
                {
                    "action": "plan_item_add",
                    "selector": {"title": "Test Plan"},
                    "text": "New item from AI"
                }
            ],
            "notes": "Added a new item"
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create a temporary file with the valid response
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json.dumps(valid_response))
                temp_response_path = f.name

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = temp_response_path
            mock_result.stderr_path = None
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 0

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

                # After applying the operations, return an updated plan
                updated_plan = Mock()
                updated_plan.title = "Test Plan"
                updated_plan.items = [Mock(), Mock()]
                updated_plan.items[0].text = "Existing item"
                updated_plan.items[1].text = "New item from AI"
                mock_store_instance.load.return_value = [updated_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture output to verify verbose messages are shown
                captured_output = []
                def mock_print_info(msg, *args, **kwargs):
                    captured_output.append(msg)

                # Mock print_info to capture verbose output
                with patch('builtins.input', return_value='y'), \
                     patch('maestro.modules.utils.print_info', side_effect=mock_print_info):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Verify that verbose diagnostics were shown
                verbose_messages_found = any(
                    'AI Engine:' in msg or 
                    'Arguments:' in msg or 
                    'Starting engine execution' in msg or
                    'Engine execution completed' in msg
                    for msg in captured_output
                )
                assert verbose_messages_found, f"Expected verbose messages not found in output: {captured_output}"

                # Verify that PlanStore was called with the correct path
                mock_planstore_class.assert_called_with(temp_path)

                # Verify that the store's save method was called (indicating changes were applied)
                assert mock_store_instance.save.called

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_engine_failure_verbose():
    """Test that plan discuss shows stderr when engine fails in verbose mode."""
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
                f.write("Error: Model not found\nAdditional error details here")
                temp_stderr_path = f.name

            # Mock the run_once method to return a failure result
            mock_result = Mock()
            mock_result.stdout_path = None
            mock_result.stderr_path = temp_stderr_path
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 1  # Failure exit code

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

                # Capture output to verify verbose messages are shown
                captured_output = []
                def mock_print_info(msg, *args, **kwargs):
                    captured_output.append(msg)

                def mock_print_error(msg, *args, **kwargs):
                    captured_output.append(f"ERROR: {msg}")

                # Mock print functions to capture output
                with patch('builtins.input', return_value='y'), \
                     patch('maestro.modules.utils.print_info', side_effect=mock_print_info), \
                     patch('maestro.modules.utils.print_error', side_effect=mock_print_error), \
                     pytest.raises(SystemExit):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Verify that stderr was shown in verbose mode
                stderr_shown = any(
                    'Stderr excerpt' in msg or 
                    'Error: Model not found' in msg
                    for msg in captured_output
                )
                assert stderr_shown, f"Expected stderr messages not found in output: {captured_output}"

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary stderr file
        Path(temp_stderr_path).unlink()


def test_plan_discuss_empty_response_verbose():
    """Test that plan discuss handles empty response with proper verbose output."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create an empty stdout file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("")  # Empty response
                temp_stdout_path = f.name

            # Mock the run_once method to return an empty response
            mock_result = Mock()
            mock_result.stdout_path = temp_stdout_path
            mock_result.stderr_path = None
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 0  # Success exit code but empty response

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

                # Capture output to verify verbose messages are shown
                captured_output = []
                def mock_print_info(msg, *args, **kwargs):
                    captured_output.append(msg)

                def mock_print_error(msg, *args, **kwargs):
                    captured_output.append(f"ERROR: {msg}")

                # Mock print functions to capture output
                with patch('builtins.input', return_value='y'), \
                     patch('maestro.modules.utils.print_info', side_effect=mock_print_info), \
                     patch('maestro.modules.utils.print_error', side_effect=mock_print_error), \
                     pytest.raises(SystemExit):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Verify that the appropriate error message was shown for empty response
                empty_response_error = any(
                    'empty response' in msg.lower() and 'engine error' in msg.lower()
                    for msg in captured_output
                )
                assert empty_response_error, f"Expected empty response error not found in output: {captured_output}"

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary stdout file
        Path(temp_stdout_path).unlink()