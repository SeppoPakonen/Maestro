"""Archive and restore operations for workflows."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from maestro.archive.storage import (
    ArchiveEntry,
    ArchiveIndex,
    generate_archive_id,
    get_current_user,
    get_git_head,
    get_timestamp_folder,
    load_archive_index,
    save_archive_index,
)
from maestro.config.paths import get_workflow_archive_index_path, get_workflows_root


class ArchiveError(Exception):
    """Raised when an archive operation fails."""

    pass


class RestoreError(Exception):
    """Raised when a restore operation fails."""

    pass


def archive_workflow(
    path: Path, reason: Optional[str] = None, repo_root: Optional[Path] = None
) -> ArchiveEntry:
    """Archive a workflow file.

    Args:
        path: Path to the workflow file to archive
        reason: Optional reason for archiving
        repo_root: Optional repository root for git context

    Returns:
        ArchiveEntry for the archived item

    Raises:
        ArchiveError: If path doesn't exist, already archived, or archive fails
    """
    # Validate path exists
    if not path.exists():
        raise ArchiveError(f"Path not found: {path}")

    if not path.is_file():
        raise ArchiveError(f"Path is not a file: {path}")

    # Get workflows root to determine relative path
    workflows_root = get_workflows_root()

    # Ensure path is under workflows root
    try:
        relative_path = path.relative_to(workflows_root)
    except ValueError:
        raise ArchiveError(
            f"Path must be under {workflows_root}, got: {path}"
        )

    # Check if already archived (by original path)
    index_path = get_workflow_archive_index_path()
    index = load_archive_index(index_path)

    for entry in index.entries:
        if entry.type == "workflow" and entry.original_path == str(path):
            raise ArchiveError(
                f"Item already archived with ID: {entry.archive_id}\n"
                f"Use 'maestro workflow list --archived' to view archived items."
            )

    # Generate timestamp folder and archived path
    timestamp = get_timestamp_folder()
    archived_path = workflows_root / "archived" / timestamp / relative_path

    # Move file to archive (atomic operation on same filesystem)
    archived_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(path), str(archived_path))
    except Exception as e:
        raise ArchiveError(f"Failed to move file to archive: {e}")

    # Create archive entry
    entry = ArchiveEntry(
        archive_id=generate_archive_id(),
        type="workflow",
        original_path=str(path),
        archived_path=str(archived_path),
        archived_at=datetime.now().isoformat(),
        reason=reason,
        git_head=get_git_head(repo_root),
        user=get_current_user(),
    )

    # Update archive index
    index.entries.append(entry)
    save_archive_index(index, index_path)

    return entry


def restore_workflow(archive_id: str) -> Path:
    """Restore a workflow from archive.

    Args:
        archive_id: Archive ID of the item to restore

    Returns:
        Path where the file was restored

    Raises:
        RestoreError: If archive not found, original path occupied, or restore fails
    """
    # Find archive entry
    entry = find_archive_entry(archive_id)
    if not entry or entry.type != "workflow":
        raise RestoreError(f"Archive not found: {archive_id}")

    # Check if original location is occupied
    original_path = Path(entry.original_path)
    if original_path.exists():
        raise RestoreError(
            f"Cannot restore: original path occupied: {original_path}\n"
            f"Move or rename the existing file first."
        )

    # Check if archived file exists
    archived_path = Path(entry.archived_path)
    if not archived_path.exists():
        raise RestoreError(f"Archived file missing: {archived_path}")

    # Move file back to original location
    original_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(archived_path), str(original_path))
    except Exception as e:
        raise RestoreError(f"Failed to restore file: {e}")

    # Remove from archive index
    index_path = get_workflow_archive_index_path()
    index = load_archive_index(index_path)
    index.entries = [e for e in index.entries if e.archive_id != archive_id]
    save_archive_index(index, index_path)

    return original_path


def list_archived_workflows() -> List[ArchiveEntry]:
    """List archived workflows.

    Returns:
        List of archived workflow entries
    """
    index_path = get_workflow_archive_index_path()
    index = load_archive_index(index_path)

    # Filter for workflow type only
    entries = [e for e in index.entries if e.type == "workflow"]

    return entries


def list_active_workflows() -> List[Path]:
    """List active workflow files by scanning the filesystem.

    Returns:
        List of workflow file paths
    """
    workflows_root = get_workflows_root()

    if not workflows_root.exists():
        return []

    # Scan for workflow files (exclude archived directory)
    workflow_files = []
    for file in workflows_root.rglob("*"):
        if file.is_file() and "archived" not in file.parts:
            workflow_files.append(file)

    return sorted(workflow_files)


def find_archive_entry(id_or_path: str) -> Optional[ArchiveEntry]:
    """Find an archive entry by ID or original path.

    Args:
        id_or_path: Archive ID or original file path

    Returns:
        ArchiveEntry if found, None otherwise
    """
    index_path = get_workflow_archive_index_path()
    index = load_archive_index(index_path)

    # Try to find by archive_id first
    for entry in index.entries:
        if entry.archive_id == id_or_path:
            return entry

    # Try to find by original_path
    for entry in index.entries:
        if entry.original_path == id_or_path:
            return entry

    return None
