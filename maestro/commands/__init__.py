"""
Commands package for Maestro CLI commands.

This module uses lazy imports to keep CLI help paths fast and side-effect-free.
"""

from __future__ import annotations

import importlib
from typing import Dict, Tuple


_LAZY_ATTRS: Dict[str, Tuple[str, str]] = {
    "add_track_parser": ("maestro.commands.track", "add_track_parsers"),
    "handle_track_command": ("maestro.commands.track", "handle_track_command"),
    "add_phase_parser": ("maestro.commands.phase", "add_phase_parser"),
    "handle_phase_command": ("maestro.commands.phase", "handle_phase_command"),
    "add_task_parser": ("maestro.commands.task", "add_task_parser"),
    "handle_task_command": ("maestro.commands.task", "handle_task_command"),
    "add_discuss_parser": ("maestro.commands.discuss", "add_discuss_parser"),
    "handle_discuss_command": ("maestro.commands.discuss", "handle_discuss_command"),
    "add_settings_parser": ("maestro.commands.settings", "add_settings_parser"),
    "handle_settings_command": ("maestro.commands.settings", "handle_settings_command"),
    "add_issues_parser": ("maestro.commands.issues", "add_issues_parser"),
    "handle_issues_command": ("maestro.commands.issues", "handle_issues_command"),
    "add_solutions_parser": ("maestro.commands.solutions", "add_solutions_parser"),
    "handle_solutions_command": ("maestro.commands.solutions", "handle_solutions_command"),
    "add_ai_parser": ("maestro.commands.ai", "add_ai_parser"),
    "add_work_parser": ("maestro.commands.work", "add_work_parser"),
    "add_wsession_parser": ("maestro.commands.work_session", "add_wsession_parser"),
    "add_init_parser": ("maestro.commands.init", "add_init_parser"),
    "handle_init_command": ("maestro.commands.init", "handle_init_command"),
    "add_plan_parser": ("maestro.commands.plan", "add_plan_parser"),
    "handle_plan_add": ("maestro.commands.plan", "handle_plan_add"),
    "handle_plan_list": ("maestro.commands.plan", "handle_plan_list"),
    "handle_plan_remove": ("maestro.commands.plan", "handle_plan_remove"),
    "handle_plan_show": ("maestro.commands.plan", "handle_plan_show"),
    "handle_plan_add_item": ("maestro.commands.plan", "handle_plan_add_item"),
    "handle_plan_remove_item": ("maestro.commands.plan", "handle_plan_remove_item"),
    "handle_plan_discuss": ("maestro.commands.plan", "handle_plan_discuss"),
    "add_understand_parser": ("maestro.commands.understand", "add_understand_parser"),
    "handle_understand_dump": ("maestro.commands.understand", "handle_understand_dump"),
    "add_tu_parser": ("maestro.commands.tu", "add_tu_parser"),
    "handle_tu_command": ("maestro.commands.tu", "handle_tu_command"),
    "add_repo_parser": ("maestro.commands.repo", "add_repo_parser"),
    "handle_repo_command": ("maestro.commands.repo", "handle_repo_command"),
    "add_runbook_parser": ("maestro.commands.runbook", "add_runbook_parser"),
    "handle_runbook_command": ("maestro.commands.runbook", "handle_runbook_command"),
    "add_workflow_parser": ("maestro.commands.workflow", "add_workflow_parser"),
    "handle_workflow_command": ("maestro.commands.workflow", "handle_workflow_command"),
    "add_convert_parser": ("maestro.commands.convert", "add_convert_parser"),
    "add_make_parser": ("maestro.commands.make", "add_make_parser"),
    "handle_make_command": ("maestro.commands.make", "handle_make_command"),
    "add_ops_parser": ("maestro.commands.ops", "add_ops_parser"),
    "handle_ops_command": ("maestro.commands.ops", "handle_ops_command"),
    "add_ux_parser": ("maestro.commands.ux", "add_ux_parser"),
    "handle_ux_command": ("maestro.commands.ux", "handle_ux_command"),
    "add_tutorial_parser": ("maestro.commands.tutorial", "add_tutorial_parser"),
    "handle_tutorial_command": ("maestro.commands.tutorial", "handle_tutorial_command"),
}

__all__ = list(_LAZY_ATTRS.keys())


def __getattr__(name: str):
    if name in _LAZY_ATTRS:
        module_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS.keys()))
