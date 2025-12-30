"""Tests for git branch guard behavior."""
from pathlib import Path

from maestro import git_guard
from maestro.git_guard import check_branch_guard
from maestro.work_session import create_session, save_session, get_sessions_base_path


def test_branch_guard_detects_mismatch(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "sessions").mkdir(parents=True)
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(git_guard, "get_current_branch", lambda *_args, **_kwargs: "current-branch")
    monkeypatch.setattr(git_guard, "get_git_root", lambda *_args, **_kwargs: str(repo_root))

    session = create_session("work_task")
    session.metadata["git_branch"] = "nonexistent-branch"
    session.metadata["git_root"] = str(repo_root)
    session_file = get_sessions_base_path() / session.session_id / "session.json"
    save_session(session, session_file)

    error = check_branch_guard(str(repo_root))
    assert error is not None
    assert "nonexistent-branch" in error
