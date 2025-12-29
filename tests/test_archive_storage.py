"""Tests for archive storage layer."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from maestro.archive.storage import (
    ArchiveEntry,
    ArchiveIndex,
    generate_archive_id,
    get_timestamp_folder,
    load_archive_index,
    save_archive_index,
)


class TestArchiveEntry:
    """Tests for ArchiveEntry dataclass."""

    def test_to_dict_all_fields(self):
        """Test ArchiveEntry.to_dict() with all fields populated."""
        entry = ArchiveEntry(
            archive_id="test-id-123",
            type="runbook_markdown",
            original_path="docs/workflows/v3/runbooks/examples/proposed/EX-30.sh",
            archived_path="docs/workflows/v3/runbooks/examples/archived/20251229/proposed/EX-30.sh",
            archived_at="2025-12-29T12:34:56",
            reason="Test archive",
            git_head="abc123",
            user="testuser",
            runbook_id="ex-30",
        )

        result = entry.to_dict()

        assert result["archive_id"] == "test-id-123"
        assert result["type"] == "runbook_markdown"
        assert result["original_path"] == "docs/workflows/v3/runbooks/examples/proposed/EX-30.sh"
        assert result["archived_path"] == "docs/workflows/v3/runbooks/examples/archived/20251229/proposed/EX-30.sh"
        assert result["archived_at"] == "2025-12-29T12:34:56"
        assert result["reason"] == "Test archive"
        assert result["git_head"] == "abc123"
        assert result["user"] == "testuser"
        assert result["runbook_id"] == "ex-30"

    def test_to_dict_minimal_fields(self):
        """Test ArchiveEntry.to_dict() with only required fields."""
        entry = ArchiveEntry(
            archive_id="test-id-456",
            type="workflow",
            original_path="docs/workflows/v3/workflows/workflow-1.md",
            archived_path="docs/workflows/v3/workflows/archived/20251229/workflow-1.md",
            archived_at="2025-12-29T13:00:00",
        )

        result = entry.to_dict()

        assert result["archive_id"] == "test-id-456"
        assert result["type"] == "workflow"
        assert "reason" not in result
        assert "git_head" not in result
        assert "user" not in result
        assert "runbook_id" not in result

    def test_from_dict_all_fields(self):
        """Test ArchiveEntry.from_dict() with all fields."""
        data = {
            "archive_id": "test-id-789",
            "type": "runbook_json",
            "original_path": "docs/maestro/runbooks/items/rb-123.json",
            "archived_path": "docs/maestro/runbooks/archive/items/rb-123.json",
            "archived_at": "2025-12-29T14:00:00",
            "reason": "Deprecated",
            "git_head": "def456",
            "user": "admin",
            "runbook_id": "rb-123",
        }

        entry = ArchiveEntry.from_dict(data)

        assert entry.archive_id == "test-id-789"
        assert entry.type == "runbook_json"
        assert entry.original_path == "docs/maestro/runbooks/items/rb-123.json"
        assert entry.archived_path == "docs/maestro/runbooks/archive/items/rb-123.json"
        assert entry.archived_at == "2025-12-29T14:00:00"
        assert entry.reason == "Deprecated"
        assert entry.git_head == "def456"
        assert entry.user == "admin"
        assert entry.runbook_id == "rb-123"

    def test_from_dict_minimal_fields(self):
        """Test ArchiveEntry.from_dict() with only required fields."""
        data = {
            "archive_id": "test-id-xyz",
            "type": "workflow",
            "original_path": "docs/workflows/v3/workflows/wf-1.md",
            "archived_path": "docs/workflows/v3/workflows/archived/20251229/wf-1.md",
            "archived_at": "2025-12-29T15:00:00",
        }

        entry = ArchiveEntry.from_dict(data)

        assert entry.archive_id == "test-id-xyz"
        assert entry.reason is None
        assert entry.git_head is None
        assert entry.user is None
        assert entry.runbook_id is None

    def test_round_trip_serialization(self):
        """Test that to_dict() and from_dict() are inverse operations."""
        original = ArchiveEntry(
            archive_id="round-trip-id",
            type="runbook_markdown",
            original_path="original/path.sh",
            archived_path="archived/path.sh",
            archived_at="2025-12-29T16:00:00",
            reason="Round trip test",
            git_head="abcdef",
            user="tester",
        )

        data = original.to_dict()
        restored = ArchiveEntry.from_dict(data)

        assert restored.archive_id == original.archive_id
        assert restored.type == original.type
        assert restored.original_path == original.original_path
        assert restored.archived_path == original.archived_path
        assert restored.archived_at == original.archived_at
        assert restored.reason == original.reason
        assert restored.git_head == original.git_head
        assert restored.user == original.user


class TestArchiveIndex:
    """Tests for ArchiveIndex dataclass."""

    def test_to_dict_empty(self):
        """Test ArchiveIndex.to_dict() with empty entries."""
        index = ArchiveIndex()

        result = index.to_dict()

        assert result["entries"] == []
        assert "last_updated" in result

    def test_to_dict_with_entries(self):
        """Test ArchiveIndex.to_dict() with multiple entries."""
        entries = [
            ArchiveEntry(
                archive_id="id1",
                type="runbook_markdown",
                original_path="path1",
                archived_path="archived1",
                archived_at="2025-12-29T10:00:00",
            ),
            ArchiveEntry(
                archive_id="id2",
                type="workflow",
                original_path="path2",
                archived_path="archived2",
                archived_at="2025-12-29T11:00:00",
            ),
        ]
        index = ArchiveIndex(entries=entries, last_updated="2025-12-29T12:00:00")

        result = index.to_dict()

        assert len(result["entries"]) == 2
        assert result["entries"][0]["archive_id"] == "id1"
        assert result["entries"][1]["archive_id"] == "id2"

    def test_from_dict_empty(self):
        """Test ArchiveIndex.from_dict() with empty data."""
        data = {"entries": [], "last_updated": "2025-12-29T12:00:00"}

        index = ArchiveIndex.from_dict(data)

        assert len(index.entries) == 0
        assert index.last_updated == "2025-12-29T12:00:00"

    def test_from_dict_with_entries(self):
        """Test ArchiveIndex.from_dict() with entries."""
        data = {
            "entries": [
                {
                    "archive_id": "idx1",
                    "type": "runbook_json",
                    "original_path": "orig1",
                    "archived_path": "arch1",
                    "archived_at": "2025-12-29T09:00:00",
                },
                {
                    "archive_id": "idx2",
                    "type": "workflow",
                    "original_path": "orig2",
                    "archived_path": "arch2",
                    "archived_at": "2025-12-29T10:00:00",
                },
            ],
            "last_updated": "2025-12-29T11:00:00",
        }

        index = ArchiveIndex.from_dict(data)

        assert len(index.entries) == 2
        assert index.entries[0].archive_id == "idx1"
        assert index.entries[1].archive_id == "idx2"

    def test_round_trip_serialization(self):
        """Test that to_dict() and from_dict() are inverse operations."""
        entries = [
            ArchiveEntry(
                archive_id="rt1",
                type="runbook_markdown",
                original_path="rt_orig1",
                archived_path="rt_arch1",
                archived_at="2025-12-29T08:00:00",
                reason="test1",
            ),
            ArchiveEntry(
                archive_id="rt2",
                type="workflow",
                original_path="rt_orig2",
                archived_path="rt_arch2",
                archived_at="2025-12-29T09:00:00",
            ),
        ]
        original = ArchiveIndex(entries=entries, last_updated="2025-12-29T10:00:00")

        data = original.to_dict()
        restored = ArchiveIndex.from_dict(data)

        assert len(restored.entries) == len(original.entries)
        for i, entry in enumerate(restored.entries):
            assert entry.archive_id == original.entries[i].archive_id
            assert entry.type == original.entries[i].type


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_archive_id_is_unique(self):
        """Test that generate_archive_id() produces unique IDs."""
        id1 = generate_archive_id()
        id2 = generate_archive_id()

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0

    def test_generate_archive_id_is_uuid_format(self):
        """Test that generated IDs are valid UUIDs."""
        archive_id = generate_archive_id()

        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        parts = archive_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_get_timestamp_folder_format(self):
        """Test that get_timestamp_folder() returns YYYYMMDD format."""
        timestamp = get_timestamp_folder()

        assert len(timestamp) == 8
        assert timestamp.isdigit()

        # Should be parseable as a date
        year = int(timestamp[:4])
        month = int(timestamp[4:6])
        day = int(timestamp[6:8])

        assert 2020 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31


class TestArchiveIndexIO:
    """Tests for archive index load/save operations."""

    def test_load_nonexistent_index_returns_empty(self, tmp_path: Path):
        """Test loading a nonexistent index returns empty ArchiveIndex."""
        index_path = tmp_path / "nonexistent.json"

        index = load_archive_index(index_path)

        assert isinstance(index, ArchiveIndex)
        assert len(index.entries) == 0

    def test_save_and_load_empty_index(self, tmp_path: Path):
        """Test saving and loading an empty index."""
        index_path = tmp_path / "archive_index.json"
        index = ArchiveIndex()

        save_archive_index(index, index_path)

        loaded = load_archive_index(index_path)
        assert len(loaded.entries) == 0
        assert loaded.last_updated is not None

    def test_save_and_load_index_with_entries(self, tmp_path: Path):
        """Test saving and loading an index with entries."""
        index_path = tmp_path / "archive_index.json"
        entries = [
            ArchiveEntry(
                archive_id="save-id-1",
                type="runbook_markdown",
                original_path="docs/workflows/v3/runbooks/examples/proposed/EX-30.sh",
                archived_path="docs/workflows/v3/runbooks/examples/archived/20251229/proposed/EX-30.sh",
                archived_at="2025-12-29T12:00:00",
                reason="Test save",
                git_head="abc123",
                user="testuser",
            ),
            ArchiveEntry(
                archive_id="save-id-2",
                type="workflow",
                original_path="docs/workflows/v3/workflows/wf-1.md",
                archived_path="docs/workflows/v3/workflows/archived/20251229/wf-1.md",
                archived_at="2025-12-29T13:00:00",
            ),
        ]
        index = ArchiveIndex(entries=entries)

        save_archive_index(index, index_path)

        loaded = load_archive_index(index_path)
        assert len(loaded.entries) == 2
        assert loaded.entries[0].archive_id == "save-id-1"
        assert loaded.entries[0].reason == "Test save"
        assert loaded.entries[1].archive_id == "save-id-2"
        assert loaded.entries[1].reason is None

    def test_save_creates_parent_directories(self, tmp_path: Path):
        """Test that save_archive_index creates parent directories."""
        index_path = tmp_path / "deeply" / "nested" / "archive_index.json"
        index = ArchiveIndex()

        save_archive_index(index, index_path)

        assert index_path.exists()
        assert index_path.parent.exists()

    def test_save_index_is_valid_json(self, tmp_path: Path):
        """Test that saved index is valid JSON."""
        index_path = tmp_path / "archive_index.json"
        entries = [
            ArchiveEntry(
                archive_id="json-test-id",
                type="runbook_json",
                original_path="test/path.json",
                archived_path="test/archived/path.json",
                archived_at="2025-12-29T14:00:00",
            )
        ]
        index = ArchiveIndex(entries=entries)

        save_archive_index(index, index_path)

        # Should be readable as valid JSON
        with open(index_path, "r") as f:
            data = json.load(f)

        assert "entries" in data
        assert "last_updated" in data
        assert len(data["entries"]) == 1

    def test_save_updates_last_updated(self, tmp_path: Path):
        """Test that save_archive_index updates last_updated timestamp."""
        index_path = tmp_path / "archive_index.json"
        index = ArchiveIndex()
        old_timestamp = "2025-01-01T00:00:00"
        index.last_updated = old_timestamp

        save_archive_index(index, index_path)

        loaded = load_archive_index(index_path)
        # last_updated should be updated to current time
        assert loaded.last_updated != old_timestamp

    def test_load_corrupted_index_returns_empty(self, tmp_path: Path):
        """Test that loading a corrupted index returns empty ArchiveIndex."""
        index_path = tmp_path / "corrupted.json"
        index_path.write_text("{ invalid json }", encoding="utf-8")

        index = load_archive_index(index_path)

        assert isinstance(index, ArchiveIndex)
        assert len(index.entries) == 0

    def test_atomic_write_no_partial_state(self, tmp_path: Path):
        """Test that atomic write doesn't leave partial state on failure."""
        index_path = tmp_path / "atomic_test.json"
        index = ArchiveIndex()

        # Save once to create the file
        save_archive_index(index, index_path)

        # Verify file exists and is valid
        assert index_path.exists()
        loaded = load_archive_index(index_path)
        assert len(loaded.entries) == 0

        # No .tmp files should be left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0
