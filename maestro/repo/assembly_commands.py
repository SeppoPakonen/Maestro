import json
import os
from pathlib import Path
from typing import Dict, Any
from .assembly import AssemblyInfo


def handle_asm_command(args):
    """
    Handle 'maestro repo asm' commands.

    Subcommands:
    - list: List all assemblies
    - show: Show details for specific assembly
    - help: Show help
    """
    repo_path = args.path if hasattr(args, 'path') and args.path else '.'

    if args.asm_subcommand in ['list', 'ls', 'l']:
        list_assemblies(repo_path, getattr(args, 'json', False))
    elif args.asm_subcommand in ['show', 's']:
        # Handle 'show' subcommand (and its alias 's') to show assembly details
        if hasattr(args, 'assembly_name') and args.assembly_name:
            show_assembly(repo_path, args.assembly_name, getattr(args, 'json', False))
        else:
            print("Error: Assembly name required for 'show' command")
            show_asm_help()
    elif args.asm_subcommand in ['help', 'h']:
        show_asm_help()
    elif args.asm_subcommand is None:
        # If no subcommand provided, show help
        show_asm_help()
    else:
        print(f"Unknown assembly command: {args.asm_subcommand}")
        show_asm_help()


def load_assemblies_data(repo_root: str) -> Dict[str, Any]:
    """Load assemblies data from .maestro/repo/assemblies.json"""
    maestro_dir = os.path.join(repo_root, '.maestro', 'repo')
    assemblies_file = os.path.join(maestro_dir, 'assemblies.json')
    
    if os.path.exists(assemblies_file):
        with open(assemblies_file, 'r') as f:
            return json.load(f)
    return {"assemblies": []}


def list_assemblies(repo_root: str, json_output: bool = False):
    """List all detected assemblies."""
    assemblies_data = load_assemblies_data(repo_root)
    assemblies = assemblies_data.get('assemblies', [])
    
    if json_output:
        print(json.dumps(assemblies_data, indent=2))
        return
    
    if not assemblies:
        print("No assemblies found in repository.")
        return
    
    print("Assemblies in repository:\n")
    
    for i, asm in enumerate(assemblies, 1):
        assembly_type_display = asm['assembly_type'].upper()
        if asm['assembly_type'] == 'upp':
            assembly_type_display = 'U++'
        elif asm['assembly_type'] == 'multi':
            assembly_type_display = f"Multi-type ({', '.join(asm['build_systems'])})"
        elif asm['assembly_type'] in ['gradle', 'maven']:
            assembly_type_display = f"Java/{asm['assembly_type'].title()}"
        elif asm['assembly_type'] in ['cmake', 'autoconf', 'visual_studio']:
            assembly_type_display = asm['assembly_type'].title()
        
        print(f"  {i}. {asm['name']} ({assembly_type_display})")
        print(f"     Location: {asm['dir']}")
        print(f"     Packages: {len(asm['packages'])} package{'s' if len(asm['packages']) != 1 else ''}")
        if asm['build_systems']:
            build_systems_str = ', '.join(asm['build_systems'])
            print(f"     Build Systems: {build_systems_str}")
        print()


def show_assembly(repo_root: str, assembly_name: str, json_output: bool = False):
    """Show detailed information about a specific assembly."""
    assemblies_data = load_assemblies_data(repo_root)
    assemblies = assemblies_data.get('assemblies', [])
    
    # Find the specific assembly
    target_assembly = None
    for asm in assemblies:
        if asm['name'] == assembly_name:
            target_assembly = asm
            break
    
    if not target_assembly:
        print(f"Assembly '{assembly_name}' not found in repository.")
        return
    
    if json_output:
        print(json.dumps(target_assembly, indent=2))
        return
    
    assembly_type_display = target_assembly['assembly_type'].upper()
    if target_assembly['assembly_type'] == 'upp':
        assembly_type_display = 'U++'
    elif target_assembly['assembly_type'] == 'multi':
        assembly_type_display = f"Multi-type ({', '.join(target_assembly['build_systems'])})"
    elif target_assembly['assembly_type'] in ['gradle', 'maven']:
        assembly_type_display = f"Java/{target_assembly['assembly_type'].title()}"
    elif target_assembly['assembly_type'] in ['cmake', 'autoconf', 'visual_studio']:
        assembly_type_display = target_assembly['assembly_type'].title()
    
    print(f"Assembly: {target_assembly['name']}\n")
    print(f"  Type: {assembly_type_display} Assembly")
    print(f"  Location: {target_assembly['dir']}")
    
    if target_assembly['build_systems']:
        build_systems_str = ', '.join(target_assembly['build_systems'])
        print(f"  Build System{'s' if len(target_assembly['build_systems']) > 1 else ''}: {build_systems_str}")
    
    print(f"\n  Packages ({len(target_assembly['packages'])}):")
    for pkg in target_assembly['packages']:
        print(f"    - {pkg}")
    
    print(f"\n  Package Directories:")
    for pkg_dir in target_assembly['package_dirs']:
        rel_path = os.path.relpath(pkg_dir, target_assembly['dir'])
        if rel_path == '.':
            print(f"    {os.path.basename(target_assembly['dir'])}/")
        else:
            print(f"    {rel_path}/")


def show_asm_help():
    """Show help for assembly commands."""
    help_text = """
Maestro Assembly Commands (maestro repo asm)

Usage:
  maestro repo asm list              # List all assemblies in repository
  maestro repo asm show <name>       # Show details for specific assembly
  maestro repo asm help              # Show this help message

Options:
  --path <path>                      # Path to repository root (default: auto-detect)
  --json                             # Output results in JSON format

Examples:
  maestro repo asm list              # List all assemblies
  maestro repo asm show FolderZ      # Show details for specific assembly
  maestro repo asm show myproject --json  # Show assembly in JSON format
"""
    print(help_text.strip())