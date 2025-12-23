"""
Command handlers for the project operations feature.
"""
import json
import sys
from typing import Optional
from pathlib import Path

from ..modules.utils import print_error, print_success, print_info, styled_print, Colors, print_header
from .decoder import decode_project_ops_json, DecodeError
from .translator import actions_to_ops
from .executor import ProjectOpsExecutor, PreviewResult


def handle_project_ops_validate(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Validate a project operations JSON file."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        project_ops_result = decode_project_ops_json(content)

        # If we get here, the JSON is valid
        print_success("JSON validation successful", 2)
        if verbose:
            print_info(f"ProjectOpsResult scope: {project_ops_result.get('scope')}", 2)
            print_info(f"Number of actions: {len(project_ops_result.get('actions', []))}", 2)
    except DecodeError as e:
        print_error(f"Validation failed: {str(e)}", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}", 2)
        sys.exit(1)


def handle_project_ops_preview(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Preview the changes that would be made by applying project operations."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        project_ops_result = decode_project_ops_json(content)
        ops = actions_to_ops(project_ops_result)

        executor = ProjectOpsExecutor()
        preview_result = executor.preview_ops(ops)

        print_header("PREVIEW OF CHANGES")
        if preview_result.changes:
            for i, change in enumerate(preview_result.changes, 1):
                styled_print(f"{i}. {change}", Colors.BRIGHT_YELLOW, None, 0)
        else:
            print_info("No changes would be made", 2)
            
        if verbose:
            print_header("\nBEFORE STATE:")
            print(preview_result.before_state)
            print_header("\nAFTER STATE:")
            print(preview_result.after_state)
    except DecodeError as e:
        print_error(f"Preview failed: {str(e)}", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}", 2)
        sys.exit(1)


def handle_project_ops_apply(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Apply project operations to the project files."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        project_ops_result = decode_project_ops_json(content)
        ops = actions_to_ops(project_ops_result)

        executor = ProjectOpsExecutor()
        result = executor.apply_ops(ops, dry_run=False)

        # Count operations that were applied
        print_success(f"Successfully applied {len(result.changes)} operations", 2)
        
        if verbose:
            print_header("CHANGES APPLIED:")
            for i, change in enumerate(result.changes, 1):
                styled_print(f"{i}. {change}", Colors.BRIGHT_GREEN, None, 0)
    except DecodeError as e:
        print_error(f"Apply failed: {str(e)}", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}", 2)
        sys.exit(1)


def add_project_ops_parser(subparsers):
    """Add project ops command subparsers."""
    # Create the ops subcommand parser under a general 'ops' command
    ops_parser = subparsers.add_parser('ops', help='Project operations automation')
    ops_subparsers = ops_parser.add_subparsers(dest='ops_subcommand', help='Project ops subcommands', required=True)
    
    # Validate subcommand
    validate_parser = ops_subparsers.add_parser('validate', help='Validate project operations JSON file')
    validate_parser.add_argument('json_file', help='JSON file containing project operations')

    # Preview subcommand
    preview_parser = ops_subparsers.add_parser('preview', help='Preview changes from project operations')
    preview_parser.add_argument('json_file', help='JSON file containing project operations')

    # Apply subcommand
    apply_parser = ops_subparsers.add_parser('apply', help='Apply project operations')
    apply_parser.add_argument('json_file', help='JSON file containing project operations')
    
    return ops_parser