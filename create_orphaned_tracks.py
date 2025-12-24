#!/usr/bin/env python3
"""
Create tracks for orphaned phases and assign track_id to those phases.
"""

import json
from pathlib import Path
from maestro.tracks.json_store import JsonStore

def create_orphaned_tracks():
    """Create tracks for orphaned phase groups."""

    json_store = JsonStore()

    # Define tracks for orphaned phases
    tracks_to_create = [
        {
            "track_id": "universal-maestrokit",
            "name": "Universal MaestroKit Build System",
            "status": "planned",
            "description": ["Universal build system abstraction supporting U++, CMake, Autotools, MSBuild, Maven and more"],
            "phase_pattern": "umk",
            "phases": ["umk1", "umk2", "umk3", "umk4", "umk5", "umk5_5", "umk6", "umk7", "umk8", "umk9", "umk10", "umk11", "umk12"]
        },
        {
            "track_id": "portage-integration",
            "name": "Gentoo Portage Integration",
            "status": "proposed",
            "description": ["Advanced package management with Gentoo Portage integration for dependency resolution"],
            "phase_pattern": "A",
            "phases": ["A1", "A2", "A3", "A4", "A5", "A6"]
        },
        {
            "track_id": "ecosystem-support",
            "name": "Language Ecosystem Support",
            "status": "planned",
            "description": ["Support for Python, Node.js, Go, and other language ecosystems"],
            "phase_pattern": "E",
            "phases": ["E1", "E2", "E3", "E4", "E5"]
        },
        {
            "track_id": "ast-infrastructure",
            "name": "AST and Code Intelligence",
            "status": "planned",
            "description": ["Translation unit and AST infrastructure for code analysis, completion, and transformation"],
            "phase_pattern": "TU",
            "phases": ["TU1", "TU2", "TU3", "TU4", "TU5", "TU6", "TU7"]
        }
    ]

    for track_info in tracks_to_create:
        track_id = track_info["track_id"]

        # Check if track already exists
        if json_store.load_track(track_id, load_phases=False, load_tasks=False):
            print(f"Track {track_id} already exists, skipping...")
            continue

        # Verify phases exist
        existing_phases = []
        for phase_id in track_info["phases"]:
            phase_file = Path(f"docs/maestro/phases/{phase_id}.json")
            if phase_file.exists():
                existing_phases.append(phase_id)

                # Update phase with track_id
                phase_data = json.loads(phase_file.read_text(encoding='utf-8'))
                if phase_data.get("track_id") is None:
                    phase_data["track_id"] = track_id
                    phase_file.write_text(json.dumps(phase_data, indent=2), encoding='utf-8')
                    print(f"  Updated phase {phase_id} with track_id={track_id}")

        # Create track file
        track_dict = {
            "track_id": track_id,
            "name": track_info["name"],
            "status": track_info["status"],
            "completion": 0,
            "description": track_info["description"],
            "phases": existing_phases,
            "priority": 0,
            "created_at": None,
            "updated_at": None,
            "tags": [],
            "owner": None,
            "is_top_priority": False
        }

        # Save to active tracks
        track_file = json_store.tracks_dir / f"{track_id}.json"
        track_file.write_text(json.dumps(track_dict, indent=2), encoding='utf-8')

        # Add to index
        index = json_store.load_index()
        if track_id not in index.tracks:
            index.tracks.append(track_id)
            json_store.save_index(index)

        print(f"Created track: {track_id} with {len(existing_phases)} phases")

if __name__ == "__main__":
    create_orphaned_tracks()
    print("\nDone!")
