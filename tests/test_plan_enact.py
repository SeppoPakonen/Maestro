"""Tests for plan enact (WorkGraph materialization)."""
import pytest
from pathlib import Path
from maestro.data.workgraph_schema import WorkGraph, Phase, Task, DefinitionOfDone
from maestro.builders.workgraph_materializer import WorkGraphMaterializer
from maestro.tracks.json_store import JsonStore


def test_materialize_creates_track_phase_task(tmp_path):
    """Test that materialize creates Track/Phase/Task files."""
    # Create a simple WorkGraph
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={}
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        id="wg-test-001",
        goal="Test goal",
        track={"id": "TRK-001", "name": "Test track", "goal": "Track goal"},
        phases=[phase]
    )

    # Materialize
    json_store = JsonStore(base_path=str(tmp_path))
    materializer = WorkGraphMaterializer(json_store=json_store)
    summary = materializer.materialize(wg)

    # Verify
    assert summary['track_id'] == "TRK-001"
    assert summary['phases_created'] == 1
    assert summary['tasks_created'] == 1

    # Verify files exist
    assert (tmp_path / "tracks" / "TRK-001.json").exists()
    assert (tmp_path / "phases" / "PH-001.json").exists()
    assert (tmp_path / "tasks" / "TASK-001.json").exists()


def test_materialize_is_idempotent(tmp_path):
    """Test that running materialize twice doesn't duplicate items."""
    # Create WorkGraph
    dod = DefinitionOfDone(kind="file", path="test.txt", expect="exists")
    task = Task(
        id="TASK-002",
        title="Task 2",
        intent="Intent 2",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={}
    )
    phase = Phase(id="PH-002", name="Phase 2", tasks=[task])
    wg = WorkGraph(
        id="wg-test-002",
        goal="Goal 2",
        track={"id": "TRK-002", "name": "Track 2"},
        phases=[phase]
    )

    # Materialize first time
    json_store = JsonStore(base_path=str(tmp_path))
    materializer1 = WorkGraphMaterializer(json_store=json_store)
    summary1 = materializer1.materialize(wg)

    assert summary1['phases_created'] == 1
    assert summary1['tasks_created'] == 1

    # Materialize second time (should update, not create)
    materializer2 = WorkGraphMaterializer(json_store=json_store)
    summary2 = materializer2.materialize(wg)

    assert summary2['phases_created'] == 0  # Already exists
    assert summary2['phases_updated'] == 1
    assert summary2['tasks_created'] == 0  # Already exists
    assert summary2['tasks_updated'] == 1

    # Verify only one set of files exists
    track_files = list((tmp_path / "tracks").glob("*.json"))
    assert len(track_files) == 1
    phase_files = list((tmp_path / "phases").glob("*.json"))
    assert len(phase_files) == 1
    task_files = list((tmp_path / "tasks").glob("*.json"))
    assert len(task_files) == 1


def test_materialize_stable_filenames(tmp_path):
    """Test that task/phase/track IDs result in stable filenames."""
    # Same WorkGraph materialized twice should produce same filenames
    dod = DefinitionOfDone(kind="command", cmd="ls", expect="exit 0")
    task = Task(
        id="TASK-STABLE",
        title="Stable task",
        intent="Intent",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={}
    )
    phase = Phase(id="PH-STABLE", name="Stable phase", tasks=[task])
    wg = WorkGraph(
        id="wg-stable",
        goal="Stable goal",
        track={"id": "TRK-STABLE", "name": "Stable track"},
        phases=[phase]
    )

    json_store = JsonStore(base_path=str(tmp_path))
    materializer = WorkGraphMaterializer(json_store=json_store)
    materializer.materialize(wg)

    # Check filenames
    assert (tmp_path / "tracks" / "TRK-STABLE.json").exists()
    assert (tmp_path / "phases" / "PH-STABLE.json").exists()
    assert (tmp_path / "tasks" / "TASK-STABLE.json").exists()


def test_materialize_dod_to_description_conversion(tmp_path):
    """Test that DoD entries are correctly converted to task description."""
    dod1 = DefinitionOfDone(kind="command", cmd="maestro test", expect="exit 0")
    dod2 = DefinitionOfDone(kind="file", path="docs/test.md", expect="exists")
    verif = DefinitionOfDone(kind="command", cmd="pytest", expect="exit 0")

    task = Task(
        id="TASK-003",
        title="Test DoD conversion",
        intent="Verify DoD conversion logic",
        definition_of_done=[dod1, dod2],
        verification=[verif],
        inputs=["input1", "input2"],
        outputs=["output1"],
        risk={"level": "low", "notes": "Test risk"}
    )
    phase = Phase(id="PH-003", name="Phase 3", tasks=[task])
    wg = WorkGraph(
        id="wg-test-003",
        goal="Test DoD conversion",
        track={"id": "TRK-003", "name": "Track 3"},
        phases=[phase]
    )

    json_store = JsonStore(base_path=str(tmp_path))
    materializer = WorkGraphMaterializer(json_store=json_store)
    materializer.materialize(wg)

    # Load the task and check description
    loaded_task = json_store.load_task("TASK-003")
    assert loaded_task is not None
    description = loaded_task.description

    # Check that description contains expected elements
    assert "**Intent**: Verify DoD conversion logic" in description
    assert "**Definition of Done**:" in description
    assert "- Run: `maestro test` (expect: exit 0)" in description
    assert "- File: `docs/test.md` (expect: exists)" in description
    assert "**Verification**:" in description
    assert "- Run: `pytest` (expect: exit 0)" in description
    assert "**Inputs**: input1, input2" in description
    assert "**Outputs**: output1" in description
    assert "**Risk**: low - Test risk" in description


def test_materialize_updates_index(tmp_path):
    """Test that materializer updates the track index."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    task = Task(
        id="TASK-004",
        title="Test task",
        intent="Test",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={}
    )
    phase = Phase(id="PH-004", name="Phase 4", tasks=[task])
    wg = WorkGraph(
        id="wg-test-004",
        goal="Test index",
        track={"id": "TRK-004", "name": "Track 4"},
        phases=[phase]
    )

    json_store = JsonStore(base_path=str(tmp_path))
    materializer = WorkGraphMaterializer(json_store=json_store)
    materializer.materialize(wg)

    # Load index and verify track is included
    index = json_store.load_index()
    assert "TRK-004" in index.tracks
