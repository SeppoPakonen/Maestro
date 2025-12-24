"""
Migration script to convert markdown-based storage to JSON storage.

This script:
1. Parses existing docs/todo.md and docs/done.md
2. Converts data to JSON format
3. Writes to docs/maestro/ directory
4. Preserves all relationships and data
"""

import sys
from pathlib import Path
from typing import List, Dict

from maestro.tracks.md_store import parse_todo_md, parse_done_md
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import TrackIndex, DoneArchive


def migrate_markdown_to_json(
    todo_md_path: str = "docs/todo.md",
    done_md_path: str = "docs/done.md",
    json_base_path: str = "docs/maestro",
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Migrate markdown storage to JSON storage.

    Args:
        todo_md_path: Path to todo.md file
        done_md_path: Path to done.md file
        json_base_path: Base path for JSON storage
        dry_run: If True, don't write files, just report what would be done

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        "tracks_migrated": 0,
        "phases_migrated": 0,
        "tasks_migrated": 0,
        "archived_tracks": 0,
        "errors": 0
    }

    print("=" * 60)
    print("MARKDOWN TO JSON MIGRATION")
    print("=" * 60)
    print()

    # Initialize JSON store
    json_store = JsonStore(json_base_path)
    print(f"JSON storage initialized at: {json_base_path}")
    print()

    # Parse todo.md
    print(f"Parsing {todo_md_path}...")
    todo_path = Path(todo_md_path)
    if todo_path.exists():
        track_index, error = parse_todo_md(todo_path)
        if error:
            print(f"ERROR parsing todo.md: {error}")
            stats["errors"] += 1
            return stats

        print(f"  Found {len(track_index.tracks)} tracks")

        # Migrate tracks
        for track in track_index.tracks:
            print(f"  Migrating track {track.track_id}: {track.name}")
            stats["tracks_migrated"] += 1

            # Count phases and tasks
            phase_count = len(track.phases)
            task_count = sum(len(phase.tasks) for phase in track.phases)
            print(f"    - {phase_count} phases, {task_count} tasks")

            stats["phases_migrated"] += phase_count
            stats["tasks_migrated"] += task_count

            if not dry_run:
                try:
                    json_store.save_track(track)
                except Exception as e:
                    print(f"    ERROR saving track {track.track_id}: {e}")
                    stats["errors"] += 1

        # Save index
        if not dry_run:
            try:
                # Create a TrackIndex with just track IDs (not full objects)
                index_to_save = TrackIndex(
                    tracks=[t.track_id for t in track_index.tracks],
                    top_priority_track=track_index.top_priority_track
                )
                json_store.save_index(index_to_save)
                print(f"  Saved track index with {len(track_index.tracks)} tracks")
            except Exception as e:
                print(f"  ERROR saving index: {e}")
                stats["errors"] += 1
    else:
        print(f"  {todo_md_path} not found, skipping")

    print()

    # Parse done.md
    print(f"Parsing {done_md_path}...")
    done_path = Path(done_md_path)
    if done_path.exists():
        done_archive, error = parse_done_md(done_path)
        if error:
            print(f"ERROR parsing done.md: {error}")
            stats["errors"] += 1
            return stats

        print(f"  Found {len(done_archive.tracks)} archived tracks")

        # Migrate archived tracks
        for track in done_archive.tracks:
            print(f"  Migrating archived track {track.track_id}: {track.name}")
            stats["archived_tracks"] += 1

            if not dry_run:
                try:
                    # Save to archive directory
                    archive_track_file = json_store.archive_dir / "tracks" / f"{track.track_id}.json"
                    import json
                    track_data = {
                        "track_id": track.track_id,
                        "name": track.name,
                        "status": track.status,
                        "completion": track.completion,
                        "description": track.description,
                        "phases": [phase.phase_id for phase in track.phases],
                        "priority": track.priority,
                        "created_at": track.created_at.isoformat() if track.created_at else None,
                        "updated_at": track.updated_at.isoformat() if track.updated_at else None,
                        "tags": track.tags,
                        "owner": track.owner,
                        "is_top_priority": track.is_top_priority
                    }
                    archive_track_file.write_text(json.dumps(track_data, indent=2), encoding='utf-8')
                except Exception as e:
                    print(f"    ERROR saving archived track {track.track_id}: {e}")
                    stats["errors"] += 1

        # Save archive index
        if not dry_run:
            try:
                # Create a DoneArchive with just track IDs (not full objects)
                archive_to_save = DoneArchive(
                    tracks=[t.track_id for t in done_archive.tracks]
                )
                json_store.save_archive(archive_to_save)
                print(f"  Saved archive index with {len(done_archive.tracks)} tracks")
            except Exception as e:
                print(f"  ERROR saving archive: {e}")
                stats["errors"] += 1
    else:
        print(f"  {done_md_path} not found, skipping")

    print()
    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Tracks migrated:    {stats['tracks_migrated']}")
    print(f"Phases migrated:    {stats['phases_migrated']}")
    print(f"Tasks migrated:     {stats['tasks_migrated']}")
    print(f"Archived tracks:    {stats['archived_tracks']}")
    print(f"Errors:             {stats['errors']}")
    print()

    if dry_run:
        print("DRY RUN - No files were written")
    else:
        print(f"JSON files written to: {json_base_path}")

    print("=" * 60)

    return stats


def main():
    """Command-line entry point for migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate markdown storage to JSON storage")
    parser.add_argument(
        "--todo-md",
        default="docs/todo.md",
        help="Path to todo.md file (default: docs/todo.md)"
    )
    parser.add_argument(
        "--done-md",
        default="docs/done.md",
        help="Path to done.md file (default: docs/done.md)"
    )
    parser.add_argument(
        "--json-path",
        default="docs/maestro",
        help="Base path for JSON storage (default: docs/maestro)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write files, just report what would be done"
    )

    args = parser.parse_args()

    stats = migrate_markdown_to_json(
        todo_md_path=args.todo_md,
        done_md_path=args.done_md,
        json_base_path=args.json_path,
        dry_run=args.dry_run
    )

    # Exit with error code if there were errors
    sys.exit(1 if stats["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
