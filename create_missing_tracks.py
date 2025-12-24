#!/usr/bin/env python3
"""
Create missing tracks referenced by phases.
"""

import json
from pathlib import Path
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track

def create_missing_tracks():
    """Create tracks that are referenced by phases but don't exist."""

    json_store = JsonStore()

    # Define missing tracks with their metadata
    missing_tracks = [
        {
            "track_id": "ai-cli-protocol",
            "name": "AI CLI Live Tool Protocol",
            "status": "in_progress",
            "description": ["Implementation of live tool protocol for AI CLI agents"],
        },
        {
            "track_id": "cli-editing",
            "name": "CLI Editing Commands",
            "status": "planned",
            "description": ["Command-line editing tools for tracks, phases, and tasks"],
        },
        {
            "track_id": "test-meaningfulness",
            "name": "Test Meaningfulness",
            "status": "planned",
            "description": ["Audit and improve test meaningfulness"],
        },
    ]

    for track_data in missing_tracks:
        track_id = track_data["track_id"]

        # Check if track already exists
        if json_store.load_track(track_id, load_phases=False, load_tasks=False):
            print(f"Track {track_id} already exists, skipping...")
            continue

        # Find phases that reference this track
        phase_ids = []
        for phase_file in Path("docs/maestro/phases").glob("*.json"):
            phase_data = json.loads(phase_file.read_text(encoding='utf-8'))
            if phase_data.get("track_id") == track_id:
                phase_ids.append(phase_data["phase_id"])

        # Create track
        track = Track(
            track_id=track_id,
            name=track_data["name"],
            status=track_data["status"],
            completion=0,
            description=track_data["description"],
            phases=phase_ids,
            priority=0,
            tags=[],
            owner=None,
            is_top_priority=False
        )

        # Save track file directly to archive
        archive_track_file = json_store.archive_dir / "tracks" / f"{track_id}.json"
        archive_track_file.parent.mkdir(parents=True, exist_ok=True)

        track_dict = {
            "track_id": track.track_id,
            "name": track.name,
            "status": track.status,
            "completion": track.completion,
            "description": track.description,
            "phases": track.phases,
            "priority": track.priority,
            "created_at": None,
            "updated_at": None,
            "tags": track.tags,
            "owner": track.owner,
            "is_top_priority": track.is_top_priority
        }

        archive_track_file.write_text(json.dumps(track_dict, indent=2), encoding='utf-8')

        # Add to archive index
        archive = json_store.load_archive(load_tracks=False, load_phases=False, load_tasks=False)
        if track_id not in archive.tracks:
            archive.tracks.append(track_id)
            json_store.save_archive(archive)

        print(f"Created archived track: {track_id} with {len(phase_ids)} phases")

if __name__ == "__main__":
    create_missing_tracks()
    print("\nDone!")
