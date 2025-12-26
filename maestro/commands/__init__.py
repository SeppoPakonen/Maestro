"""
Commands package for Maestro CLI commands.
"""

from .track import add_track_parsers as add_track_parser, handle_track_command
from .phase import add_phase_parser, handle_phase_command
from .task import add_task_parser, handle_task_command
from .discuss import add_discuss_parser, handle_discuss_command
from .settings import add_settings_parser, handle_settings_command
from .issues import add_issues_parser, handle_issues_command
from .solutions import add_solutions_parser, handle_solutions_command
from .ai import add_ai_parser
from .work import add_work_parser
from .work_session import add_wsession_parser
from .init import add_init_parser, handle_init_command
from .plan import add_plan_parser, handle_plan_add, handle_plan_list, handle_plan_remove, handle_plan_show, handle_plan_add_item, handle_plan_remove_item, handle_plan_discuss
from .understand import add_understand_parser, handle_understand_dump
from .tu import add_tu_parser, handle_tu_command
from .repo import add_repo_parser, handle_repo_command
from .convert import add_convert_parser

__all__ = [
    'add_track_parser',
    'handle_track_command',
    'add_phase_parser',
    'handle_phase_command',
    'add_task_parser',
    'handle_task_command',
    'add_discuss_parser',
    'handle_discuss_command',
    'add_settings_parser',
    'handle_settings_command',
    'add_issues_parser',
    'handle_issues_command',
    'add_solutions_parser',
    'handle_solutions_command',
    'add_ai_parser',
    'add_work_parser',
    'add_wsession_parser',
    'add_init_parser',
    'handle_init_command',
    'add_plan_parser',
    'handle_plan_add',
    'handle_plan_list',
    'handle_plan_remove',
    'handle_plan_show',
    'handle_plan_add_item',
    'handle_plan_remove_item',
    'handle_plan_discuss',
    'add_understand_parser',
    'handle_understand_dump',
    'add_tu_parser',
    'handle_tu_command',
    'add_repo_parser',
    'handle_repo_command',
    'add_convert_parser',
]
