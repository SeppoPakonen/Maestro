"""Core storage layer for archive lifecycle management."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ArchiveEntry:
    """Represents a single archived item with full metadata."""

    archive_id: str
    type: str  # "runbook_markdown", "runbook_json", "workflow"
    original_path: str
    archived_path: str
    archived_at: str
    reason: Optional[str] = None
    git_head: Optional[str] = None
    user: Optional[str] = None
    runbook_id: Optional[str] = None  # For JSON runbooks only

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for JSON serialization."""
        data = {
            "archive_id": self.archive_id,
            "type": self.type,
            "original_path": self.original_path,
            "archived_path": self.archived_path,
            "archived_at": self.archived_at,
        }
        if self.reason is not None:
            data["reason"] = self.reason
        if self.git_head is not None:
            data["git_head"] = self.git_head
        if self.user is not None:
            data["user"] = self.user
        if self.runbook_id is not None:
            data["runbook_id"] = self.runbook_id
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ArchiveEntry:
        """Create entry from dictionary."""
        return ArchiveEntry(
            archive_id=data["archive_id"],
            type=data["type"],
            original_path=data["original_path"],
            archived_path=data["archived_path"],
            archived_at=data["archived_at"],
            reason=data.get("reason"),
            git_head=data.get("git_head"),
            user=data.get("user"),
            runbook_id=data.get("runbook_id"),
        )


@dataclass
class ArchiveIndex:
    """Represents an archive index containing all archived items."""

    entries: List[ArchiveEntry] = field(default_factory=list)
    last_updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert index to dictionary for JSON serialization."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "last_updated": self.last_updated or datetime.now().isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ArchiveIndex:
        """Create index from dictionary."""
        entries = [ArchiveEntry.from_dict(e) for e in data.get("entries", [])]
        return ArchiveIndex(
            entries=entries,
            last_updated=data.get("last_updated"),
        )


def generate_archive_id() -> str:
    """Generate a unique archive ID using UUID4."""
    return str(uuid.uuid4())


def get_timestamp_folder() -> str:
    """Get current timestamp in YYYYMMDD format for archive folder naming."""
    return datetime.now().strftime("%Y%m%d")


def load_archive_index(index_path: Path) -> ArchiveIndex:
    """Load archive index from JSON file.

    Args:
        index_path: Path to the archive index JSON file

    Returns:
        ArchiveIndex instance, empty if file doesn't exist
    """
    if not index_path.exists():
        return ArchiveIndex()

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ArchiveIndex.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        # If index is corrupted, return empty index
        # TODO: Consider logging warning here
        return ArchiveIndex()


def save_archive_index(index: ArchiveIndex, index_path: Path) -> None:
    """Save archive index to JSON file using atomic write.

    Args:
        index: ArchiveIndex instance to save
        index_path: Path to the archive index JSON file
    """
    index.last_updated = datetime.now().isoformat()
    data = index.to_dict()
    _atomic_write_json(index_path, data)


def get_git_head(repo_root: Optional[Path] = None) -> Optional[str]:
    """Get current git HEAD commit hash if in a git repository.

    Args:
        repo_root: Optional repository root path, defaults to cwd

    Returns:
        Git HEAD hash or None if not in a git repo or git unavailable
    """
    try:
        cwd = str(repo_root) if repo_root else None
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def get_current_user() -> Optional[str]:
    """Get current user from environment.

    Returns:
        Username from USER or USERNAME env var, or None
    """
    return os.environ.get("USER") or os.environ.get("USERNAME")


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON data to file atomically using temp file + rename.

    This ensures that the file is never in a partially-written state,
    even if the process is interrupted. Uses fsync for durability.

    Args:
        path: Target file path
        data: Dictionary to write as JSON
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, dir=path.parent, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, path)
