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

            # Mock the run_completion method to return our valid response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = json.dumps(valid_response)

            mock_manager_instance.run_completion.return_value = mock_response

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

            # Configure side_effect to return invalid response first, then valid
            mock_response_invalid = Mock()
            mock_response_invalid.choices = [Mock()]
            mock_response_invalid.choices[0].message = Mock()
            mock_response_invalid.choices[0].message.content = invalid_response

            mock_response_valid = Mock()
            mock_response_valid.choices = [Mock()]
            mock_response_valid.choices[0].message = Mock()
            mock_response_valid.choices[0].message.content = json.dumps(valid_response)

            mock_manager_instance.run_completion.side_effect = [mock_response_invalid, mock_response_valid]

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

                # Verify that run_completion was called twice (once for initial, once for retry)
                assert mock_manager_instance.run_completion.call_count == 2

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

            # Configure side_effect to return invalid response first, then valid
            mock_response_invalid = Mock()
            mock_response_invalid.choices = [Mock()]
            mock_response_invalid.choices[0].message = Mock()
            mock_response_invalid.choices[0].message.content = json.dumps(invalid_schema_response)

            mock_response_valid = Mock()
            mock_response_valid.choices = [Mock()]
            mock_response_valid.choices[0].message = Mock()
            mock_response_valid.choices[0].message.content = json.dumps(valid_response)

            mock_manager_instance.run_completion.side_effect = [mock_response_invalid, mock_response_valid]

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

                # Verify that run_completion was called twice (once for initial, once for retry)
                assert mock_manager_instance.run_completion.call_count == 2

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
            
            # Configure to always return invalid response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = invalid_response
            
            mock_manager_instance.run_completion.return_value = mock_response

            # Should raise SystemExit due to max retries
            with patch('builtins.input', return_value='y'), \
                 patch('sys.stdout'), \
                 pytest.raises(SystemExit):
                handle_plan_discuss("Test Plan", verbose=True)

            # Verify that run_completion was called 3 times (initial + 2 retries)
            assert mock_manager_instance.run_completion.call_count == 3

    finally:
        # Clean up temp file
        Path(temp_path).unlink()


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
            
            # Mock the run_completion method to return our valid response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = json.dumps(valid_response)
            
            mock_manager_instance.run_completion.return_value = mock_response

            # Capture input and output - user declines
            with patch('builtins.input', return_value='n'), \
                 patch('sys.stdout'):
                handle_plan_discuss("Test Plan", verbose=True)

            # Check that the plan was NOT updated
            store = PlanStore(temp_path)
            plans = store.load()
            test_plan = next((p for p in plans if p.title == "Test Plan"), None)
            assert test_plan is not None
            assert len(test_plan.items) == 1  # Should still have only the original item

    finally:
        # Clean up temp file
        Path(temp_path).unlink()