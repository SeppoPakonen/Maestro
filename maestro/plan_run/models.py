"""Data models for WorkGraph run records.

Run records track execution of WorkGraph plans with:
- Deterministic run IDs
- Append-only event log (JSONL)
- Resume capability
- Graph change detection
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RunEvent:
    """A single event in the run record event log.

    Events are stored as JSONL records (one JSON object per line).
    """
    event_type: str  # RUN_STARTED, TASK_PLANNED, TASK_STARTED, TASK_RESULT, RUN_SUMMARY, etc.
    timestamp: str  # ISO 8601 timestamp
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RunEvent':
        """Create RunEvent from dictionary."""
        return RunEvent(
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            data=data.get("data", {})
        )


@dataclass
class RunMeta:
    """Metadata for a WorkGraph run.

    Stored in runs/<RUN_ID>/meta.json.
    """
    run_id: str
    workgraph_id: str
    workgraph_hash: str  # SHA256 of workgraph JSON for change detection
    started_at: str  # ISO 8601
    completed_at: Optional[str] = None
    status: str = "running"  # running, completed, failed, stopped
    dry_run: bool = True
    max_steps: Optional[int] = None
    only_tasks: List[str] = field(default_factory=list)
    skip_tasks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "workgraph_id": self.workgraph_id,
            "workgraph_hash": self.workgraph_hash,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "dry_run": self.dry_run,
            "max_steps": self.max_steps,
            "only_tasks": self.only_tasks,
            "skip_tasks": self.skip_tasks
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RunMeta':
        """Create RunMeta from dictionary."""
        return RunMeta(
            run_id=data["run_id"],
            workgraph_id=data["workgraph_id"],
            workgraph_hash=data["workgraph_hash"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=data.get("status", "running"),
            dry_run=data.get("dry_run", True),
            max_steps=data.get("max_steps"),
            only_tasks=data.get("only_tasks", []),
            skip_tasks=data.get("skip_tasks", [])
        )


def generate_run_id(workgraph_id: str, start_time_iso: str) -> str:
    """Generate deterministic run ID.

    Format: wr-YYYYMMDD-HHMMSS-<shortsha>
    where shortsha is derived from (workgraph_id + start_time_iso)

    Args:
        workgraph_id: ID of the WorkGraph being run
        start_time_iso: ISO 8601 timestamp of run start

    Returns:
        Run ID string
    """
    # Parse timestamp to extract date and time components
    dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
    date_part = dt.strftime('%Y%m%d')
    time_part = dt.strftime('%H%M%S')

    # Generate short hash from workgraph_id + timestamp
    hash_input = f"{workgraph_id}{start_time_iso}".encode()
    short_hash = hashlib.sha256(hash_input).hexdigest()[:8]

    return f"wr-{date_part}-{time_part}-{short_hash}"


def compute_workgraph_hash(workgraph_json: str) -> str:
    """Compute SHA256 hash of WorkGraph JSON for change detection.

    Args:
        workgraph_json: JSON string of the WorkGraph

    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(workgraph_json.encode()).hexdigest()
