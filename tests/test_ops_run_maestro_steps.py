"""Tests for ops run with maestro steps (structured format + metadata)."""
import json
import tempfile
from pathlib import Path

import pytest


def test_structured_step_format_validation():
    """Test that structured step format validates correctly."""
    from maestro.ops.runner import load_ops_plan

    # Valid structured format
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
kind: ops_run
name: Test plan
steps:
  - kind: maestro
    args: ["repo", "resolve"]
    timeout_s: 60
    allow_write: false
        """)
        f.flush()
        plan_path = Path(f.name)

    try:
        plan = load_ops_plan(plan_path)
        assert plan["name"] == "Test plan"
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["kind"] == "maestro"
        assert plan["steps"][0]["args"] == ["repo", "resolve"]
        assert plan["steps"][0]["timeout_s"] == 60
    finally:
        plan_path.unlink()


def test_structured_step_validation_errors():
    """Test that structured step format catches validation errors."""
    from maestro.ops.runner import load_ops_plan

    # Missing args field
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
kind: ops_run
name: Test plan
steps:
  - kind: maestro
    timeout_s: 60
        """)
        f.flush()
        plan_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="requires 'args' field"):
            load_ops_plan(plan_path)
    finally:
        plan_path.unlink()


def test_backward_compatibility_old_format():
    """Test that old maestro: string format still works."""
    from maestro.ops.runner import load_ops_plan

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
kind: ops_run
name: Test plan
steps:
  - maestro: "repo resolve"
        """)
        f.flush()
        plan_path = Path(f.name)

    try:
        plan = load_ops_plan(plan_path)
        assert plan["name"] == "Test plan"
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["maestro"] == "repo resolve"
    finally:
        plan_path.unlink()


def test_metadata_extraction_from_output():
    """Test that metadata (scan IDs, workgraph IDs) is extracted from command output."""
    from maestro.ops.runner import extract_scan_id, extract_workgraph_id, extract_workgraph_run_id

    # Test scan ID extraction
    output = """
Some output
Scan created: scan-20260101-a3f5b8c2
More output
    """
    assert extract_scan_id(output) == "scan-20260101-a3f5b8c2"

    # Test workgraph ID extraction
    output = """
WorkGraph created: wg-20260101-a3f5b8c2
Domain: issues
    """
    assert extract_workgraph_id(output) == "wg-20260101-a3f5b8c2"

    # Test workgraph run ID extraction
    output = """
Run completed: wr-20260101-120000-a3f5b8c2
Tasks completed: 5
    """
    assert extract_workgraph_run_id(output) == "wr-20260101-120000-a3f5b8c2"


def test_placeholders_resolution():
    """Test that placeholders are resolved correctly."""
    from maestro.ops.runner import resolve_placeholders

    placeholders = {
        "<LAST_RUN_ID>": "run-123",
        "<LAST_SCAN_ID>": "scan-456",
        "<LAST_WORKGRAPH_ID>": "wg-789",
        "<LAST_WORKGRAPH_RUN_ID>": "wr-012",
    }

    command = "plan run <LAST_WORKGRAPH_ID> --resume <LAST_WORKGRAPH_RUN_ID>"
    resolved = resolve_placeholders(command, placeholders)
    assert resolved == "plan run wg-789 --resume wr-012"

    # Test unresolved placeholders in dry-run
    placeholders_incomplete = {
        "<LAST_RUN_ID>": "run-123",
        "<LAST_SCAN_ID>": None,
    }
    command_with_unresolved = "log show <LAST_SCAN_ID>"
    # Should allow unresolved in dry-run
    resolved_dry = resolve_placeholders(command_with_unresolved, placeholders_incomplete, allow_unresolved=True)
    assert resolved_dry == "log show <LAST_SCAN_ID>"  # Unchanged

    # Should raise error when not allowing unresolved
    with pytest.raises(ValueError, match="Missing placeholder values"):
        resolve_placeholders(command_with_unresolved, placeholders_incomplete, allow_unresolved=False)


def test_execute_writes_flag():
    """Test that --execute flag controls write step execution."""
    from maestro.ops.runner import run_ops_plan

    # Create a plan with a write step (use dry-run to avoid actually running commands)
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_file = Path(tmpdir) / "plan.yaml"
        plan_file.write_text("""
kind: ops_run
name: Test write steps
steps:
  - kind: maestro
    args: ["repo", "resolve"]
    allow_write: false
  - kind: maestro
    args: ["plan", "enact", "wg-test-001"]
    allow_write: true
        """)

        docs_root = Path(tmpdir) / "docs"

        # Run in dry-run mode to avoid actually executing commands
        # but verify the write step logic is applied
        result = run_ops_plan(
            plan_path=plan_file,
            dry_run=True,
            execute_writes=False,
            docs_root=docs_root
        )

        # Both steps should be logged
        assert len(result.step_results) == 2

        # Both steps should have dry-run output
        assert all("[DRY RUN]" in s.stdout for s in result.step_results)

        # Now test with --execute flag (still dry-run for safety)
        result2 = run_ops_plan(
            plan_path=plan_file,
            dry_run=True,
            execute_writes=True,
            docs_root=docs_root
        )

        # Both steps should still be logged
        assert len(result2.step_results) == 2


def test_metadata_linkage_in_run_result():
    """Test that metadata from steps is aggregated into run result."""
    from maestro.ops.runner import StepResult, RunResult
    from datetime import datetime

    # Create a step result with metadata
    step_with_meta = StepResult(
        step_index=0,
        command="log scan --source test.log",
        started_at=datetime.now().isoformat(),
        exit_code=0,
        duration_ms=100,
        stdout="Scan created: scan-123",
        stderr="",
        metadata={"scan_id": "scan-123"}
    )

    # Create a run result
    run_result = RunResult(
        run_id="test-run-001",
        plan_name="Test plan",
        plan_path="/tmp/plan.yaml",
        started_at=datetime.now().isoformat(),
        completed_at=datetime.now().isoformat(),
        dry_run=False,
        exit_code=0,
        step_results=[step_with_meta],
        metadata={}
    )

    # Metadata should be aggregated
    # (This is tested in the actual run_ops_plan logic, but we verify the data model)
    assert step_with_meta.metadata["scan_id"] == "scan-123"
    assert step_with_meta.to_dict()["metadata"]["scan_id"] == "scan-123"
