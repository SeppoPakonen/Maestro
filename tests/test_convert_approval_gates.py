from pathlib import Path

from maestro.convert.plan_approval import (
    approve_plan,
    create_pipeline,
    plan_conversion,
    reject_plan,
    run_conversion_pipeline,
)


def _make_repo(tmp_path: Path, name: str) -> Path:
    repo_root = tmp_path / name
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    return repo_root


def test_run_blocks_when_not_approved(tmp_path, capsys):
    repo_root = _make_repo(tmp_path, "source")
    pipeline_id = "pipe-approval-block"

    create_pipeline(pipeline_id, repo_root=str(repo_root))
    plan_conversion(pipeline_id, repo_root=str(repo_root))

    result = run_conversion_pipeline(pipeline_id, repo_root=str(repo_root))
    captured = capsys.readouterr()

    assert not result.success
    assert "CONVERT_PLAN_NOT_APPROVED" in captured.out


def test_approve_enables_run(tmp_path):
    repo_root = _make_repo(tmp_path, "source")
    pipeline_id = "pipe-approval-allow"

    create_pipeline(pipeline_id, repo_root=str(repo_root))
    plan_conversion(pipeline_id, repo_root=str(repo_root))
    approve_plan(pipeline_id, repo_root=str(repo_root))

    result = run_conversion_pipeline(pipeline_id, repo_root=str(repo_root))
    assert result.success
    assert result.run_id
    assert (Path(repo_root) / "docs" / "maestro" / "convert" / "pipelines" / pipeline_id / "runs" / result.run_id / "run.json").exists()


def test_reject_blocks_run(tmp_path, capsys):
    repo_root = _make_repo(tmp_path, "source")
    pipeline_id = "pipe-approval-reject"

    create_pipeline(pipeline_id, repo_root=str(repo_root))
    plan_conversion(pipeline_id, repo_root=str(repo_root))
    reject_plan(pipeline_id, repo_root=str(repo_root))

    result = run_conversion_pipeline(pipeline_id, repo_root=str(repo_root))
    captured = capsys.readouterr()

    assert not result.success
    assert "CONVERT_PLAN_NOT_APPROVED" in captured.out


def test_ignore_gates_bypass_logs_warning(tmp_path, capsys):
    repo_root = _make_repo(tmp_path, "source")
    pipeline_id = "pipe-approval-ignore"

    create_pipeline(pipeline_id, repo_root=str(repo_root))
    plan_conversion(pipeline_id, repo_root=str(repo_root))

    result = run_conversion_pipeline(pipeline_id, repo_root=str(repo_root), ignore_gates=True)
    captured = capsys.readouterr()

    assert result.success
    assert "bypassing convert plan gates" in captured.out
