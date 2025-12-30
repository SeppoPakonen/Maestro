"""Tests for ops doctor command."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from maestro.ops.doctor import (
    check_repo_lock,
    check_git_status,
    check_repo_truth,
    check_repo_conf,
    check_blocker_issues,
    run_doctor,
    format_text_output,
)
from maestro.repo_lock import RepoLock


def test_check_repo_lock_no_lock(tmp_path):
    """Test repo lock check when no lock exists."""
    finding = check_repo_lock(tmp_path)
    assert finding.id == "REPO_LOCK"
    assert finding.severity == "ok"
    assert "No active" in finding.message


def test_check_repo_lock_with_stale_lock(tmp_path):
    """Test repo lock check with stale lock (dead PID)."""
    lock = RepoLock(lock_dir=tmp_path / "docs" / "maestro" / "locks")
    lock.lock_dir.mkdir(parents=True, exist_ok=True)

    # Write a lock with a dead PID
    lock_data = {
        "session_id": "test-session",
        "pid": 999999,  # Unlikely to exist
        "timestamp": "2025-01-01T00:00:00",
    }
    with open(lock.lock_file, 'w', encoding='utf-8') as f:
        json.dump(lock_data, f)

    finding = check_repo_lock(tmp_path)
    assert finding.id == "STALE_LOCK"
    assert finding.severity == "warning"
    assert "Stale" in finding.message


def test_check_git_status():
    """Test git status check."""
    findings = check_git_status()
    # Should return at least one finding
    assert len(findings) >= 1

    # Check that we get expected finding IDs
    finding_ids = {f.id for f in findings}
    assert "DIRTY_TREE" in finding_ids or "GIT_REPO" in finding_ids


def test_check_repo_truth_missing(tmp_path):
    """Test repo truth check when model doesn't exist."""
    finding = check_repo_truth(tmp_path)
    assert finding.id == "REPO_TRUTH_EXISTS"
    assert finding.severity == "warning"
    assert "not found" in finding.message
    assert "maestro repo resolve" in finding.recommended_commands


def test_check_repo_truth_exists(tmp_path):
    """Test repo truth check when model exists."""
    model_path = tmp_path / "docs" / "maestro" / "repo" / "model.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Write valid model
    model_data = {"packages": [], "targets": []}
    with open(model_path, 'w', encoding='utf-8') as f:
        json.dump(model_data, f)

    finding = check_repo_truth(tmp_path)
    assert finding.id == "REPO_TRUTH_EXISTS"
    assert finding.severity == "ok"
    assert "valid" in finding.message


def test_check_repo_truth_corrupted(tmp_path):
    """Test repo truth check when model is corrupted."""
    model_path = tmp_path / "docs" / "maestro" / "repo" / "model.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Write invalid JSON
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write("{invalid json")

    finding = check_repo_truth(tmp_path)
    assert finding.id == "REPO_TRUTH_EXISTS"
    assert finding.severity == "error"
    assert "corrupted" in finding.message


def test_check_repo_conf_missing(tmp_path):
    """Test repo conf check when conf doesn't exist."""
    finding = check_repo_conf(tmp_path)
    assert finding.id == "REPO_CONF_EXISTS"
    assert finding.severity == "warning"
    assert "not found" in finding.message


def test_check_repo_conf_exists(tmp_path):
    """Test repo conf check when conf exists with targets."""
    conf_path = tmp_path / "docs" / "maestro" / "repo" / "conf.json"
    conf_path.parent.mkdir(parents=True, exist_ok=True)

    # Write valid conf with targets
    conf_data = {"targets": ["main", "test"]}
    with open(conf_path, 'w', encoding='utf-8') as f:
        json.dump(conf_data, f)

    finding = check_repo_conf(tmp_path)
    assert finding.id == "REPO_CONF_EXISTS"
    assert finding.severity == "ok"
    assert "2 target(s)" in finding.message


def test_check_repo_conf_no_targets(tmp_path):
    """Test repo conf check when conf has no targets."""
    conf_path = tmp_path / "docs" / "maestro" / "repo" / "conf.json"
    conf_path.parent.mkdir(parents=True, exist_ok=True)

    # Write conf with no targets
    conf_data = {"targets": []}
    with open(conf_path, 'w', encoding='utf-8') as f:
        json.dump(conf_data, f)

    finding = check_repo_conf(tmp_path)
    assert finding.id == "REPO_CONF_EXISTS"
    assert finding.severity == "warning"
    assert "no targets" in finding.message


def test_check_blocker_issues(tmp_path):
    """Test blocker issues check."""
    finding = check_blocker_issues(tmp_path)
    assert finding.id == "BLOCKED_BY_ISSUES"
    # Should be ok if no issues module or no blockers
    assert finding.severity in ("ok", "blocker")


def test_run_doctor_clean(tmp_path):
    """Test running doctor with a clean environment."""
    # Set up minimal valid environment
    model_path = tmp_path / "docs" / "maestro" / "repo" / "model.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, 'w', encoding='utf-8') as f:
        json.dump({"packages": []}, f)

    conf_path = tmp_path / "docs" / "maestro" / "repo" / "conf.json"
    with open(conf_path, 'w', encoding='utf-8') as f:
        json.dump({"targets": ["main"]}, f)

    result = run_doctor(docs_root=tmp_path)

    # Should have findings
    assert len(result.findings) > 0

    # Exit code should be 0 or 2 depending on git status
    assert result.exit_code in (0, 2)


def test_run_doctor_strict_mode(tmp_path):
    """Test running doctor in strict mode."""
    result = run_doctor(strict=True, docs_root=tmp_path)

    # If there are any warnings, exit code should be 2 in strict mode
    has_warnings = any(f.severity == "warning" for f in result.findings)
    if has_warnings:
        assert result.exit_code == 2


def test_run_doctor_ignore_gates(tmp_path):
    """Test running doctor with --ignore-gates."""
    result = run_doctor(ignore_gates=True, docs_root=tmp_path)

    # Blockers should be downgraded to warnings
    assert not any(f.severity == "blocker" for f in result.findings)


def test_format_text_output(tmp_path):
    """Test text output formatting."""
    result = run_doctor(docs_root=tmp_path)
    output = format_text_output(result)

    # Should contain key sections
    assert "Maestro Ops Doctor" in output
    assert "Summary:" in output
    assert "Exit code:" in output


def test_doctor_json_output(tmp_path):
    """Test JSON output format."""
    result = run_doctor(docs_root=tmp_path)
    output_dict = result.to_dict()

    # Should have required keys
    assert "findings" in output_dict
    assert "exit_code" in output_dict
    assert "summary" in output_dict

    # Summary should have counts
    summary = output_dict["summary"]
    assert "total" in summary
    assert "ok" in summary
    assert "warnings" in summary
    assert "errors" in summary
    assert "blockers" in summary
