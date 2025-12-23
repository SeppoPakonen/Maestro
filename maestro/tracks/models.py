"""
Data models for Track/Phase/Task system.

These models define the structure of the track/phase/task data
that will be stored in the docs markdown files.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Task:
    """Represents a single task within a phase."""
    task_id: str
    name: str
    status: str = "todo"  # todo, in_progress, done, blocked
    priority: str = "P2"  # P1, P2, P3, P4
    estimated_hours: Optional[int] = None
    description: List[str] = field(default_factory=list)
    phase_id: Optional[str] = None
    completed: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    subtasks: List['Task'] = field(default_factory=list)


@dataclass
class Phase:
    """Represents a phase within a track."""
    phase_id: str
    name: str
    status: str = "planned"  # planned, in_progress, done, proposed
    completion: int = 0  # 0-100
    description: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    track_id: Optional[str] = None
    priority: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    order: Optional[int] = None


@dataclass
class Track:
    """Represents a track containing multiple phases."""
    track_id: str
    name: str
    status: str = "planned"  # planned, in_progress, done, proposed
    completion: int = 0  # 0-100
    description: List[str] = field(default_factory=list)
    phases: List[Phase] = field(default_factory=list)
    priority: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    is_top_priority: bool = False  # Marks this track as top priority


@dataclass
class PhaseRef:
    """Reference to a phase with status and completion."""
    phase_id: str
    name: str
    status: str
    completion: int = 0
    order: Optional[int] = None


@dataclass
class TrackIndex:
    """Index of tracks with phase references."""
    tracks: List[Track] = field(default_factory=list)
    top_priority_track: Optional[str] = None  # ID of top priority track
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DoneArchive:
    """Archive of completed tracks and phases."""
    tracks: List[Track] = field(default_factory=list)
    archived_at: Optional[datetime] = None


@dataclass
class ParseError:
    """Represents a parsing error with location and details."""
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_message: str = ""
    hint: str = ""

    def __str__(self):
        location = f"{self.file_path}"
        if self.line_number is not None:
            location += f":{self.line_number}"
            if self.column_number is not None:
                location += f":{self.column_number}"
        
        return f"ParseError at {location}: {self.error_message}. {self.hint}"