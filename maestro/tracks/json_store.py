"""
JSON-based storage layer for Track/Phase/Task system.

This module implements efficient JSON file-based storage with:
- No duplicate data (relational design using ID references)
- Separate files for better git tracking
- Fast lookups by ID
- Easy modification of individual items
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from maestro.tracks.models import (
    Track, Phase, Task, TrackIndex, DoneArchive, PhaseRef, ParseError
)


class JsonStoreError(Exception):
    """Base exception for JSON storage errors."""
    pass


class JsonStore:
    """Handles JSON-based storage for tracks, phases, and tasks."""

    def __init__(self, base_path: str = "docs/maestro"):
        self.base_path = Path(base_path)
        self.tracks_dir = self.base_path / "tracks"
        self.phases_dir = self.base_path / "phases"
        self.tasks_dir = self.base_path / "tasks"
        self.archive_dir = self.base_path / "archive"
        self.index_file = self.base_path / "index.json"
        self.archive_index_file = self.archive_dir / "index.json"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.tracks_dir.mkdir(exist_ok=True)
        self.phases_dir.mkdir(exist_ok=True)
        self.tasks_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        (self.archive_dir / "tracks").mkdir(exist_ok=True)

    # ========== Task Operations ==========

    def save_task(self, task: Task) -> None:
        """Save a task to its JSON file."""
        task_file = self.tasks_dir / f"{task.task_id}.json"
        data = {
            "task_id": task.task_id,
            "name": task.name,
            "status": task.status,
            "priority": task.priority,
            "estimated_hours": task.estimated_hours,
            "description": task.description,
            "phase_id": task.phase_id,
            "completed": task.completed,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else datetime.now().isoformat(),
            "tags": task.tags,
            "owner": task.owner,
            "dependencies": task.dependencies,
            "subtasks": [st.task_id if isinstance(st, Task) else st for st in task.subtasks]
        }
        task_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def load_task(self, task_id: str) -> Optional[Task]:
        """Load a task from its JSON file."""
        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            return None

        try:
            data = json.loads(task_file.read_text(encoding='utf-8'))
            return Task(
                task_id=data["task_id"],
                name=data["name"],
                status=data.get("status", "todo"),
                priority=data.get("priority", "P2"),
                estimated_hours=data.get("estimated_hours"),
                description=data.get("description", []),
                phase_id=data.get("phase_id"),
                completed=data.get("completed", False),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
                updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
                tags=data.get("tags", []),
                owner=data.get("owner"),
                dependencies=data.get("dependencies", []),
                subtasks=data.get("subtasks", [])
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise JsonStoreError(f"Failed to load task {task_id}: {e}")

    def delete_task(self, task_id: str) -> bool:
        """Delete a task file."""
        task_file = self.tasks_dir / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
            return True
        return False

    # ========== Phase Operations ==========

    def save_phase(self, phase: Phase) -> None:
        """Save a phase to its JSON file."""
        phase_file = self.phases_dir / f"{phase.phase_id}.json"
        data = {
            "phase_id": phase.phase_id,
            "name": phase.name,
            "status": phase.status,
            "completion": phase.completion,
            "description": phase.description,
            "tasks": [task.task_id if isinstance(task, Task) else task for task in phase.tasks],
            "track_id": phase.track_id,
            "priority": phase.priority,
            "created_at": phase.created_at.isoformat() if phase.created_at else None,
            "updated_at": phase.updated_at.isoformat() if phase.updated_at else datetime.now().isoformat(),
            "tags": phase.tags,
            "owner": phase.owner,
            "dependencies": phase.dependencies,
            "order": phase.order
        }
        phase_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

        # Also save all tasks in the phase
        for task in phase.tasks:
            if isinstance(task, Task):
                self.save_task(task)

    def load_phase(self, phase_id: str, load_tasks: bool = False) -> Optional[Phase]:
        """Load a phase from its JSON file, optionally loading full task objects."""
        phase_file = self.phases_dir / f"{phase_id}.json"
        if not phase_file.exists():
            return None

        try:
            data = json.loads(phase_file.read_text(encoding='utf-8'))
            tasks = []
            if load_tasks:
                # Load full task objects
                for task_id in data.get("tasks", []):
                    task = self.load_task(task_id)
                    if task:
                        tasks.append(task)
            else:
                # Just store task IDs as strings
                tasks = data.get("tasks", [])

            return Phase(
                phase_id=data["phase_id"],
                name=data["name"],
                status=data.get("status", "planned"),
                completion=data.get("completion", 0),
                description=data.get("description", []),
                tasks=tasks,
                track_id=data.get("track_id"),
                priority=data.get("priority", 0),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
                updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
                tags=data.get("tags", []),
                owner=data.get("owner"),
                dependencies=data.get("dependencies", []),
                order=data.get("order")
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise JsonStoreError(f"Failed to load phase {phase_id}: {e}")

    def delete_phase(self, phase_id: str, delete_tasks: bool = False) -> bool:
        """Delete a phase file, optionally deleting all its tasks."""
        phase_file = self.phases_dir / f"{phase_id}.json"
        if not phase_file.exists():
            return False

        if delete_tasks:
            # Load phase to get task IDs
            phase = self.load_phase(phase_id, load_tasks=False)
            if phase:
                for task_id in phase.tasks:
                    self.delete_task(task_id)

        phase_file.unlink()
        return True

    # ========== Track Operations ==========

    def save_track(self, track: Track) -> None:
        """Save a track to its JSON file."""
        track_file = self.tracks_dir / f"{track.track_id}.json"
        data = {
            "track_id": track.track_id,
            "name": track.name,
            "status": track.status,
            "completion": track.completion,
            "description": track.description,
            "phases": [phase.phase_id if isinstance(phase, Phase) else phase for phase in track.phases],
            "priority": track.priority,
            "created_at": track.created_at.isoformat() if track.created_at else None,
            "updated_at": track.updated_at.isoformat() if track.updated_at else datetime.now().isoformat(),
            "tags": track.tags,
            "owner": track.owner,
            "is_top_priority": track.is_top_priority
        }
        track_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

        # Also save all phases in the track
        for phase in track.phases:
            if isinstance(phase, Phase):
                self.save_phase(phase)

    def load_track(self, track_id: str, load_phases: bool = False, load_tasks: bool = False) -> Optional[Track]:
        """Load a track from its JSON file, optionally loading full phase/task objects."""
        track_file = self.tracks_dir / f"{track_id}.json"
        if not track_file.exists():
            return None

        try:
            data = json.loads(track_file.read_text(encoding='utf-8'))
            phases = []
            if load_phases:
                # Load full phase objects
                for phase_id in data.get("phases", []):
                    phase = self.load_phase(phase_id, load_tasks=load_tasks)
                    if phase:
                        phases.append(phase)
            else:
                # Just store phase IDs as strings
                phases = data.get("phases", [])

            return Track(
                track_id=data["track_id"],
                name=data["name"],
                status=data.get("status", "planned"),
                completion=data.get("completion", 0),
                description=data.get("description", []),
                phases=phases,
                priority=data.get("priority", 0),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
                updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
                tags=data.get("tags", []),
                owner=data.get("owner"),
                is_top_priority=data.get("is_top_priority", False)
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise JsonStoreError(f"Failed to load track {track_id}: {e}")

    def delete_track(self, track_id: str, delete_phases: bool = False, delete_tasks: bool = False) -> bool:
        """Delete a track file, optionally deleting all its phases and tasks."""
        track_file = self.tracks_dir / f"{track_id}.json"
        if not track_file.exists():
            return False

        if delete_phases or delete_tasks:
            # Load track to get phase IDs
            track = self.load_track(track_id, load_phases=False)
            if track:
                for phase_id in track.phases:
                    self.delete_phase(phase_id, delete_tasks=delete_tasks)

        track_file.unlink()
        return True

    # ========== Index Operations ==========

    def save_index(self, track_index: TrackIndex) -> None:
        """Save the track index."""
        data = {
            "tracks": [track.track_id if isinstance(track, Track) else track for track in track_index.tracks],
            "top_priority_track": track_index.top_priority_track,
            "created_at": track_index.created_at.isoformat() if track_index.created_at else None,
            "updated_at": track_index.updated_at.isoformat() if track_index.updated_at else datetime.now().isoformat()
        }
        self.index_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def load_index(self, load_tracks: bool = False, load_phases: bool = False, load_tasks: bool = False) -> TrackIndex:
        """Load the track index, optionally loading full track/phase/task objects."""
        if not self.index_file.exists():
            return TrackIndex()

        try:
            data = json.loads(self.index_file.read_text(encoding='utf-8'))
            tracks = []
            if load_tracks:
                # Load full track objects
                for track_id in data.get("tracks", []):
                    track = self.load_track(track_id, load_phases=load_phases, load_tasks=load_tasks)
                    if track:
                        tracks.append(track)
            else:
                # Just store track IDs as strings
                tracks = data.get("tracks", [])

            return TrackIndex(
                tracks=tracks,
                top_priority_track=data.get("top_priority_track"),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
                updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise JsonStoreError(f"Failed to load index: {e}")

    # ========== Archive Operations ==========

    def save_archive(self, done_archive: DoneArchive) -> None:
        """Save the done archive index."""
        data = {
            "tracks": [track.track_id if isinstance(track, Track) else track for track in done_archive.tracks],
            "archived_at": done_archive.archived_at.isoformat() if done_archive.archived_at else datetime.now().isoformat()
        }
        self.archive_index_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def load_archive(self, load_tracks: bool = False, load_phases: bool = False, load_tasks: bool = False) -> DoneArchive:
        """Load the done archive index, optionally loading full track/phase/task objects."""
        if not self.archive_index_file.exists():
            return DoneArchive()

        try:
            data = json.loads(self.archive_index_file.read_text(encoding='utf-8'))
            tracks = []
            if load_tracks:
                # Load full track objects from archive
                for track_id in data.get("tracks", []):
                    # Archive tracks are stored in archive/tracks/ directory
                    archive_track_file = self.archive_dir / "tracks" / f"{track_id}.json"
                    if archive_track_file.exists():
                        track_data = json.loads(archive_track_file.read_text(encoding='utf-8'))
                        # Reconstruct track (simplified, can be expanded)
                        track = Track(
                            track_id=track_data["track_id"],
                            name=track_data["name"],
                            status=track_data.get("status", "done"),
                            completion=track_data.get("completion", 100),
                            description=track_data.get("description", []),
                            phases=track_data.get("phases", [])
                        )
                        tracks.append(track)
            else:
                # Just store track IDs as strings
                tracks = data.get("tracks", [])

            return DoneArchive(
                tracks=tracks,
                archived_at=datetime.fromisoformat(data["archived_at"]) if data.get("archived_at") else None
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise JsonStoreError(f"Failed to load archive: {e}")

    def archive_track(self, track_id: str) -> bool:
        """Move a track to the archive."""
        track = self.load_track(track_id, load_phases=True, load_tasks=True)
        if not track:
            return False

        # Save track to archive directory
        archive_track_file = self.archive_dir / "tracks" / f"{track_id}.json"
        track_data = {
            "track_id": track.track_id,
            "name": track.name,
            "status": track.status,
            "completion": track.completion,
            "description": track.description,
            "phases": [phase.phase_id if isinstance(phase, Phase) else phase for phase in track.phases],
            "priority": track.priority,
            "created_at": track.created_at.isoformat() if track.created_at else None,
            "updated_at": datetime.now().isoformat(),
            "tags": track.tags,
            "owner": track.owner,
            "is_top_priority": track.is_top_priority
        }
        archive_track_file.write_text(json.dumps(track_data, indent=2), encoding='utf-8')

        # Update archive index
        archive = self.load_archive()
        if track_id not in archive.tracks:
            archive.tracks.append(track_id)
            self.save_archive(archive)

        # Remove from main index
        index = self.load_index()
        if track_id in index.tracks:
            index.tracks.remove(track_id)
            if index.top_priority_track == track_id:
                index.top_priority_track = None
            self.save_index(index)

        # Delete from main storage
        self.delete_track(track_id, delete_phases=False, delete_tasks=False)

        return True

    # ========== Utility Operations ==========

    def list_all_tracks(self) -> List[str]:
        """List all track IDs in the storage (supports both numbered and slug formats)."""
        return [f.stem for f in self.tracks_dir.glob("*.json")]

    def list_all_phases(self) -> List[str]:
        """List all phase IDs in the storage (supports both numbered and slug formats)."""
        return [f.stem for f in self.phases_dir.glob("*.json")]

    def list_all_tasks(self) -> List[str]:
        """List all task IDs in the storage (supports both numbered and slug formats)."""
        return [f.stem for f in self.tasks_dir.glob("*.json")]
