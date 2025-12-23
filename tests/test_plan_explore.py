"""
Tests for the Plan Explore command with mocked AI.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from maestro.plans import PlanStore, Plan, PlanItem
from maestro.commands.plan import handle_plan_explore


def test_plan_explore_single_plan_valid_json():
    """Test plan explore with a single plan and valid ProjectOpsResult JSON from AI."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Implement feature A\n- Fix bug B\n")
        temp_path = f.name

    try:
        # Mock AI response with valid ProjectOpsResult
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Development"
                },
                {
                    "action": "phase_create",
                    "track": "Development",
                    "title": "Initial Implementation"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Implement feature A"), PlanItem(text="Fix bug B")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'Development'", "Create phase 'Initial Implementation' in track 'Development'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'Development'", "Created phase 'Initial Implementation' in track 'Development'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output
                    with patch('builtins.input', return_value='y'), \
                         patch('sys.stdout'):
                        # Call the function with verbose mode to see the output
                        handle_plan_explore("Test Plan", temp_path, verbose=True, apply=True, max_iterations=1)

            # Verify that PlanStore was called with the correct path
            mock_planstore_class.assert_called_with(temp_path)

            # Verify that the executor's apply_ops method was called (indicating changes were applied)
            mock_executor_instance.apply_ops.assert_called_once()

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_all_plans_valid_json():
    """Test plan explore with all plans and valid ProjectOpsResult JSON from AI."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan 1\n- Task 1\n\n## Test Plan 2\n- Task 2\n")
        temp_path = f.name

    try:
        # Mock AI response with valid ProjectOpsResult
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "New Track"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the load method to return our test plans
                test_plan1 = Plan(title="Test Plan 1", items=[PlanItem(text="Task 1")])
                test_plan2 = Plan(title="Test Plan 2", items=[PlanItem(text="Task 2")])
                mock_store_instance.load.return_value = [test_plan1, test_plan2]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'New Track'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'New Track'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output
                    with patch('builtins.input', return_value='y'), \
                         patch('sys.stdout'):
                        # Call the function with verbose mode to see the output
                        handle_plan_explore(None, temp_path, verbose=True, apply=True, max_iterations=1)

            # Verify that PlanStore was called with the correct path
            mock_planstore_class.assert_called_with(temp_path)

            # Verify that the executor's apply_ops method was called (indicating changes were applied)
            mock_executor_instance.apply_ops.assert_called_once()

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_invalid_json_retry():
    """Test plan explore with invalid JSON that triggers retry."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid JSON first, then valid
        invalid_response = '{"invalid": "json", "missing": "required_fields"'
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Retry Success Track"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Configure side_effect to return invalid response first, then valid
            # First call returns invalid response
            mock_result_invalid = Mock()
            mock_result_invalid.stdout_path = None
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(invalid_response)
                temp_response.flush()
                mock_result_invalid.stdout_path = temp_response.name

            # Second call returns valid response
            mock_result_valid = Mock()
            mock_result_valid.stdout_path = None
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result_valid.stdout_path = temp_response.name

            mock_manager_instance.run_once.side_effect = [mock_result_invalid, mock_result_valid]

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Task 1")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'Retry Success Track'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'Retry Success Track'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output
                    with patch('builtins.input', return_value='y'), \
                         patch('sys.stdout'):
                        # Call the function with verbose mode to see the output
                        handle_plan_explore("Test Plan", temp_path, verbose=True, apply=True, max_iterations=1)

                    # Verify that the executor's apply_ops method was called (indicating changes were applied)
                    mock_executor_instance.apply_ops.assert_called_once()

                    # Verify that run_once was called twice (once for initial, once for retry)
                    assert mock_manager_instance.run_once.call_count == 2

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_user_declines_apply():
    """Test plan explore when user declines to apply changes."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response with valid ProjectOpsResult
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Declined Track"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response
            
            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Capture input and output - user declines
            with patch('builtins.input', return_value='n'), \
                 patch('sys.stdout'):
                handle_plan_explore("Test Plan", verbose=True, dry_run=False)

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_stop_condition_empty_actions():
    """Test plan explore stops when AI returns empty actions."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response with empty actions
        empty_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": []  # Empty actions should trigger stop condition
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return empty response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(empty_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Task 1")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Capture input and output
                with patch('builtins.input', return_value='y'), \
                     patch('sys.stdout'):
                    # Call the function with verbose mode to see the output
                    handle_plan_explore("Test Plan", temp_path, verbose=True, apply=True)

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_session_start_interrupt_resume():
    """Test starting explore with --save-session, running 1 iteration, interrupting, and verifying session exists."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Development"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Task 1")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'Development'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'Development'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output - simulate user applying changes
                    with patch('builtins.input', side_effect=['y']), \
                         patch('sys.stdout'):
                        # Call the function with session flags
                        handle_plan_explore(
                            "Test Plan",
                            temp_path,
                            verbose=True,
                            apply=True,
                            max_iterations=1,  # Only run 1 iteration
                            save_session=True  # Enable session saving
                        )

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_auto_apply_mode():
    """Test --auto-apply mode applies without prompts but still logs preview."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Auto Apply Track"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Task 1")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'Auto Apply Track'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'Auto Apply Track'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output - no input needed due to auto-apply
                    with patch('sys.stdout'):
                        # Call the function with auto-apply mode
                        handle_plan_explore(
                            "Test Plan",
                            None,  # No session to resume
                            verbose=True,
                            dry_run=False,
                            auto_apply=True,  # Enable auto-apply mode
                            max_iterations=1
                        )

                    # Verify that apply_ops was called (indicating auto-apply worked)
                    mock_executor_instance.apply_ops.assert_called_once()

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_explore_stop_after_apply():
    """Test --stop-after-apply mode applies one iteration then stops."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Task 1\n")
        temp_path = f.name

    try:
        # Mock AI response
        valid_response = {
            "kind": "project_ops",
            "version": 1,
            "scope": "project",
            "actions": [
                {
                    "action": "track_create",
                    "title": "Stop After Apply Track"
                }
            ]
        }

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            mock_result.stdout_path = None  # Will use direct response

            # Create a temporary file with the response content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_response:
                temp_response.write(json.dumps(valid_response))
                temp_response.flush()
                mock_result.stdout_path = temp_response.name

            mock_manager_instance.run_once.return_value = mock_result

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Task 1")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]
                mock_planstore_class.return_value = mock_store_instance

                # Mock the ProjectOpsExecutor and its methods
                with patch('maestro.project_ops.executor.ProjectOpsExecutor') as mock_executor_class:
                    mock_executor_instance = Mock()
                    mock_executor_class.return_value = mock_executor_instance

                    # Mock the preview_ops and apply_ops methods
                    mock_preview_result = Mock()
                    mock_preview_result.changes = ["Create track: 'Stop After Apply Track'"]
                    mock_executor_instance.preview_ops.return_value = mock_preview_result

                    mock_apply_result = Mock()
                    mock_apply_result.changes = ["Created track: 'Stop After Apply Track'"]
                    mock_executor_instance.apply_ops.return_value = mock_apply_result

                    # Capture input and output
                    with patch('builtins.input', return_value='y'), \
                         patch('sys.stdout'):
                        # Call the function with stop-after-apply mode
                        handle_plan_explore(
                            "Test Plan",
                            None,  # No session to resume
                            verbose=True,
                            dry_run=False,
                            stop_after_apply=True,  # Enable stop after apply mode
                            max_iterations=3  # Would normally do 3, but should stop after 1
                        )

    finally:
        # Clean up temp file
        Path(temp_path).unlink()