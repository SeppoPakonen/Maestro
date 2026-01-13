"""
Maestro Link - Communication layer between ai-run and Maestro.
Handles metadata retrieval (Track, Phase, Task) and context injection.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from maestro.ai.task_sync import load_sync_state, find_task_context
from maestro.commands.runbook import _load_runbook, _load_index

def get_current_state() -> Dict[str, Any]:
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

def get_runbook_context() -> str:
    """Fetch relevant Runbook or Workflow context."""
    index = _load_index()
    if not index:
        return ""

    # Sort by updated_at to get the most recent ones
    sorted_index = sorted(index, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    # Take the top 3 relevant runbooks
    relevant_runbooks = []
    for entry in sorted_index[:3]:
        runbook = _load_runbook(entry["id"])
        if runbook:
            relevant_runbooks.append(runbook)

    if not relevant_runbooks:
        return ""

    context_lines = ["", "### Current Runbook Context:"]
    for rb in relevant_runbooks:
        context_lines.append(f"Runbook: {rb['title']} (ID: {rb['id']})")
        context_lines.append(f"Goal: {rb.get('goal', 'N/A')}")
        steps = rb.get("steps", [])
        if steps:
            context_lines.append("Recent Steps:")
            for step in steps[:5]:  # Just show a few steps
                context_lines.append(f"  {step.get('n', '?')}. [{step.get('actor', '?')}] {step.get('action', '?')}")
        context_lines.append("")

    return "\n".join(context_lines)

def inject_maestro_context(prompt: str) -> str:
    """Inject current Maestro state and runbook context into the prompt."""
    state = get_current_state()
    runbook_ctx = get_runbook_context()

    context_header = ["[MAESTRO CONTEXT]"]
    if state:
        if "track_id" in state:
            context_header.append(f"Track: {state['track_id']}")
        if "phase_id" in state:
            context_header.append(f"Phase: {state['phase_id']} ({state.get('phase_name', 'Unnamed Phase')})")
        if "task_id" in state:
            context_header.append(f"Task: {state['task_id']} ({state.get('task_name', 'Unnamed Task')})")
            if state.get("task_description"):
                desc = "\n".join(state["task_description"])
                context_header.append(f"Description:\n{desc}")
    
    if runbook_ctx:
        context_header.append(runbook_ctx)

    context_header.append("[END MAESTRO CONTEXT]\n")

    return "\n".join(context_header) + prompt

if __name__ == "__main__":
    # Test output
    print(inject_maestro_context("Test prompt"))
