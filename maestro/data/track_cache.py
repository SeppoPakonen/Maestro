"""
Persistent cache for Maestro track/phase/task JSON data.

Caches the deserialized dataclasses along with file metadata so that repeated
CLI invocations can short-circuit disk IO as long as the underlying files do
not change.
"""

from __future__ import annotations

import hashlib
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track, Phase, Task

_VALIDATE_CACHE = False


def set_cache_validation(enabled: bool) -> None:
    """Enable or disable cache validation before reading stored snapshots."""
    global _VALIDATE_CACHE
    _VALIDATE_CACHE = enabled


def cache_validation_enabled() -> bool:
    """Return whether cache validation is enabled."""
    return _VALIDATE_CACHE


@dataclass(frozen=True)
class TrackCacheSnapshot:
    """Holds cached track, phase, and task dataclasses."""

    track_order: List[str]
    tracks: Dict[str, Track]
    phases: Dict[str, Phase]
    tasks_by_phase: Dict[str, List[Task]]


@dataclass(frozen=True)
class CacheLoadResult:
    """Outcome of loading from the persistent track cache."""

    snapshot: TrackCacheSnapshot
    cached: bool
    reason: Optional[str] = None


class TrackDataCache:
    """Persistent cache stored under ~/.maestro/track_cache/<repo_hash>/."""

    CACHE_VERSION = 1

    def __init__(self, repo_root: Path, cache_root: Optional[Path] = None):
        self.repo_root = repo_root.resolve()
        self.cache_root = cache_root or (Path.home() / ".maestro" / "track_cache")
        repo_hash = hashlib.sha256(str(self.repo_root).encode("utf-8")).hexdigest()
        self.scope_dir = self.cache_root / repo_hash
        self.meta_file = self.scope_dir / "meta.bin"
        self.data_file = self.scope_dir / "data.bin"
        self.scope_dir.mkdir(parents=True, exist_ok=True)

    def load_or_rebuild(self, json_store: JsonStore, validate: bool = False) -> CacheLoadResult:
        """Load the snapshot if cache is fresh; otherwise rebuild it."""
        if not self.data_file.exists() or not self.meta_file.exists():
            snapshot = self._build_and_persist(json_store)
            return CacheLoadResult(snapshot=snapshot, cached=False, reason="cache rebuild")

        if validate:
            snapshot, reason = self._load_snapshot(json_store)
            if snapshot is not None:
                return CacheLoadResult(snapshot=snapshot, cached=True)
            snapshot = self._build_and_persist(json_store)
            return CacheLoadResult(snapshot=snapshot, cached=False, reason=reason or "cache rebuild")

        try:
            payload = pickle.loads(self.data_file.read_bytes())
            return CacheLoadResult(snapshot=payload, cached=True)
        except Exception:
            snapshot = self._build_and_persist(json_store)
            return CacheLoadResult(snapshot=snapshot, cached=False, reason="invalid cache payload")

    def invalidate(self) -> bool:
        """Remove cached files for this repo."""
        if not self.scope_dir.exists():
            return False
        shutil.rmtree(self.scope_dir)
        return True

    def _load_snapshot(
        self, json_store: JsonStore
    ) -> Tuple[Optional[TrackCacheSnapshot], Optional[str]]:
        """Load cache only if metadata agrees with the repo files."""
        if not self.meta_file.exists() or not self.data_file.exists():
            return None, "cache files missing"

        try:
            metadata = pickle.loads(self.meta_file.read_bytes())
        except Exception:
            return None, "failed to read cache metadata"

        if metadata.get("version") != self.CACHE_VERSION:
            return None, "cache version mismatch"
        if metadata.get("repo_path") != str(self.repo_root):
            return None, "repo root mismatch"

        current_paths = self._monitored_paths(json_store)
        stored_paths = set(metadata.get("files", {}).keys())
        current_keys = {str(p.resolve()) for p in current_paths}
        if current_keys != stored_paths:
            return None, "cache file list changed"

        for path in current_paths:
            key = str(path.resolve())
            signature = metadata["files"].get(key)
            if not signature:
                return None, "cache metadata missing entry"
            stat = path.stat()
            if (
                stat.st_size != signature.get("size")
                or stat.st_mtime_ns != signature.get("mtime")
            ):
                return None, "watched file metadata changed"

        try:
            payload = pickle.loads(self.data_file.read_bytes())
            return payload, None
        except Exception:
            return None, "failed to deserialize cache payload"

    def _build_and_persist(self, json_store: JsonStore) -> TrackCacheSnapshot:
        """Rebuild the cache by reading all JSON files and persisting metadata."""
        track_ids = sorted(json_store.list_all_tracks())
        tracks: Dict[str, Track] = {}
        phases: Dict[str, Phase] = {}
        tasks_by_phase: Dict[str, List[Task]] = {}
        file_meta: Dict[str, Dict[str, int]] = {}

        for track_id in track_ids:
            track = json_store.load_track(track_id, load_phases=False, load_tasks=False)
            track_file = json_store.tracks_dir / f"{track_id}.json"
            if track:
                tracks[track_id] = track
                if track_file.exists():
                    file_meta[str(track_file.resolve())] = self._file_signature(track_file)

        for phase_id in sorted(json_store.list_all_phases()):
            phase = json_store.load_phase(phase_id, load_tasks=False)
            phase_file = json_store.phases_dir / f"{phase_id}.json"
            if phase:
                phases[phase_id] = phase
                if phase_file.exists():
                    file_meta[str(phase_file.resolve())] = self._file_signature(phase_file)

        for task_id in sorted(json_store.list_all_tasks()):
            task = json_store.load_task(task_id)
            task_file = json_store.tasks_dir / f"{task_id}.json"
            if task:
                tasks_by_phase.setdefault(task.phase_id or "", []).append(task)
                if task_file.exists():
                    file_meta[str(task_file.resolve())] = self._file_signature(task_file)

        snapshot = TrackCacheSnapshot(track_ids, tracks, phases, tasks_by_phase)
        self.data_file.write_bytes(pickle.dumps(snapshot, protocol=pickle.HIGHEST_PROTOCOL))
        metadata = {
            "version": self.CACHE_VERSION,
            "repo_path": str(self.repo_root),
            "files": file_meta,
        }
        self.meta_file.write_bytes(pickle.dumps(metadata, protocol=pickle.HIGHEST_PROTOCOL))
        return snapshot

    def _monitored_paths(self, json_store: JsonStore) -> List[Path]:
        """List the files that are part of the cache footprint."""
        return [
            *sorted(json_store.tracks_dir.glob("*.json")),
            *sorted(json_store.phases_dir.glob("*.json")),
            *sorted(json_store.tasks_dir.glob("*.json")),
        ]

    @staticmethod
    def _file_signature(path: Path) -> Dict[str, int]:
        """Record size and mtime for the given file."""
        stat = path.stat()
        return {
            "size": stat.st_size,
            "mtime": stat.st_mtime_ns,
        }
