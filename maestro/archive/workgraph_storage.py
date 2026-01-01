"""Storage layer for WorkGraph artifacts with atomic writes and index management.

Provides persistence for WorkGraph plans with:
- Atomic file writes (temp + fsync + rename)
- Index maintenance for fast lookup
- Deterministic storage paths
- Overwrite protection
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..data.workgraph_schema import WorkGraph
from .storage import _atomic_write_json


def save_workgraph(workgraph: WorkGraph, output_path: Path) -> None:
    """Save a WorkGraph to disk using atomic write.

    Args:
        workgraph: WorkGraph instance to save
        output_path: Path where the WorkGraph JSON should be saved

    Raises:
        OSError: If file cannot be written
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and save atomically
    data = workgraph.to_dict()
    _atomic_write_json(output_path, data)

    # Update the index
    _update_workgraph_index(workgraph, output_path)


def load_workgraph(workgraph_path: Path) -> WorkGraph:
    """Load a WorkGraph from disk.

    Args:
        workgraph_path: Path to the WorkGraph JSON file

    Returns:
        WorkGraph instance with full validation

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the JSON is invalid or validation fails
    """
    if not workgraph_path.exists():
        raise FileNotFoundError(f"WorkGraph not found: {workgraph_path}")

    with open(workgraph_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return WorkGraph.from_dict(data)


def load_workgraph_index(index_path: Path) -> Dict[str, any]:
    """Load the WorkGraph index from disk.

    Args:
        index_path: Path to the index.json file

    Returns:
        Dictionary with index data (workgraphs list + metadata)
    """
    if not index_path.exists():
        return {
            "workgraphs": [],
            "last_updated": None
        }

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, KeyError):
        # If index is corrupted, return empty index
        return {
            "workgraphs": [],
            "last_updated": None
        }


def _update_workgraph_index(workgraph: WorkGraph, workgraph_path: Path) -> None:
    """Update the WorkGraph index with a new or updated WorkGraph.

    Args:
        workgraph: WorkGraph instance that was saved
        workgraph_path: Path where the WorkGraph was saved
    """
    # Determine index path (same directory as workgraph)
    index_path = workgraph_path.parent / "index.json"

    # Load existing index
    index = load_workgraph_index(index_path)

    # Create entry for this workgraph
    entry = {
        "id": workgraph.id,
        "domain": workgraph.domain,
        "profile": workgraph.profile,
        "goal": workgraph.goal[:100],  # Truncate goal for index
        "path": str(workgraph_path.relative_to(workgraph_path.parent)),
        "created_at": datetime.now().isoformat(),
        "track_name": workgraph.track.get("name", ""),
        "phase_count": len(workgraph.phases),
        "task_count": sum(len(p.tasks) for p in workgraph.phases)
    }

    # Check if workgraph already exists in index
    existing_index = None
    for i, existing_entry in enumerate(index["workgraphs"]):
        if existing_entry["id"] == workgraph.id:
            existing_index = i
            break

    if existing_index is not None:
        # Update existing entry
        index["workgraphs"][existing_index] = entry
    else:
        # Append new entry
        index["workgraphs"].append(entry)

    # Update last_updated timestamp
    index["last_updated"] = datetime.now().isoformat()

    # Save index atomically
    _atomic_write_json(index_path, index)


def list_workgraphs(workgraph_dir: Path) -> List[Dict[str, any]]:
    """List all WorkGraphs from the index.

    Args:
        workgraph_dir: Directory containing workgraph files and index

    Returns:
        List of workgraph entries from the index
    """
    index_path = workgraph_dir / "index.json"
    index = load_workgraph_index(index_path)
    return index.get("workgraphs", [])


def get_workgraph_by_id(workgraph_id: str, workgraph_dir: Path) -> Optional[WorkGraph]:
    """Get a WorkGraph by its ID.

    Args:
        workgraph_id: ID of the WorkGraph to retrieve
        workgraph_dir: Directory containing workgraph files

    Returns:
        WorkGraph instance if found, None otherwise
    """
    # Load index to find the path
    index_path = workgraph_dir / "index.json"
    index = load_workgraph_index(index_path)

    # Find entry in index
    for entry in index.get("workgraphs", []):
        if entry["id"] == workgraph_id:
            # Load the workgraph from its path
            workgraph_path = workgraph_dir / entry["path"]
            return load_workgraph(workgraph_path)

    return None
