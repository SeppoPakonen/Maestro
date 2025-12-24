#!/usr/bin/env python3
"""
Clean up track files to remove references to non-existent phase IDs.
"""

import json
from pathlib import Path

def cleanup_track_phases():
    """Remove invalid phase IDs from track files."""

    # Get all valid phase IDs
    phases_dir = Path("docs/maestro/phases")
    valid_phase_ids = {f.stem for f in phases_dir.glob("*.json")}

    print(f"Found {len(valid_phase_ids)} valid phase files")

    # Process active tracks
    tracks_dir = Path("docs/maestro/tracks")
    if tracks_dir.exists():
        for track_file in tracks_dir.glob("*.json"):
            cleanup_track_file(track_file, valid_phase_ids)

    # Process archived tracks
    archive_tracks_dir = Path("docs/maestro/archive/tracks")
    if archive_tracks_dir.exists():
        for track_file in archive_tracks_dir.glob("*.json"):
            cleanup_track_file(track_file, valid_phase_ids)

def cleanup_track_file(track_file: Path, valid_phase_ids: set):
    """Clean up a single track file."""
    track_data = json.loads(track_file.read_text(encoding='utf-8'))

    original_phases = track_data.get('phases', [])
    if not original_phases:
        return

    # Filter to only valid phase IDs
    valid_phases = [pid for pid in original_phases if pid in valid_phase_ids]

    removed = len(original_phases) - len(valid_phases)
    if removed > 0:
        print(f"\n{track_file.name}:")
        print(f"  Original phases: {len(original_phases)}")
        print(f"  Valid phases: {len(valid_phases)}")
        print(f"  Removed: {removed}")

        invalid_ids = [pid for pid in original_phases if pid not in valid_phase_ids]
        print(f"  Invalid IDs removed: {', '.join(invalid_ids)}")

        # Update the track file
        track_data['phases'] = valid_phases
        track_file.write_text(json.dumps(track_data, indent=2), encoding='utf-8')

if __name__ == "__main__":
    cleanup_track_phases()
    print("\nCleanup complete!")
