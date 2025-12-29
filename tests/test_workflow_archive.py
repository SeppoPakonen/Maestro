"""Tests for workflow archive operations."""
from __future__ import annotations

from pathlib import Path

import pytest

from maestro.archive.workflow_archive import (
    ArchiveError,
    RestoreError,
    archive_workflow,
    find_archive_entry,
    list_active_workflows,
    list_archived_workflows,
    restore_workflow,
)
from maestro.config.paths import (
    get_workflow_archive_index_path,
    get_workflows_root,
)


class TestArchiveWorkflow:
    """Tests for archiving workflow files."""

    def test_archive_workflow_success(self, tmp_path: Path, monkeypatch):
        """Test successful archiving of a workflow file."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create test workflow file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "workflow-test.md"
        test_content = "# Test Workflow\n\nThis is a test workflow."
        test_file.write_text(test_content)

        # Archive the file
        entry = archive_workflow(test_file, reason="Test archive")

        # Verify file was moved
        assert not test_file.exists()
        archived_path = Path(entry.archived_path)
        assert archived_path.exists()
        assert archived_path.read_text() == test_content

        # Verify archive entry
        assert entry.type == "workflow"
        assert entry.original_path == str(test_file)
        assert "archived" in entry.archived_path
        assert entry.reason == "Test archive"

        # Verify index was updated
        index_path = get_workflow_archive_index_path()
        assert index_path.exists()

    def test_archive_workflow_nonexistent_file_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a nonexistent file raises error."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(ArchiveError, match="Path not found"):
            archive_workflow(nonexistent)

    def test_archive_workflow_directory_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a directory raises error."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)

        with pytest.raises(ArchiveError, match="not a file"):
            archive_workflow(workflows_dir)

    def test_archive_workflow_outside_root_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving a file outside workflows root fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create file outside workflows directory
        outside_file = tmp_path / "outside.md"
        outside_file.write_text("test")

        with pytest.raises(ArchiveError, match="must be under"):
            archive_workflow(outside_file)

    def test_archive_workflow_already_archived_fails(self, tmp_path: Path, monkeypatch):
        """Test archiving an already-archived file fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-double.md"
        test_file.write_text("test")

        archive_workflow(test_file)

        # Try to archive again (should fail)
        # Need to recreate the file first since it was moved
        test_file.write_text("test")

        with pytest.raises(ArchiveError, match="already archived"):
            archive_workflow(test_file)

    def test_archive_workflow_preserves_content(self, tmp_path: Path, monkeypatch):
        """Test that archiving preserves file content exactly."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-content.md"

        # Create file with specific content
        original_content = "# Workflow\n\n## Steps\n\n1. First step\n2. Second step\n"
        test_file.write_text(original_content)

        # Archive it
        entry = archive_workflow(test_file)

        # Verify content is preserved exactly
        archived_path = Path(entry.archived_path)
        assert archived_path.read_text() == original_content

    def test_archive_workflow_mirrors_path_structure(self, tmp_path: Path, monkeypatch):
        """Test that archive mirrors the original path structure."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        subdir = workflows_dir / "category"
        subdir.mkdir(parents=True)
        test_file = subdir / "wf-mirror.md"
        test_file.write_text("test")

        entry = archive_workflow(test_file)

        # Verify archived path mirrors original structure
        archived_path = Path(entry.archived_path)
        assert "category" in str(archived_path)
        assert "wf-mirror.md" in str(archived_path)
        assert "archived" in str(archived_path)


class TestRestoreWorkflow:
    """Tests for restoring workflow files."""

    def test_restore_workflow_success(self, tmp_path: Path, monkeypatch):
        """Test successful restore of a workflow file."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-restore.md"
        test_content = "# Restore Test Workflow"
        test_file.write_text(test_content)

        entry = archive_workflow(test_file)
        archive_id = entry.archive_id

        # Restore it
        restored_path = restore_workflow(archive_id)

        # Verify file was restored
        assert restored_path.exists()
        assert restored_path.read_text() == test_content
        assert str(restored_path) == entry.original_path

        # Verify archived file is gone
        archived_path = Path(entry.archived_path)
        assert not archived_path.exists()

        # Verify removed from archive index
        archived_list = list_archived_workflows()
        archive_ids = [e.archive_id for e in archived_list]
        assert archive_id not in archive_ids

    def test_restore_workflow_nonexistent_archive_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring a nonexistent archive fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        with pytest.raises(RestoreError, match="Archive not found"):
            restore_workflow("nonexistent-id")

    def test_restore_workflow_occupied_path_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring to an occupied path fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-occupied.md"
        test_file.write_text("original")

        entry = archive_workflow(test_file)
        archive_id = entry.archive_id

        # Create a new file at the original path
        test_file.write_text("new content")

        # Try to restore (should fail)
        with pytest.raises(RestoreError, match="original path occupied"):
            restore_workflow(archive_id)

    def test_restore_workflow_missing_archived_file_fails(self, tmp_path: Path, monkeypatch):
        """Test restoring when archived file is missing fails."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-missing.md"
        test_file.write_text("test")

        entry = archive_workflow(test_file)
        archive_id = entry.archive_id

        # Delete the archived file manually
        archived_path = Path(entry.archived_path)
        archived_path.unlink()

        # Try to restore (should fail)
        with pytest.raises(RestoreError, match="Archived file missing"):
            restore_workflow(archive_id)

    def test_restore_workflow_preserves_content(self, tmp_path: Path, monkeypatch):
        """Test that restore preserves content exactly."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-preserve.md"

        original_content = "# Complex Workflow\n\n## Prerequisites\n- Requirement 1\n- Requirement 2\n"
        test_file.write_text(original_content)

        entry = archive_workflow(test_file)
        restored_path = restore_workflow(entry.archive_id)

        assert restored_path.read_text() == original_content


class TestListWorkflows:
    """Tests for listing workflows."""

    def test_list_archived_empty(self, tmp_path: Path, monkeypatch):
        """Test listing when archive is empty."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        archived = list_archived_workflows()
        assert len(archived) == 0

    def test_list_archived_workflows(self, tmp_path: Path, monkeypatch):
        """Test listing archived workflows."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a workflow
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        wf_file = workflows_dir / "wf-list.md"
        wf_file.write_text("test workflow")

        archive_workflow(wf_file)

        # List archived
        archived = list_archived_workflows()
        assert len(archived) == 1
        assert archived[0].type == "workflow"

    def test_list_active_workflows_empty(self, tmp_path: Path, monkeypatch):
        """Test listing active workflows when directory doesn't exist."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        active = list_active_workflows()
        assert len(active) == 0

    def test_list_active_workflows(self, tmp_path: Path, monkeypatch):
        """Test listing active workflow files."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)

        # Create several workflow files
        wf1 = workflows_dir / "workflow-1.md"
        wf2 = workflows_dir / "workflow-2.md"
        subdir = workflows_dir / "category"
        subdir.mkdir()
        wf3 = subdir / "workflow-3.md"

        wf1.write_text("workflow 1")
        wf2.write_text("workflow 2")
        wf3.write_text("workflow 3")

        # List active
        active = list_active_workflows()
        assert len(active) == 3
        assert wf1 in active
        assert wf2 in active
        assert wf3 in active

    def test_list_active_excludes_archived(self, tmp_path: Path, monkeypatch):
        """Test that listing active workflows excludes archived directory."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)

        # Create active workflow
        active_wf = workflows_dir / "active.md"
        active_wf.write_text("active")

        # Create and archive another workflow
        archive_wf = workflows_dir / "to-archive.md"
        archive_wf.write_text("to archive")
        archive_workflow(archive_wf)

        # List active should only show active workflow
        active = list_active_workflows()
        assert len(active) == 1
        assert active_wf in active


class TestFindArchiveEntry:
    """Tests for finding archive entries."""

    def test_find_by_archive_id(self, tmp_path: Path, monkeypatch):
        """Test finding entry by archive ID."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-find.md"
        test_file.write_text("test")

        entry = archive_workflow(test_file)
        archive_id = entry.archive_id

        # Find it
        found = find_archive_entry(archive_id)
        assert found is not None
        assert found.archive_id == archive_id

    def test_find_by_original_path(self, tmp_path: Path, monkeypatch):
        """Test finding entry by original path."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create and archive a file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "wf-path.md"
        test_file.write_text("test")

        entry = archive_workflow(test_file)
        original_path = entry.original_path

        # Find it
        found = find_archive_entry(original_path)
        assert found is not None
        assert found.original_path == original_path

    def test_find_nonexistent_returns_none(self, tmp_path: Path, monkeypatch):
        """Test finding nonexistent entry returns None."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        found = find_archive_entry("nonexistent")
        assert found is None


class TestArchiveRestoreRoundTrip:
    """Tests for complete archive/restore workflows."""

    def test_workflow_archive_restore_roundtrip(self, tmp_path: Path, monkeypatch):
        """Test complete archive and restore cycle for workflow."""
        monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))

        # Create original file
        workflows_dir = get_workflows_root()
        workflows_dir.mkdir(parents=True)
        original_file = workflows_dir / "wf-roundtrip.md"
        original_content = "# Roundtrip Workflow\n\n1. Step one\n2. Step two\n"
        original_file.write_text(original_content)
        original_path_str = str(original_file)

        # Archive
        entry = archive_workflow(original_file, reason="Roundtrip test")
        assert not original_file.exists()

        # Restore
        restored_path = restore_workflow(entry.archive_id)
        assert restored_path.exists()
        assert str(restored_path) == original_path_str
        assert restored_path.read_text() == original_content
