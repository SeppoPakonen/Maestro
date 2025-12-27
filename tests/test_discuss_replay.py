"""Tests for deterministic discuss replay functionality."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from maestro.session_format import load_session, extract_final_json
from maestro.ai import PatchOperationType


class TestDiscussReplay:
    """Tests for deterministic replay (no AI engines)."""

    def test_load_canonical_session(self):
        """Test loading session from canonical format."""
        fixture_path = Path("tests/fixtures/discuss_sessions/session_task_valid_jsonl")
        session = load_session(str(fixture_path))

        assert session.meta.session_id == "test-session-task-valid"
        assert session.meta.context["kind"] == "task"
        assert session.meta.context["ref"] == "test-task-123"
        assert session.meta.final_json_present is True

    def test_extract_final_json_from_session(self):
        """Test extracting final_json from canonical session."""
        fixture_path = Path("tests/fixtures/discuss_sessions/session_task_valid_jsonl")
        session = load_session(str(fixture_path))

        patch_ops = extract_final_json(session)

        assert patch_ops is not None
        assert len(patch_ops) == 1
        assert patch_ops[0]["op_type"] == "add_task"
        assert patch_ops[0]["data"]["task_id"] == "test-123"

    def test_extract_final_json_missing(self):
        """Test extracting final_json when not present returns None."""
        # Create minimal session without final_json
        from maestro.session_format import DiscussSession, SessionMeta

        meta = SessionMeta(
            session_id="test-empty",
            context={"kind": "global", "ref": None, "router_reason": "test"},
            contract_type="global",
            created_at="2025-12-27T10:00:00",
            updated_at="2025-12-27T10:00:00",
            status="open",
            final_json_present=False,
            engine="test",
            model="test",
            initial_prompt="test"
        )
        session = DiscussSession(meta=meta, transcript=[])

        patch_ops = extract_final_json(session)
        assert patch_ops is None

    def test_load_legacy_artifact(self):
        """Test loading session from legacy artifact format."""
        fixture_path = Path("tests/fixtures/discuss_sessions/session_legacy_artifact/discuss_global_20251227_100000_results.json")
        session = load_session(str(fixture_path))

        assert session.meta.session_id == "discuss_global_20251227_100000"
        assert session.meta.context["kind"] == "global"
        assert session.meta.final_json_present is True

        # Check that final_json was extracted from legacy format
        patch_ops = extract_final_json(session)
        assert patch_ops is not None
        assert len(patch_ops) == 1
        assert patch_ops[0]["op_type"] == "add_track"

    def test_invalid_op_type_in_final_json(self):
        """Test that invalid operation types can be detected."""
        fixture_path = Path("tests/fixtures/discuss_sessions/session_task_invalid_jsonl")
        session = load_session(str(fixture_path))

        patch_ops = extract_final_json(session)
        assert patch_ops is not None

        # Try to convert to PatchOperation - should raise ValueError
        with pytest.raises(ValueError):
            PatchOperationType(patch_ops[0]["op_type"])

    @patch('maestro.commands.discuss.apply_patch_operations')
    def test_replay_dry_run_no_mutation(self, mock_apply):
        """Test that dry-run replay doesn't call apply_patch_operations."""
        from maestro.commands.discuss import handle_discuss_replay
        from unittest.mock import Mock

        args = Mock()
        args.path = "tests/fixtures/discuss_sessions/session_task_valid_jsonl"
        args.dry_run = True
        args.allow_cross_context = False

        result = handle_discuss_replay(args)

        # Should succeed without calling apply_patch_operations
        assert result == 0
        mock_apply.assert_not_called()

    def test_session_not_found(self):
        """Test that loading nonexistent session raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_session("nonexistent-session-id")
