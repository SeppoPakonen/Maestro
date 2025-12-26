"""Tests for make command gating."""
import argparse
from pathlib import Path
import pytest

from maestro.commands.make import handle_make_command
from maestro.repo import storage


def _make_args() -> argparse.Namespace:
    return argparse.Namespace(
        make_subcommand="build",
        package="testpkg",
        method=None,
        config=None,
        jobs=None,
        target=None,
        verbose=False,
        clean_first=False,
        group=None,
    )


def test_make_requires_repo_model(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    monkeypatch.chdir(repo_root)

    args = _make_args()
    with pytest.raises(SystemExit):
        handle_make_command(args)


def test_make_requires_repoconf_target(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    storage.write_repo_model(str(repo_root), {"packages_detected": []})
    monkeypatch.chdir(repo_root)

    args = _make_args()
    with pytest.raises(SystemExit):
        handle_make_command(args)
