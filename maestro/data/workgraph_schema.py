"""WorkGraph schema with strict validation for decompose-to-workflow loop.

This module defines the core data structures for WorkGraph plans, which decompose
freeform requests into structured tracks/phases/tasks with verifiable Definitions-of-Done (DoD).

Schema Version: v1
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DefinitionOfDone:
    """A verifiable condition that must be satisfied for task completion.

    Each DoD must be machine-checkable via either:
    - Command execution (exit code check)
    - File existence/contents check
    """
    kind: str  # "command" or "file"
    cmd: Optional[str] = None
    path: Optional[str] = None
    expect: str = "exit 0"  # or "contains X", "exists", etc.

    def __post_init__(self):
        """Validate DoD immediately after construction."""
        if self.kind not in ["command", "file"]:
            raise ValueError(f"DoD kind must be 'command' or 'file', got '{self.kind}'")

        if self.kind == "command" and not self.cmd:
            raise ValueError("Command DoD missing required 'cmd' field")

        if self.kind == "file" and not self.path:
            raise ValueError("File DoD missing required 'path' field")


@dataclass
class Task:
    """A single executable task within a phase.

    Tasks must have at least one Definition-of-Done (DoD) to prevent "meta-runbook" tasks
    that are not machine-verifiable.
    """
    id: str
    title: str
    intent: str
    definition_of_done: List[DefinitionOfDone]
    verification: List[DefinitionOfDone] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    risk: Dict[str, Any] = field(default_factory=dict)
    safe_to_execute: bool = False  # Default: require explicit opt-in for execution

    def __post_init__(self):
        """Validate task immediately after construction.

        HARD GATE: No meta-runbook tasks allowed. Every task must have at least one
        executable Definition-of-Done.
        """
        if not self.definition_of_done:
            raise ValueError(
                f"Task '{self.title}' missing definition_of_done. "
                f"All tasks must have at least one machine-checkable DoD."
            )

        # Validate each DoD (validation happens in DefinitionOfDone.__post_init__)
        for i, dod in enumerate(self.definition_of_done):
            # Trigger validation by accessing the object
            # (already validated in DefinitionOfDone.__post_init__, but we check here for clarity)
            if not isinstance(dod, DefinitionOfDone):
                raise ValueError(f"definition_of_done[{i}] must be a DefinitionOfDone instance")

        # Validate verification items
        for i, verif in enumerate(self.verification):
            if not isinstance(verif, DefinitionOfDone):
                raise ValueError(f"verification[{i}] must be a DefinitionOfDone instance")


@dataclass
class Phase:
    """A collection of related tasks within a track."""
    id: str
    name: str
    tasks: List[Task] = field(default_factory=list)

    def __post_init__(self):
        """Validate phase after construction."""
        if not self.name or not self.name.strip():
            raise ValueError("Phase name cannot be empty")


@dataclass
class WorkGraph:
    """A complete WorkGraph plan decomposing a freeform request into structured work.

    A WorkGraph contains:
    - Repo discovery evidence
    - A single track with multiple phases
    - Phases containing tasks with verifiable DoDs
    - Stop conditions for handling blockers
    """
    schema_version: str = "v1"
    id: str = ""
    domain: str = "general"
    profile: str = "default"
    goal: str = ""
    repo_discovery: Dict[str, Any] = field(default_factory=dict)
    track: Dict[str, str] = field(default_factory=dict)
    phases: List[Phase] = field(default_factory=list)
    stop_conditions: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate WorkGraph and generate deterministic ID if not provided."""
        # Generate deterministic ID if not provided
        if not self.id:
            timestamp = datetime.now().strftime('%Y%m%d')
            goal_hash = hashlib.sha256(self.goal.encode()).hexdigest()[:8]
            self.id = f"wg-{timestamp}-{goal_hash}"

        # Validate schema version
        if self.schema_version != "v1":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")

        # Validate goal is non-empty
        if not self.goal or not self.goal.strip():
            raise ValueError("WorkGraph goal cannot be empty")

        # Validate all phases and tasks (validation happens in Phase/Task.__post_init__)
        for phase in self.phases:
            if not isinstance(phase, Phase):
                raise ValueError(f"All phases must be Phase instances")

    def to_dict(self) -> Dict[str, Any]:
        """Convert WorkGraph to dictionary for JSON serialization."""
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "domain": self.domain,
            "profile": self.profile,
            "goal": self.goal,
            "repo_discovery": self.repo_discovery,
            "track": self.track,
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "intent": t.intent,
                            "definition_of_done": [
                                {
                                    "kind": d.kind,
                                    "cmd": d.cmd,
                                    "path": d.path,
                                    "expect": d.expect
                                }
                                for d in t.definition_of_done
                            ],
                            "verification": [
                                {
                                    "kind": v.kind,
                                    "cmd": v.cmd,
                                    "path": v.path,
                                    "expect": v.expect
                                }
                                for v in t.verification
                            ],
                            "inputs": t.inputs,
                            "outputs": t.outputs,
                            "risk": t.risk
                        }
                        for t in p.tasks
                    ]
                }
                for p in self.phases
            ],
            "stop_conditions": self.stop_conditions
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WorkGraph':
        """Create WorkGraph from dictionary (deserialization).

        Args:
            data: Dictionary representing a WorkGraph (typically from JSON)

        Returns:
            WorkGraph instance with full validation

        Raises:
            ValueError: If validation fails (missing DoDs, invalid structure, etc.)
        """
        # Parse phases
        phases = []
        for p_data in data.get("phases", []):
            tasks = []
            for t_data in p_data.get("tasks", []):
                # Parse definition_of_done
                dods = [
                    DefinitionOfDone(
                        kind=d["kind"],
                        cmd=d.get("cmd"),
                        path=d.get("path"),
                        expect=d.get("expect", "exit 0")
                    )
                    for d in t_data.get("definition_of_done", [])
                ]

                # Parse verification
                verifs = [
                    DefinitionOfDone(
                        kind=v["kind"],
                        cmd=v.get("cmd"),
                        path=v.get("path"),
                        expect=v.get("expect", "exit 0")
                    )
                    for v in t_data.get("verification", [])
                ]

                # Create task (validation happens in Task.__post_init__)
                task = Task(
                    id=t_data["id"],
                    title=t_data["title"],
                    intent=t_data["intent"],
                    definition_of_done=dods,
                    verification=verifs,
                    inputs=t_data.get("inputs", []),
                    outputs=t_data.get("outputs", []),
                    risk=t_data.get("risk", {})
                )
                tasks.append(task)

            # Create phase (validation happens in Phase.__post_init__)
            phase = Phase(
                id=p_data["id"],
                name=p_data["name"],
                tasks=tasks
            )
            phases.append(phase)

        # Create WorkGraph (validation happens in WorkGraph.__post_init__)
        return WorkGraph(
            schema_version=data.get("schema_version", "v1"),
            id=data.get("id", ""),
            domain=data.get("domain", "general"),
            profile=data.get("profile", "default"),
            goal=data.get("goal", ""),
            repo_discovery=data.get("repo_discovery", {}),
            track=data.get("track", {}),
            phases=phases,
            stop_conditions=data.get("stop_conditions", [])
        )
