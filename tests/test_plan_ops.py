"""
Tests for the Plan Operations pipeline.
"""
import json
import tempfile
from pathlib import Path
import pytest

from maestro.plan_ops.schemas import validate_plan_ops_result
from maestro.plan_ops.operations import Selector, CreatePlan, DeletePlan, AddPlanItem, RemovePlanItem, Commentary
from maestro.plan_ops.decoder import decode_plan_ops_json, DecodeError
from maestro.plan_ops.translator import actions_to_ops, create_selector
from maestro.plan_ops.executor import PlanOpsExecutor, PreviewResult
from maestro.plans import PlanStore, Plan, PlanItem


def test_validate_plan_ops_result_valid():
    """Test that valid PlanOpsResult passes validation."""
    valid_data = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": []
    }

    result = validate_plan_ops_result(valid_data)
    assert result["kind"] == "plan_ops"
    assert result["version"] == 1
    assert result["scope"] == "plan"


def test_validate_plan_ops_result_invalid():
    """Test that invalid PlanOpsResult raises ValidationError."""
    invalid_data = {
        "kind": "wrong_kind",
        "version": 1,
        "scope": "plan",
        "actions": []
    }

    with pytest.raises(Exception):
        validate_plan_ops_result(invalid_data)


def test_validate_plan_ops_result_actions_valid():
    """Test that valid PlanOpsResult with actions passes validation."""
    valid_data = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "plan_create",
                "title": "Test Plan"
            }
        ]
    }

    result = validate_plan_ops_result(valid_data)
    assert result["kind"] == "plan_ops"
    assert result["scope"] == "plan"
    assert len(result["actions"]) == 1


def test_validate_plan_ops_result_actions_invalid():
    """Test that invalid PlanOpsResult raises ValidationError."""
    invalid_data = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "wrong_scope",
        "actions": []
    }

    with pytest.raises(Exception):
        validate_plan_ops_result(invalid_data)


def test_create_selector_valid():
    """Test creating valid selectors."""
    # Test with title
    selector1 = create_selector({"title": "Test Plan"})
    assert selector1.title == "Test Plan"
    assert selector1.index is None
    
    # Test with index
    selector2 = create_selector({"index": 1})
    assert selector2.title is None
    assert selector2.index == 1


def test_create_selector_invalid():
    """Test creating invalid selectors raises DecodeError."""
    # Test with both title and index
    with pytest.raises(DecodeError):
        create_selector({"title": "Test Plan", "index": 1})
    
    # Test with neither title nor index
    with pytest.raises(DecodeError):
        create_selector({})


def test_decode_plan_ops_json_valid():
    """Test decoding valid PlanOpsResult JSON."""
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "plan_create",
                "title": "Test Plan"
            }
        ]
    }

    result = decode_plan_ops_json(json.dumps(plan_ops_result))
    assert result["kind"] == "plan_ops"
    assert result["scope"] == "plan"
    assert len(result["actions"]) == 1
    assert result["actions"][0]["action"] == "plan_create"


def test_decode_plan_ops_json_invalid():
    """Test decoding invalid PlanOpsResult JSON raises DecodeError."""
    invalid_json = '{"kind": "wrong", "version": 1, "scope": "plan", "actions": []}'

    with pytest.raises(DecodeError, match="PlanOpsResult JSON invalid"):
        decode_plan_ops_json(invalid_json)


def test_decode_plan_ops_json_missing_fields():
    """Test decoding when required fields are missing."""
    invalid_payload = {
        "kind": "plan_ops",
        "version": 1
        # Missing 'scope' and 'actions' fields
    }

    with pytest.raises(DecodeError, match="PlanOpsResult JSON invalid"):
        decode_plan_ops_json(json.dumps(invalid_payload))


def test_decode_plan_ops_json_invalid_actions():
    """Test decoding PlanOpsResult with invalid actions raises DecodeError."""
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "invalid_action_type",
                "title": "Test"
            }
        ]
    }

    with pytest.raises(DecodeError, match="PlanOpsResult JSON invalid"):
        decode_plan_ops_json(json.dumps(plan_ops_result))


def test_actions_to_ops_valid():
    """Test translating valid actions to operations."""
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "plan_create",
                "title": "New Plan"
            },
            {
                "action": "plan_delete",
                "selector": {"title": "Old Plan"}
            },
            {
                "action": "plan_item_add",
                "selector": {"index": 1},
                "text": "New item"
            },
            {
                "action": "plan_item_remove",
                "selector": {"title": "Test Plan"},
                "item_index": 2
            },
            {
                "action": "commentary",
                "text": "This is a comment"
            }
        ]
    }

    ops = actions_to_ops(plan_ops_result)
    assert len(ops) == 5
    assert isinstance(ops[0], CreatePlan)
    assert isinstance(ops[1], DeletePlan)
    assert isinstance(ops[2], AddPlanItem)
    assert isinstance(ops[3], RemovePlanItem)
    assert isinstance(ops[4], Commentary)


def test_actions_to_ops_invalid_scope():
    """Test that invalid scope raises DecodeError."""
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "invalid",
        "actions": []
    }

    with pytest.raises(DecodeError, match="Invalid scope"):
        actions_to_ops(plan_ops_result)


def test_actions_to_ops_unknown_action():
    """Test that unknown action type raises DecodeError."""
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "unknown_action",
                "title": "Test"
            }
        ]
    }

    with pytest.raises(DecodeError, match="Unknown action type"):
        actions_to_ops(plan_ops_result)


def test_actions_to_ops_missing_required_fields():
    """Test that missing required fields raise DecodeError."""
    # Missing title for plan_create
    plan_ops_result = {
        "kind": "plan_ops",
        "version": 1,
        "scope": "plan",
        "actions": [
            {
                "action": "plan_create"
            }
        ]
    }

    with pytest.raises(DecodeError, match="plan_create action requires 'title'"):
        actions_to_ops(plan_ops_result)


def test_preview_ops():
    """Test preview functionality of the executor."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name
    
    try:
        store = PlanStore(temp_path)
        executor = PlanOpsExecutor(store)
        
        # Create operations
        ops = [
            AddPlanItem(
                selector=Selector(title="Test Plan"),
                text="New item from ops"
            )
        ]
        
        preview_result = executor.preview_ops(ops)
        
        assert isinstance(preview_result, PreviewResult)
        assert len(preview_result.changes) == 1
        assert "Add item to plan" in preview_result.changes[0]
    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_apply_ops_dry_run():
    """Test apply functionality with dry_run=True."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name
    
    try:
        store = PlanStore(temp_path)
        executor = PlanOpsExecutor(store)
        
        # Create operations
        ops = [
            AddPlanItem(
                selector=Selector(title="Test Plan"),
                text="New item from ops"
            )
        ]
        
        preview_result = executor.apply_ops(ops, dry_run=True)
        
        assert isinstance(preview_result, PreviewResult)
        # The file should not have been changed since it was a dry run
        plans = store.load()
        assert len(plans[0].items) == 1  # Only original item
    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_apply_ops():
    """Test apply functionality."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name
    
    try:
        store = PlanStore(temp_path)
        executor = PlanOpsExecutor(store)
        
        # Create operations
        ops = [
            AddPlanItem(
                selector=Selector(title="Test Plan"),
                text="New item from ops"
            )
        ]
        
        # Apply the operations
        result = executor.apply_ops(ops, dry_run=False)
        
        # Check that the file was actually changed
        plans = store.load()
        assert len(plans[0].items) == 2  # Original + new item
        assert plans[0].items[1].text == "New item from ops"
    finally:
        # Clean up temp file
        Path(temp_path).unlink()


def test_executor_with_all_operation_types():
    """Test executor with all operation types."""
    # Create a temporary plan store
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("# Plans\n\n## Test Plan\n- Existing item\n")
        temp_path = f.name
    
    try:
        store = PlanStore(temp_path)
        executor = PlanOpsExecutor(store)
        
        # Create operations of all types
        ops = [
            CreatePlan(title="New Plan"),
            AddPlanItem(
                selector=Selector(title="Test Plan"),
                text="Added item"
            ),
            RemovePlanItem(
                selector=Selector(title="Test Plan"),
                item_index=1
            )
        ]
        
        # Preview the operations
        preview_result = executor.preview_ops(ops)
        assert len(preview_result.changes) == 3
        
        # Apply the operations
        result = executor.apply_ops(ops, dry_run=False)
        
        # Check that operations were applied
        plans = store.load()
        assert len(plans) == 2  # Original + new plan
        test_plan = next((p for p in plans if p.title == "Test Plan"), None)
        assert test_plan is not None
        # Should have only the "Added item" since original was removed
        assert len(test_plan.items) == 1
        assert test_plan.items[0].text == "Added item"
        
        new_plan = next((p for p in plans if p.title == "New Plan"), None)
        assert new_plan is not None
        assert len(new_plan.items) == 0
    finally:
        # Clean up temp file
        Path(temp_path).unlink()