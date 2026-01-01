"""WorkGraph → Track/Phase/Task materializer.

This module converts WorkGraph JSON plans into actual maestro work items
(Track/Phase/Task) stored as JSON files using the existing JsonStore.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from maestro.data.workgraph_schema import WorkGraph
from maestro.tracks.models import Track, Phase, Task
from maestro.tracks.json_store import JsonStore


class WorkGraphMaterializer:
    """Converts WorkGraph plans into Track/Phase/Task JSON files."""

    def __init__(self, json_store: Optional[JsonStore] = None):
        """Initialize the materializer.

        Args:
            json_store: Optional JsonStore instance. If not provided, uses default.
        """
        self.json_store = json_store or JsonStore()
        self.created_items: List[str] = []
        self.updated_items: List[str] = []

    def materialize(
        self,
        workgraph: WorkGraph,
        track_name_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Materialize a WorkGraph into Track/Phase/Task files.

        Args:
            workgraph: WorkGraph object to materialize
            track_name_override: Optional override for track name

        Returns:
            Dict with summary: {
                'track_id': str,
                'phases_created': int,
                'phases_updated': int,
                'tasks_created': int,
                'tasks_updated': int,
                'created_items': List[str],
                'updated_items': List[str]
            }
        """
        self.created_items = []
        self.updated_items = []

        # 1. Create or update Track
        track_id = workgraph.track.get('id', workgraph.id)
        track_name = track_name_override or workgraph.track.get('name', workgraph.goal)

        # Check if track exists
        existing_track = self.json_store.load_track(track_id, load_phases=False)

        if existing_track:
            # Update existing track
            track = existing_track
            track.name = track_name
            track.description = [workgraph.goal]
            track.updated_at = datetime.now()
            self.updated_items.append(f"track:{track_id}")
        else:
            # Create new track
            track = Track(
                track_id=track_id,
                name=track_name,
                status="planned",
                completion=0,
                description=[workgraph.goal],
                phases=[],  # Will populate with phase IDs
                priority=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=[workgraph.domain, workgraph.profile],
                owner=None,
                is_top_priority=False
            )
            self.created_items.append(f"track:{track_id}")

        # 2. Create or update Phases
        phase_ids = []
        tasks_created = 0
        tasks_updated = 0

        for wg_phase in workgraph.phases:
            phase_id = wg_phase.id
            phase_name = wg_phase.name

            # Check if phase exists
            existing_phase = self.json_store.load_phase(phase_id, load_tasks=False)

            if existing_phase:
                # Update existing phase
                phase = existing_phase
                phase.name = phase_name
                phase.track_id = track_id
                phase.updated_at = datetime.now()
                self.updated_items.append(f"phase:{phase_id}")
            else:
                # Create new phase
                phase = Phase(
                    phase_id=phase_id,
                    name=phase_name,
                    status="planned",
                    completion=0,
                    description=[],
                    tasks=[],  # Will populate with task IDs
                    track_id=track_id,
                    priority=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=[],
                    owner=None,
                    dependencies=[],
                    order=None
                )
                self.created_items.append(f"phase:{phase_id}")

            phase_ids.append(phase_id)

            # 3. Create or update Tasks for this phase
            task_ids = []

            for wg_task in wg_phase.tasks:
                task_id = wg_task.id
                task_name = wg_task.title

                # Convert DoD to description lines
                description_lines = []
                description_lines.append(f"**Intent**: {wg_task.intent}")
                description_lines.append("")
                description_lines.append("**Definition of Done**:")
                for dod in wg_task.definition_of_done:
                    if dod.kind == "command":
                        description_lines.append(f"- Run: `{dod.cmd}` (expect: {dod.expect})")
                    elif dod.kind == "file":
                        description_lines.append(f"- File: `{dod.path}` (expect: {dod.expect})")

                if wg_task.verification:
                    description_lines.append("")
                    description_lines.append("**Verification**:")
                    for verif in wg_task.verification:
                        if verif.kind == "command":
                            description_lines.append(f"- Run: `{verif.cmd}` (expect: {verif.expect})")
                        elif verif.kind == "file":
                            description_lines.append(f"- File: `{verif.path}` (expect: {verif.expect})")

                if wg_task.inputs:
                    description_lines.append("")
                    description_lines.append(f"**Inputs**: {', '.join(wg_task.inputs)}")

                if wg_task.outputs:
                    description_lines.append("")
                    description_lines.append(f"**Outputs**: {', '.join(wg_task.outputs)}")

                if wg_task.risk:
                    risk_level = wg_task.risk.get('level', 'unknown')
                    risk_notes = wg_task.risk.get('notes', '')
                    description_lines.append("")
                    description_lines.append(f"**Risk**: {risk_level} - {risk_notes}")

                # Check if task exists
                existing_task = self.json_store.load_task(task_id)

                if existing_task:
                    # Update existing task
                    task = existing_task
                    task.name = task_name
                    task.description = description_lines
                    task.phase_id = phase_id
                    task.updated_at = datetime.now()
                    self.updated_items.append(f"task:{task_id}")
                    tasks_updated += 1
                else:
                    # Create new task
                    task = Task(
                        task_id=task_id,
                        name=task_name,
                        status="todo",
                        priority="P2",
                        estimated_hours=None,
                        description=description_lines,
                        phase_id=phase_id,
                        completed=False,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        tags=[],
                        owner=None,
                        dependencies=[],
                        subtasks=[]
                    )
                    self.created_items.append(f"task:{task_id}")
                    tasks_created += 1

                # Save task
                self.json_store.save_task(task)
                task_ids.append(task_id)

            # Update phase with task IDs
            phase.tasks = task_ids
            self.json_store.save_phase(phase)

        # Update track with phase IDs
        track.phases = phase_ids
        self.json_store.save_track(track)

        # Update index
        index = self.json_store.load_index(load_tracks=False)
        if track_id not in index.tracks:
            index.tracks.append(track_id)
            index.updated_at = datetime.now()
            self.json_store.save_index(index)

        # Return summary
        return {
            'track_id': track_id,
            'phases_created': len([p for p in self.created_items if p.startswith('phase:')]),
            'phases_updated': len([p for p in self.updated_items if p.startswith('phase:')]),
            'tasks_created': tasks_created,
            'tasks_updated': tasks_updated,
            'created_items': self.created_items,
            'updated_items': self.updated_items
        }
