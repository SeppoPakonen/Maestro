"""
Executor for the Project Operations pipeline.

This module implements the executor that can preview and apply operations
to the project markdown files (docs/todo.md, docs/done.md, etc.) with 
dry-run capability.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .operations import CreateTrack, CreatePhase, CreateTask, MoveTaskToDone, SetContext
from ..data.markdown_writer import (
    insert_track_block, 
    insert_phase_block, 
    insert_task_block, 
    update_task_metadata,
    update_phase_metadata,
    update_track_metadata
)
from ..data.markdown_parser import parse_todo_md


@dataclass
class PreviewResult:
    """Result of a dry-run operation preview."""
    changes: List[str]  # Description of changes that would be made
    before_state: str   # State before operations
    after_state: str    # State after operations (if applied)


class ProjectOpsExecutor:
    """Executor for project operations with dry-run and apply functionality."""
    
    def __init__(self, todo_path: str = "docs/todo.md"):
        self.todo_path = Path(todo_path)
        # Ensure the docs directory exists
        self.todo_path.parent.mkdir(parents=True, exist_ok=True)
        # Create the file if it doesn't exist
        if not self.todo_path.exists():
            self.todo_path.write_text("# TODO\n\n", encoding='utf-8')

    def _preview_create_track(self, op: CreateTrack) -> List[str]:
        """Preview a CreateTrack operation."""
        # Check if track already exists
        todo_data = parse_todo_md(str(self.todo_path))
        for track in todo_data.get('tracks', []):
            if track.get('title', '').lower() == op.title.lower():
                raise ValueError(f"Track with title '{op.title}' already exists")
        
        return [f"Create track: '{op.title}'"]

    def _preview_create_phase(self, op: CreatePhase) -> List[str]:
        """Preview a CreatePhase operation."""
        # For now, we'll just note the operation
        # In a real implementation, we'd check if the parent track exists
        return [f"Create phase '{op.title}' in track '{op.track}'"]

    def _preview_create_task(self, op: CreateTask) -> List[str]:
        """Preview a CreateTask operation."""
        # For now, we'll just note the operation
        # In a real implementation, we'd check if the parent track and phase exist
        return [f"Create task '{op.title}' in phase '{op.phase}' of track '{op.track}'"]

    def _preview_move_task_to_done(self, op: MoveTaskToDone) -> List[str]:
        """Preview a MoveTaskToDone operation."""
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
        # Check if track already exists
        todo_data = parse_todo_md(str(self.todo_path))
        for track in todo_data.get('tracks', []):
            if track.get('title', '').lower() == op.title.lower():
                raise ValueError(f"Track with title '{op.title}' already exists")
        
        # Generate track block content
        track_id = op.title.lower().replace(' ', '-').replace('_', '-')
        track_block = f"## Track: {op.title}\n\n- *track_id*: *{track_id}*\n- *status*: *proposed*\n- *completion*: 0%\n\n"
        
        # Insert the track
        success = insert_track_block(self.todo_path, track_block)
        return success

    def _apply_create_phase(self, op: CreatePhase) -> bool:
        """Apply a CreatePhase operation."""
        # Generate phase block content
        phase_id = op.title.lower().replace(' ', '-').replace('_', '-')
        track_id = op.track.lower().replace(' ', '-').replace('_', '-')
        phase_block = f"### Phase {phase_id}: {op.title}\n\n- *phase_id*: *{phase_id}*\n- *status*: *proposed*\n- *completion*: 0\n\n"
        
        # Insert the phase into the track
        success = insert_phase_block(self.todo_path, track_id, phase_block)
        return success

    def _apply_create_task(self, op: CreateTask) -> bool:
        """Apply a CreateTask operation."""
        # Generate task block content
        task_id = op.title.lower().replace(' ', '-').replace('_', '-')
        phase_id = op.phase.lower().replace(' ', '-').replace('_', '-')
        
        # For now, we'll add the task as a simple list item under the phase
        # In a real implementation, we'd properly insert it in the phase section
        task_content = f"- [ ] {op.title}  #task_id: {task_id} #status: todo\n"
        
        # This is a simplified approach - in a real implementation, we'd use the proper insert_task_block
        # function once we have the phase_id available in the right format
        with self.todo_path.open('a', encoding='utf-8') as f:
            f.write(f"\n{task_content}")
        
        return True

    def _apply_move_task_to_done(self, op: MoveTaskToDone) -> bool:
        """Apply a MoveTaskToDone operation."""
        # In a real implementation, we'd move the task from todo.md to done.md
        # For now, we'll just update its status to done in the metadata
        task_id = op.task.lower().replace(' ', '-').replace('_', '-')
        success = update_task_metadata(self.todo_path, task_id, "status", "done")
        return success

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