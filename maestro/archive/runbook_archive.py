"""Archive and restore operations for runbooks (markdown and JSON)."""
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
from maestro.config.paths import get_runbook_archive_index_path, get_runbook_examples_root


class ArchiveError(Exception):
    """Raised when an archive operation fails."""

    pass


class RestoreError(Exception):
    """Raised when a restore operation fails."""

    pass


def archive_runbook_markdown(
    path: Path, reason: Optional[str] = None, repo_root: Optional[Path] = None
) -> ArchiveEntry:
    """Archive a markdown runbook example file.

    Args:
        path: Path to the markdown runbook file to archive
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

    # Get examples root to determine relative path
    examples_root = get_runbook_examples_root()

    # Ensure path is under examples root
    try:
        relative_path = path.relative_to(examples_root)
    except ValueError:
        raise ArchiveError(
            f"Path must be under {examples_root}, got: {path}"
        )

    # Check if already archived (by original path)
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)

    for entry in index.entries:
        if entry.type == "runbook_markdown" and entry.original_path == str(path):
            raise ArchiveError(
                f"Item already archived with ID: {entry.archive_id}\n"
                f"Use 'maestro runbook list --archived' to view archived items."
            )

    # Generate timestamp folder and archived path
    timestamp = get_timestamp_folder()
    archived_path = examples_root / "archived" / timestamp / relative_path

    # Move file to archive (atomic operation on same filesystem)
    archived_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(path), str(archived_path))
    except Exception as e:
        raise ArchiveError(f"Failed to move file to archive: {e}")

    # Create archive entry
    entry = ArchiveEntry(
        archive_id=generate_archive_id(),
        type="runbook_markdown",
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


def archive_runbook_json(
    runbook_id: str, reason: Optional[str] = None, repo_root: Optional[Path] = None
) -> ArchiveEntry:
    """Archive a JSON runbook from the runbook store.

    Args:
        runbook_id: ID of the JSON runbook to archive
        reason: Optional reason for archiving
        repo_root: Optional repository root for git context

    Returns:
        ArchiveEntry for the archived item

    Raises:
        ArchiveError: If runbook doesn't exist, already archived, or archive fails
    """
    from maestro.config.paths import get_docs_root

    # Construct paths
    docs_root = get_docs_root()
    runbook_items_path = docs_root / "docs" / "maestro" / "runbooks" / "items"
    runbook_archive_path = docs_root / "docs" / "maestro" / "runbooks" / "archive" / "items"

    source_path = runbook_items_path / f"{runbook_id}.json"
    dest_path = runbook_archive_path / f"{runbook_id}.json"

    # Validate source exists
    if not source_path.exists():
        raise ArchiveError(f"Runbook not found: {runbook_id}")

    # Check if already archived
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)

    for entry in index.entries:
        if entry.type == "runbook_json" and entry.runbook_id == runbook_id:
            raise ArchiveError(
                f"Runbook already archived with ID: {entry.archive_id}\n"
                f"Use 'maestro runbook list --archived' to view archived items."
            )

    # Move file to archive
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source_path), str(dest_path))
    except Exception as e:
        raise ArchiveError(f"Failed to move runbook to archive: {e}")

    # Remove from main index (if it exists)
    main_index_path = docs_root / "docs" / "maestro" / "runbooks" / "index.json"
    if main_index_path.exists():
        try:
            import json

            with open(main_index_path, "r") as f:
                main_index = json.load(f)

            # Remove runbook from main index if present
            if isinstance(main_index, list):
                main_index = [item for item in main_index if item.get("id") != runbook_id]
            elif isinstance(main_index, dict) and "runbooks" in main_index:
                main_index["runbooks"] = [
                    item for item in main_index["runbooks"] if item.get("id") != runbook_id
                ]

            with open(main_index_path, "w") as f:
                json.dump(main_index, f, indent=2)
        except Exception:
            # If index update fails, continue - archive is still successful
            pass

    # Create archive entry
    entry = ArchiveEntry(
        archive_id=generate_archive_id(),
        type="runbook_json",
        original_path=str(source_path),
        archived_path=str(dest_path),
        archived_at=datetime.now().isoformat(),
        reason=reason,
        git_head=get_git_head(repo_root),
        user=get_current_user(),
        runbook_id=runbook_id,
    )

    # Update archive index
    index.entries.append(entry)
    save_archive_index(index, index_path)

    return entry


def restore_runbook_markdown(archive_id: str) -> Path:
    """Restore a markdown runbook from archive.

    Args:
        archive_id: Archive ID of the item to restore

    Returns:
        Path where the file was restored

    Raises:
        RestoreError: If archive not found, original path occupied, or restore fails
    """
    # Find archive entry
    entry = find_archive_entry(archive_id)
    if not entry or entry.type != "runbook_markdown":
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
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)
    index.entries = [e for e in index.entries if e.archive_id != archive_id]
    save_archive_index(index, index_path)

    return original_path


def restore_runbook_json(archive_id: str) -> str:
    """Restore a JSON runbook from archive.

    Args:
        archive_id: Archive ID of the item to restore

    Returns:
        Runbook ID that was restored

    Raises:
        RestoreError: If archive not found, original path occupied, or restore fails
    """
    # Find archive entry
    entry = find_archive_entry(archive_id)
    if not entry or entry.type != "runbook_json":
        raise RestoreError(f"Archive not found: {archive_id}")

    if not entry.runbook_id:
        raise RestoreError(f"Archive entry missing runbook_id: {archive_id}")

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

    # Add back to main index (if it exists)
    from maestro.config.paths import get_docs_root

    docs_root = get_docs_root()
    main_index_path = docs_root / "docs" / "maestro" / "runbooks" / "index.json"
    if main_index_path.exists():
        try:
            import json

            with open(main_index_path, "r") as f:
                main_index = json.load(f)

            # Load runbook data to add to index
            with open(original_path, "r") as f:
                runbook_data = json.load(f)

            # Add to main index
            if isinstance(main_index, list):
                if runbook_data not in main_index:
                    main_index.append(runbook_data)
            elif isinstance(main_index, dict) and "runbooks" in main_index:
                if runbook_data not in main_index["runbooks"]:
                    main_index["runbooks"].append(runbook_data)

            with open(main_index_path, "w") as f:
                json.dump(main_index, f, indent=2)
        except Exception:
            # If index update fails, continue - restore is still successful
            pass

    # Remove from archive index
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)
    index.entries = [e for e in index.entries if e.archive_id != archive_id]
    save_archive_index(index, index_path)

    return entry.runbook_id


def list_archived_runbooks(type_filter: Optional[str] = None) -> List[ArchiveEntry]:
    """List archived runbooks.

    Args:
        type_filter: Optional filter ("markdown", "json", or None for all)

    Returns:
        List of archived runbook entries
    """
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)

    entries = index.entries

    # Apply type filter
    if type_filter == "markdown":
        entries = [e for e in entries if e.type == "runbook_markdown"]
    elif type_filter == "json":
        entries = [e for e in entries if e.type == "runbook_json"]

    return entries


def find_archive_entry(id_or_path: str) -> Optional[ArchiveEntry]:
    """Find an archive entry by ID or original path.

    Args:
        id_or_path: Archive ID or original file path

    Returns:
        ArchiveEntry if found, None otherwise
    """
    index_path = get_runbook_archive_index_path()
    index = load_archive_index(index_path)

    # Try to find by archive_id first
    for entry in index.entries:
        if entry.archive_id == id_or_path:
            return entry

    # Try to find by original_path
    for entry in index.entries:
        if entry.original_path == id_or_path:
            return entry

    # Try to find by runbook_id (for JSON runbooks)
    for entry in index.entries:
        if entry.runbook_id == id_or_path:
            return entry

    return None
