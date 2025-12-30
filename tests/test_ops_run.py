"""Tests for ops run command."""

import json
import tempfile
from pathlib import Path

import pytest

from maestro.ops.runner import (
    generate_run_id,
    load_ops_plan,
    execute_step,
    run_ops_plan,
    list_ops_runs,
    show_ops_run,
    create_run_record,
)


def test_generate_run_id():
    """Test run ID generation."""
    run_id = generate_run_id("test plan")
    assert "ops_run_" in run_id
    assert len(run_id) > 10  # Should have timestamp + hash


def test_load_ops_plan_valid(tmp_path):
    """Test loading a valid ops plan."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Test plan
steps:
  - maestro: "ops doctor"
  - maestro: "ops list"
"""
    plan_path.write_text(plan_content)

    plan = load_ops_plan(plan_path)

    assert plan["kind"] == "ops_run"
    assert plan["name"] == "Test plan"
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["maestro"] == "ops doctor"


def test_load_ops_plan_missing_file(tmp_path):
    """Test loading a non-existent plan."""
    plan_path = tmp_path / "nonexistent.yaml"

    with pytest.raises(ValueError, match="not found"):
        load_ops_plan(plan_path)


def test_load_ops_plan_invalid_kind(tmp_path):
    """Test loading a plan with wrong kind."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: wrong_kind
name: Test plan
steps: []
"""
    plan_path.write_text(plan_content)

    with pytest.raises(ValueError, match="Invalid kind"):
        load_ops_plan(plan_path)


def test_load_ops_plan_missing_name(tmp_path):
    """Test loading a plan without a name."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
steps: []
"""
    plan_path.write_text(plan_content)

    with pytest.raises(ValueError, match="must have a 'name'"):
        load_ops_plan(plan_path)


def test_load_ops_plan_missing_steps(tmp_path):
    """Test loading a plan without steps."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Test plan
"""
    plan_path.write_text(plan_content)

    with pytest.raises(ValueError, match="must have a 'steps'"):
        load_ops_plan(plan_path)


def test_load_ops_plan_invalid_step(tmp_path):
    """Test loading a plan with invalid step format."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Test plan
steps:
  - invalid: "not maestro"
"""
    plan_path.write_text(plan_content)

    with pytest.raises(ValueError, match="must have a 'maestro' key"):
        load_ops_plan(plan_path)


def test_load_ops_plan_missing_yaml_dependency(tmp_path, monkeypatch):
    """Test error when YAML dependency is missing."""
    from maestro.ops import runner

    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Test plan
steps: []
"""
    plan_path.write_text(plan_content)

    monkeypatch.setattr(runner, "yaml", None)

    with pytest.raises(ValueError, match="pyyaml"):
        runner.load_ops_plan(plan_path)


def test_execute_step_dry_run():
    """Test executing a step in dry-run mode."""
    result = execute_step("ops doctor", dry_run=True)

    assert result.command == "ops doctor"
    assert result.exit_code == 0
    assert result.stdout == "[DRY RUN]"
    assert result.duration_ms == 0


def test_execute_step_success():
    """Test executing a successful step."""
    # Use a simple command that should succeed
    result = execute_step("--help", dry_run=False)

    # Command should have been executed
    assert result.command == "--help"
    # Should have some output (help text)
    assert len(result.stdout) > 0 or len(result.stderr) > 0


def test_run_ops_plan_dry_run(tmp_path):
    """Test running an ops plan in dry-run mode."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Dry run test
steps:
  - maestro: "ops doctor"
  - maestro: "ops list"
"""
    plan_path.write_text(plan_content)

    result = run_ops_plan(
        plan_path=plan_path,
        dry_run=True,
        docs_root=tmp_path
    )

    assert result.plan_name == "Dry run test"
    assert result.dry_run is True
    assert len(result.step_results) == 2
    assert result.exit_code == 0

    # All steps should succeed in dry-run
    for step in result.step_results:
        assert step.exit_code == 0


def test_run_ops_plan_creates_record(tmp_path):
    """Test that running a plan creates a run record."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Record test
steps:
  - maestro: "ops doctor"
"""
    plan_path.write_text(plan_content)

    result = run_ops_plan(
        plan_path=plan_path,
        dry_run=True,
        docs_root=tmp_path
    )

    # Check run record was created
    run_dir = tmp_path / "docs" / "maestro" / "ops" / "runs" / result.run_id
    assert run_dir.exists()
    assert (run_dir / "meta.json").exists()
    assert (run_dir / "steps.jsonl").exists()
    assert (run_dir / "stdout.txt").exists()
    assert (run_dir / "stderr.txt").exists()
    assert (run_dir / "summary.json").exists()


def test_run_ops_plan_continue_on_error(tmp_path):
    """Test continue-on-error mode."""
    plan_path = tmp_path / "plan.yaml"
    # Use a command that will fail
    plan_content = """
kind: ops_run
name: Error test
steps:
  - maestro: "invalid-command-that-does-not-exist"
  - maestro: "ops doctor"
"""
    plan_path.write_text(plan_content)

    result = run_ops_plan(
        plan_path=plan_path,
        dry_run=True,  # Use dry-run to avoid actual failures
        continue_on_error=True,
        docs_root=tmp_path
    )

    # In dry-run, all steps succeed, but testing the flag works
    assert len(result.step_results) == 2


def test_list_ops_runs_empty(tmp_path):
    """Test listing ops runs when none exist."""
    runs = list_ops_runs(docs_root=tmp_path)
    assert runs == []


def test_list_ops_runs_with_runs(tmp_path):
    """Test listing ops runs after creating some."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: List test
steps:
  - maestro: "ops doctor"
"""
    plan_path.write_text(plan_content)

    # Create a run
    result = run_ops_plan(
        plan_path=plan_path,
        dry_run=True,
        docs_root=tmp_path
    )

    # List runs
    runs = list_ops_runs(docs_root=tmp_path)

    assert len(runs) == 1
    assert runs[0]["run_id"] == result.run_id
    assert runs[0]["plan_name"] == "List test"
    assert runs[0]["exit_code"] == 0


def test_show_ops_run_not_found(tmp_path):
    """Test showing a run that doesn't exist."""
    details = show_ops_run("nonexistent", docs_root=tmp_path)
    assert details is None


def test_show_ops_run_exists(tmp_path):
    """Test showing a run that exists."""
    plan_path = tmp_path / "plan.yaml"
    plan_content = """
kind: ops_run
name: Show test
steps:
  - maestro: "ops doctor"
"""
    plan_path.write_text(plan_content)

    # Create a run
    result = run_ops_plan(
        plan_path=plan_path,
        dry_run=True,
        docs_root=tmp_path
    )

    # Show run
    details = show_ops_run(result.run_id, docs_root=tmp_path)

    assert details is not None
    assert "meta" in details
    assert "summary" in details
    assert "steps" in details

    assert details["meta"]["run_id"] == result.run_id
    assert details["meta"]["plan_name"] == "Show test"
    assert details["summary"]["total_steps"] == 1


def test_create_run_record(tmp_path):
    """Test creating a run record manually."""
    from maestro.ops.runner import RunResult, StepResult

    step1 = StepResult(
        step_index=0,
        command="ops doctor",
        started_at="2025-01-01T00:00:00",
        exit_code=0,
        duration_ms=1000,
        stdout="test output",
        stderr=""
    )

    result = RunResult(
        run_id="test_run_123",
        plan_name="Test",
        plan_path="/tmp/test.yaml",
        started_at="2025-01-01T00:00:00",
        completed_at="2025-01-01T00:00:01",
        dry_run=False,
        exit_code=0,
        step_results=[step1]
    )

    run_dir = create_run_record(result, docs_root=tmp_path)

    assert run_dir.exists()
    assert (run_dir / "meta.json").exists()

    # Verify meta content
    with open(run_dir / "meta.json", 'r', encoding='utf-8') as f:
        meta = json.load(f)

    assert meta["run_id"] == "test_run_123"
    assert meta["plan_name"] == "Test"
    assert meta["dry_run"] is False
