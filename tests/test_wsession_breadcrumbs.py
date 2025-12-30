"""Tests for wsession breadcrumb gating."""
from types import SimpleNamespace
from pathlib import Path

from maestro.commands.work_session import handle_wsession_breadcrumb_add
from maestro.work_session import create_session, complete_session, save_session, get_session_cookie, get_sessions_base_path


def test_breadcrumb_add_requires_cookie(capsys) -> None:
    args = SimpleNamespace(cookie=None, prompt="", response="", model="manual", depth=0)
    handle_wsession_breadcrumb_add(args)
    captured = capsys.readouterr()
    assert "cookie" in captured.out.lower()


def test_breadcrumb_add_rejects_closed_session(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path
    (repo_root / "docs" / "sessions").mkdir(parents=True)
    monkeypatch.chdir(repo_root)

    session = create_session("work_task")
    session = complete_session(session)
    session_file = get_sessions_base_path() / session.session_id / "session.json"
    save_session(session, session_file)

    args = SimpleNamespace(
        cookie=get_session_cookie(session),
        prompt="test",
        response="ok",
        model="manual",
        depth=0,
    )
    handle_wsession_breadcrumb_add(args)
    captured = capsys.readouterr()
    assert "closed" in captured.out.lower()
