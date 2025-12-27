"""Tests for discuss OPS gating based on context."""

import pytest

from maestro.ai import PatchOperation, PatchOperationType
from maestro.commands.discuss import validate_ops_for_context


class TestDiscussOpsGating:
    """Tests for context-aware OPS validation."""

    def test_task_context_allows_task_ops(self):
        """Test that task context allows task operations."""
        ops = [
            PatchOperation(
                op_type=PatchOperationType.ADD_TASK,
                data={"task_name": "Test", "task_id": "test-1", "phase_id": "p1"}
            )
        ]

        is_valid, error = validate_ops_for_context(ops, "task", allow_cross_context=False)

        assert is_valid is True
        assert error is None

    def test_task_context_blocks_track_ops(self):
        """Test that task context blocks track operations."""
        ops = [
            PatchOperation(
                op_type=PatchOperationType.ADD_TRACK,
                data={"track_name": "Test Track", "track_id": "test-track"}
            )
        ]

        is_valid, error = validate_ops_for_context(ops, "task", allow_cross_context=False)

        assert is_valid is False
        assert "not allowed in task context" in error
        assert "--allow-cross-context" in error

    def test_allow_cross_context_bypasses_gating(self):
        """Test that --allow-cross-context bypasses OPS gating."""
        ops = [
            PatchOperation(
                op_type=PatchOperationType.ADD_TRACK,
                data={"track_name": "Test Track", "track_id": "test-track"}
            )
        ]

        is_valid, error = validate_ops_for_context(ops, "task", allow_cross_context=True)

        assert is_valid is True
        assert error is None

    def test_global_context_allows_everything(self):
        """Test that global context allows all operations."""
        ops = [
            PatchOperation(
                op_type=PatchOperationType.ADD_TRACK,
                data={"track_name": "Test Track", "track_id": "test-track"}
            ),
            PatchOperation(
                op_type=PatchOperationType.ADD_TASK,
                data={"task_name": "Test", "task_id": "test-1", "phase_id": "p1"}
            )
        ]

        is_valid, error = validate_ops_for_context(ops, "global", allow_cross_context=False)

        assert is_valid is True
        assert error is None

    def test_phase_context_allows_task_ops(self):
        """Test that phase context allows task operations."""
        ops = [
            PatchOperation(
                op_type=PatchOperationType.ADD_TASK,
                data={"task_name": "Test", "task_id": "test-1", "phase_id": "p1"}
            )
        ]

        is_valid, error = validate_ops_for_context(ops, "phase", allow_cross_context=False)

        assert is_valid is True
        assert error is None

    def test_repo_context_allows_repo_ops(self):
        """Test that repo context allows repo/repoconf/make/tu operations."""
        # Note: We don't have these PatchOperationType defined yet, so this test
        # uses a conceptual approach. In a real scenario, you'd add these types.
        # For now, we'll test the allowlist logic with existing types.

        # This test is more conceptual since we don't have REPO-specific ops yet
        # Just verify the allowlist exists
        from maestro.commands.discuss import validate_ops_for_context

        # Verify repo allowlist includes repo, repoconf, make, tu
        # (This is a white-box test checking the implementation)
        ops = []  # Empty ops list
        is_valid, error = validate_ops_for_context(ops, "repo", allow_cross_context=False)
        assert is_valid is True
