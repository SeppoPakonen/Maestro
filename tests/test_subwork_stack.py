from types import SimpleNamespace

from maestro.breadcrumb import list_breadcrumbs
from maestro.commands.work import handle_work_subwork_start, handle_work_subwork_close
from maestro.work_session import (
    create_session,
    find_session_by_id,
    get_child_sessions,
    get_session_hierarchy,
    get_sessions_base_path,
)


def _find_node(nodes, session_id):
    for node in nodes:
        if node["session"].session_id == session_id:
            return node
        child = _find_node(node.get("children", []), session_id)
        if child:
            return child
    return None


def test_subwork_stack_flow() -> None:
    parent = create_session(
        session_type="work_task",
        related_entity={"task_id": "task-001"},
        purpose="Parent work",
        context={"kind": "task", "ref": "task-001"},
    )

    start_args = SimpleNamespace(
        parent_wsession_id=parent.session_id,
        purpose="Diagnose failing tests",
        context=None,
        no_pause_parent=False,
    )
    assert handle_work_subwork_start(start_args) == 0

    parent_loaded, _ = find_session_by_id(parent.session_id)
    assert parent_loaded.status == "paused"

    children = get_child_sessions(parent.session_id, base_path=get_sessions_base_path())
    assert len(children) == 1
    child = children[0]

    close_args = SimpleNamespace(
        child_wsession_id=child.session_id,
        summary="Tests fail in module X; log points to missing fixture.",
        status="ok",
        no_resume_parent=False,
    )
    assert handle_work_subwork_close(close_args) == 0

    parent_loaded, _ = find_session_by_id(parent.session_id)
    assert parent_loaded.status == "running"

    breadcrumbs = list_breadcrumbs(parent.session_id)
    result_breadcrumbs = [b for b in breadcrumbs if b.kind == "result"]
    assert result_breadcrumbs
    payload = result_breadcrumbs[-1].payload
    assert payload["child_wsession_id"] == child.session_id
    assert "missing fixture" in payload["summary"]

    hierarchy = get_session_hierarchy()
    parent_node = _find_node(hierarchy.get("root", []), parent.session_id)
    assert parent_node is not None
    child_ids = [node["session"].session_id for node in parent_node.get("children", [])]
    assert child.session_id in child_ids
