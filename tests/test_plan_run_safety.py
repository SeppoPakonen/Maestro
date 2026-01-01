"""Tests for plan run safety policy (safe_to_execute)."""
import pytest
import tempfile
from pathlib import Path
from maestro.data.workgraph_schema import WorkGraph, Phase, Task, DefinitionOfDone
from maestro.plan_run.runner import WorkGraphRunner
from maestro.archive.workgraph_storage import save_workgraph


def test_safe_to_execute_blocks_unsafe_tasks_in_execute_mode():
    """Test that tasks without safe_to_execute are skipped in execute mode."""
    # Create a WorkGraph with an unsafe task
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    unsafe_task = Task(
        id="TASK-UNSAFE",
        title="Unsafe task",
        intent="This task is not marked safe",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={},
        safe_to_execute=False  # NOT SAFE
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[unsafe_task])
    wg = WorkGraph(
        id="wg-test-safety",
        goal="Test safety policy",
        track={"id": "TRK-001", "name": "Safety test"},
        phases=[phase]
    )

    # Save workgraph
    with tempfile.TemporaryDirectory() as tmpdir:
        wg_dir = Path(tmpdir) / "workgraphs"
        wg_dir.mkdir(parents=True)
        wg_path = wg_dir / f"{wg.id}.json"
        save_workgraph(wg, wg_path)

        # Create runner in EXECUTE mode (dry_run=False)
        runner = WorkGraphRunner(
            workgraph=wg,
            workgraph_dir=wg_dir,
            dry_run=False,  # EXECUTE MODE
            verbose=False
        )

        # Run
        summary = runner.run()

        # Verify the task was skipped
        assert summary['tasks_skipped'] == 1
        assert summary['tasks_completed'] == 0
        assert summary['tasks_failed'] == 0

        # Check that the task is in skipped set
        assert unsafe_task.id in runner.skipped_tasks


def test_safe_to_execute_allows_safe_tasks_in_execute_mode():
    """Test that tasks with safe_to_execute=true run in execute mode."""
    # Create a WorkGraph with a safe task
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    safe_task = Task(
        id="TASK-SAFE",
        title="Safe task",
        intent="This task is marked safe",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={},
        safe_to_execute=True  # SAFE TO EXECUTE
    )
    phase = Phase(id="PH-002", name="Safe phase", tasks=[safe_task])
    wg = WorkGraph(
        id="wg-test-safe",
        goal="Test safe execution",
        track={"id": "TRK-002", "name": "Safe test"},
        phases=[phase]
    )

    # Save workgraph
    with tempfile.TemporaryDirectory() as tmpdir:
        wg_dir = Path(tmpdir) / "workgraphs"
        wg_dir.mkdir(parents=True)
        wg_path = wg_dir / f"{wg.id}.json"
        save_workgraph(wg, wg_path)

        # Create runner in EXECUTE mode (dry_run=False)
        runner = WorkGraphRunner(
            workgraph=wg,
            workgraph_dir=wg_dir,
            dry_run=False,  # EXECUTE MODE
            verbose=False
        )

        # Run
        summary = runner.run()

        # Verify the task was executed
        assert summary['tasks_completed'] == 1
        assert summary['tasks_skipped'] == 0
        assert summary['tasks_failed'] == 0

        # Check that the task is in completed set
        assert safe_task.id in runner.completed_tasks


def test_safe_to_execute_ignored_in_dry_run_mode():
    """Test that safe_to_execute is ignored in dry-run mode (all tasks preview)."""
    # Create a WorkGraph with both safe and unsafe tasks
    dod1 = DefinitionOfDone(kind="command", cmd="echo safe", expect="exit 0")
    dod2 = DefinitionOfDone(kind="command", cmd="echo unsafe", expect="exit 0")

    safe_task = Task(
        id="TASK-SAFE-DRYRUN",
        title="Safe task",
        intent="Safe",
        definition_of_done=[dod1],
        safe_to_execute=True
    )

    unsafe_task = Task(
        id="TASK-UNSAFE-DRYRUN",
        title="Unsafe task",
        intent="Unsafe",
        definition_of_done=[dod2],
        safe_to_execute=False
    )

    phase = Phase(id="PH-003", name="Mixed phase", tasks=[safe_task, unsafe_task])
    wg = WorkGraph(
        id="wg-test-dryrun",
        goal="Test dry-run ignores safety",
        track={"id": "TRK-003", "name": "Dry-run test"},
        phases=[phase]
    )

    # Save workgraph
    with tempfile.TemporaryDirectory() as tmpdir:
        wg_dir = Path(tmpdir) / "workgraphs"
        wg_dir.mkdir(parents=True)
        wg_path = wg_dir / f"{wg.id}.json"
        save_workgraph(wg, wg_path)

        # Create runner in DRY-RUN mode (dry_run=True)
        runner = WorkGraphRunner(
            workgraph=wg,
            workgraph_dir=wg_dir,
            dry_run=True,  # DRY-RUN MODE
            verbose=False
        )

        # Run
        summary = runner.run()

        # Both tasks should complete in dry-run (safety ignored)
        assert summary['tasks_completed'] == 2
        assert summary['tasks_skipped'] == 0
        assert summary['tasks_failed'] == 0


def test_mixed_safe_and_unsafe_tasks_in_execute_mode():
    """Test that in execute mode, safe tasks run and unsafe tasks skip."""
    dod1 = DefinitionOfDone(kind="command", cmd="echo safe1", expect="exit 0")
    dod2 = DefinitionOfDone(kind="command", cmd="echo unsafe1", expect="exit 0")
    dod3 = DefinitionOfDone(kind="command", cmd="echo safe2", expect="exit 0")

    task1 = Task(
        id="TASK-001",
        title="Safe 1",
        intent="Safe",
        definition_of_done=[dod1],
        safe_to_execute=True
    )

    task2 = Task(
        id="TASK-002",
        title="Unsafe 1",
        intent="Unsafe",
        definition_of_done=[dod2],
        safe_to_execute=False
    )

    task3 = Task(
        id="TASK-003",
        title="Safe 2",
        intent="Safe",
        definition_of_done=[dod3],
        safe_to_execute=True
    )

    phase = Phase(id="PH-004", name="Mixed tasks", tasks=[task1, task2, task3])
    wg = WorkGraph(
        id="wg-test-mixed",
        goal="Test mixed safety",
        track={"id": "TRK-004", "name": "Mixed test"},
        phases=[phase]
    )

    # Save workgraph
    with tempfile.TemporaryDirectory() as tmpdir:
        wg_dir = Path(tmpdir) / "workgraphs"
        wg_dir.mkdir(parents=True)
        wg_path = wg_dir / f"{wg.id}.json"
        save_workgraph(wg, wg_path)

        # Create runner in EXECUTE mode
        runner = WorkGraphRunner(
            workgraph=wg,
            workgraph_dir=wg_dir,
            dry_run=False,
            verbose=False
        )

        # Run
        summary = runner.run()

        # 2 safe tasks completed, 1 unsafe skipped
        assert summary['tasks_completed'] == 2
        assert summary['tasks_skipped'] == 1
        assert summary['tasks_failed'] == 0

        assert task1.id in runner.completed_tasks
        assert task2.id in runner.skipped_tasks
        assert task3.id in runner.completed_tasks


def test_safe_to_execute_default_is_false():
    """Test that default value for safe_to_execute is False."""
    # Create task without specifying safe_to_execute
    dod = DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
    task = Task(
        id="TASK-DEFAULT",
        title="Default task",
        intent="No safe_to_execute specified",
        definition_of_done=[dod]
    )

    # Should default to False
    assert task.safe_to_execute == False


def test_run_record_shows_skipped_unsafe_tasks():
    """Test that run record events include TASK_SKIPPED_UNSAFE events."""
    dod = DefinitionOfDone(kind="command", cmd="echo unsafe", expect="exit 0")
    unsafe_task = Task(
        id="TASK-RECORD-UNSAFE",
        title="Unsafe for record",
        intent="Test run record",
        definition_of_done=[dod],
        safe_to_execute=False
    )
    phase = Phase(id="PH-005", name="Record phase", tasks=[unsafe_task])
    wg = WorkGraph(
        id="wg-test-record",
        goal="Test run record",
        track={"id": "TRK-005", "name": "Record test"},
        phases=[phase]
    )

    # Save workgraph
    with tempfile.TemporaryDirectory() as tmpdir:
        wg_dir = Path(tmpdir) / "workgraphs"
        wg_dir.mkdir(parents=True)
        wg_path = wg_dir / f"{wg.id}.json"
        save_workgraph(wg, wg_path)

        # Create runner in EXECUTE mode
        runner = WorkGraphRunner(
            workgraph=wg,
            workgraph_dir=wg_dir,
            dry_run=False,
            verbose=False
        )

        # Run
        summary = runner.run()

        # Check run record for TASK_SKIPPED_UNSAFE event
        run_dir = wg_dir / wg.id / "runs" / summary['run_id']
        events_file = run_dir / "events.jsonl"

        assert events_file.exists()

        # Read events and check for TASK_SKIPPED_UNSAFE
        import json
        events = []
        with open(events_file, 'r') as f:
            for line in f:
                events.append(json.loads(line))

        # Find TASK_SKIPPED_UNSAFE event
        skipped_events = [e for e in events if e['event_type'] == 'TASK_SKIPPED_UNSAFE']
        assert len(skipped_events) == 1
        assert skipped_events[0]['data']['task_id'] == unsafe_task.id
        assert 'safe_to_execute' in skipped_events[0]['data']['reason']
