from types import SimpleNamespace

from maestro.commands.work import handle_work_subwork_close
from maestro.commands.work_session import handle_wsession_close
from maestro.work_session import create_session, find_session_by_id, is_session_closed


def test_parent_close_blocked_with_open_child(capsys) -> None:
    parent = create_session(session_type="work_task", purpose="Parent")
    _child = create_session(
        session_type="work_subwork",
        parent_wsession_id=parent.session_id,
        purpose="Child",
    )

    args = SimpleNamespace(session_id=parent.session_id)
    handle_wsession_close(args)
    output = capsys.readouterr().out.lower()
    assert "open child" in output

    reloaded_parent, _ = find_session_by_id(parent.session_id)
    assert reloaded_parent.status == "running"


def test_orphan_child_close_warns(capsys) -> None:
    orphan = create_session(
        session_type="work_subwork",
        parent_wsession_id="missing-parent",
        purpose="Orphan child",
    )

    args = SimpleNamespace(
        child_wsession_id=orphan.session_id,
        summary="Orphan child completed work.",
        status="ok",
        no_resume_parent=True,
    )
    handle_work_subwork_close(args)
    output = capsys.readouterr().out.lower()
    assert "parent session" in output
    assert "not found" in output

    reloaded_orphan, _ = find_session_by_id(orphan.session_id)
    assert is_session_closed(reloaded_orphan)
