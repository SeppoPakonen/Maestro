"""
Test work gates and blocker issue enforcement.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from maestro.commands.work import check_work_gates
from maestro.issues.json_store import (
    create_or_update_issue,
    get_issues_dir,
)


class TestWorkGates:
    """Test work gate enforcement."""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_no_issues_allows_work(self, temp_repo):
        """Test that work proceeds when no issues exist."""
        # No issues directory exists
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is True, "Work should proceed when no issues exist"

    def test_ignore_gates_bypasses_check(self, temp_repo):
        """Test that --ignore-gates bypasses all gate checks."""
        # Create a blocker issue
        create_or_update_issue(
            fingerprint="test-fp-001",
            severity="blocker",
            message="Build failed due to missing dependency",
            scan_id="test-scan-001",
            timestamp="2025-01-28T12:00:00",
            tool="gcc",
            file="main.cpp",
            line=42,
            kind="error",
            repo_root=temp_repo,
        )

        # With ignore_gates=True, should allow work
        result = check_work_gates(ignore_gates=True, repo_root=temp_repo)
        assert result is True, "Work should proceed when ignore_gates=True"

    def test_blocker_issue_blocks_work(self, temp_repo, capsys):
        """Test that blocker issue blocks work when no linked task."""
        # Create a blocker issue
        create_or_update_issue(
            fingerprint="test-fp-002",
            severity="blocker",
            message="Undefined reference to 'initialize()'",
            scan_id="test-scan-002",
            timestamp="2025-01-28T12:00:00",
            tool="ld",
            file="main.cpp",
            kind="error",
            repo_root=temp_repo,
        )

        # Should block work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is False, "Work should be blocked by blocker issue"

        # Check that gate message was printed
        captured = capsys.readouterr()
        assert "GATE: BLOCKED_BY_ISSUES" in captured.out
        assert "ISSUE-001" in captured.out
        assert "Undefined reference to 'initialize()'" in captured.out
        assert "--ignore-gates" in captured.out

    def test_blocker_with_linked_task_allows_work(self, temp_repo):
        """Test that blocker with linked in_progress task allows work."""
        # Create a blocker issue
        issue_id, _ = create_or_update_issue(
            fingerprint="test-fp-003",
            severity="blocker",
            message="Segfault in core module",
            scan_id="test-scan-003",
            timestamp="2025-01-28T12:00:00",
            tool="runtime",
            kind="crash",
            repo_root=temp_repo,
        )

        # Link issue to a task
        from maestro.issues.json_store import link_issue_to_task

        link_issue_to_task(issue_id, "TASK-123", repo_root=temp_repo)

        # Create a mock phase with the linked task in in_progress status
        phases_dir = Path(temp_repo) / "docs" / "phases"
        phases_dir.mkdir(parents=True, exist_ok=True)

        phase_content = """# Phase: Test Phase

## Metadata
- phase_id: test-phase
- track_id: test-track
- status: in_progress

## Tasks

### Task 123
- task_id: TASK-123
- status: in_progress
- description: Fix the segfault issue
"""
        phase_file = phases_dir / "test_phase.md"
        phase_file.write_text(phase_content)

        # With linked in_progress task, should allow work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is True, "Work should proceed when blocker has linked in_progress task"

    def test_blocker_with_linked_todo_task_blocks_work(self, temp_repo, capsys):
        """Test that blocker with linked todo task still blocks work."""
        # Create a blocker issue
        issue_id, _ = create_or_update_issue(
            fingerprint="test-fp-004",
            severity="blocker",
            message="Memory leak in parser",
            scan_id="test-scan-004",
            timestamp="2025-01-28T12:00:00",
            tool="valgrind",
            kind="error",
            repo_root=temp_repo,
        )

        # Link issue to a task
        from maestro.issues.json_store import link_issue_to_task

        link_issue_to_task(issue_id, "TASK-124", repo_root=temp_repo)

        # Create a mock phase with the linked task in todo status
        phases_dir = Path(temp_repo) / "docs" / "phases"
        phases_dir.mkdir(parents=True, exist_ok=True)

        phase_content = """# Phase: Test Phase

## Metadata
- phase_id: test-phase
- track_id: test-track
- status: todo

## Tasks

### Task 124
- task_id: TASK-124
- status: todo
- description: Fix the memory leak
"""
        phase_file = phases_dir / "test_phase.md"
        phase_file.write_text(phase_content)

        # With linked todo task, should still block
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is False, "Work should be blocked when linked task is not in_progress"

        # Check gate message
        captured = capsys.readouterr()
        assert "GATE: BLOCKED_BY_ISSUES" in captured.out

    def test_multiple_blockers_shows_all(self, temp_repo, capsys):
        """Test that multiple blocker issues are all shown in gate message."""
        # Create multiple blocker issues
        create_or_update_issue(
            fingerprint="test-fp-005",
            severity="blocker",
            message="Build error 1",
            scan_id="test-scan-005",
            timestamp="2025-01-28T12:00:00",
            repo_root=temp_repo,
        )

        create_or_update_issue(
            fingerprint="test-fp-006",
            severity="blocker",
            message="Build error 2",
            scan_id="test-scan-006",
            timestamp="2025-01-28T12:00:00",
            repo_root=temp_repo,
        )

        create_or_update_issue(
            fingerprint="test-fp-007",
            severity="blocker",
            message="Build error 3",
            scan_id="test-scan-007",
            timestamp="2025-01-28T12:00:00",
            repo_root=temp_repo,
        )

        # Should block work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is False, "Work should be blocked by multiple blocker issues"

        # Check that all issues are mentioned
        captured = capsys.readouterr()
        assert "ISSUE-001" in captured.out
        assert "ISSUE-002" in captured.out
        assert "ISSUE-003" in captured.out
        assert "Build error 1" in captured.out
        assert "Build error 2" in captured.out
        assert "Build error 3" in captured.out

    def test_warning_severity_does_not_block(self, temp_repo):
        """Test that warning-severity issues do not block work."""
        # Create a warning issue
        create_or_update_issue(
            fingerprint="test-fp-008",
            severity="warning",
            message="Unused variable 'x'",
            scan_id="test-scan-008",
            timestamp="2025-01-28T12:00:00",
            tool="gcc",
            file="main.cpp",
            line=10,
            kind="warning",
            repo_root=temp_repo,
        )

        # Warning should not block work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is True, "Work should proceed with only warning-severity issues"

    def test_resolved_blocker_does_not_block(self, temp_repo):
        """Test that resolved blocker issues do not block work."""
        # Create and resolve a blocker issue
        issue_id, _ = create_or_update_issue(
            fingerprint="test-fp-009",
            severity="blocker",
            message="Build error already fixed",
            scan_id="test-scan-009",
            timestamp="2025-01-28T12:00:00",
            repo_root=temp_repo,
        )

        # Resolve the issue
        from maestro.issues.json_store import resolve_issue

        resolve_issue(issue_id, reason="Fixed in commit abc123", repo_root=temp_repo)

        # Resolved blocker should not block work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is True, "Work should proceed when blocker is resolved"

    def test_ignored_blocker_does_not_block(self, temp_repo):
        """Test that ignored blocker issues do not block work."""
        # Create and ignore a blocker issue
        issue_id, _ = create_or_update_issue(
            fingerprint="test-fp-010",
            severity="blocker",
            message="False positive build error",
            scan_id="test-scan-010",
            timestamp="2025-01-28T12:00:00",
            repo_root=temp_repo,
        )

        # Ignore the issue
        from maestro.issues.json_store import ignore_issue

        ignore_issue(issue_id, reason="False positive", repo_root=temp_repo)

        # Ignored blocker should not block work
        result = check_work_gates(ignore_gates=False, repo_root=temp_repo)
        assert result is True, "Work should proceed when blocker is ignored"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
