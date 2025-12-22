"""Track worker module for executing work on tracks."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..work_session import WorkSession
from ..breadcrumb import create_breadcrumb, estimate_tokens, write_breadcrumb
from ..engines import EngineError, get_engine
from ..ai.task_sync import build_task_prompt, write_sync_state
from ..data import parse_phase_md, parse_todo_md
from ..work_session import save_session


class WorkProgress:
    """Track and report work progress during execution."""

    def __init__(self, session: WorkSession):
        self.session = session
        self.steps_completed = 0
        self.total_steps = 0
        self.current_step = None

    def start_step(self, step_name: str):
        """Mark step as started."""
        self.current_step = step_name
        print(f"Starting: {step_name}")

    def complete_step(self):
        """Mark current step as completed."""
        self.steps_completed += 1
        print(f"Completed: {self.current_step} ({self.steps_completed}/{self.total_steps})")

    def report_error(self, error: str):
        """Report error during step."""
        print(f"Error in {self.current_step}: {error}")


async def execute_track_work(track_id: str, session: WorkSession) -> Dict[str, Any]:
    """
    Execute work on a track.

    Args:
        track_id: ID of the track to work on
        session: Work session for the track

    Returns:
        Work result with status and details
    """
    progress = WorkProgress(session)
    tasks = _load_track_tasks(track_id)
    progress.total_steps = len(tasks) or 3

    if tasks:
        task_queue = [entry[0] for entry in tasks]
        session_path = Path("docs") / "sessions" / session.session_id / "session.json"
        responses: List[Dict[str, str]] = []

        for task_id, task, phase in tasks:
            progress.start_step(f"Work task {task_id}")
            session.metadata["task_queue"] = task_queue
            session.metadata["current_task_id"] = task_id
            save_session(session, session_path)
            write_sync_state(session, task_queue, task_id)

            prompt = build_task_prompt(
                task_id,
                task,
                phase,
                session_id=session.session_id,
                sync_source="work track",
            )
            response, error = _safe_generate(prompt, "claude_planner")
            responses.append({"task_id": task_id, "response": response})

            breadcrumb = create_breadcrumb(
                prompt=prompt,
                response=response,
                tools_called=[],
                files_modified=[],
                parent_session_id=session.parent_session_id,
                depth_level=0,
                model_used="claude_planner",
                token_count={
                    "input": estimate_tokens(prompt, "claude"),
                    "output": estimate_tokens(response, "claude"),
                },
                cost=0.0,
                error=error,
            )
            write_breadcrumb(breadcrumb, session.session_id)
            progress.complete_step()

        return {
            "status": "success",
            "message": f"Completed work on track {track_id}",
            "details": {
                "tasks": responses
            }
        }

    try:
        progress.start_step("Analyze track")
        analysis_prompt = f"Analyze the track '{track_id}'. Identify goals, current state, and required work."
        analysis_result, analysis_error = _safe_generate(analysis_prompt, "claude_planner")
        progress.complete_step()

        progress.start_step("Plan track work")
        plan_prompt = (
            f"Based on this analysis: {analysis_result}\n"
            f"Plan the work needed for track '{track_id}'. Include phases, dependencies, and priorities."
        )
        plan_result, plan_error = _safe_generate(plan_prompt, "claude_planner")
        progress.complete_step()

        progress.start_step("Execute track work")
        execution_prompt = (
            f"Execute the planned work for track '{track_id}': {plan_result}. "
            "Return the completed work and summary."
        )
        execution_result, execution_error = _safe_generate(execution_prompt, "claude_planner")
        progress.complete_step()

        breadcrumb = create_breadcrumb(
            prompt=f"Complete work on track {track_id}",
            response=execution_result,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=0,
            model_used="claude_planner",
            token_count={
                "input": estimate_tokens(f"Complete work on track {track_id}", "claude"),
                "output": estimate_tokens(execution_result, "claude"),
            },
            cost=0.0,
            error=analysis_error or plan_error or execution_error,
        )

        write_breadcrumb(breadcrumb, session.session_id)

        return {
            "status": "success",
            "message": f"Completed work on track {track_id}",
            "details": {
                "analysis": analysis_result,
                "plan": plan_result,
                "execution": execution_result
            }
        }

    except Exception as e:
        progress.report_error(str(e))
        return {
            "status": "error",
            "message": f"Error executing work on track {track_id}: {str(e)}"
        }


def _safe_generate(prompt: str, engine_name: str) -> Tuple[str, Optional[str]]:
    try:
        engine = get_engine(engine_name)
        return engine.generate(prompt), None
    except (EngineError, KeyError, AttributeError, OSError) as exc:
        return f"[SIMULATED RESPONSE] {prompt[:200]}", str(exc)


def _load_track_tasks(track_id: str) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    todo_data = parse_todo_md("docs/todo.md")
    track = next(
        (item for item in todo_data.get("tracks", []) if item.get("track_id") == track_id),
        None,
    )
    if not track:
        return []

    phases = track.get("phases", [])
    if not phases:
        return []

    tasks: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    phases_dir = Path("docs/phases")
    for phase in phases:
        phase_id = phase.get("phase_id")
        if not phase_id:
            continue
        phase_path = phases_dir / f"{phase_id}.md"
        if not phase_path.exists():
            continue
        phase_data = parse_phase_md(str(phase_path))
        for task in phase_data.get("tasks", []):
            task_id = task.get("task_id") or task.get("task_number")
            if not task_id:
                continue
            tasks.append((task_id, task, phase_data))
    return tasks
