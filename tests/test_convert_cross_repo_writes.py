from pathlib import Path

from maestro.convert.plan_approval import approve_plan, create_pipeline, plan_conversion, run_conversion_pipeline


def _make_repo(tmp_path: Path, name: str) -> Path:
    repo_root = tmp_path / name
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    return repo_root


def test_cross_repo_outputs_written_to_target(tmp_path):
    source_root = _make_repo(tmp_path, "source")
    target_root = _make_repo(tmp_path, "target")
    pipeline_id = "pipe-cross-repo"

    create_pipeline(
        pipeline_id,
        source_repo=str(source_root),
        target_repo=str(target_root),
        repo_root=str(source_root),
    )
    plan_conversion(pipeline_id, repo_root=str(source_root))
    approve_plan(pipeline_id, repo_root=str(source_root))

    result = run_conversion_pipeline(pipeline_id, repo_root=str(source_root))
    assert result.success
    assert result.run_id

    target_run = (
        target_root
        / "docs"
        / "maestro"
        / "convert"
        / "pipelines"
        / pipeline_id
        / "runs"
        / result.run_id
        / "run.json"
    )
    assert target_run.exists()

    source_runs_dir = source_root / "docs" / "maestro" / "convert" / "pipelines" / pipeline_id / "runs"
    assert not source_runs_dir.exists()
