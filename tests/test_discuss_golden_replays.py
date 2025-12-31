"""Golden fixture replays for discuss sessions (engine-free)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def _run_replay(session_dir: Path, allow_cross_context: bool) -> subprocess.CompletedProcess:
    repo_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, str(repo_root / "maestro.py"), "discuss", "replay", str(session_dir), "--dry-run"]
    if allow_cross_context:
        cmd.append("--allow-cross-context")
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)


def test_discuss_golden_replays(tmp_path):
    golden_root = Path("tests/fixtures/discuss_sessions/golden")
    assert golden_root.exists(), "Golden fixture directory missing"

    fixture_dirs = sorted(p for p in golden_root.iterdir() if p.is_dir())
    assert fixture_dirs, "No golden fixtures found"

    for fixture_dir in fixture_dirs:
        meta_path = fixture_dir / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        context_kind = meta.get("context", {}).get("kind", "global")
        allow_cross_context = context_kind in {"repo", "runbook", "solutions"}

        temp_dir = tmp_path / fixture_dir.name
        shutil.copytree(fixture_dir, temp_dir)

        result = _run_replay(temp_dir, allow_cross_context)
        assert result.returncode == 0, (
            f"Replay failed for {fixture_dir.name}: {result.stdout}\n{result.stderr}"
        )
        assert "REPLAY_OK" in result.stdout, f"Missing REPLAY_OK for {fixture_dir.name}"

        transcript_path = temp_dir / "transcript.jsonl"
        transcript = transcript_path.read_text(encoding="utf-8")
        assert "\"replay_run\"" in transcript, f"Replay run not recorded for {fixture_dir.name}"
