"""Issue worker module for executing work on issues with 4-phase workflow."""

import asyncio
import json
from typing import Any, Dict, Optional

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


async def work_on_issue(issue_id: str, parent_session: Optional[WorkSession] = None):
    """
    Execute full issue workflow with sub-sessions.

    Workflow:
    1. Analyze phase:
       - Create child session (type='analyze')
       - Run issue analysis
       - Write breadcrumbs
       - Return analysis result

    2. Decide phase:
       - Create child session (type='decide')
       - AI decides whether to fix issue
       - Write breadcrumbs
       - Return decision

    3. Fix phase (if decision = yes):
       - Create child session (type='fix')
       - Execute fix
       - Write breadcrumbs
       - Return fix result

    4. Verify phase:
       - Create child session (type='verify')
       - Run tests/validation
       - Write breadcrumbs
       - Complete parent session

    All child sessions linked via parent_session_id.
    """
    from ..work_session import create_session

    # Phase 1: Analyze
    analyze_session = create_session(
        session_type="analyze",
        parent_session_id=parent_session.session_id if parent_session else None,
        related_entity={"issue_id": issue_id}
    )
    
    analysis_result = await _analyze_issue(issue_id, analyze_session)
    
    # Phase 2: Decide
    decide_session = create_session(
        session_type="decide",
        parent_session_id=parent_session.session_id if parent_session else None,
        related_entity={"issue_id": issue_id}
    )
    
    decision_result = await _decide_issue(issue_id, analysis_result, decide_session)
    
    # Phase 3: Fix (if decision is to fix)
    fix_result = None
    if decision_result.get("decision", "").lower() == "yes":
        fix_session = create_session(
            session_type="fix",
            parent_session_id=parent_session.session_id if parent_session else None,
            related_entity={"issue_id": issue_id}
        )
        
        fix_result = await _fix_issue(issue_id, analysis_result, fix_session)
    
    # Phase 4: Verify
    verify_session = create_session(
        session_type="verify",
        parent_session_id=parent_session.session_id if parent_session else None,
        related_entity={"issue_id": issue_id}
    )
    
    verify_result = await _verify_issue(issue_id, fix_result, verify_session)
    
    # Return complete results
    return {
        "analysis": analysis_result,
        "decision": decision_result,
        "fix": fix_result,
        "verification": verify_result
    }


async def _analyze_issue(issue_id: str, session: WorkSession):
    """Analyze the issue."""
    progress = WorkProgress(session)
    progress.total_steps = 1
    
    try:
        progress.start_step("Analyze issue")
        prompt = f"Analyze issue '{issue_id}'. Identify the problem, context, and possible approaches to solve it."
        engine = get_engine("claude_planner")  # Using appropriate engine
        response = engine.generate(prompt)
        progress.complete_step()

        # Record in breadcrumbs
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=1,
            model_used="sonnet",
            token_count={"input": len(prompt), "output": len(response)},
            cost=0.0
        )

        write_breadcrumb(breadcrumb, session.session_id)

        return {
            "status": "success",
            "analysis": response
        }
    except Exception as e:
        progress.report_error(str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def _decide_issue(issue_id: str, analysis: Dict[str, Any], session: WorkSession):
    """Decide whether to fix the issue."""
    progress = WorkProgress(session)
    progress.total_steps = 1
    
    try:
        progress.start_step("Decide on issue")
        prompt = f"Based on this analysis: {json.dumps(analysis)}\nShould this issue '{issue_id}' be fixed? If yes, how complex is the fix? Return 'decision': 'yes' or 'no', and 'complexity': 'low', 'medium', or 'high'."
        engine = get_engine("claude_planner")  # Using appropriate engine
        response = engine.generate(prompt)
        progress.complete_step()

        # Record in breadcrumbs
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=1,
            model_used="sonnet",
            token_count={"input": len(prompt), "output": len(response)},
            cost=0.0
        )

        write_breadcrumb(breadcrumb, session.session_id)

        return {
            "status": "success",
            "decision": response
        }
    except Exception as e:
        progress.report_error(str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def _fix_issue(issue_id: str, analysis: Dict[str, Any], session: WorkSession):
    """Execute the fix for the issue."""
    progress = WorkProgress(session)
    progress.total_steps = 1
    
    try:
        progress.start_step("Fix issue")
        prompt = f"Based on this analysis: {json.dumps(analysis)}\nFix issue '{issue_id}'. Provide the necessary changes or solution."
        engine = get_engine("claude_planner")  # Using appropriate engine
        response = engine.generate(prompt)
        progress.complete_step()

        # Record in breadcrumbs
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=1,
            model_used="sonnet",
            token_count={"input": len(prompt), "output": len(response)},
            cost=0.0
        )

        write_breadcrumb(breadcrumb, session.session_id)

        return {
            "status": "success",
            "fix": response
        }
    except Exception as e:
        progress.report_error(str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def _verify_issue(issue_id: str, fix_result: Optional[Dict[str, Any]], session: WorkSession):
    """Verify the issue fix."""
    progress = WorkProgress(session)
    progress.total_steps = 1
    
    try:
        progress.start_step("Verify issue fix")
        engine = get_engine("claude_planner")  # Using appropriate engine
        if fix_result:
            prompt = f"Based on this fix: {json.dumps(fix_result)}\nVerify that issue '{issue_id}' has been properly resolved. Run tests or validation checks if possible."
            response = engine.generate(prompt)
        else:
            # No fix was applied, verify that issue still exists or doesn't need fixing
            prompt = f"Verify issue '{issue_id}'. No fix was applied. Confirm the current state of the issue."
            response = engine.generate(prompt)

        progress.complete_step()

        # Record in breadcrumbs
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=[],
            files_modified=[],
            parent_session_id=session.parent_session_id,
            depth_level=1,
            model_used="sonnet",
            token_count={"input": len(prompt), "output": len(response)},
            cost=0.0
        )

        write_breadcrumb(breadcrumb, session.session_id)

        return {
            "status": "success",
            "verification": response
        }
    except Exception as e:
        progress.report_error(str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def execute_issue_work(issue_id: str, session: WorkSession) -> Dict[str, Any]:
    """
    Execute work on an issue using 4-phase workflow.

    Args:
        issue_id: ID of the issue to work on
        session: Work session for the issue

    Returns:
        Work result with status and details
    """
    try:
        # Execute the 4-phase workflow
        result = await work_on_issue(issue_id, session)
        
        return {
            "status": "success",
            "message": f"Completed 4-phase workflow for issue {issue_id}",
            "details": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error executing work on issue {issue_id}: {str(e)}"
        }