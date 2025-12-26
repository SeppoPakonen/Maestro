"""Tests for v3 repo truth storage invariants."""
from pathlib import Path
import pytest

from maestro.commands import repo as repo_cmd
from maestro.repo.scanner import RepoScanResult
from maestro.repo import storage


def test_write_repo_artifacts_creates_repo_model(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)

    repo_cmd.write_repo_artifacts(str(repo_root), RepoScanResult(), verbose=False)

    repo_model = repo_root / "docs" / "maestro" / "repo_model.json"
    repo_state = repo_root / "docs" / "maestro" / "repo_state.json"

    assert repo_model.exists()
    assert repo_state.exists()
    assert not (repo_root / ".maestro").exists()


def test_repo_truth_rejects_dot_maestro(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    (repo_root / ".maestro").mkdir()

    with pytest.raises(SystemExit):
        storage.ensure_repo_truth_dir(str(repo_root))
