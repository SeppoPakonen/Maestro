"""
Tests for the Truth Gate fixtures and validation.
"""
import json
import pytest
from pathlib import Path

from maestro.plan_ops.schemas import validate_plan_ops_result
from maestro.project_ops.schemas import validate_project_ops_result
from maestro.plan_ops.decoder import decode_plan_ops_json, DecodeError
from maestro.project_ops.decoder import decode_project_ops_json, DecodeError as ProjectDecodeError


def test_plan_ops_valid_fixture():
    """Test that the valid plan ops fixture passes validation."""
    fixture_path = Path("tests/fixtures/plan_ops_valid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"
    
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    # This should not raise an exception
    validated_data = validate_plan_ops_result(data)
    assert validated_data["kind"] == "plan_ops"
    assert validated_data["version"] == 1
    assert validated_data["scope"] == "plan"
    assert len(validated_data["actions"]) > 0


def test_plan_ops_invalid_fixture():
    """Test that the invalid plan ops fixture fails validation."""
    fixture_path = Path("tests/fixtures/plan_ops_invalid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"

    with open(fixture_path, 'r') as f:
        data = json.load(f)

    # This should raise a ValueError due to invalid kind
    with pytest.raises(ValueError, match="Invalid kind"):
        validate_plan_ops_result(data)


def test_project_ops_valid_fixture():
    """Test that the valid project ops fixture passes validation."""
    fixture_path = Path("tests/fixtures/project_ops_valid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"
    
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    # This should not raise an exception
    validated_data = validate_project_ops_result(data)
    assert validated_data["kind"] == "project_ops"
    assert validated_data["version"] == 1
    assert validated_data["scope"] == "project"
    assert len(validated_data["actions"]) > 0


def test_project_ops_invalid_fixture():
    """Test that the invalid project ops fixture fails validation."""
    fixture_path = Path("tests/fixtures/project_ops_invalid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"

    with open(fixture_path, 'r') as f:
        data = json.load(f)

    # This should raise a ValueError due to invalid kind
    with pytest.raises(ValueError, match="Invalid kind"):
        validate_project_ops_result(data)


def test_plan_ops_decoder_with_valid_fixture():
    """Test that the plan ops decoder can handle the valid fixture."""
    fixture_path = Path("tests/fixtures/plan_ops_valid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"
    
    with open(fixture_path, 'r') as f:
        content = f.read()
    
    # This should not raise an exception
    result = decode_plan_ops_json(content)
    assert result["kind"] == "plan_ops"
    assert result["scope"] == "plan"


def test_project_ops_decoder_with_valid_fixture():
    """Test that the project ops decoder can handle the valid fixture."""
    fixture_path = Path("tests/fixtures/project_ops_valid_1.json")
    assert fixture_path.exists(), f"Fixture file does not exist: {fixture_path}"
    
    with open(fixture_path, 'r') as f:
        content = f.read()
    
    # This should not raise an exception
    result = decode_project_ops_json(content)
    assert result["kind"] == "project_ops"
    assert result["scope"] == "project"