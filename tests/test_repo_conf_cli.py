"""Repo conf CLI tests for canonical subverbs and persistence."""
import argparse
import json
from pathlib import Path

import pytest

from maestro.commands.repo import add_repo_parser, handle_repo_command
from maestro.repo import storage


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_repo_parser(subparsers)
    return parser


def test_repo_conf_help_lists_subcommands(capsys) -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["repo", "conf", "--help"])
    out = capsys.readouterr().out
    assert "show" in out
    assert "list" in out
    assert "select-default" in out


def test_repo_conf_list_json_includes_selected_target(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    storage.save_repoconf(str(repo_root), {
        "selected_target": "target-a",
        "targets": ["target-a", "target-b"],
    })

    args = argparse.Namespace(
        repo_subcommand="conf",
        conf_subcommand="list",
        path=str(repo_root),
        json=True,
    )
    handle_repo_command(args)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert data["selected_target"] == "target-a"
    assert "target-b" in data["targets"]


def test_repo_conf_show_json_round_trip(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    repoconf = {
        "selected_target": "target-x",
        "targets": ["target-x"],
    }
    storage.save_repoconf(str(repo_root), repoconf)

    args = argparse.Namespace(
        repo_subcommand="conf",
        conf_subcommand="show",
        path=str(repo_root),
        json=True,
    )
    handle_repo_command(args)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert data["selected_target"] == "target-x"
    assert data["targets"] == ["target-x"]


def test_repo_conf_select_default_persists(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)

    args = argparse.Namespace(
        repo_subcommand="conf",
        conf_subcommand="select-default",
        path=str(repo_root),
        entity="target",
        value="target-alpha",
    )
    handle_repo_command(args)

    repoconf = storage.load_repoconf(str(repo_root))
    assert repoconf["selected_target"] == "target-alpha"
    assert "target-alpha" in repoconf.get("targets", [])
