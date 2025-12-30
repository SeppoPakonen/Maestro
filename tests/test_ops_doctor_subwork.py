from maestro.ops.doctor import run_doctor
from maestro.work_session import create_session


def _find_finding(result, finding_id):
    for finding in result.findings:
        if finding.id == finding_id:
            return finding
    return None


def test_ops_doctor_reports_subwork_state() -> None:
    parent = create_session(session_type="work_task", purpose="Parent")
    child = create_session(
        session_type="work_subwork",
        parent_wsession_id=parent.session_id,
        purpose="Child",
    )
    orphan = create_session(
        session_type="work_subwork",
        parent_wsession_id="missing-parent",
        purpose="Orphan",
    )

    result = run_doctor()

    open_children = _find_finding(result, "SUBWORK_OPEN_CHILDREN")
    assert open_children is not None
    assert open_children.severity == "warning"
    assert parent.session_id in (open_children.details or "")
    assert child.session_id in (open_children.details or "")

    orphans = _find_finding(result, "SUBWORK_ORPHANS")
    assert orphans is not None
    assert orphans.severity == "warning"
    assert orphan.session_id in (orphans.details or "")
