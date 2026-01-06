"""
Assembly configuration commands for Maestro.

Handles assembly configurations that define which parts of the repository to include
in builds, helping to resolve the "multiple packages" issue by creating specific
configurations for different use cases.
"""

import json
import os
from typing import Any, Dict, List
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
        print_info(f"    Packages ({len(config['packages'])}):", 3)
        for pkg in config["packages"][:5]:  # Show first 5 packages
            print_info(f"      - {pkg}", 3)
        if len(config["packages"]) > 5:
            print_info(f"      ... and {len(config['packages']) - 5} more", 3)


def add_asm_config(repo_root: str, name: str, packages: List[str], json_output: bool = False):
    """Add a new assembly configuration."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name in configs["configurations"]:
        print_error(f"Configuration '{name}' already exists", 2)
        return

    # Validate packages exist in the repository
    assemblies_data = load_assemblies_data(resolved_root)
    all_packages = assemblies_data.get('packages', [])
    all_package_names = [pkg.get('name') for pkg in all_packages if pkg.get('name')]
    
    invalid_packages = [pkg for pkg in packages if pkg not in all_package_names]
    if invalid_packages:
        print_error(f"The following packages don't exist in the repository: {', '.join(invalid_packages)}", 2)
        return

    configs["configurations"][name] = {
        "packages": packages,
        "created_at": str(os.times()[4])  # Using process time as timestamp
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
        print_success(f"Configuration '{name}' added successfully with {len(packages)} packages", 2)


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


def modify_asm_config(repo_root: str, name: str, packages: List[str], json_output: bool = False):
    """Modify an existing assembly configuration."""
    resolved_root = find_repo_root() if not repo_root else repo_root
    configs = load_asm_configs(resolved_root)
    
    if name not in configs["configurations"]:
        print_error(f"Configuration '{name}' does not exist", 2)
        return

    # Validate packages exist in the repository
    assemblies_data = load_assemblies_data(resolved_root)
    all_packages = assemblies_data.get('packages', [])
    all_package_names = [pkg.get('name') for pkg in all_packages if pkg.get('name')]
    
    invalid_packages = [pkg for pkg in packages if pkg not in all_package_names]
    if invalid_packages:
        print_error(f"The following packages don't exist in the repository: {', '.join(invalid_packages)}", 2)
        return

    configs["configurations"][name]["packages"] = packages
    configs["configurations"][name]["updated_at"] = str(os.times()[4])  # Using process time as timestamp
    
    save_asm_configs(resolved_root, configs)
    
    if json_output:
        result = {
            "status": "success",
            "message": f"Configuration '{name}' modified successfully",
            "configuration": configs["configurations"][name]
        }
        print(json.dumps(result, indent=2))
    else:
        print_success(f"Configuration '{name}' modified successfully with {len(packages)} packages", 2)


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


def show_asm_conf_help():
    """Show help for assembly configuration commands."""
    help_text = """
Maestro Assembly Configuration Commands (maestro repo asm conf)

Usage:
  maestro repo asm conf list                    # List all assembly configurations
  maestro repo asm conf add <name> [packages]  # Add a new assembly configuration
  maestro repo asm conf remove <name>          # Remove an assembly configuration
  maestro repo asm conf modify <name> [packages] # Modify an existing configuration
  maestro repo asm conf select <name>          # Select an active configuration

Options:
  --path <path>                                # Path to repository root (default: auto-detect)
  --json                                       # Output results in JSON format

Examples:
  maestro repo asm conf list                   # List all configurations
  maestro repo asm conf add umk examples,tutorial,reference,upptst,uppsrc  # Create umk config
  maestro repo asm conf remove myconfig        # Remove a configuration
  maestro repo asm conf modify umk examples,uppsrc  # Modify existing config
  maestro repo asm conf select umk             # Select umk config as active
"""
    print(help_text.strip())