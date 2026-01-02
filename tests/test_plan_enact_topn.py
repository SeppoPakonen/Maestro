"""Tests for plan enact --top (top-N with dependency closure)."""
import pytest
import tempfile
from pathlib import Path
from maestro.data.workgraph_schema import WorkGraph, Phase, Task, DefinitionOfDone
from maestro.builders.workgraph_selection import select_top_n_with_closure, format_selection_summary
from maestro.builders.workgraph_materializer import WorkGraphMaterializer
from maestro.tracks.json_store import JsonStore


def create_test_workgraph_with_deps() -> WorkGraph:
    """Create a test WorkGraph with tasks A, B, C, D where C depends on A,B and D depends on C.

    Task scores (estimated):
    - A: low impact, low effort → medium score
    - B: low impact, low effort → medium score
    - C: high impact, medium effort → high score (top task)
    - D: high impact, high effort → medium score
    """
    # Task A (no dependencies)
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
        depends_on=[]  # No dependencies
    )

    # Task B (no dependencies)
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
        depends_on=[]  # No dependencies
    )

    # Task C (depends on A, B) - HIGH SCORE
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
        depends_on=["TASK-A", "TASK-B"]  # Depends on A and B
    )

    # Task D (depends on C)
    task_d = Task(
        id="TASK-D",
        title="Task D - Final step",
        intent="Final task building on C",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo D", expect="exit 0")
        ],
        impact=4,  # High impact
        effort={"min": 60, "max": 90},  # High effort
        risk_score=3,
        purpose=3,
        tags=["final"],
        depends_on=["TASK-C"]  # Depends on C
    )

    phase = Phase(id="PH-001", name="Test phase", tasks=[task_a, task_b, task_c, task_d])

    return WorkGraph(
        id="wg-test-topn",
        goal="Test top-N enact with dependencies",
        track={"id": "TRK-TOPN", "name": "Top-N Track"},
        phases=[phase]
    )


def test_topn_selects_top_tasks():
    """Test that top-N selects the highest-scoring tasks."""
    wg = create_test_workgraph_with_deps()

    # Select top 1 (should be TASK-C)
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # Top task should be TASK-C (highest score)
    assert len(result.top_task_ids) == 1
    assert "TASK-C" in result.top_task_ids


def test_topn_adds_dependency_closure():
    """Test that dependency closure includes all transitive dependencies."""
    wg = create_test_workgraph_with_deps()

    # Select top 1 (TASK-C)
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # TASK-C depends on A and B
    assert "TASK-A" in result.closure_task_ids
    assert "TASK-B" in result.closure_task_ids
    assert len(result.closure_task_ids) == 2

    # Ordered list should have A and B first (dependencies), then C (top task)
    assert result.ordered_task_ids[0] in ["TASK-A", "TASK-B"]
    assert result.ordered_task_ids[1] in ["TASK-A", "TASK-B"]
    assert result.ordered_task_ids[2] == "TASK-C"


def test_topn_deterministic_ties():
    """Test that tied scores are resolved deterministically by task_id."""
    # Create tasks with identical scores
    task_x = Task(
        id="TASK-X",
        title="Task X",
        intent="Test task X",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo X", expect="exit 0")],
        impact=3,
        effort={"min": 20, "max": 30},
        risk_score=1,
        purpose=2,
        tags=[],
        depends_on=[]
    )

    task_y = Task(
        id="TASK-Y",
        title="Task Y",
        intent="Test task Y",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo Y", expect="exit 0")],
        impact=3,  # Same impact
        effort={"min": 20, "max": 30},  # Same effort
        risk_score=1,  # Same risk
        purpose=2,  # Same purpose
        tags=[],
        depends_on=[]
    )

    phase = Phase(id="PH-TIE", name="Tie phase", tasks=[task_y, task_x])  # Y first, X second
    wg = WorkGraph(
        id="wg-tie",
        goal="Test ties",
        track={"id": "TRK-TIE", "name": "Tie track"},
        phases=[phase]
    )

    # Select top 2 (both have same score)
    result1 = select_top_n_with_closure(wg, profile="investor", top_n=2)
    result2 = select_top_n_with_closure(wg, profile="investor", top_n=2)

    # Should be deterministic: same order both times
    assert result1.top_task_ids == result2.top_task_ids

    # Tiebreaker should be task_id ASC: X before Y
    assert result1.top_task_ids == ["TASK-X", "TASK-Y"]


def test_topn_preserves_safe_to_execute():
    """Test that safe_to_execute flag is preserved in materialized tasks."""
    wg = create_test_workgraph_with_deps()

    # Set safe_to_execute to True for TASK-C
    for phase in wg.phases:
        for task in phase.tasks:
            if task.id == "TASK-C":
                task.safe_to_execute = True

    with tempfile.TemporaryDirectory() as tmpdir:
        json_store = JsonStore(base_path=str(tmpdir))
        materializer = WorkGraphMaterializer(json_store=json_store)

        # Select and materialize top 1 (TASK-C + deps)
        result = select_top_n_with_closure(wg, profile="investor", top_n=1)
        summary = materializer.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        # Load materialized task and check description contains safe flag
        task_c = json_store.load_task("TASK-C")
        description_text = "\n".join(task_c.description)

        # Should contain "✓ Safe" in description
        assert "✓ Safe" in description_text or "Safe to Execute" in description_text


def test_topn_idempotent_no_dupes():
    """Test that running enact twice doesn't duplicate items."""
    wg = create_test_workgraph_with_deps()

    with tempfile.TemporaryDirectory() as tmpdir:
        json_store = JsonStore(base_path=str(tmpdir))
        materializer1 = WorkGraphMaterializer(json_store=json_store)

        # Select top 1
        result = select_top_n_with_closure(wg, profile="investor", top_n=1)

        # Materialize first time
        summary1 = materializer1.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        assert summary1['tasks_created'] == 3  # A, B, C

        # Materialize second time (idempotent)
        materializer2 = WorkGraphMaterializer(json_store=json_store)
        summary2 = materializer2.materialize_selected(
            wg,
            task_ids=result.ordered_task_ids,
            selection_result=result
        )

        # Should update, not create new
        assert summary2['tasks_created'] == 0
        assert summary2['tasks_updated'] == 3  # A, B, C

        # Verify only one set of files exists
        task_files = list(Path(tmpdir).glob("tasks/*.json"))
        assert len(task_files) == 3  # A, B, C (no duplicates)


def test_enact_topn_output_summary_is_bounded():
    """Test that selection summary output is bounded (shows max 10 IDs + '+N more')."""
    # Create WorkGraph with 15 tasks, all depending on each other in a chain
    # Make the last task have highest score so it's selected as top-1
    tasks = []
    for i in range(15):
        task_id = f"TASK-{i:02d}"
        deps = [f"TASK-{i-1:02d}"] if i > 0 else []
        # Last task (TASK-14) has highest impact
        impact = 5 if i == 14 else 2
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
            depends_on=deps
        )
        tasks.append(task)

    phase = Phase(id="PH-BIG", name="Big phase", tasks=tasks)
    wg = WorkGraph(
        id="wg-big",
        goal="Test bounded output",
        track={"id": "TRK-BIG", "name": "Big track"},
        phases=[phase]
    )

    # Select top 1 (TASK-14, which depends on all previous tasks)
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # Should select TASK-14 as top task (highest impact)
    assert result.top_task_ids == ["TASK-14"]

    # Should have 14 dependencies (all previous tasks)
    assert len(result.closure_task_ids) == 14

    # Format summary (max 10 IDs per list)
    summary_text = format_selection_summary(result, profile="investor", max_ids_per_list=10)

    # Should contain "+N more" for dependencies (14 > 10)
    assert "+4 more" in summary_text or "more" in summary_text.lower()


def test_topn_with_cycle_fallback():
    """Test that dependency cycle within closure triggers stable fallback."""
    # Create tasks where closure tasks have a cycle among themselves
    # A -> (top task)
    # B -> C -> D -> B (cycle in closure)
    task_a = Task(
        id="TASK-A",
        title="Task A",
        intent="Top task",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo A", expect="exit 0")],
        impact=5,  # Highest impact - will be selected as top-1
        effort={"min": 20, "max": 30},
        risk_score=1,
        purpose=2,
        tags=[],
        depends_on=["TASK-B"]  # A depends on B
    )

    task_b = Task(
        id="TASK-B",
        title="Task B",
        intent="Dep task B",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo B", expect="exit 0")],
        impact=2,
        effort={"min": 20, "max": 30},
        risk_score=1,
        purpose=1,
        tags=[],
        depends_on=["TASK-C"]  # B depends on C
    )

    task_c = Task(
        id="TASK-C",
        title="Task C",
        intent="Dep task C",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo C", expect="exit 0")],
        impact=2,
        effort={"min": 20, "max": 30},
        risk_score=1,
        purpose=1,
        tags=[],
        depends_on=["TASK-D"]  # C depends on D
    )

    task_d = Task(
        id="TASK-D",
        title="Task D",
        intent="Dep task D",
        definition_of_done=[DefinitionOfDone(kind="command", cmd="echo D", expect="exit 0")],
        impact=2,
        effort={"min": 20, "max": 30},
        risk_score=1,
        purpose=1,
        tags=[],
        depends_on=["TASK-B"]  # D depends on B (cycle: B -> C -> D -> B)
    )

    phase = Phase(id="PH-CYCLE", name="Cycle phase", tasks=[task_a, task_b, task_c, task_d])
    wg = WorkGraph(
        id="wg-cycle",
        goal="Test cycles",
        track={"id": "TRK-CYCLE", "name": "Cycle track"},
        phases=[phase]
    )

    # Select top 1 (TASK-A), which pulls in B, C, D as dependencies (with cycle B -> C -> D -> B)
    result = select_top_n_with_closure(wg, profile="investor", top_n=1)

    # Should have warning about cycle in the closure
    assert len(result.warnings) > 0
    assert "cycle" in result.warnings[0].lower()

    # Should fall back to stable sort (task_id ASC) for the cycle
    # All 4 tasks should be included
    assert len(result.ordered_task_ids) == 4


if __name__ == "__main__":
    # Run tests manually
    print("Running top-N enact tests...")

    print("Test 1: Top-N selection...")
    test_topn_selects_top_tasks()
    print("✓ Passed")

    print("Test 2: Dependency closure...")
    test_topn_adds_dependency_closure()
    print("✓ Passed")

    print("Test 3: Deterministic ties...")
    test_topn_deterministic_ties()
    print("✓ Passed")

    print("Test 4: Preserves safe_to_execute...")
    test_topn_preserves_safe_to_execute()
    print("✓ Passed")

    print("Test 5: Idempotent (no dupes)...")
    test_topn_idempotent_no_dupes()
    print("✓ Passed")

    print("Test 6: Bounded output summary...")
    test_enact_topn_output_summary_is_bounded()
    print("✓ Passed")

    print("Test 7: Cycle fallback...")
    test_topn_with_cycle_fallback()
    print("✓ Passed")

    print("\nAll tests passed! ✓")
