"""
Assembly configuration commands for Maestro.

Handles assembly configurations that define which parts of the repository to include
in builds, helping to resolve the "multiple packages" issue by creating specific
configurations for different use cases.
"""

import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from maestro.modules.utils import (
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from maestro.repo.storage import find_repo_root, load_repo_model, repo_model_path
from maestro.repo.assembly_commands import load_assemblies_data


def handle_asm_conf_command(args):
    """
    Handle 'maestro repo asm conf' commands.

    Subcommands:
    - list: List all assembly configurations
    - add: Add a new assembly configuration
    - remove: Remove an assembly configuration
    - modify: Modify an existing assembly configuration
    - select: Select an active assembly configuration
    - import: Import an assembly configuration from a .var file
    """
    repo_path = args.path if hasattr(args, 'path') and args.path else None

    if args.asm_conf_subcommand in ['list', 'ls', 'l']:
        list_asm_configs(repo_path, getattr(args, 'json', False))
    elif args.asm_conf_subcommand in ['add', 'create']:
        name = getattr(args, 'name', None)
        if name:
            add_asm_config(repo_path, name, getattr(args, 'packages', []), getattr(args, 'json', False))
        else:
            print_error("Configuration name required for 'add' command", 2)
    elif args.asm_conf_subcommand == 'import':
        var_file = getattr(args, 'var_file', None)
        name = getattr(args, 'name', None)
        if var_file:
            import_asm_config(repo_path, var_file, name, getattr(args, 'json', False))
        else:
            print_error(".var file path required for 'import' command", 2)
    elif args.asm_conf_subcommand in ['remove', 'rm', 'delete']:
        name = getattr(args, 'name', None)
        if name:
            remove_asm_config(repo_path, name, getattr(args, 'json', False))
        else:
            print_error("Configuration name required for 'remove' command", 2)
    elif args.asm_conf_subcommand in ['modify', 'update']:
        name = getattr(args, 'name', None)
        if name:
            modify_asm_config(repo_path, name, getattr(args, 'packages', []), getattr(args, 'json', False))
        else:
            print_error("Configuration name required for 'modify' command", 2)
    elif args.asm_conf_subcommand == 'select':
        name = getattr(args, 'name', None)
        if name:
            select_asm_config(repo_path, name, getattr(args, 'json', False))
        else:
            print_error("Configuration name required for 'select' command", 2)
    else:
        print_error(f"Unknown assembly configuration command: {args.asm_conf_subcommand}", 2)
        show_asm_conf_help()


def _get_config_file_path(repo_root: str) -> Path:
    """Get the path to the assembly configurations file."""
    repo_path = Path(repo_root)
    config_dir = repo_path / "docs" / "maestro" / "repo"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "assembly_configs.json"


def load_asm_configs(repo_root: str) -> Dict[str, Any]:
    """Load assembly configurations from file."""
    config_file = _get_config_file_path(repo_root)
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Return default structure
        return {
            "configurations": {},
            "selected": None
        }


def save_asm_configs(repo_root: str, configs: Dict[str, Any]) -> None:
    """Save assembly configurations to file."""
    config_file = _get_config_file_path(repo_root)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2)


def list_asm_configs(repo_root: str, json_output: bool = False):
    """List all assembly configurations."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if json_output:
        print(json.dumps(configs, indent=2))
        return

    if not configs["configurations"]:
        print("No assembly configurations found.")
        return

    print_header("ASSEMBLY CONFIGURATIONS")
    print(f"\nRepository: {resolved_root}")
    print(f"Selected: {configs['selected'] or 'None'}")
    print("\nConfigurations:")
    
    for name, config in configs["configurations"].items():
        selected_marker = " (selected)" if name == configs["selected"] else ""
        print_info(f"  {name}{selected_marker}", 2)
        roots = config.get("roots", [])
        print_info(f"    Roots ({len(roots)}):", 3)
        for root in roots:
            print_info(f"      - {root}", 3)


def add_asm_config(repo_root: str, name: str, roots: List[str], json_output: bool = False):
    """Add a new assembly configuration."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name in configs["configurations"]:
        print_error(f"Configuration '{name}' already exists", 2)
        return

    # Process roots (handle potential comma-separated strings if passed as a single argument)
    processed_roots = []
    for r in roots:
        if ',' in r:
            processed_roots.extend([part.strip() for part in r.split(',') if part.strip()])
        else:
            processed_roots.append(r)

    # Validate roots exist
    invalid_roots = []
    normalized_roots = []
    for root in processed_roots:
        # Try relative to repo root first
        abs_path = os.path.normpath(os.path.join(resolved_root, root))
        if not os.path.exists(abs_path):
            # Try as absolute path
            abs_path = os.path.normpath(root)
            if not os.path.exists(abs_path):
                invalid_roots.append(root)
                continue
        
        # If it's inside repo, store as relative path
        try:
            rel = os.path.relpath(abs_path, resolved_root)
            if not rel.startswith('..'):
                normalized_roots.append(rel)
            else:
                normalized_roots.append(abs_path)
        except ValueError:
            normalized_roots.append(abs_path)

    if invalid_roots:
        print_error(f"The following paths don't exist: {', '.join(invalid_roots)}", 2)
        return

    configs["configurations"][name] = {
        "roots": normalized_roots,
        "created_at": str(os.times()[4])
    }
    
    save_asm_configs(resolved_root, configs)
    
    if json_output:
        result = {
            "status": "success",
            "message": f"Configuration '{name}' added successfully",
            "configuration": configs["configurations"][name]
        }
        print(json.dumps(result, indent=2))
    else:
        print_success(f"Configuration '{name}' added successfully with {len(normalized_roots)} roots", 2)


def remove_asm_config(repo_root: str, name: str, json_output: bool = False):
    """Remove an assembly configuration."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name not in configs["configurations"]:
        print_error(f"Configuration '{name}' does not exist", 2)
        return

    del configs["configurations"][name]
    
    # If this was the selected config, clear the selection
    if configs["selected"] == name:
        configs["selected"] = None
    
    save_asm_configs(resolved_root, configs)
    
    if json_output:
        result = {
            "status": "success",
            "message": f"Configuration '{name}' removed successfully"
        }
        print(json.dumps(result, indent=2))
    else:
        print_success(f"Configuration '{name}' removed successfully", 2)


def modify_asm_config(repo_root: str, name: str, roots: List[str], json_output: bool = False):
    """Modify an existing assembly configuration."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name not in configs["configurations"]:
        print_error(f"Configuration '{name}' does not exist", 2)
        return

    # Process roots (handle potential comma-separated strings if passed as a single argument)
    processed_roots = []
    for r in roots:
        if ',' in r:
            processed_roots.extend([part.strip() for part in r.split(',') if part.strip()])
        else:
            processed_roots.append(r)

    # Validate roots exist
    invalid_roots = []
    normalized_roots = []
    for root in processed_roots:
        abs_path = os.path.normpath(os.path.join(resolved_root, root))
        if not os.path.exists(abs_path):
            abs_path = os.path.normpath(root)
            if not os.path.exists(abs_path):
                invalid_roots.append(root)
                continue
        
        try:
            rel = os.path.relpath(abs_path, resolved_root)
            if not rel.startswith('..'):
                normalized_roots.append(rel)
            else:
                normalized_roots.append(abs_path)
        except ValueError:
            normalized_roots.append(abs_path)

    if invalid_roots:
        print_error(f"The following paths don't exist: {', '.join(invalid_roots)}", 2)
        return

    configs["configurations"][name]["roots"] = normalized_roots
    configs["configurations"][name]["updated_at"] = str(os.times()[4])
    
    save_asm_configs(resolved_root, configs)
    
    if json_output:
        result = {
            "status": "success",
            "message": f"Configuration '{name}' modified successfully",
            "configuration": configs["configurations"][name]
        }
        print(json.dumps(result, indent=2))
    else:
        print_success(f"Configuration '{name}' modified successfully with {len(normalized_roots)} roots", 2)


def select_asm_config(repo_root: str, name: str, json_output: bool = False):
    """Select an assembly configuration as the active one."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name not in configs["configurations"]:
        print_error(f"Configuration '{name}' does not exist", 2)
        return

    configs["selected"] = name
    save_asm_configs(resolved_root, configs)
    
    if json_output:
        result = {
            "status": "success",
            "message": f"Configuration '{name}' selected as active"
        }
        print(json.dumps(result, indent=2))
    else:
        print_success(f"Configuration '{name}' selected as active", 2)


def import_asm_config(repo_root: str, var_file_path: str, name: Optional[str] = None, json_output: bool = False):
    """Import assembly configuration from a .var file."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    
    if not os.path.exists(var_file_path):
        print_error(f".var file not found: {var_file_path}", 2)
        return

    # If name not provided, use filename without extension
    if not name:
        name = os.path.splitext(os.path.basename(var_file_path))[0]

    try:
        from maestro.builders.config import load_var_file
        variables = load_var_file(var_file_path)
        
        upp_val = variables.get("UPP", "")
        if not upp_val:
            print_error(f"No UPP key found in {var_file_path}", 2)
            return
            
        # UPP is semicolon separated list of paths
        roots = [r.strip() for root in upp_val.split(';') if (r := root.strip())]
        
        # Add the assembly config
        add_asm_config(resolved_root, name, roots, json_output)
        
    except Exception as e:
        print_error(f"Failed to import .var file: {e}", 2)


def show_asm_conf_help():
    """Show help for assembly configuration commands."""
    help_text = """
Maestro Assembly Configuration Commands (maestro repo asm conf)

Usage:
  maestro repo asm conf list                    # List all assembly configurations
  maestro repo asm conf add <name> [roots]      # Add a new assembly configuration
  maestro repo asm conf import <var_file> [--name <name>] # Import from U++ .var file
  maestro repo asm conf remove <name>          # Remove an assembly configuration
  maestro repo asm conf modify <name> [roots]   # Modify an existing configuration
  maestro repo asm conf select <name>          # Select an active configuration

Options:
  --path <path>                                # Path to repository root (default: auto-detect)
  --json                                       # Output results in JSON format

Examples:
  maestro repo asm conf list                   # List all configurations
  maestro repo asm conf add umk uppsrc,upptst  # Create umk config with two roots
  maestro repo asm conf import ~/upp/main.var  # Import from U++ assembly file
  maestro repo asm conf remove myconfig        # Remove a configuration
  maestro repo asm conf select umk             # Select umk config as active
"""
    print(help_text.strip())