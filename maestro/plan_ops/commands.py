"""
Command handlers for the plan operations feature.
"""
import json
import sys
from typing import Optional
from pathlib import Path

from ..plans import PlanStore
from ..modules.utils import print_error, print_success, print_info, styled_print, Colors, print_header
from .decoder import decode_plan_ops_json, DecodeError
from .translator import actions_to_ops
from .executor import PlanOpsExecutor, PreviewResult
from .operations import Commentary


def handle_plan_ops_validate(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Validate a plan operations JSON file."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        plan_ops_result = decode_plan_ops_json(content)

        # If we get here, the JSON is valid
        print_success("JSON validation successful", 2)
        if verbose:
            print_info(f"PlanOpsResult scope: {plan_ops_result.get('scope')}", 2)
            print_info(f"Number of actions: {len(plan_ops_result.get('actions', []))}", 2)
    except DecodeError as e:
        print_error(f"Validation failed: {str(e)}", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}", 2)
        sys.exit(1)


def handle_plan_ops_preview(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Preview the changes that would be made by applying plan operations."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        plan_ops_result = decode_plan_ops_json(content)
        ops = actions_to_ops(plan_ops_result)

        executor = PlanOpsExecutor()
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


def handle_plan_ops_apply(json_file: str, session_path: Optional[str] = None, verbose: bool = False):
    """Apply plan operations to the plan store."""
    try:
        file_path = Path(json_file)
        if not file_path.exists():
            print_error(f"File not found: {json_file}", 2)
            sys.exit(1)
        
        content = file_path.read_text(encoding='utf-8')
        plan_ops_result = decode_plan_ops_json(content)
        ops = actions_to_ops(plan_ops_result)

        executor = PlanOpsExecutor()
        result = executor.apply_ops(ops, dry_run=False)

        # Count non-commentary operations from the original ops list
        non_commentary_ops = [op for op in ops if not isinstance(op, Commentary)]
        print_success(f"Successfully applied {len(non_commentary_ops)} operations", 2)
        
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


def add_plan_ops_parser(plan_subparsers):
    """Add plan ops command subparsers."""
    # Create the ops subcommand parser
    ops_parser = plan_subparsers.add_parser('ops', help='Plan operations automation')
    ops_subparsers = ops_parser.add_subparsers(dest='ops_subcommand', help='Plan ops subcommands', required=True)
    
    # Validate subcommand
    validate_parser = ops_subparsers.add_parser('validate', help='Validate plan operations JSON file')
    validate_parser.add_argument('json_file', help='JSON file containing plan operations')
    
    # Preview subcommand
    preview_parser = ops_subparsers.add_parser('preview', help='Preview changes from plan operations')
    preview_parser.add_argument('json_file', help='JSON file containing plan operations')
    
    # Apply subcommand
    apply_parser = ops_subparsers.add_parser('apply', help='Apply plan operations')
    apply_parser.add_argument('json_file', help='JSON file containing plan operations')
    
    return ops_parser