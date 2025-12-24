"""
Tests for the Plan Discuss command with mocked AI.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from maestro.plans import PlanStore, Plan, PlanItem
from maestro.commands.plan import handle_plan_discuss


def test_plan_discuss_valid_json():
    """Test plan discuss with valid PlanOpsResult JSON from AI."""
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

            # Mock the run_once method to return our valid response
            mock_result = Mock()
            # Create a temporary file with the valid response
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json.dumps(valid_response))
                temp_response_path = f.name

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
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                # After applying the operations, return an updated plan
                updated_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item"), PlanItem(text="New item from AI")])
                mock_store_instance.load.return_value = [updated_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture input and output
                with patch('builtins.input', return_value='y'), \
                     patch('sys.stdout'):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

            # Verify that PlanStore was called with the correct path
            mock_planstore_class.assert_called_with(temp_path)

            # Verify that the store's save method was called (indicating changes were applied)
            assert mock_store_instance.save.called

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_invalid_json_retry():
    """Test plan discuss with invalid JSON that triggers retry."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid JSON first, then valid
        invalid_response = '{"invalid": "json", "missing": "required_fields"'
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

            # Create temporary files for the responses
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(invalid_response)
                temp_invalid_path = f.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json.dumps(valid_response))
                temp_valid_path = f.name

            # Configure side_effect to return invalid response first, then valid
            mock_result_invalid = Mock()
            mock_result_invalid.stdout_path = temp_invalid_path
            mock_result_invalid.stderr_path = None
            mock_result_invalid.session_id = None
            mock_result_invalid.raw_events_count = 0
            mock_result_invalid.exit_code = 0

            mock_result_valid = Mock()
            mock_result_valid.stdout_path = temp_valid_path
            mock_result_valid.stderr_path = None
            mock_result_valid.session_id = None
            mock_result_valid.raw_events_count = 0
            mock_result_valid.exit_code = 0

            mock_manager_instance.run_once.side_effect = [mock_result_invalid, mock_result_valid]

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                # After applying the operations, return an updated plan
                updated_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item"), PlanItem(text="New item from AI")])
                mock_store_instance.load.return_value = [updated_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture input and output
                with patch('builtins.input', return_value='y'), \
                     patch('sys.stdout'):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Verify that the store's save method was called (indicating changes were applied)
                assert mock_store_instance.save.called

                # Verify that run_once was called twice (once for initial, once for retry)
                assert mock_manager_instance.run_once.call_count == 2

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_discuss_invalid_schema_retry():
    """Test plan discuss with invalid schema that triggers retry."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid schema first, then valid
        invalid_schema_response = {
            "kind": "plan_ops",
            "version": 1,
            "scope": "plan",
            "actions": [
                {
                    "action": "invalid_action_type",  # Invalid action
                    "selector": {"title": "Test Plan"},
                    "text": "Invalid action"
                }
            ]
        }

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

            # Create temporary files for the responses
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json.dumps(invalid_schema_response))
                temp_invalid_path = f.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json.dumps(valid_response))
                temp_valid_path = f.name

            # Configure side_effect to return invalid response first, then valid
            mock_result_invalid = Mock()
            mock_result_invalid.stdout_path = temp_invalid_path
            mock_result_invalid.stderr_path = None
            mock_result_invalid.session_id = None
            mock_result_invalid.raw_events_count = 0
            mock_result_invalid.exit_code = 0

            mock_result_valid = Mock()
            mock_result_valid.stdout_path = temp_valid_path
            mock_result_valid.stderr_path = None
            mock_result_valid.session_id = None
            mock_result_valid.raw_events_count = 0
            mock_result_valid.exit_code = 0

            mock_manager_instance.run_once.side_effect = [mock_result_invalid, mock_result_valid]

            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the get_plan method to return our test plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item")])
                mock_store_instance.get_plan.return_value = test_plan
                mock_store_instance.load.return_value = [test_plan]

                # After applying the operations, return an updated plan
                updated_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item"), PlanItem(text="New item from AI")])
                mock_store_instance.load.return_value = [updated_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture input and output
                with patch('builtins.input', return_value='y'), \
                     patch('sys.stdout'):
                    # Call the function with verbose mode to see the output
                    handle_plan_discuss("Test Plan", temp_path, verbose=True)

                # Verify that the store's save method was called (indicating changes were applied)
                assert mock_store_instance.save.called

                # Verify that run_once was called twice (once for initial, once for retry)
                assert mock_manager_instance.run_once.call_count == 2

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_discuss_max_retries_fail():
    """Test plan discuss fails after max retries."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name

    try:
        # Mock AI response with invalid JSON every time
        invalid_response = '{"invalid": "json", "missing": "required_fields"'

        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            mock_manager_instance = Mock()
            mock_manager_class.return_value = mock_manager_instance

            # Create a temporary file with the invalid response
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(invalid_response)
                temp_response_path = f.name

            # Configure to always return invalid response
            mock_result = Mock()
            mock_result.stdout_path = temp_response_path
            mock_result.stderr_path = None
            mock_result.session_id = None
            mock_result.raw_events_count = 0
            mock_result.exit_code = 0

            mock_manager_instance.run_once.return_value = mock_result

            # Should raise SystemExit due to max retries
            with patch('builtins.input', return_value='y'), \
                 patch('sys.stdout'), \
                 pytest.raises(SystemExit):
                handle_plan_discuss("Test Plan", temp_path, verbose=True)

            # Verify that run_once was called 3 times (initial + 2 retries)
            assert mock_manager_instance.run_once.call_count == 3

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_user_declines_apply():
    """Test plan discuss when user declines to apply changes."""
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

            # Capture input and output - user declines
            with patch('builtins.input', return_value='n'), \
                 patch('sys.stdout'):
                handle_plan_discuss("Test Plan", temp_path, verbose=True)

            # Check that the plan was NOT updated
            store = PlanStore(temp_path)
            plans = store.load()
            test_plan = next((p for p in plans if p.title == "Test Plan"), None)
            assert test_plan is not None
            assert len(test_plan.items) == 1  # Should still have only the original item

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_no_argument_no_plans():
    """Test plan discuss with no argument when no plans exist."""
    # Create a temporary plan store with no plans
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n")  # Empty plans section
        temp_path = f.name

    try:
        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the load method to return empty list
                mock_store_instance.load.return_value = []
                mock_planstore_class.return_value = mock_store_instance

                # Should raise SystemExit due to no plans
                with patch('sys.stdout'), \
                     pytest.raises(SystemExit):
                    handle_plan_discuss(None, temp_path, verbose=True)

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_plan_discuss_no_argument_single_plan():
    """Test plan discuss with no argument when there is exactly one plan."""
    # Create a temporary plan store with one plan
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
                # Mock the load method to return a single plan
                test_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item")])
                mock_store_instance.load.return_value = [test_plan]
                # Mock get_plan to return the same plan
                mock_store_instance.get_plan.return_value = test_plan

                # After applying the operations, return an updated plan
                updated_plan = Plan(title="Test Plan", items=[PlanItem(text="Existing item"), PlanItem(text="New item from AI")])
                mock_store_instance.load.return_value = [updated_plan]

                mock_planstore_class.return_value = mock_store_instance

                # Capture input and output
                with patch('builtins.input', return_value='y'), \
                     patch('sys.stdout'):
                    # Call the function with no title_or_number (None)
                    handle_plan_discuss(None, temp_path, verbose=True)

                # Verify that the store's save method was called (indicating changes were applied)
                assert mock_store_instance.save.called

    finally:
        # Clean up temp file
        Path(temp_path).unlink()
        # Clean up the temporary response file
        Path(temp_response_path).unlink()


def test_plan_discuss_no_argument_multiple_plans():
    """Test plan discuss with no argument when there are multiple plans."""
    # Create a temporary plan store with multiple plans
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Plan 1\n- Item 1\n\n## Plan 2\n- Item 2\n")
        temp_path = f.name

    try:
        with patch('maestro.ai.manager.AiEngineManager') as mock_manager_class:
            # Mock PlanStore to use our temp file
            with patch('maestro.commands.plan.PlanStore') as mock_planstore_class:
                mock_store_instance = Mock()
                # Mock the load method to return multiple plans
                plan1 = Plan(title="Plan 1", items=[PlanItem(text="Item 1")])
                plan2 = Plan(title="Plan 2", items=[PlanItem(text="Item 2")])
                mock_store_instance.load.return_value = [plan1, plan2]
                mock_planstore_class.return_value = mock_store_instance

                # Should raise SystemExit due to multiple plans
                with patch('sys.stdout'), \
                     pytest.raises(SystemExit):
                    handle_plan_discuss(None, temp_path, verbose=True)

    finally:
        # Clean up temp file
        Path(temp_path).unlink()