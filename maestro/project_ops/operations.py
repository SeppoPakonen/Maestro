"""
Typed operations for the Project Operations pipeline.

This module defines internal operation objects that represent
actions to be performed on tracks, phases, and tasks.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateTrack:
    """Operation to create a new track."""
    title: str


@dataclass
class CreatePhase:
    """Operation to create a new phase."""
    track: str
    title: str


@dataclass
class CreateTask:
    """Operation to create a new task."""
    track: str
    phase: str
    title: str


@dataclass
class MoveTaskToDone:
    """Operation to move a task to done."""
    track: str
    phase: str
    task: str


@dataclass
class SetContext:
    """Operation to set the current context."""
    current_track: Optional[str] = None
    current_phase: Optional[str] = None
    current_task: Optional[str] = None