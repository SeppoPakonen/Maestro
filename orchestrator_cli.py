"""
Minimal orchestration helpers used by tests.
Provides JSON-plan application and lightweight CLI shims.
"""
import argparse
import json
import sys
from datetime import datetime
from typing import Iterable

import engines
from session_model import Session, Subtask, load_session, save_session


LEGACY_TITLES = {
    "Analysis and Research",
    "Implementation",
    "Testing and Integration",
}


def _now_iso() -> str:
    """Return a UTC timestamp in ISO format without timezone suffix."""
    return datetime.utcnow().isoformat()


def apply_json_plan_to_session(session: Session, plan_json: dict) -> None:
    """
    Map a planner JSON payload to session.subtasks.

    Raises:
        ValueError: if subtasks are missing or empty.
    """
    if not isinstance(plan_json, dict) or "subtasks" not in plan_json:
        raise ValueError("plan_json must contain a 'subtasks' list")

    subtasks_data = plan_json.get("subtasks") or []
    if not subtasks_data:
        raise ValueError("plan_json.subtasks must not be empty")

    planner_model = plan_json.get("planner_model") or plan_json.get("model", "planner")
    new_subtasks = []

    for idx, item in enumerate(subtasks_data):
        sub_id = item.get("id") or f"S{idx + 1}"
        title = item.get("title", "").strip()
        description = item.get("description", "").strip()

        allowed = item.get("allowed_workers") or []
        preferred = item.get("preferred_worker")
        worker_model = preferred or (allowed[0] if allowed else "qwen")

        subtask = Subtask(
            id=sub_id,
            title=title,
            description=description,
            planner_model=item.get("planner_model", planner_model),
            worker_model=worker_model,
            status="pending",
            summary_file=f"{sub_id}_summary.txt",
            categories=item.get("categories", []),
            root_excerpt=item.get("root_excerpt"),
            plan_id=item.get("id"),
        )
        new_subtasks.append(subtask)

    session.subtasks = new_subtasks
    session.updated_at = _now_iso()
    session.status = "planned"


def assert_no_legacy_subtasks(subtasks: Iterable) -> None:
    """Fail if all legacy titles are present."""
    titles = {getattr(sub, "title", "") for sub in subtasks}
    if LEGACY_TITLES.issubset(titles):
        raise AssertionError("Legacy hard-coded subtasks detected")


def has_legacy_plan(session_path: str) -> bool:
    """Check whether the saved session contains legacy subtasks."""
    session = load_session(session_path)
    titles = {getattr(sub, "title", "") for sub in session.subtasks}
    return LEGACY_TITLES.issubset(titles)


def handle_plan_session(session_path: str, verbose: bool = False) -> Session:
    """
    Generate a plan using the configured engine and update the session.
    Engine selection is patched in tests; default falls back to 'planner'.
    """
    session = load_session(session_path)

    engine_name = getattr(session, "planner_model", None) or "planner"
    engine = engines.get_engine(engine_name)

    prompt = session.root_task
    response = engine.generate(prompt)
    plan_json = json.loads(response) if isinstance(response, str) else response

    apply_json_plan_to_session(session, plan_json)
    save_session(session, session_path)

    if verbose:
        assert_no_legacy_subtasks(session.subtasks)

    return session


def handle_resume_session(session_path: str, verbose: bool = False) -> Session:
    """
    Resume a session, migrating legacy plans if needed.
    """
    if has_legacy_plan(session_path):
        return handle_plan_session(session_path, verbose=verbose)
    return load_session(session_path)


def migrate_session_if_needed(session_path: str) -> Session:
    """Compatibility shim for tests expecting migration logic."""
    return handle_resume_session(session_path, verbose=False)


def collect_worker_summaries(session_path: str) -> str:
    """Placeholder hook used in tests."""
    _ = session_path
    return "(summaries unavailable)"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal orchestrator CLI stub.")
    parser.add_argument("--plan", dest="plan_path", help="Apply planner to session JSON")
    parser.add_argument("--resume", dest="resume_path", help="Resume session JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.plan_path:
        handle_plan_session(args.plan_path, verbose=args.verbose)
        return 0
    if args.resume_path:
        handle_resume_session(args.resume_path, verbose=args.verbose)
        return 0

    _build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
