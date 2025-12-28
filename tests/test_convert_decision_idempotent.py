import json
from pathlib import Path

from maestro.convert.plan_approval import approve_plan, create_pipeline, plan_conversion


def _make_repo(tmp_path: Path, name: str) -> Path:
    repo_root = tmp_path / name
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    return repo_root


def test_approve_is_idempotent(tmp_path):
    repo_root = _make_repo(tmp_path, "source")
    pipeline_id = "pipe-idempotent"

    create_pipeline(pipeline_id, repo_root=str(repo_root))
    plan_conversion(pipeline_id, repo_root=str(repo_root))

    approve_plan(pipeline_id, repo_root=str(repo_root))
    decision_path = repo_root / "docs" / "maestro" / "convert" / "pipelines" / pipeline_id / "decision.json"
    with open(decision_path, "r", encoding="utf-8") as handle:
        first_decision = json.load(handle)

    approve_plan(pipeline_id, repo_root=str(repo_root))
    with open(decision_path, "r", encoding="utf-8") as handle:
        second_decision = json.load(handle)

    assert first_decision == second_decision
