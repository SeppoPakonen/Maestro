import json
from pathlib import Path

from maestro.data.track_cache import TrackDataCache
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Track, Phase, Task


def _setup_sample_repo(tmp_path: Path) -> JsonStore:
    """Create a minimal Maestro JSON store with one track/phase/task."""
    json_store = JsonStore(base_path=str(tmp_path / "docs" / "maestro"))

    task = Task(
        task_id="task-alpha",
        name="Task Alpha",
        phase_id="phase-alpha",
        completed=False,
    )
    phase = Phase(
        phase_id="phase-alpha",
        name="Phase Alpha",
        track_id="track-alpha",
        tasks=["task-alpha"],
    )
    track = Track(
        track_id="track-alpha",
        name="Track Alpha",
        phases=["phase-alpha"],
    )

    json_store.save_task(task)
    json_store.save_phase(phase)
    json_store.save_track(track)

    return json_store


def test_track_cache_reuses_snapshot(tmp_path):
    json_store = _setup_sample_repo(tmp_path)
    cache = TrackDataCache(tmp_path)

    first = cache.load_or_rebuild(json_store)
    assert not first.cached
    assert first.snapshot.track_order == ["track-alpha"]
    assert list(first.snapshot.tracks.keys()) == ["track-alpha"]

    meta_bytes = cache.meta_file.read_bytes()
    data_bytes = cache.data_file.read_bytes()

    second = cache.load_or_rebuild(json_store)
    assert second.cached
    assert second.snapshot.track_order == first.snapshot.track_order
    assert cache.meta_file.read_bytes() == meta_bytes
    assert cache.data_file.read_bytes() == data_bytes

    # Modify a watched file so the cache must rebuild
    task_file = json_store.tasks_dir / "task-alpha.json"
    data = json.loads(task_file.read_text(encoding="utf-8"))
    data["name"] = "Task Alpha Updated"
    task_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    third = cache.load_or_rebuild(json_store)
    assert not third.cached
    assert cache.meta_file.read_bytes() != meta_bytes
    assert cache.data_file.read_bytes() != data_bytes
    assert third.snapshot.tracks["track-alpha"].name == "Track Alpha"
    assert any(task.name == "Task Alpha Updated" for task in third.snapshot.tasks_by_phase.get("phase-alpha", []))


def test_track_cache_invalidate(tmp_path):
    json_store = _setup_sample_repo(tmp_path)
    cache = TrackDataCache(tmp_path)
    cache.load_or_rebuild(json_store)
    assert cache.scope_dir.exists()

    assert cache.invalidate()
    assert not cache.scope_dir.exists()

    # After invalidation a rebuild recreates the cache directory
    cache = TrackDataCache(tmp_path)
    cache.load_or_rebuild(json_store)
    assert cache.scope_dir.exists()
