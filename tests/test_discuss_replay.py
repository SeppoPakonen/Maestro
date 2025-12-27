"""Tests for discuss replay stub handling JSON payloads."""
import argparse
import json
from pathlib import Path

from maestro.commands.discuss import handle_discuss_command


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "discuss_replay"


def _build_args(path: Path, contract: str = "global") -> argparse.Namespace:
    return argparse.Namespace(
        discuss_subcommand="replay",
        path=str(path),
        contract=contract,
        dry_run=True,
        track_id=None,
        phase_id=None,
        task_id=None,
        mode=None,
        prompt=None,
        engine=None,
        model=None,
    )


def test_discuss_replay_valid_jsonl(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    monkeypatch.chdir(repo_root)

    replay_path = repo_root / "valid.jsonl"
    replay_path.write_text((FIXTURE_DIR / "valid.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

    args = _build_args(replay_path)
    result = handle_discuss_command(args)

    assert result == 0
    artifacts_dir = repo_root / "docs" / "maestro" / "ai" / "artifacts"
    assert artifacts_dir.exists()
    assert any(p.name.endswith("_results.json") for p in artifacts_dir.iterdir())


def test_discuss_replay_invalid_jsonl(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "maestro").mkdir(parents=True)
    monkeypatch.chdir(repo_root)

    replay_path = repo_root / "invalid.jsonl"
    replay_path.write_text((FIXTURE_DIR / "invalid.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

    args = _build_args(replay_path)
    result = handle_discuss_command(args)

    assert result == 1
    artifacts_dir = repo_root / "docs" / "maestro" / "ai" / "artifacts"
    artifacts = list(artifacts_dir.glob("*_results.json"))
    assert artifacts
    latest = sorted(artifacts)[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert data.get("status") == "invalid_json"
