"""
Executor for the Project Operations pipeline.

This module implements the executor that can preview and apply operations
to the project JSON storage with dry-run capability.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import re

from .operations import CreateTrack, CreatePhase, CreateTask, MoveTaskToDone, SetContext
from ..tracks.json_store import JsonStore
from ..tracks.models import Track, Phase, Task


@dataclass
class PreviewResult:
    """Result of a dry-run operation preview."""
    changes: List[str]  # Description of changes that would be made
    before_state: str   # State before operations
    after_state: str    # State after operations (if applied)


class ProjectOpsExecutor:
    """Executor for project operations with dry-run and apply functionality."""

    def __init__(self, base_path: str = "docs/maestro"):
        path = Path(base_path)
        if path.suffix == ".md":
            path = path.parent / "maestro"
        elif path.name == "docs":
            path = path / "maestro"
        self.json_store = JsonStore(str(path))

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "item"

    def _resolve_track_id(self, track_ref: str) -> str:
        track_ref_norm = track_ref.strip().lower()
        for track_id in self.json_store.list_all_tracks():
            track = self.json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if track and track.name.strip().lower() == track_ref_norm:
                return track.track_id
        if track_ref in self.json_store.list_all_tracks():
            return track_ref
        raise ValueError(f"Track '{track_ref}' not found")

    def _resolve_phase_id(self, track_id: str, phase_ref: str) -> str:
        phase_ref_norm = phase_ref.strip().lower()
        for phase_id in self.json_store.list_all_phases():
            phase = self.json_store.load_phase(phase_id, load_tasks=False)
            if phase and phase.track_id == track_id and phase.name.strip().lower() == phase_ref_norm:
                return phase.phase_id
        if phase_ref in self.json_store.list_all_phases():
            return phase_ref
        raise ValueError(f"Phase '{phase_ref}' not found in track '{track_id}'")

    def _ensure_unique_id(self, base_id: str, existing_ids: List[str]) -> str:
        if base_id not in existing_ids:
            return base_id
        suffix = 2
        while f"{base_id}-{suffix}" in existing_ids:
            suffix += 1
        return f"{base_id}-{suffix}"

    def _preview_create_track(self, op: CreateTrack) -> List[str]:
        """Preview a CreateTrack operation."""
        track_names = []
        for track_id in self.json_store.list_all_tracks():
            track = self.json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if track:
                track_names.append(track.name.lower())
        if op.title.lower() in track_names:
            raise ValueError(f"Track with title '{op.title}' already exists")
        return [f"Create track: '{op.title}'"]

    def _preview_create_phase(self, op: CreatePhase) -> List[str]:
        """Preview a CreatePhase operation."""
        self._resolve_track_id(op.track)
        return [f"Create phase '{op.title}' in track '{op.track}'"]

    def _preview_create_task(self, op: CreateTask) -> List[str]:
        """Preview a CreateTask operation."""
        track_id = self._resolve_track_id(op.track)
        self._resolve_phase_id(track_id, op.phase)
        return [f"Create task '{op.title}' in phase '{op.phase}' of track '{op.track}'"]

    def _preview_move_task_to_done(self, op: MoveTaskToDone) -> List[str]:
        """Preview a MoveTaskToDone operation."""
        track_id = self._resolve_track_id(op.track)
        self._resolve_phase_id(track_id, op.phase)
        return [f"Move task '{op.task}' in phase '{op.phase}' of track '{op.track}' to done"]

    def _preview_set_context(self, op: SetContext) -> List[str]:
        """Preview a SetContext operation."""
        changes = []
        if op.current_track:
            changes.append(f"Set current track to '{op.current_track}'")
        if op.current_phase:
            changes.append(f"Set current phase to '{op.current_phase}'")
        if op.current_task:
            changes.append(f"Set current task to '{op.current_task}'")
        return changes

    def _apply_create_track(self, op: CreateTrack) -> bool:
        """Apply a CreateTrack operation."""
        track_names = []
        existing_ids = self.json_store.list_all_tracks()
        for track_id in existing_ids:
            track = self.json_store.load_track(track_id, load_phases=False, load_tasks=False)
            if track:
                track_names.append(track.name.lower())
        if op.title.lower() in track_names:
            raise ValueError(f"Track with title '{op.title}' already exists")

        base_id = self._slugify(op.title)
        track_id = self._ensure_unique_id(base_id, existing_ids)
        track = Track(
            track_id=track_id,
            name=op.title,
            status='proposed',
            completion=0,
            description=[],
            phases=[],
            priority=0,
            tags=[],
            owner=None,
            is_top_priority=False
        )
        self.json_store.save_track(track)
        index = self.json_store.load_index()
        if track_id not in index.tracks:
            index.tracks.append(track_id)
            self.json_store.save_index(index)
        return True

    def _apply_create_phase(self, op: CreatePhase) -> bool:
        """Apply a CreatePhase operation."""
        track_id = self._resolve_track_id(op.track)
        existing_ids = self.json_store.list_all_phases()
        base_id = self._slugify(op.title)
        phase_id = self._ensure_unique_id(base_id, existing_ids)
        phase = Phase(
            phase_id=phase_id,
            name=op.title,
            status='proposed',
            completion=0,
            description=[],
            tasks=[],
            track_id=track_id,
            priority='P2',
            tags=[],
            owner=None,
            dependencies=[],
            order=None
        )
        self.json_store.save_phase(phase)

        track = self.json_store.load_track(track_id, load_phases=True, load_tasks=False)
        if not track:
            raise ValueError(f"Track '{track_id}' not found")
        if not track.phases:
            track.phases = []
        if phase_id not in track.phases:
            track.phases.append(phase_id)
            self.json_store.save_track(track)
        return True

    def _apply_create_task(self, op: CreateTask) -> bool:
        """Apply a CreateTask operation."""
        track_id = self._resolve_track_id(op.track)
        phase_id = self._resolve_phase_id(track_id, op.phase)
        phase = self.json_store.load_phase(phase_id, load_tasks=True)
        if not phase:
            raise ValueError(f"Phase '{phase_id}' not found")

        existing_task_ids = [
            task.task_id if hasattr(task, "task_id") else task
            for task in (phase.tasks or [])
        ]
        base_num = 1
        while f"{phase_id}.{base_num}" in existing_task_ids:
            base_num += 1
        task_id = f"{phase_id}.{base_num}"

        task = Task(
            task_id=task_id,
            name=op.title,
            status='planned',
            priority='P2',
            estimated_hours=None,
            description=[],
            phase_id=phase_id,
            completed=False,
            tags=[],
            owner=None,
            dependencies=[],
            subtasks=[]
        )
        self.json_store.save_task(task)

        # Update phase to include this task
        if not phase.tasks:
            phase.tasks = []
        if task_id not in phase.tasks:
            phase.tasks.append(task_id)
            self.json_store.save_phase(phase)

        return True

    def _apply_move_task_to_done(self, op: MoveTaskToDone) -> bool:
        """Apply a MoveTaskToDone operation."""
        track_id = self._resolve_track_id(op.track)
        phase_id = self._resolve_phase_id(track_id, op.phase)
        phase = self.json_store.load_phase(phase_id, load_tasks=True)
        if not phase:
            raise ValueError(f"Phase '{phase_id}' not found")

        task_ref_norm = op.task.strip().lower()
        task_id = None
        for task in phase.tasks or []:
            if hasattr(task, "name") and task.name.strip().lower() == task_ref_norm:
                task_id = task.task_id
                break
            if isinstance(task, str) and task.strip().lower() == task_ref_norm:
                task_id = task
                break
        if not task_id:
            slugged = self._slugify(op.task)
            if slugged in self.json_store.list_all_tasks():
                task_id = slugged
        if not task_id:
            raise ValueError(f"Task '{op.task}' not found in phase '{phase_id}'")

        task_obj = self.json_store.load_task(task_id)
        if not task_obj:
            raise ValueError(f"Task '{task_id}' not found")
        task_obj.status = 'done'
        task_obj.completed = True
        self.json_store.save_task(task_obj)
        return True

    def _apply_set_context(self, op: SetContext) -> bool:
        """Apply a SetContext operation."""
        # Context settings might be stored in a config file or session data
        # For now, we'll just return success
        # In a real implementation, this would update the current context
        return True

    def preview_ops(self, ops: List) -> PreviewResult:
        """Preview what changes would be made by applying operations."""
        # For preview, we'll just return what would change without actually changing anything
        changes = []
        for op in ops:
            if isinstance(op, CreateTrack):
                changes.extend(self._preview_create_track(op))
            elif isinstance(op, CreatePhase):
                changes.extend(self._preview_create_phase(op))
            elif isinstance(op, CreateTask):
                changes.extend(self._preview_create_task(op))
            elif isinstance(op, MoveTaskToDone):
                changes.extend(self._preview_move_task_to_done(op))
            elif isinstance(op, SetContext):
                changes.extend(self._preview_set_context(op))
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")
        
        return PreviewResult(
            changes=changes,
            before_state="",  # Not implemented for preview in this simplified version
            after_state=""    # Not implemented for preview in this simplified version
        )

    def apply_ops(self, ops: List, dry_run: bool = False) -> PreviewResult:
        """
        Apply operations to the project files.
        
        Args:
            ops: List of operations to apply
            dry_run: If True, only preview changes without applying them
            
        Returns:
            PreviewResult with details of changes made
        """
        if dry_run:
            return self.preview_ops(ops)
        
        changes = []
        for op in ops:
            success = False
            if isinstance(op, CreateTrack):
                success = self._apply_create_track(op)
                if success:
                    changes.append(f"Created track: '{op.title}'")
            elif isinstance(op, CreatePhase):
                success = self._apply_create_phase(op)
                if success:
                    changes.append(f"Created phase '{op.title}' in track '{op.track}'")
            elif isinstance(op, CreateTask):
                success = self._apply_create_task(op)
                if success:
                    changes.append(f"Created task '{op.title}' in phase '{op.phase}' of track '{op.track}'")
            elif isinstance(op, MoveTaskToDone):
                success = self._apply_move_task_to_done(op)
                if success:
                    changes.append(f"Moved task '{op.task}' in phase '{op.phase}' of track '{op.track}' to done")
            elif isinstance(op, SetContext):
                success = self._apply_set_context(op)
                if success:
                    context_changes = []
                    if op.current_track:
                        context_changes.append(f"Set current track to '{op.current_track}'")
                    if op.current_phase:
                        context_changes.append(f"Set current phase to '{op.current_phase}'")
                    if op.current_task:
                        context_changes.append(f"Set current task to '{op.current_task}'")
                    changes.extend(context_changes)
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")
            
            if not success:
                raise RuntimeError(f"Failed to apply operation: {op}")

        # Return a preview result showing the changes
        return PreviewResult(
            changes=changes,
            before_state="",  # Not calculated for apply mode in this simplified version
            after_state=""    # Not calculated for apply mode in this simplified version
        )
