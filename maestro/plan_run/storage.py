"""Storage layer for WorkGraph run records.

Provides:
- Append-only event log (JSONL)
- Run metadata persistence
- Index management
- Resume capability
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import RunEvent, RunMeta, compute_workgraph_hash
from ..archive.storage import _atomic_write_json


def get_run_dir(workgraph_dir: Path, workgraph_id: str, run_id: str) -> Path:
    """Get the directory for a specific run.

    Args:
        workgraph_dir: Base directory for workgraphs (e.g., docs/maestro/plans/workgraphs)
        workgraph_id: ID of the WorkGraph
        run_id: ID of the run

    Returns:
        Path to run directory
    """
    return workgraph_dir / workgraph_id / "runs" / run_id


def save_run_meta(run_meta: RunMeta, run_dir: Path) -> None:
    """Save run metadata atomically.

    Args:
        run_meta: RunMeta instance to save
        run_dir: Directory for this run
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "meta.json"
    _atomic_write_json(meta_path, run_meta.to_dict())


def load_run_meta(run_dir: Path) -> Optional[RunMeta]:
    """Load run metadata from disk.

    Args:
        run_dir: Directory for this run

    Returns:
        RunMeta instance if found, None otherwise
    """
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RunMeta.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def append_event(event: RunEvent, run_dir: Path) -> None:
    """Append an event to the run's event log (JSONL).

    Args:
        event: RunEvent to append
        run_dir: Directory for this run
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    events_path = run_dir / "events.jsonl"

    # Append to JSONL file (one JSON object per line)
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict()) + "\n")


def load_events(run_dir: Path) -> List[RunEvent]:
    """Load all events from the run's event log.

    Args:
        run_dir: Directory for this run

    Returns:
        List of RunEvent objects in chronological order
    """
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return []

    events = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                events.append(RunEvent.from_dict(data))
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    return events


def update_run_index(workgraph_dir: Path, workgraph_id: str, run_meta: RunMeta) -> None:
    """Update the run index for a WorkGraph.

    Args:
        workgraph_dir: Base directory for workgraphs
        workgraph_id: ID of the WorkGraph
        run_meta: RunMeta to add/update in index
    """
    index_path = workgraph_dir / workgraph_id / "runs" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing index
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except (json.JSONDecodeError, KeyError):
            index = {"runs": [], "last_updated": None}
    else:
        index = {"runs": [], "last_updated": None}

    # Create entry for this run
    entry = {
        "run_id": run_meta.run_id,
        "started_at": run_meta.started_at,
        "completed_at": run_meta.completed_at,
        "status": run_meta.status,
        "dry_run": run_meta.dry_run
    }

    # Check if run already exists in index
    existing_index = None
    for i, existing_entry in enumerate(index["runs"]):
        if existing_entry["run_id"] == run_meta.run_id:
            existing_index = i
            break

    if existing_index is not None:
        # Update existing entry
        index["runs"][existing_index] = entry
    else:
        # Append new entry (newest last)
        index["runs"].append(entry)

    # Update last_updated timestamp
    index["last_updated"] = datetime.now().isoformat()

    # Save index atomically
    _atomic_write_json(index_path, index)


def list_runs(workgraph_dir: Path, workgraph_id: str) -> List[Dict[str, any]]:
    """List all runs for a WorkGraph.

    Args:
        workgraph_dir: Base directory for workgraphs
        workgraph_id: ID of the WorkGraph

    Returns:
        List of run entries from the index (newest last)
    """
    index_path = workgraph_dir / workgraph_id / "runs" / "index.json"
    if not index_path.exists():
        return []

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        return index.get("runs", [])
    except (json.JSONDecodeError, KeyError):
        return []


def get_latest_run(workgraph_dir: Path, workgraph_id: str) -> Optional[RunMeta]:
    """Get the latest run for a WorkGraph.

    Args:
        workgraph_dir: Base directory for workgraphs
        workgraph_id: ID of the WorkGraph

    Returns:
        RunMeta of the latest run, or None if no runs exist
    """
    runs = list_runs(workgraph_dir, workgraph_id)
    if not runs:
        return None

    # Get the last run (newest)
    latest_entry = runs[-1]
    run_id = latest_entry["run_id"]

    # Load full run meta
    run_dir = get_run_dir(workgraph_dir, workgraph_id, run_id)
    return load_run_meta(run_dir)
