"""
UX evaluation and telemetry modules for Maestro.

This package provides tools for discovering CLI surface via help text,
evaluating goal discoverability, and generating UX improvement reports,
and converting UX findings into actionable issues and WorkGraphs.
"""

from .help_surface import HelpSurface, HelpNode, DiscoveryBudget
from .evaluator import GoalEvaluator, AttemptPlan
from .telemetry import TelemetryRecorder, AttemptRecord
from .report import UXReportGenerator
from .postmortem import UXPostmortem, load_eval_artifacts, build_ux_log

__all__ = [
    'HelpSurface',
    'HelpNode',
    'DiscoveryBudget',
    'GoalEvaluator',
    'AttemptPlan',
    'TelemetryRecorder',
    'AttemptRecord',
    'UXReportGenerator',
    'UXPostmortem',
    'load_eval_artifacts',
    'build_ux_log',
]
