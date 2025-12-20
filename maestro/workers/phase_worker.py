"""Phase worker module for executing work on phases."""

import asyncio
import json
from typing import Any, Dict

from ..work_session import WorkSession
from ..breadcrumb import create_breadcrumb, write_breadcrumb
from ..engines import get_engine


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


async def execute_phase_work(phase_id: str, session: WorkSession) -> Dict[str, Any]:
    """
    Execute work on a phase.

    Args:
        phase_id: ID of the phase to work on
        session: Work session for the phase

    Returns:
        Work result with status and details
    """
    progress = WorkProgress(session)
    progress.total_steps = 3  # For example: analyze, plan, execute
    
    try:
        # Step 1: Analyze the phase
        progress.start_step("Analyze phase")
        analysis_prompt = f"Analyze the phase '{phase_id}'. Identify goals, current state, and required work."
        engine = get_engine("claude_planner")  # Using appropriate engine
        analysis_result = engine.generate(analysis_prompt)
        progress.complete_step()

        # Step 2: Plan the work
        progress.start_step("Plan phase work")
        plan_prompt = f"Based on this analysis: {analysis_result}\nPlan the work needed for phase '{phase_id}'. Include specific tasks, dependencies, and priorities."
        plan_result = engine.generate(plan_prompt)
        progress.complete_step()

        # Step 3: Execute the work
        progress.start_step("Execute phase work")
        execution_prompt = f"Execute the planned work for phase '{phase_id}': {plan_result}. Return the completed work and summary."
        execution_result = engine.generate(execution_prompt)
        progress.complete_step()
        
        # Record in breadcrumbs
        breadcrumb = create_breadcrumb(
            prompt=f"Complete work on phase {phase_id}",
            response=execution_result,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=1,
            model_used="sonnet",
            token_count={"input": len(f"Complete work on phase {phase_id}"), "output": len(execution_result)},
            cost=0.0  # Would need to calculate actual cost
        )
        
        write_breadcrumb(breadcrumb, session.session_id)
        
        return {
            "status": "success",
            "message": f"Completed work on phase {phase_id}",
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
            "message": f"Error executing work on phase {phase_id}: {str(e)}"
        }