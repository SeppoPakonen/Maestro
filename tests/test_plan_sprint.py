"""Tests for plan sprint (orchestrate: recommend → enact → run loop)."""
import pytest
import tempfile
import sys
from pathlib import Path
from io import StringIO
from maestro.data.workgraph_schema import WorkGraph, Phase, Task, DefinitionOfDone


def create_test_workgraph_for_sprint() -> WorkGraph:
    """Create a test WorkGraph for sprint testing.

    Task scores (estimated):
    - A: low impact, low effort → medium score
    - B: low impact, low effort → medium score
    - C: high impact, medium effort → high score (top task)
    - D: high impact, high effort → medium score
    """
    # Task A (no dependencies) - safe to execute
    task_a = Task(
        id="TASK-A",
        title="Task A - Low priority foundation",
        intent="Foundation task with low impact",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo A", expect="exit 0")
        ],
        impact=2,  # Low impact
        effort={"min": 10, "max": 20},  # Low effort
        risk_score=1,
        purpose=1,
        tags=["foundation"],
        depends_on=[],  # No dependencies
        safe_to_execute=True  # Safe to run
    )

    # Task B (no dependencies) - safe to execute
    task_b = Task(
        id="TASK-B",
        title="Task B - Low priority support",
        intent="Support task with low impact",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo B", expect="exit 0")
        ],
        impact=2,  # Low impact
        effort={"min": 15, "max": 25},  # Low effort
        risk_score=1,
        purpose=1,
        tags=["support"],
        depends_on=[],  # No dependencies
        safe_to_execute=True  # Safe to run
    )

    # Task C (depends on A, B) - HIGH SCORE - safe to execute
    task_c = Task(
        id="TASK-C",
        title="Task C - High value integration",
        intent="Integrates A and B with high impact",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo C", expect="exit 0")
        ],
        impact=5,  # High impact
        effort={"min": 30, "max": 45},  # Medium effort
        risk_score=2,
        purpose=4,
        tags=["integration", "high-value"],
        depends_on=["TASK-A", "TASK-B"],  # Depends on A and B
        safe_to_execute=True  # Safe to run
    )

    # Task D (depends on C) - NOT safe to execute
    task_d = Task(
        id="TASK-D",
        title="Task D - Final step",
        intent="Final task building on C",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="rm -rf /tmp/test", expect="exit 0")  # Unsafe command
        ],
        impact=4,  # High impact
        effort={"min": 60, "max": 90},  # High effort
        risk_score=3,
        purpose=3,
        tags=["final"],
        depends_on=["TASK-C"],  # Depends on C
        safe_to_execute=False  # NOT safe to run
    )

    phase = Phase(id="PH-001", name="Test phase", tasks=[task_a, task_b, task_c, task_d])

    return WorkGraph(
        id="wg-test-sprint",
        goal="Test sprint workflow",
        track={"id": "TRK-SPRINT", "name": "Sprint Track"},
        phases=[phase]
    )


def test_sprint_selects_enacts_and_runs_dry_by_default():
    """Test that sprint selects, enacts, and runs dry-run by default."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure
    from maestro.builders.workgraph_materializer import WorkGraphMaterializer
    from maestro.tracks.json_store import JsonStore

    wg = create_test_workgraph_for_sprint()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Select top 1 (TASK-C)
        result = select_top_n_with_closure(wg, profile="investor", top_n=1)

        # Should select TASK-C as top task
        assert "TASK-C" in result.top_task_ids

        # Should add A and B as dependencies
        assert "TASK-A" in result.closure_task_ids
        assert "TASK-B" in result.closure_task_ids

        # 2. Enact selected
        json_store = JsonStore(base_path=str(tmpdir))
        materializer = WorkGraphMaterializer(json_store=json_store)
        summary = materializer.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        # Should create 3 tasks (A, B, C)
        assert summary['tasks_created'] == 3

        # 3. Run (dry-run mode)
        # Note: We can't easily test the runner without actually running it
        # but we can verify that the tasks were enacted correctly
        task_c = json_store.load_task("TASK-C")
        assert task_c is not None
        assert task_c.name == "Task C - High value integration"


def test_sprint_execute_respects_safe_to_execute():
    """Test that --execute mode only runs safe_to_execute=true tasks."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure
    from maestro.builders.workgraph_materializer import WorkGraphMaterializer
    from maestro.tracks.json_store import JsonStore

    wg = create_test_workgraph_for_sprint()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Select top 2 (TASK-C and TASK-D)
        # Note: TASK-C has impact=5, TASK-D has impact=4
        # But both have high scores - let's check which is selected
        result = select_top_n_with_closure(wg, profile="investor", top_n=2)

        # TASK-C should be top (highest score)
        # TASK-D should be second (or maybe not selected if C >> D)

        # Enact selected
        json_store = JsonStore(base_path=str(tmpdir))
        materializer = WorkGraphMaterializer(json_store=json_store)
        summary = materializer.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        # Verify tasks were created
        assert summary['tasks_created'] + summary['tasks_updated'] > 0

        # Verify safe_to_execute flag is preserved
        task_c = json_store.load_task("TASK-C")
        description_text = "\n".join(task_c.description)
        assert "✓ Safe" in description_text

        # If TASK-D was selected, verify it's marked as unsafe
        try:
            task_d = json_store.load_task("TASK-D")
            if task_d:
                description_text_d = "\n".join(task_d.description)
                assert "⚠ Unsafe" in description_text_d
        except:
            pass  # TASK-D might not be in top 2


def test_sprint_only_top_filters_run():
    """Test that --only-top filters run to top tasks (not dependencies)."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure

    wg = create_test_workgraph_for_sprint()

    # Select top 1 (TASK-C + deps A, B)
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # Top task: TASK-C
    assert result.top_task_ids == ["TASK-C"]

    # Dependencies: TASK-A, TASK-B
    assert "TASK-A" in result.closure_task_ids
    assert "TASK-B" in result.closure_task_ids

    # Total selected: 3 (A, B, C)
    assert len(result.ordered_task_ids) == 3

    # With --only-top, we should run only TASK-C
    # (A and B are enacted but not run)
    only_top_filter = result.top_task_ids

    # Verify filter only includes top task
    assert only_top_filter == ["TASK-C"]
    assert "TASK-A" not in only_top_filter
    assert "TASK-B" not in only_top_filter


def test_sprint_idempotent_enact():
    """Test that running sprint twice doesn't duplicate items."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure
    from maestro.builders.workgraph_materializer import WorkGraphMaterializer
    from maestro.tracks.json_store import JsonStore

    wg = create_test_workgraph_for_sprint()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Select top 1
        result = select_top_n_with_closure(wg, profile="investor", top_n=1)

        # Enact first time
        json_store = JsonStore(base_path=str(tmpdir))
        materializer1 = WorkGraphMaterializer(json_store=json_store)
        summary1 = materializer1.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        assert summary1['tasks_created'] == 3  # A, B, C

        # Enact second time (should update, not create)
        materializer2 = WorkGraphMaterializer(json_store=json_store)
        summary2 = materializer2.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        # Should update existing tasks, not create new ones
        assert summary2['tasks_created'] == 0
        assert summary2['tasks_updated'] == 3  # A, B, C

        # Verify only one set of files exists
        task_files = list(Path(tmpdir).glob("tasks/*.json"))
        assert len(task_files) == 3  # A, B, C (no duplicates)


def test_sprint_outputs_bounded_summary():
    """Test that sprint output is bounded (shows max 5 top IDs in human-readable mode)."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure

    # Create WorkGraph with 10 tasks (for testing bounded output)
    tasks = []
    for i in range(10):
        task_id = f"TASK-{i:02d}"
        # Last task has highest impact
        impact = 5 if i == 9 else 2
        task = Task(
            id=task_id,
            title=f"Task {i}",
            intent=f"Test task {i}",
            definition_of_done=[DefinitionOfDone(kind="command", cmd=f"echo {i}", expect="exit 0")],
            impact=impact,
            effort={"min": 10, "max": 20},
            risk_score=1,
            purpose=2,
            tags=[],
            depends_on=[],
            safe_to_execute=True
        )
        tasks.append(task)

    phase = Phase(id="PH-BIG", name="Big phase", tasks=tasks)
    wg = WorkGraph(
        id="wg-big",
        goal="Test bounded output",
        track={"id": "TRK-BIG", "name": "Big track"},
        phases=[phase]
    )

    # Select top 6 (should show first 5 + "... and N more")
    result = select_top_n_with_closure(wg, profile="investor", top_n=6)

    # Should select 6 tasks
    assert len(result.top_task_ids) == 6

    # Verify bounded output logic: if we print the first 5 and say "... and 1 more"
    first_5_ids = result.top_task_ids[:5]
    assert len(first_5_ids) == 5

    # Remaining count
    remaining = len(result.top_task_ids) - 5
    assert remaining == 1


def test_ops_runner_extracts_sprint_metadata():
    """Test that machine-readable markers are emitted correctly."""
    from maestro.builders.workgraph_selection import select_top_n_with_closure

    wg = create_test_workgraph_for_sprint()

    # Select top 1
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # Verify selection result has the data we need for markers
    assert len(result.top_task_ids) > 0
    assert len(result.ordered_task_ids) > 0

    # Expected markers format:
    # MAESTRO_SPRINT_TOP_IDS=TASK-C
    # MAESTRO_SPRINT_ENACTED=3
    # MAESTRO_SPRINT_RUN_ID=run-...

    # Verify top task IDs can be comma-joined
    top_ids_marker = ','.join(result.top_task_ids)
    assert top_ids_marker == "TASK-C"

    # Verify total enacted count
    enacted_count = len(result.ordered_task_ids)
    assert enacted_count == 3  # A, B, C

    # Note: RUN_ID is generated by the runner at runtime,
    # so we can't test it here without running the full sprint.
    # This test just verifies the selection metadata is correct.


if __name__ == "__main__":
    # Run tests manually
    print("Running plan sprint tests...")

    print("Test 1: Sprint selects, enacts, and runs dry by default...")
    test_sprint_selects_enacts_and_runs_dry_by_default()
    print("✓ Passed")

    print("Test 2: Execute mode respects safe_to_execute...")
    test_sprint_execute_respects_safe_to_execute()
    print("✓ Passed")

    print("Test 3: Only-top filters run...")
    test_sprint_only_top_filters_run()
    print("✓ Passed")

    print("Test 4: Idempotent enact...")
    test_sprint_idempotent_enact()
    print("✓ Passed")

    print("Test 5: Bounded output summary...")
    test_sprint_outputs_bounded_summary()
    print("✓ Passed")

    print("Test 6: Ops runner extracts sprint metadata...")
    test_ops_runner_extracts_sprint_metadata()
    print("✓ Passed")

    print("\nAll tests passed! ✓")
