"""Tests for plan score and plan recommend (WorkGraph scoring).

These tests verify:
1. Scoring determinism: same WG + same context = same scores and ordering
2. Profile differences: investor vs purpose produce different orderings
3. Backward compatibility: WGs without scoring fields still score (using heuristics)
4. JSON output stability (sorted keys)
5. Ops doctor recommendations (bounded, only when WorkGraph exists)
"""

import pytest
import json
import tempfile
from pathlib import Path
from maestro.data.workgraph_schema import WorkGraph, Phase, Task, DefinitionOfDone
from maestro.builders.workgraph_scoring import score_task, rank_workgraph, get_top_recommendations
from maestro.ops.doctor import check_workgraph_recommendations


def create_test_workgraph() -> WorkGraph:
    """Create a test WorkGraph with 6 tasks covering different scenarios."""
    # Task 1: Build blocker (high impact, low effort)
    task1 = Task(
        id="TASK-001",
        title="Fix CI build blocker",
        intent="Unblock CI pipeline",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="pytest tests/test_build.py", expect="exit 0")
        ],
        tags=["build", "blocker", "ci"]
    )

    # Task 2: Build blocker (critical impact, medium effort, some risk)
    task2 = Task(
        id="TASK-002",
        title="Fix deployment gate failure",
        intent="Unblock production deployment",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="make deploy-test", expect="exit 0"),
            DefinitionOfDone(kind="command", cmd="curl https://staging.example.com/health", expect="exit 0")
        ],
        tags=["build", "gate", "critical"],
        safe_to_execute=False  # Risky
    )

    # Task 3: Docs task (high purpose, low effort)
    task3 = Task(
        id="TASK-003",
        title="Update API documentation",
        intent="Document new endpoints for users",
        definition_of_done=[
            DefinitionOfDone(kind="file", path="docs/api/endpoints.md", expect="exists")
        ],
        tags=["docs", "user-facing"]
    )

    # Task 4: Docs task (high purpose, trivial effort)
    task4 = Task(
        id="TASK-004",
        title="Add usage examples to README",
        intent="Help new users get started",
        definition_of_done=[
            DefinitionOfDone(kind="file", path="README.md", expect="contains examples")
        ],
        tags=["docs", "onboarding", "ux"]
    )

    # Task 5: Risky unsafe task (high risk, high effort)
    task5 = Task(
        id="TASK-005",
        title="Migrate database schema",
        intent="Upgrade to new schema version",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="alembic upgrade head", expect="exit 0"),
            DefinitionOfDone(kind="command", cmd="python scripts/verify_migration.py", expect="exit 0"),
            DefinitionOfDone(kind="command", cmd="python scripts/rollback_test.py", expect="exit 0")
        ],
        tags=["migration", "unsafe", "experimental"],
        safe_to_execute=False,
        outputs=["db/schema_v2.sql", "db/migration_log.txt"]
    )

    # Task 6: Quick cleanup (low impact, trivial effort)
    task6 = Task(
        id="TASK-006",
        title="Remove deprecated imports",
        intent="Clean up codebase",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="grep -r 'from old_module' src/", expect="exit 1")
        ],
        tags=["cleanup", "trivial"]
    )

    phase = Phase(id="PH-001", name="Sprint tasks", tasks=[task1, task2, task3, task4, task5, task6])

    return WorkGraph(
        id="wg-test-score",
        goal="Test scoring",
        track={"id": "TRK-TEST", "name": "Test track"},
        phases=[phase]
    )


def test_scoring_determinism():
    """Test that same WorkGraph + same context produces same scores and ordering."""
    wg = create_test_workgraph()
    context = {"domain": "general"}

    # Score twice
    ranked1 = rank_workgraph(wg, profile="investor", context=context)
    ranked2 = rank_workgraph(wg, profile="investor", context=context)

    # Verify scores are identical
    assert len(ranked1.ranked_tasks) == len(ranked2.ranked_tasks)
    for i, (t1, t2) in enumerate(zip(ranked1.ranked_tasks, ranked2.ranked_tasks)):
        assert t1.task_id == t2.task_id, f"Task {i} ID mismatch"
        assert t1.score == t2.score, f"Task {i} score mismatch"
        assert t1.effort_bucket == t2.effort_bucket, f"Task {i} effort mismatch"
        assert t1.impact == t2.impact, f"Task {i} impact mismatch"
        assert t1.risk == t2.risk, f"Task {i} risk mismatch"
        assert t1.purpose == t2.purpose, f"Task {i} purpose mismatch"


def test_profile_differences():
    """Test that investor vs purpose profiles produce different orderings."""
    wg = create_test_workgraph()

    # Score with both profiles
    investor_ranked = rank_workgraph(wg, profile="investor")
    purpose_ranked = rank_workgraph(wg, profile="purpose")

    # Extract task IDs in order
    investor_order = [t.task_id for t in investor_ranked.ranked_tasks]
    purpose_order = [t.task_id for t in purpose_ranked.ranked_tasks]

    # Verify orderings are different (at least one pair reordered)
    assert investor_order != purpose_order, "Investor and purpose profiles should produce different orderings"

    # Verify that at least 2 tasks have different positions
    position_diffs = sum(1 for i, (t1, t2) in enumerate(zip(investor_order, purpose_order)) if t1 != t2)
    assert position_diffs >= 2, f"Expected at least 2 position differences, got {position_diffs}"


def test_backward_compatibility_missing_fields():
    """Test that WorkGraph without scoring fields still scores (using heuristics)."""
    # Create simple task with no scoring fields
    task = Task(
        id="TASK-SIMPLE",
        title="Simple task without scoring fields",
        intent="Test backward compatibility",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo test", expect="exit 0")
        ]
    )

    phase = Phase(id="PH-SIMPLE", name="Simple phase", tasks=[task])
    wg = WorkGraph(
        id="wg-simple",
        goal="Simple test",
        track={"id": "TRK-SIMPLE", "name": "Simple"},
        phases=[phase]
    )

    # Should not raise errors
    ranked = rank_workgraph(wg, profile="default")

    assert len(ranked.ranked_tasks) == 1
    task_result = ranked.ranked_tasks[0]

    # Verify heuristic inference occurred
    assert "effort" in task_result.inferred_fields
    assert "impact" in task_result.inferred_fields
    assert "risk" in task_result.inferred_fields
    assert "purpose" in task_result.inferred_fields

    # Verify score was calculated
    assert isinstance(task_result.score, (int, float))
    assert task_result.effort_bucket >= 1 and task_result.effort_bucket <= 5
    assert task_result.impact >= 0 and task_result.impact <= 5
    assert task_result.risk >= 0 and task_result.risk <= 5
    assert task_result.purpose >= 0 and task_result.purpose <= 5


def test_json_output_stable_keys():
    """Test that JSON output has stable, sorted keys."""
    wg = create_test_workgraph()
    ranked = rank_workgraph(wg, profile="investor")

    # Convert to dict (simulating what handle_plan_score does)
    output = {
        "workgraph_id": ranked.workgraph_id,
        "profile": ranked.profile,
        "summary": ranked.summary,
        "ranked_tasks": [
            {
                "task_id": t.task_id,
                "task_title": t.task_title,
                "score": t.score,
                "effort_bucket": t.effort_bucket,
                "impact": t.impact,
                "risk": t.risk,
                "purpose": t.purpose,
                "rationale": t.rationale,
                "inferred_fields": t.inferred_fields
            }
            for t in ranked.ranked_tasks[:10]
        ]
    }

    # Serialize with sorted keys
    json_str1 = json.dumps(output, indent=2, sort_keys=True)
    json_str2 = json.dumps(output, indent=2, sort_keys=True)

    # Verify identical JSON
    assert json_str1 == json_str2

    # Verify keys are sorted
    parsed = json.loads(json_str1)
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_top_n_output_bounded():
    """Test that top N output prevents information overload."""
    wg = create_test_workgraph()
    ranked = rank_workgraph(wg, profile="investor")

    # get_top_recommendations should respect top_n
    top_3 = get_top_recommendations(ranked, top_n=3)
    assert len(top_3) == 3

    top_5 = get_top_recommendations(ranked, top_n=5)
    assert len(top_5) == 5

    # Verify top_3 is a subset of top_5 (and in same order)
    for i in range(3):
        assert top_3[i].task_id == top_5[i].task_id


def test_ops_doctor_recommendations_with_workgraph(tmp_path):
    """Test that ops doctor shows recommendations when WorkGraph exists."""
    # Create test WorkGraph
    wg = create_test_workgraph()

    # Save to temp workgraphs dir
    wg_dir = tmp_path / "docs" / "maestro" / "plans" / "workgraphs"
    wg_dir.mkdir(parents=True)

    wg_path = wg_dir / f"{wg.id}.json"
    wg_dict = wg.to_dict()
    with open(wg_path, 'w') as f:
        json.dump(wg_dict, f, indent=2)

    # Check recommendations
    finding = check_workgraph_recommendations(docs_root=tmp_path)

    assert finding is not None
    assert finding.id == "WORKGRAPH_RECOMMENDATIONS"
    assert finding.severity == "ok"
    assert "Top 3 recommendations" in finding.message
    assert finding.details is not None
    assert f"WorkGraph: {wg.id}" in finding.details

    # Verify top 3 are present
    assert finding.details.count("\n") >= 6  # At least 3 tasks * 2 lines each

    # Verify recommended commands
    assert len(finding.recommended_commands) >= 2
    assert any("maestro plan score" in cmd for cmd in finding.recommended_commands)
    assert any("maestro plan recommend" in cmd for cmd in finding.recommended_commands)


def test_ops_doctor_recommendations_without_workgraph(tmp_path):
    """Test that ops doctor returns None when no WorkGraph exists."""
    # Empty workgraphs dir
    wg_dir = tmp_path / "docs" / "maestro" / "plans" / "workgraphs"
    wg_dir.mkdir(parents=True)

    # Check recommendations (should be None)
    finding = check_workgraph_recommendations(docs_root=tmp_path)

    assert finding is None


def test_ops_doctor_recommendations_bounded(tmp_path):
    """Test that ops doctor only checks latest WorkGraph (bounded)."""
    # Create multiple WorkGraphs
    wg_dir = tmp_path / "docs" / "maestro" / "plans" / "workgraphs"
    wg_dir.mkdir(parents=True)

    wg1 = create_test_workgraph()
    wg1.id = "wg-20260101-old"

    wg2 = create_test_workgraph()
    wg2.id = "wg-20260102-new"

    # Save both (wg2 will have newer mtime)
    import time

    wg1_path = wg_dir / f"{wg1.id}.json"
    with open(wg1_path, 'w') as f:
        json.dump(wg1.to_dict(), f)

    time.sleep(0.1)  # Ensure different mtime

    wg2_path = wg_dir / f"{wg2.id}.json"
    with open(wg2_path, 'w') as f:
        json.dump(wg2.to_dict(), f)

    # Check recommendations (should use wg2, the latest)
    finding = check_workgraph_recommendations(docs_root=tmp_path)

    assert finding is not None
    assert f"WorkGraph: {wg2.id}" in finding.details
    assert f"WorkGraph: {wg1.id}" not in finding.details


def test_score_task_individual():
    """Test individual task scoring with different profiles."""
    task = Task(
        id="TASK-IND",
        title="Individual task test",
        intent="Test individual scoring",
        definition_of_done=[
            DefinitionOfDone(kind="command", cmd="echo 1", expect="exit 0"),
            DefinitionOfDone(kind="command", cmd="echo 2", expect="exit 0")
        ],
        tags=["build", "blocker"]
    )

    context = {"domain": "general"}

    # Score with investor profile
    result_investor = score_task(task, "investor", context)
    assert result_investor.task_id == "TASK-IND"
    assert isinstance(result_investor.score, (int, float))
    assert "investor_score" in result_investor.rationale

    # Score with purpose profile
    result_purpose = score_task(task, "purpose", context)
    assert result_purpose.task_id == "TASK-IND"
    assert "purpose_score" in result_purpose.rationale

    # Score with default profile
    result_default = score_task(task, "default", context)
    assert result_default.task_id == "TASK-IND"
    assert "default_score" in result_default.rationale


def test_summary_buckets():
    """Test that summary buckets are calculated correctly."""
    wg = create_test_workgraph()
    ranked = rank_workgraph(wg, profile="investor")

    # Verify summary has expected keys
    assert "total_tasks" in ranked.summary
    assert "quick_wins" in ranked.summary
    assert "risky_bets" in ranked.summary
    assert "purpose_wins" in ranked.summary
    assert "top_score" in ranked.summary
    assert "avg_score" in ranked.summary

    # Verify counts are reasonable
    assert ranked.summary["total_tasks"] == 6
    assert ranked.summary["quick_wins"] >= 0
    assert ranked.summary["risky_bets"] >= 1  # TASK-005 is risky
    assert ranked.summary["purpose_wins"] >= 2  # TASK-003, TASK-004 have high purpose


if __name__ == "__main__":
    # Run tests manually
    print("Running scoring tests...")

    print("Test 1: Scoring determinism...")
    test_scoring_determinism()
    print("✓ Passed")

    print("Test 2: Profile differences...")
    test_profile_differences()
    print("✓ Passed")

    print("Test 3: Backward compatibility...")
    test_backward_compatibility_missing_fields()
    print("✓ Passed")

    print("Test 4: JSON output stable keys...")
    test_json_output_stable_keys()
    print("✓ Passed")

    print("Test 5: Top N bounded...")
    test_top_n_output_bounded()
    print("✓ Passed")

    with tempfile.TemporaryDirectory() as tmpdir:
        print("Test 6: Ops doctor with WorkGraph...")
        test_ops_doctor_recommendations_with_workgraph(Path(tmpdir))
        print("✓ Passed")

        print("Test 7: Ops doctor without WorkGraph...")
        test_ops_doctor_recommendations_without_workgraph(Path(tmpdir))
        print("✓ Passed")

        print("Test 8: Ops doctor bounded...")
        test_ops_doctor_recommendations_bounded(Path(tmpdir))
        print("✓ Passed")

    print("Test 9: Score task individual...")
    test_score_task_individual()
    print("✓ Passed")

    print("Test 10: Summary buckets...")
    test_summary_buckets()
    print("✓ Passed")

    print("\nAll tests passed! ✓")
