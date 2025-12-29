"""Tests for runbook archive operations."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maestro.archive.runbook_archive import (
    ArchiveError,
    RestoreError,
    archive_runbook_json,
    archive_runbook_markdown,
    find_archive_entry,
    list_archived_runbooks,
    restore_runbook_json,
    restore_runbook_markdown,
)
from maestro.config.paths import (
    get_runbook_archive_index_path,
    get_runbook_examples_root,
)


class TestArchiveRunbookMarkdown:
    """Tests for archiving markdown runbook examples."""

    def test_archive_markdown_success(self, tmp_path: Path, monkeypatch):
        """Test successful archiving of a markdown runbook."""
        # Setup test environment
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create test runbook file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-TEST.sh"
        test_content = "#!/bin/bash\necho test"
        test_file.write_text(test_content)

        # Archive the file
        entry = archive_runbook_markdown(test_file, reason="Test archive")

        # Verify file was moved
        assert not test_file.exists()
        archived_path = Path(entry.archived_path)
        assert archived_path.exists()
        assert archived_path.read_text() == test_content

        # Verify archive entry
        assert entry.type == "runbook_markdown"
        assert entry.original_path == str(test_file)
        assert "archived" in entry.archived_path
        assert entry.reason == "Test archive"

        # Verify index was updated
        index_path = get_runbook_archive_index_path()
        assert index_path.exists()

    def test_archive_markdown_nonexistent_file_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a nonexistent file raises error."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        nonexistent = tmp_path / "nonexistent.sh"

        with pytest.raises(ArchiveError, match="Path not found"):
            archive_runbook_markdown(nonexistent)

    def test_archive_markdown_directory_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a directory raises error."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)

        with pytest.raises(ArchiveError, match="not a file"):
            archive_runbook_markdown(proposed_dir)

    def test_archive_markdown_outside_examples_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a file outside examples root fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create file outside examples directory
        outside_file = tmp_path / "outside.sh"
        outside_file.write_text("test")

        with pytest.raises(ArchiveError, match="must be under"):
            archive_runbook_markdown(outside_file)

    def test_archive_markdown_already_archived_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving an already-archived file fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-DOUBLE.sh"
        test_file.write_text("test")

        archive_runbook_markdown(test_file)

        # Try to archive again (should fail)
        # Need to recreate the file first since it was moved
        test_file.write_text("test")

        with pytest.raises(ArchiveError, match="already archived"):
            archive_runbook_markdown(test_file)

    def test_archive_markdown_preserves_content(self, tmp_path: Path, monkeypatch):
        """Test that archiving preserves file content exactly."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-CONTENT.sh"

        # Create file with specific content
        original_content = "#!/bin/bash\necho 'special content'\n# comment\n"
        test_file.write_text(original_content)

        # Archive it
        entry = archive_runbook_markdown(test_file)

        # Verify content is preserved exactly
        archived_path = Path(entry.archived_path)
        assert archived_path.read_text() == original_content

    def test_archive_markdown_mirrors_path_structure(self, tmp_path: Path, monkeypatch):
        """Test that archive mirrors the original path structure."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        examples_dir = get_runbook_examples_root()
        input_dir = examples_dir / "input_from_v2_proposed"
        input_dir.mkdir(parents=True)
        test_file = input_dir / "EX-MIRROR.sh"
        test_file.write_text("test")

        entry = archive_runbook_markdown(test_file)

        # Verify archived path mirrors original structure
        archived_path = Path(entry.archived_path)
        assert "input_from_v2_proposed" in str(archived_path)
        assert "EX-MIRROR.sh" in str(archived_path)
        assert "archived" in str(archived_path)


class TestRestoreRunbookMarkdown:
    """Tests for restoring markdown runbooks."""

    def test_restore_markdown_success(self, tmp_path: Path, monkeypatch):
        """Test successful restore of a markdown runbook."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-RESTORE.sh"
        test_content = "#!/bin/bash\necho restore test"
        test_file.write_text(test_content)

        entry = archive_runbook_markdown(test_file)
        archive_id = entry.archive_id

        # Restore it
        restored_path = restore_runbook_markdown(archive_id)

        # Verify file was restored
        assert restored_path.exists()
        assert restored_path.read_text() == test_content
        assert str(restored_path) == entry.original_path

        # Verify archived file is gone
        archived_path = Path(entry.archived_path)
        assert not archived_path.exists()

        # Verify removed from archive index
        archived_list = list_archived_runbooks()
        archive_ids = [e.archive_id for e in archived_list]
        assert archive_id not in archive_ids

    def test_restore_markdown_nonexistent_archive_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring a nonexistent archive fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        with pytest.raises(RestoreError, match="Archive not found"):
            restore_runbook_markdown("nonexistent-id")

    def test_restore_markdown_occupied_path_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring to an occupied path fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-OCCUPIED.sh"
        test_file.write_text("original")

        entry = archive_runbook_markdown(test_file)
        archive_id = entry.archive_id

        # Create a new file at the original path
        test_file.write_text("new content")

        # Try to restore (should fail)
        with pytest.raises(RestoreError, match="original path occupied"):
            restore_runbook_markdown(archive_id)

    def test_restore_markdown_missing_archived_file_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring when archived file is missing fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-MISSING.sh"
        test_file.write_text("test")

        entry = archive_runbook_markdown(test_file)
        archive_id = entry.archive_id

        # Delete the archived file manually
        archived_path = Path(entry.archived_path)
        archived_path.unlink()

        # Try to restore (should fail)
        with pytest.raises(RestoreError, match="Archived file missing"):
            restore_runbook_markdown(archive_id)

    def test_restore_markdown_preserves_content(self, tmp_path: Path, monkeypatch):
        """Test that restore preserves content exactly."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-PRESERVE.sh"

        original_content = "#!/bin/bash\n# Complex script\necho 'test'\n\nfunction foo() {\n  bar\n}\n"
        test_file.write_text(original_content)

        entry = archive_runbook_markdown(test_file)
        restored_path = restore_runbook_markdown(entry.archive_id)

        assert restored_path.read_text() == original_content


class TestArchiveRunbookJSON:
    """Tests for archiving JSON runbooks."""

    def test_archive_json_success(self, tmp_path: Path, monkeypatch):
        """Test successful archiving of a JSON runbook."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create runbook items directory and file
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "test-rb-123"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_data = {"id": runbook_id, "title": "Test Runbook"}
        runbook_file.write_text(json.dumps(runbook_data, indent=2))

        # Archive it
        entry = archive_runbook_json(runbook_id, reason="Test JSON archive")

        # Verify file was moved
        assert not runbook_file.exists()
        archived_path = Path(entry.archived_path)
        assert archived_path.exists()

        # Verify archive entry
        assert entry.type == "runbook_json"
        assert entry.runbook_id == runbook_id
        assert entry.reason == "Test JSON archive"

    def test_archive_json_nonexistent_runbook_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a nonexistent runbook fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        with pytest.raises(ArchiveError, match="Runbook not found"):
            archive_runbook_json("nonexistent-rb")

    def test_archive_json_already_archived_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving an already-archived JSON runbook fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a runbook
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "double-archive-rb"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_file.write_text(json.dumps({"id": runbook_id}))

        archive_runbook_json(runbook_id)

        # Recreate the file
        runbook_file.write_text(json.dumps({"id": runbook_id}))

        # Try to archive again
        with pytest.raises(ArchiveError, match="already archived"):
            archive_runbook_json(runbook_id)


class TestRestoreRunbookJSON:
    """Tests for restoring JSON runbooks."""

    def test_restore_json_success(self, tmp_path: Path, monkeypatch):
        """Test successful restore of a JSON runbook."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a runbook
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "restore-json-rb"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_data = {"id": runbook_id, "title": "Restore Test"}
        runbook_file.write_text(json.dumps(runbook_data))

        entry = archive_runbook_json(runbook_id)
        archive_id = entry.archive_id

        # Restore it
        restored_id = restore_runbook_json(archive_id)

        # Verify restoration
        assert restored_id == runbook_id
        assert runbook_file.exists()

        # Verify removed from archive
        archived_list = list_archived_runbooks(type_filter="json")
        archive_ids = [e.archive_id for e in archived_list]
        assert archive_id not in archive_ids


class TestListArchivedRunbooks:
    """Tests for listing archived runbooks."""

    def test_list_empty_archive(self, tmp_path: Path, monkeypatch):
        """Test listing when archive is empty."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        archived = list_archived_runbooks()
        assert len(archived) == 0

    def test_list_markdown_filter(self, tmp_path: Path, monkeypatch):
        """Test listing with markdown filter."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive markdown file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        md_file = proposed_dir / "EX-MD.sh"
        md_file.write_text("markdown runbook")

        archive_runbook_markdown(md_file)

        # List with filter
        archived = list_archived_runbooks(type_filter="markdown")
        assert len(archived) == 1
        assert archived[0].type == "runbook_markdown"

    def test_list_json_filter(self, tmp_path: Path, monkeypatch):
        """Test listing with json filter."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive JSON runbook
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "filter-test-rb"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_file.write_text(json.dumps({"id": runbook_id}))

        archive_runbook_json(runbook_id)

        # List with filter
        archived = list_archived_runbooks(type_filter="json")
        assert len(archived) == 1
        assert archived[0].type == "runbook_json"

    def test_list_all_types(self, tmp_path: Path, monkeypatch):
        """Test listing all archived runbooks regardless of type."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Archive both types
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        md_file = proposed_dir / "EX-ALL.sh"
        md_file.write_text("markdown")

        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "all-test-rb"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_file.write_text(json.dumps({"id": runbook_id}))

        archive_runbook_markdown(md_file)
        archive_runbook_json(runbook_id)

        # List all
        archived = list_archived_runbooks()
        assert len(archived) == 2
        types = {e.type for e in archived}
        assert "runbook_markdown" in types
        assert "runbook_json" in types


class TestFindArchiveEntry:
    """Tests for finding archive entries."""

    def test_find_by_archive_id(self, tmp_path: Path, monkeypatch):
        """Test finding entry by archive ID."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-FIND.sh"
        test_file.write_text("test")

        entry = archive_runbook_markdown(test_file)
        archive_id = entry.archive_id

        # Find it
        found = find_archive_entry(archive_id)
        assert found is not None
        assert found.archive_id == archive_id

    def test_find_by_original_path(self, tmp_path: Path, monkeypatch):
        """Test finding entry by original path."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        test_file = proposed_dir / "EX-PATH.sh"
        test_file.write_text("test")

        entry = archive_runbook_markdown(test_file)
        original_path = entry.original_path

        # Find it
        found = find_archive_entry(original_path)
        assert found is not None
        assert found.original_path == original_path

    def test_find_by_runbook_id(self, tmp_path: Path, monkeypatch):
        """Test finding JSON runbook entry by runbook ID."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a runbook
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "find-by-rb-id"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_file.write_text(json.dumps({"id": runbook_id}))

        archive_runbook_json(runbook_id)

        # Find it
        found = find_archive_entry(runbook_id)
        assert found is not None
        assert found.runbook_id == runbook_id

    def test_find_nonexistent_returns_none(self, tmp_path: Path, monkeypatch):
        """Test finding nonexistent entry returns None."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        found = find_archive_entry("nonexistent")
        assert found is None


class TestArchiveRestoreRoundTrip:
    """Tests for complete archive/restore workflows."""

    def test_markdown_archive_restore_roundtrip(self, tmp_path: Path, monkeypatch):
        """Test complete archive and restore cycle for markdown."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create original file
        examples_dir = get_runbook_examples_root()
        proposed_dir = examples_dir / "proposed"
        proposed_dir.mkdir(parents=True)
        original_file = proposed_dir / "EX-ROUNDTRIP.sh"
        original_content = "#!/bin/bash\necho 'roundtrip test'\n"
        original_file.write_text(original_content)
        original_path_str = str(original_file)

        # Archive
        entry = archive_runbook_markdown(original_file, reason="Roundtrip test")
        assert not original_file.exists()

        # Restore
        restored_path = restore_runbook_markdown(entry.archive_id)
        assert restored_path.exists()
        assert str(restored_path) == original_path_str
        assert restored_path.read_text() == original_content

    def test_json_archive_restore_roundtrip(self, tmp_path: Path, monkeypatch):
        """Test complete archive and restore cycle for JSON."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create original runbook
        items_dir = tmp_path / "docs" / "maestro" / "runbooks" / "items"
        items_dir.mkdir(parents=True)
        runbook_id = "roundtrip-rb"
        runbook_file = items_dir / f"{runbook_id}.json"
        runbook_data = {
            "id": runbook_id,
            "title": "Roundtrip Test",
            "status": "approved",
        }
        runbook_file.write_text(json.dumps(runbook_data, indent=2))
        original_content = runbook_file.read_text()

        # Archive
        entry = archive_runbook_json(runbook_id, reason="Roundtrip test")
        assert not runbook_file.exists()

        # Restore
        restored_id = restore_runbook_json(entry.archive_id)
        assert restored_id == runbook_id
        assert runbook_file.exists()
        assert runbook_file.read_text() == original_content
