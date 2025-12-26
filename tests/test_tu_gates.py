"""Tests for TU gate enforcement."""
import argparse
from pathlib import Path
import pytest

from maestro.commands.tu import handle_tu_build_command
from maestro.repo import storage


def _tu_args(path: str) -> argparse.Namespace:
    return argparse.Namespace(
        path=path,
        lang="cpp",
        output="docs/maestro/tu/cache",
        force=False,
        compile_flags=None,
        verbose=False,
    )


def test_tu_requires_repo_model(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    monkeypatch.chdir(repo_root)

    with pytest.raises(SystemExit):
        handle_tu_build_command(_tu_args(str(repo_root)))


def test_tu_requires_repoconf(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    storage.write_repo_model(str(repo_root), {"packages_detected": []})
    monkeypatch.chdir(repo_root)

    with pytest.raises(SystemExit):
        handle_tu_build_command(_tu_args(str(repo_root)))
