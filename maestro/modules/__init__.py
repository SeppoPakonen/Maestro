"""
Modules for Maestro CLI.

This package contains the split modules from the original main.py file.
"""

# Import all modules to make them available
from .dataclasses import *
from .utils import *
from .cli_parser import *
from .command_handlers import *

__all__ = [
    # Dataclasses
    'StepConfig', 'ValgrindConfig', 'PipelineConfig', 'BuilderConfig',
    'StepResult', 'PipelineRunResult', 'Diagnostic', 
    'MatchCondition', 'RuleMatch', 'RuleAction', 'RuleVerify', 'Rule', 'Rulebook',
    'ConversionStage', 'ConversionPipeline', 'BatchJobSpec', 'BatchDefaults', 'BatchSpec',
    'FixIteration', 'FixRun', 'BuildTarget', 'UppPackage', 'UppFile', 'UppProject',
    'UppRepoIndex', 'PackageInfo', 'AssemblyInfo', 'UnknownPath', 'InternalPackage',
    'RepoScanResult', 'FixOperation', 'RenameOperation', 'WriteFileOperation', 
    'EditFileOperation', 'UpdateUppOperation', 'FixPlan', 'StructureRule',
    'Colors', 'LEGACY_TITLES',
    
    # Utility functions
    'styled_print', 'print_header', 'print_subheader', 'print_success', 
    'print_warning', 'print_error', 'print_info', 'print_debug', 'print_ai_response',
    'print_user_input', 'log_verbose', 'get_maestro_dir', 'get_maestro_sessions_dir',
    'get_user_config_dir', 'get_project_config_file', 'get_user_projects_config_file',
    'get_user_session_config_file', 'get_project_id', 'get_active_session_name',
    'set_active_session_name', 'find_repo_root_from_path', 'is_under_any',
    'parse_upp_list', 'parse_mainconfig_list', 'parse_file_list', 'render_upp',
    'capitalize_first_letter', 'update_subtask_summary_paths', 'has_legacy_plan',
    'assert_no_legacy_subtasks', 'check_git_hygiene', 'clean_json_response',
    'save_prompt_for_traceability', 'save_ai_output', 'build_prompt',
    'build_structured_prompt',
    
    # CLI parsing functions
    'create_main_parser', 'normalize_command_aliases',
    
    # Command handler functions
    'handle_session_new', 'handle_session_list', 'handle_session_set', 
    'handle_session_get', 'handle_session_remove', 'handle_session_details',
    'handle_plan_list', 'handle_plan_show', 'handle_interactive_plan_session',
    'handle_show_plan_tree', 'handle_focus_plan', 'handle_kill_plan',
    'handle_rules_list', 'handle_rules_enable', 'handle_rules_disable',
    'handle_task_list', 'handle_task_run', 'handle_root_refine',
    'handle_root_discuss', 'handle_root_show', 'handle_root_set', 
    'handle_root_get', 'handle_resume_session', 'handle_log_list',
    'handle_log_list_work', 'handle_log_list_plan'
]