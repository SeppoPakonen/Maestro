"""Tests for plan run (WorkGraph execution)."""
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from maestro.data.workgraph_schema import DefinitionOfDone, Phase, Task, WorkGraph
from maestro.plan_run.models import RunEvent, RunMeta, compute_workgraph_hash, generate_run_id
from maestro.plan_run.runner import WorkGraphRunner
from maestro.plan_run.storage import (
    append_event,
    get_run_dir,
    load_events,
    load_run_meta,
    save_run_meta
)


def test_topological_ordering_is_deterministic(tmp_path):
    """Test that topological ordering is deterministic."""
    # Create tasks with dependencies
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")

    task1 = Task(
        id="TASK-001",
        title="Task 1",
        intent="First task",
        definition_of_done=[dod],
        outputs=["output1"]
    )

    task2 = Task(
        id="TASK-002",
        title="Task 2",
        intent="Second task",
        definition_of_done=[dod],
        inputs=["output1"],
        outputs=["output2"]
    )

    task3 = Task(
        id="TASK-003",
        title="Task 3",
        intent="Third task",
        definition_of_done=[dod],
        inputs=["output1"],
        outputs=["output3"]
    )

    phase = Phase(id="PH-001", name="Test phase", tasks=[task3, task1, task2])  # Intentionally out of order
    wg = WorkGraph(
        id="wg-test-001",
        goal="Test goal",
        track={"id": "TRK-001", "name": "Test track"},
        phases=[phase]
    )

    # Run twice and verify same order
    runner1 = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        verbose=False
    )

    summary1 = runner1.run()

    # Load events and extract task order
    run_dir1 = get_run_dir(tmp_path, wg.id, runner1.run_meta.run_id)
    events1 = load_events(run_dir1)
    task_order1 = [
        e.data.get("task_id")
        for e in events1
        if e.event_type == "TASK_STARTED"
    ]

    # Run again
    runner2 = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        verbose=False
    )

    summary2 = runner2.run()

    run_dir2 = get_run_dir(tmp_path, wg.id, runner2.run_meta.run_id)
    events2 = load_events(run_dir2)
    task_order2 = [
        e.data.get("task_id")
        for e in events2
        if e.event_type == "TASK_STARTED"
    ]

    # Verify same order
    assert task_order1 == task_order2
    # Verify correct dependency order (TASK-001 must come before TASK-002 and TASK-003)
    assert task_order1[0] == "TASK-001"
    assert "TASK-002" in task_order1[1:]
    assert "TASK-003" in task_order1[1:]


def test_run_record_layout_correct(tmp_path):
    """Test that run record layout is correct and append-only."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod]
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        id="wg-test-002",
        goal="Test goal",
        track={"id": "TRK-002", "name": "Test track"},
        phases=[phase]
    )

    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True
    )

    summary = runner.run()

    # Verify run directory structure
    run_dir = get_run_dir(tmp_path, wg.id, runner.run_meta.run_id)
    assert run_dir.exists()
    assert (run_dir / "meta.json").exists()
    assert (run_dir / "events.jsonl").exists()

    # Verify index exists
    index_path = tmp_path / wg.id / "runs" / "index.json"
    assert index_path.exists()

    # Verify meta content
    meta = load_run_meta(run_dir)
    assert meta.run_id == runner.run_meta.run_id
    assert meta.workgraph_id == wg.id
    assert meta.dry_run is True

    # Verify events content
    events = load_events(run_dir)
    assert len(events) > 0
    # Should have RUN_STARTED, TASK_STARTED, TASK_RESULT, RUN_SUMMARY
    event_types = [e.event_type for e in events]
    assert "RUN_STARTED" in event_types
    assert "TASK_STARTED" in event_types
    assert "TASK_RESULT" in event_types
    assert "RUN_SUMMARY" in event_types


def test_resume_continues_from_last_task(tmp_path):
    """Test that resume continues where it left off."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")

    task1 = Task(
        id="TASK-001",
        title="Task 1",
        intent="First task",
        definition_of_done=[dod]
    )

    task2 = Task(
        id="TASK-002",
        title="Task 2",
        intent="Second task",
        definition_of_done=[dod]
    )

    phase = Phase(id="PH-001", name="Test phase", tasks=[task1, task2])
    wg = WorkGraph(
        id="wg-test-003",
        goal="Test goal",
        track={"id": "TRK-003", "name": "Test track"},
        phases=[phase]
    )

    # First run with max_steps=1
    runner1 = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        max_steps=1
    )

    summary1 = runner1.run()
    assert summary1['tasks_completed'] == 1

    # Resume
    runner2 = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        resume_run_id=runner1.run_meta.run_id
    )

    summary2 = runner2.run()
    # Should complete the remaining task
    assert summary2['tasks_completed'] == 1  # Only the second task


def test_graph_change_detection_blocks_resume(tmp_path):
    """Test that graph change detection blocks resume."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod]
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg1 = WorkGraph(
        id="wg-test-004",
        goal="Test goal 1",
        track={"id": "TRK-004", "name": "Test track"},
        phases=[phase]
    )

    # First run
    runner1 = WorkGraphRunner(
        workgraph=wg1,
        workgraph_dir=tmp_path,
        dry_run=True,
        max_steps=0  # Don't complete any tasks
    )

    summary1 = runner1.run()

    # Change the WorkGraph (different goal)
    wg2 = WorkGraph(
        id="wg-test-004",
        goal="Test goal 2",  # Changed!
        track={"id": "TRK-004", "name": "Test track"},
        phases=[phase]
    )

    # Try to resume with changed WorkGraph
    runner2 = WorkGraphRunner(
        workgraph=wg2,
        workgraph_dir=tmp_path,
        dry_run=True,
        resume_run_id=runner1.run_meta.run_id
    )

    with pytest.raises(ValueError, match="WorkGraph has changed"):
        runner2.run()


def test_dry_run_never_executes_subprocesses(tmp_path):
    """Test that dry-run mode never executes subprocesses."""
    # Create a task with a command that would fail if executed
    dod = DefinitionOfDone(kind="command", cmd="exit 1", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod]
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        id="wg-test-005",
        goal="Test goal",
        track={"id": "TRK-005", "name": "Test track"},
        phases=[phase]
    )

    # Run in dry-run mode
    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True
    )

    summary = runner.run()

    # In dry-run, the task should "complete" successfully even though command would fail
    assert summary['tasks_completed'] == 1
    assert summary['tasks_failed'] == 0


def test_execute_mode_runs_commands(tmp_path):
    """Test that execute mode runs commands and records output."""
    # Create a task with a simple echo command
    dod = DefinitionOfDone(kind="command", cmd="echo hello", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod]
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        id="wg-test-006",
        goal="Test goal",
        track={"id": "TRK-006", "name": "Test track"},
        phases=[phase]
    )

    # Run in execute mode
    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=False
    )

    summary = runner.run()

    # Task should complete successfully
    assert summary['tasks_completed'] == 1
    assert summary['tasks_failed'] == 0

    # Verify event log has output
    run_dir = get_run_dir(tmp_path, wg.id, runner.run_meta.run_id)
    events = load_events(run_dir)
    task_result_events = [e for e in events if e.event_type == "TASK_RESULT"]
    assert len(task_result_events) == 1
    assert task_result_events[0].data["result"] == "ok"


def test_execute_mode_command_failure(tmp_path):
    """Test that execute mode detects command failures."""
    # Create a task with a failing command
    dod = DefinitionOfDone(kind="command", cmd="exit 1", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod]
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        id="wg-test-007",
        goal="Test goal",
        track={"id": "TRK-007", "name": "Test track"},
        phases=[phase]
    )

    # Run in execute mode
    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=False
    )

    summary = runner.run()

    # Task should fail
    assert summary['tasks_completed'] == 0
    assert summary['tasks_failed'] == 1

    # Verify event log has failure reason
    run_dir = get_run_dir(tmp_path, wg.id, runner.run_meta.run_id)
    events = load_events(run_dir)
    task_result_events = [e for e in events if e.event_type == "TASK_RESULT"]
    assert len(task_result_events) == 1
    assert task_result_events[0].data["result"] == "fail"
    assert "exit 1" in task_result_events[0].data["reason"]


def test_run_id_generation():
    """Test that run ID generation is deterministic."""
    workgraph_id = "wg-test-001"
    start_time = "2026-01-01T12:00:00"

    run_id1 = generate_run_id(workgraph_id, start_time)
    run_id2 = generate_run_id(workgraph_id, start_time)

    # Same inputs should produce same run ID
    assert run_id1 == run_id2

    # Different timestamp should produce different run ID
    run_id3 = generate_run_id(workgraph_id, "2026-01-01T12:00:01")
    assert run_id1 != run_id3

    # Verify format
    assert run_id1.startswith("wr-20260101-120000-")


def test_workgraph_hash_computation():
    """Test that workgraph hash computation is stable."""
    wg_json1 = '{"id": "test", "goal": "test goal"}'
    wg_json2 = '{"id": "test", "goal": "test goal"}'
    wg_json3 = '{"id": "test", "goal": "different goal"}'

    hash1 = compute_workgraph_hash(wg_json1)
    hash2 = compute_workgraph_hash(wg_json2)
    hash3 = compute_workgraph_hash(wg_json3)

    # Same JSON should produce same hash
    assert hash1 == hash2

    # Different JSON should produce different hash
    assert hash1 != hash3


def test_only_tasks_filter(tmp_path):
    """Test that --only flag filters tasks correctly."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")

    task1 = Task(id="TASK-001", title="Task 1", intent="First", definition_of_done=[dod])
    task2 = Task(id="TASK-002", title="Task 2", intent="Second", definition_of_done=[dod])
    task3 = Task(id="TASK-003", title="Task 3", intent="Third", definition_of_done=[dod])

    phase = Phase(id="PH-001", name="Test phase", tasks=[task1, task2, task3])
    wg = WorkGraph(
        id="wg-test-008",
        goal="Test goal",
        track={"id": "TRK-008"},
        phases=[phase]
    )

    # Run with only TASK-001 and TASK-003
    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        only_tasks=["TASK-001", "TASK-003"]
    )

    summary = runner.run()

    # Only 2 tasks should complete
    assert summary['tasks_completed'] == 2
    assert summary['tasks_skipped'] == 1

    # Verify correct tasks were executed
    run_dir = get_run_dir(tmp_path, wg.id, runner.run_meta.run_id)
    events = load_events(run_dir)
    started_tasks = [
        e.data.get("task_id")
        for e in events
        if e.event_type == "TASK_STARTED"
    ]
    assert "TASK-001" in started_tasks
    assert "TASK-003" in started_tasks
    assert "TASK-002" not in started_tasks


def test_skip_tasks_filter(tmp_path):
    """Test that --skip flag filters tasks correctly."""
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")

    task1 = Task(id="TASK-001", title="Task 1", intent="First", definition_of_done=[dod])
    task2 = Task(id="TASK-002", title="Task 2", intent="Second", definition_of_done=[dod])

    phase = Phase(id="PH-001", name="Test phase", tasks=[task1, task2])
    wg = WorkGraph(
        id="wg-test-009",
        goal="Test goal",
        track={"id": "TRK-009"},
        phases=[phase]
    )

    # Run with TASK-002 skipped
    runner = WorkGraphRunner(
        workgraph=wg,
        workgraph_dir=tmp_path,
        dry_run=True,
        skip_tasks=["TASK-002"]
    )

    summary = runner.run()

    # Only 1 task should complete
    assert summary['tasks_completed'] == 1
    assert summary['tasks_skipped'] == 1

    # Verify TASK-001 was executed
    run_dir = get_run_dir(tmp_path, wg.id, runner.run_meta.run_id)
    events = load_events(run_dir)
    started_tasks = [
        e.data.get("task_id")
        for e in events
        if e.event_type == "TASK_STARTED"
    ]
    assert "TASK-001" in started_tasks
    assert "TASK-002" not in started_tasks
