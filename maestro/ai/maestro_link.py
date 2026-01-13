"""
Maestro Link - Communication layer between ai-run and Maestro.
Handles metadata retrieval (Track, Phase, Task) and context injection.
Also handles state mutation (updating task status, logging AI reasoning).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Import Maestro components
try:
    from maestro.ai.task_sync import load_sync_state, find_task_context
    from maestro.commands.runbook import _load_runbook, _load_index, save_runbook_with_update_semantics
    from maestro.tracks.json_store import JsonStore
    from maestro.tracks.models import Task
    MAESTRO_AVAILABLE = True
except ImportError:
    MAESTRO_AVAILABLE = False

class MaestroLink:
    """Robust interface between ai-run and Maestro project state."""

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.project_root = self._discover_project_root()
        self.is_standalone = self.project_root is None and not mock_mode
        
        if not self.is_standalone and not self.mock_mode:
            self.store = JsonStore()
        else:
            self.store = None

    def _discover_project_root(self) -> Optional[Path]:
        """Locate the .maestro directory by walking up from the current directory."""
        curr = Path.cwd()
        for parent in [curr] + list(curr.parents):
            if (parent / ".maestro").is_dir():
                return parent
        return None

    # ========== Getter Interface ========== 

    def get_maestro_context(self) -> Dict[str, Any]:
        """Retrieve structured dictionary containing current workflow, runbook, and tasks."""
        if self.mock_mode:
            return {
                "track_id": "Mock-Track",
                "phase_id": "Mock-Phase",
                "task_id": "Mock-Task",
                "task_name": "Mock Task Name",
                "runbook_title": "Mock Runbook",
                "workflow_goal": "Mock overarching goal"
            }
        
        if self.is_standalone or not MAESTRO_AVAILABLE:
            return {}

        state = self._get_current_state()
        runbook_info = self._get_runbook_info()
        
        context = {
            "session_id": state.get("session_id"),
            "track_id": state.get("track_id"),
            "phase_id": state.get("phase_id"),
            "phase_name": state.get("phase_name"),
            "task_id": state.get("task_id"),
            "task_name": state.get("task_name"),
            "task_description": state.get("task_description"),
            "active_runbook": runbook_info
        }
        
        return context

    def _get_current_state(self) -> Dict[str, Any]:
        """Retrieve the current Maestro state (Track, Phase, Task)."""
        sync_state = load_sync_state()
        if not sync_state:
            return {}

        task_id = sync_state.get("current_task_id")
        if not task_id:
            return {"session_id": sync_state.get("session_id")}

        context = find_task_context(task_id)
        if not context:
            return {"session_id": sync_state.get("session_id"), "task_id": task_id}

        return {
            "session_id": sync_state.get("session_id"),
            "task_id": task_id,
            "task_name": context["task"].get("name"),
            "task_description": context["task"].get("description"),
            "phase_id": context["phase"].get("phase_id"),
            "phase_name": context["phase"].get("name"),
            "track_id": context["phase"].get("track_id"),
        }

    def _get_runbook_info(self) -> Optional[Dict[str, Any]]:
        """Fetch the most relevant active Runbook."""
        index = _load_index()
        if not index:
            return None

        # Sort by updated_at to get the most recent one
        sorted_index = sorted(index, key=lambda x: x.get("updated_at", ""), reverse=True)
        if not sorted_index:
            return None
            
        runbook = _load_runbook(sorted_index[0]["id"])
        return runbook

    def inject_maestro_context(self, prompt: str) -> str:
        """Enrich the prompt with Maestro metadata header."""
        if self.is_standalone:
            return prompt

        ctx = self.get_maestro_context()
        if not ctx:
            return prompt

        header = ["[MAESTRO CONTEXT]"]
        if ctx.get("track_id"):
            header.append(f"Track: {ctx['track_id']}")
        if ctx.get("phase_id"):
            header.append(f"Phase: {ctx['phase_id']} ({ctx.get('phase_name', 'Unnamed')})")
        if ctx.get("task_id"):
            header.append(f"Task: {ctx['task_id']} ({ctx.get('task_name', 'Unnamed')})")
            if ctx.get("task_description"):
                desc = "\n".join(ctx["task_description"])
                header.append(f"Description:\n{desc}")
        
        rb = ctx.get("active_runbook")
        if rb:
            header.append(f"\nActive Runbook: {rb['title']} (ID: {rb['id']})")
            if rb.get("goal"):
                header.append(f"Goal: {rb['goal']}")
            steps = rb.get("steps", [])
            if steps:
                header.append("Recent Steps:")
                for step in steps[:3]:
                    header.append(f"  {step.get('n', '?')}. [{step.get('actor', '?')}] {step.get('action', '?')}")

        header.append("[END MAESTRO CONTEXT]\n")
        
        return "\n".join(header) + prompt

    # ========== Setter Interface ========== 

    def update_task_status(self, task_id: str, status: str, summary: Optional[str] = None) -> bool:
        """Update the status of a Maestro task (Attempted, Fixed, Failed, Done)."""
        if self.mock_mode:
            print(f"[Mock] Updated task {task_id} to {status}. Summary: {summary}")
            return True

        if self.is_standalone or self.store is None:
            return False

        task = self.store.load_task(task_id)
        if not task:
            return False

        task.status = status
        task.updated_at = datetime.now()
        
        if summary:
            if not hasattr(task, 'details') or task.details is None:
                task.details = {}
            
            logs = task.details.get("logs", [])
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "summary": summary
            })
            task.details["logs"] = logs

        if status.lower() == "done":
            task.completed = True

        self.store.save_task(task)
        return True

    def log_ai_event(self, task_id: str, event_data: Dict[str, Any]) -> bool:
        """Store AI's reasoning or model metadata into the task log."""
        if self.mock_mode:
            print(f"[Mock] Logged AI event for {task_id}: {event_data}")
            return True

        if self.is_standalone or self.store is None:
            return False

        task = self.store.load_task(task_id)
        if not task:
            return False

        if not hasattr(task, 'details') or task.details is None:
            task.details = {}
        
        ai_history = task.details.get("ai_history", [])
        event_data["timestamp"] = datetime.now().isoformat()
        ai_history.append(event_data)
        task.details["ai_history"] = ai_history

        self.store.save_task(task)
        return True

    def propose_runbook_step(self, runbook_id: str, actor: str, action: str, expected: str) -> bool:
        """Propose a new step to be added to an existing Runbook."""
        if self.mock_mode:
            print(f"[Mock] Proposed step for {runbook_id}: [{actor}] {action}")
            return True

        if self.is_standalone:
            return False

        runbook = _load_runbook(runbook_id)
        if not runbook:
            return False

        steps = runbook.get("steps", [])
        next_n = len(steps) + 1
        
        new_step = {
            "n": next_n,
            "actor": actor,
            "action": action,
            "expected": expected,
            "proposed_by": "ai-run"
        }
        
        steps.append(new_step)
        runbook["steps"] = steps
        runbook["updated_at"] = datetime.now().isoformat()
        
        save_runbook_with_update_semantics(runbook)
        return True

# Helper functions for ai-run to use directly
def get_link(mock: bool = False) -> MaestroLink:
    return MaestroLink(mock_mode=mock)

if __name__ == "__main__":
    # Test
    link = get_link(mock=True)
    print(link.inject_maestro_context("My Prompt"))
    link.update_task_status("T1", "Fixed", "Found and fixed a typo")
    link.log_ai_event("T1", {"model": "gpt-5.2-codex", "reasoning": "Standard bugfix pattern"})
    link.propose_runbook_step("RB1", "ai", "Verify fixes with unit tests", "Tests pass")