"""
Repository resolve, refresh, and package commands.

Handles repository scanning, package queries, conventions, rules, and metadata management.
"""

from __future__ import annotations

import json
import os
import sys
import re
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro.modules.utils import (
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_debug,
    Colors
)

# Import from maestro.repo
from maestro.repo.build_config import get_package_config
from maestro.repo.upp_conditions import match_when

def handle_repo_pkg_list(packages: List[Dict[str, Any]], json_output: bool = False, repo_root: str = None):
    """List all packages in the repository (U++ and internal)."""
    if json_output:
        # JSON output with package names, numbers, and type info
        output = []
        for i, p in enumerate(packages, 1):
            pkg_type = p.get('_type', 'upp')
            entry = {
                'number': i,
                'name': p['name'],
                'type': pkg_type
            }

            if pkg_type == 'internal':
                entry['members'] = len(p.get('members', []))
                entry['guessed_type'] = p.get('guessed_type', 'misc')
                entry['root_path'] = p.get('root_path', '')
                if repo_root:
                    entry['rel_path'] = os.path.relpath(p['root_path'], repo_root)
            else:
                entry['files'] = len(p.get('files', []))
                entry['dir'] = p.get('dir', '')
                entry['build_system'] = p.get('build_system', 'upp')

                # Handle multi-build system packages
                if p.get('build_system') == 'multi' and 'build_systems' in p:
                    entry['build_systems'] = p['build_systems']
                    entry['primary_build_system'] = p.get('primary_build_system', p['build_systems'][0] if p['build_systems'] else 'unknown')
                else:
                    entry['build_systems'] = [p.get('build_system', 'upp')]

                if repo_root and p.get('dir'):
                    entry['rel_path'] = os.path.relpath(p['dir'], repo_root)

            output.append(entry)
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output with numbers and relative paths
        print_header(f"PACKAGES ({len(packages)} total)")
        sorted_packages = sorted(packages, key=lambda p: p['name'].lower())
        for i, pkg in enumerate(sorted_packages, 1):
            pkg_type = pkg.get('_type', 'upp')

            if pkg_type == 'internal':
                # Internal package display
                guessed_type = pkg.get('guessed_type', 'misc')
                members_count = len(pkg.get('members', []))
                root_path = pkg.get('root_path', '')
                rel_path = os.path.relpath(root_path, repo_root) if repo_root else root_path
                print_info(f"[{i:4d}] {pkg['name']:30s} {members_count:4d} items  [{guessed_type}] {rel_path}", 2)
            else:
                # Build system package display (U++, CMake, Make, etc.)
                build_system = pkg.get('build_system', 'upp')
                rel_path = os.path.relpath(pkg['dir'], repo_root) if repo_root else pkg['dir']

                # Handle multi-build system packages
                if build_system == 'multi':
                    build_systems = pkg.get('build_systems', ['multi'])
                    build_system_label = '+'.join(build_systems)
                    print_info(f"[{i:4d}] {pkg['name']:30s} {len(pkg['files']):4d} files  [{build_system_label}] {rel_path}", 2)
                elif build_system == 'upp':
                    print_info(f"[{i:4d}] {pkg['name']:30s} {len(pkg['files']):4d} files  {rel_path}", 2)
                else:
                    # Show build system label for non-U++ packages
                    print_info(f"[{i:4d}] {pkg['name']:30s} {len(pkg['files']):4d} files  [{build_system}] {rel_path}", 2)


def handle_repo_pkg_info(pkg: Dict[str, Any], json_output: bool = False):
    """Show detailed information about a package (U++ or internal)."""
    pkg_type = pkg.get('_type', 'upp')

    if json_output:
        print(json.dumps(pkg, indent=2))
    else:
        if pkg_type == 'internal':
            # Internal package info
            print_header(f"INTERNAL PACKAGE: {pkg['name']}")
            print(f"\nRoot path: {pkg.get('root_path', 'N/A')}")
            print(f"Type: {pkg.get('guessed_type', 'misc')}")
            print(f"Members: {len(pkg.get('members', []))}")

            # Show members
            if pkg.get('members'):
                print("\n" + "─" * 60)
                print_info("MEMBERS", 2)
                for member in sorted(pkg['members'])[:50]:
                    print_info(member, 2)
                if len(pkg['members']) > 50:
                    print_info(f"... and {len(pkg['members']) - 50} more", 2)
        else:
            # Build system package info (U++, CMake, etc.)
            build_system = pkg.get('build_system', 'upp')

            if build_system == 'upp':
                print_header(f"PACKAGE: {pkg['name']}")
            else:
                print_header(f"{build_system.upper()} PACKAGE: {pkg['name']}")

            print(f"\nDirectory: {pkg['dir']}")
            print(f"Build system: {build_system}")

            if build_system == 'upp':
                print(f"UPP file: {pkg['upp_path']}")

            print(f"Files: {len(pkg['files'])}")

        # Show parsed .upp metadata if available
        if pkg.get('upp'):
            upp = pkg['upp']
            print("\n" + "─" * 60)
            print_info("UPP METADATA", 2)

            if upp.get('description_text'):
                print_info(f"Description: {upp['description_text']}", 2)

            if upp.get('description_color'):
                r, g, b = upp['description_color']
                print_info(f"Color: RGB({r}, {g}, {b})", 2)

            if upp.get('uses'):
                print_info(f"Dependencies ({len(upp['uses'])}):", 2)
                for dep in upp['uses'][:10]:
                    print_info(f"  - {dep}", 2)
                if len(upp['uses']) > 10:
                    print_info(f"  ... and {len(upp['uses']) - 10} more", 2)

            if upp.get('acceptflags'):
                print_info(f"Accept flags: {', '.join(upp['acceptflags'])}", 2)

            if upp.get('libraries'):
                print_info(f"Libraries ({len(upp['libraries'])}):", 2)
                for lib in upp['libraries'][:5]:
                    print_info(f"  [{lib['condition']}] {lib['libs']}", 2)
                if len(upp['libraries']) > 5:
                    print_info(f"  ... and {len(upp['libraries']) - 5} more", 2)

            if upp.get('files'):
                print_info(f"Files declared in .upp: {len(upp['files'])}", 2)


def handle_repo_pkg_files(pkg: Dict[str, Any], json_output: bool = False):
    """List all files in a package."""
    pkg_type = pkg.get('_type', 'upp')

    if json_output:
        output = {
            'package': pkg['name'],
            'type': pkg_type
        }
        if pkg_type == 'internal':
            output['members'] = pkg.get('members', [])
        else:
            output['files'] = pkg.get('files', [])
            output['upp_files'] = pkg.get('upp', {}).get('files', [])
        print(json.dumps(output, indent=2))
    else:
        print_header(f"PACKAGE FILES: {pkg['name']}")

        # For internal packages, show members
        if pkg_type == 'internal':
            members = pkg.get('members', [])
            print(f"\n" + "─" * 60)
            print_info(f"Members in package ({len(members)}):", 2)
            for member in sorted(members):
                print_info(f"  {member}", 2)
        else:
            # Show files from .upp if available
            if pkg.get('upp') and pkg['upp'].get('files'):
                upp_files = pkg['upp']['files']
                print(f"\n" + "─" * 60)
                print_info(f"Files from .upp ({len(upp_files)}):", 2)
                for file_entry in upp_files:
                    file_info = file_entry['path']
                    modifiers = []
                    if file_entry.get('readonly'):
                        modifiers.append('readonly')
                    if file_entry.get('separator'):
                        modifiers.append('separator')
                    if file_entry.get('highlight'):
                        modifiers.append(f"highlight:{file_entry['highlight']}")
                    if file_entry.get('options'):
                        modifiers.append(f"options:{file_entry['options']}")

                    if modifiers:
                        file_info += f" [{', '.join(modifiers)}]"

                    print_info(f"  {file_info}", 2)

            # Show all filesystem files
            print(f"\n" + "─" * 60)
            files = pkg.get('files', [])
            print_info(f"All files in package ({len(files)}):", 2)
            for file in sorted(files):
                print_info(f"  {file}", 2)


def handle_repo_pkg_groups(pkg: Dict[str, Any], json_output: bool = False, show_groups: bool = True, group_filter: str = None):
    """Show package file groups."""
    pkg_type = pkg.get('_type', 'upp')

    if json_output:
        # Output groups in JSON format
        output = {
            'package': pkg['name'],
            'type': pkg_type,
        }

        # Add groups info if available
        if hasattr(pkg, 'groups'):
            output['groups'] = [
                {
                    'name': group.name,
                    'files': group.files,
                    'readonly': group.readonly,
                    'auto_generated': group.auto_generated
                } for group in pkg['groups']
            ]
        elif 'groups' in pkg:
            output['groups'] = [
                {
                    'name': group.name if hasattr(group, 'name') else group.get('name', 'Unknown'),
                    'files': group.files if hasattr(group, 'files') else group.get('files', []),
                    'readonly': group.readonly if hasattr(group, 'readonly') else group.get('readonly', False),
                    'auto_generated': group.auto_generated if hasattr(group, 'auto_generated') else group.get('auto_generated', False)
                } for group in pkg['groups']
            ]

        # Add ungrouped files
        if hasattr(pkg, 'ungrouped_files'):
            output['ungrouped_files'] = pkg['ungrouped_files']
        elif 'ungrouped_files' in pkg:
            output['ungrouped_files'] = pkg['ungrouped_files']
        else:
            output['ungrouped_files'] = pkg.get('files', [])

        print(json.dumps(output, indent=2))
    else:
        # Display formatted output following the documentation format
        build_system = pkg.get('build_system', 'upp')
        if build_system == 'upp':
            print_header(f"PACKAGE: {pkg['name']} (U++)")
        else:
            print_header(f"PACKAGE: {pkg['name']} ({build_system.upper()})")

        print(f"Root path: {pkg.get('dir', pkg.get('root_path', 'N/A'))}")

        # Count groups and files - handle both object and dict formats for groups
        groups = pkg.get('groups', [])
        ungrouped_files = pkg.get('ungrouped_files', pkg.get('files', []))

        # Calculate total files - handle group files as both objects and dicts
        total_files = len(ungrouped_files)
        for group in groups:
            if isinstance(group, dict):
                total_files += len(group.get('files', []))
            else:
                total_files += len(group.files)

        # Check if any groups are auto-generated
        has_auto_groups = any(
            (hasattr(g, 'auto_generated') and g.auto_generated) or
            (isinstance(g, dict) and g.get('auto_generated', False))
            for g in groups
        )
        print(f"Groups: {len(groups)} (auto-generated)" if has_auto_groups else f"Groups: {len(groups)}")
        print(f"Total files: {total_files}")

        # Show groups
        if groups:
            print("\n" + "─" * 80)
            for i, group in enumerate(groups):
                # Handle both object and dict formats
                if isinstance(group, dict):
                    group_name = group.get('name', 'Unknown')
                    files_list = group.get('files', [])
                    readonly_val = group.get('readonly', False)
                    auto_val = group.get('auto_generated', False)
                else:
                    group_name = getattr(group, 'name', 'Unknown')
                    files_list = getattr(group, 'files', [])
                    readonly_val = getattr(group, 'readonly', False)
                    auto_val = getattr(group, 'auto_generated', False)

                # Skip if filtering and doesn't match
                if group_filter and group_filter.lower() not in group_name.lower():
                    continue

                readonly_flag = " readonly" if readonly_val else ""
                auto_flag = " (auto-generated)" if auto_val else ""

                print_info(f"  GROUP: {group_name} ({len(files_list)} files){readonly_flag}{auto_flag}", 2)

                for j, file in enumerate(sorted(files_list)):
                    print_info(f"    {file}", 2)
                    if j >= 19:  # Show first 20 files per group
                        print_info(f"    ... ({len(files_list) - 20} more)", 2)
                        break

        # Show ungrouped files if any
        if ungrouped_files:
            if groups:
                print("\n" + "─" * 80)
            print_info(f"  UNGROUPED FILES ({len(ungrouped_files)}):", 2)
            for j, file in enumerate(sorted(ungrouped_files)):
                print_info(f"    {file}", 2)
                if j >= 19:  # Limit display to 20 ungrouped files
                    print_info(f"    ... ({len(ungrouped_files) - 20} more)", 2)
                    break


def handle_repo_pkg_search(pkg: Dict[str, Any], query: str, json_output: bool = False):
    """Search for files in a package matching a query."""
    pkg_type = pkg.get('_type', 'upp')

    # Filter files or members matching the query
    if pkg_type == 'internal':
        items = pkg.get('members', [])
    else:
        items = pkg.get('files', [])

    matches = [f for f in items if query.lower() in f.lower()]

    if json_output:
        output = {
            'package': pkg['name'],
            'type': pkg_type,
            'query': query,
            'matches': matches
        }
        print(json.dumps(output, indent=2))
    else:
        print_header(f"SEARCH: {pkg['name']} / {query}")
        item_type = "members" if pkg_type == 'internal' else "files"
        print(f"\nFound {len(matches)} {item_type} matching '{query}':")
        for item in sorted(matches):
            print_info(f"  {item}", 2)


def handle_repo_pkg_tree(pkg: Dict[str, Any], all_packages: List[Dict[str, Any]], json_output: bool = False, deep: bool = False, config_flags: List[str] = None):
    """Show dependency tree for a package (with cycle detection and duplicate suppression)."""
    def build_tree(pkg_name: str, path_visited: set, global_visited: set, depth: int = 0, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Recursively build dependency tree with cycle detection and duplicate suppression.

        Args:
            pkg_name: Name of package to process
            path_visited: Set of packages visited in current path (for circular detection)
            global_visited: Set of packages already expanded (for duplicate suppression)
            depth: Current depth in tree
            max_depth: Maximum depth to traverse
        """
        if depth > max_depth:
            return [{'name': pkg_name, 'error': 'max_depth_exceeded'}]

        # Check for circular dependency in current path
        if pkg_name in path_visited:
            return [{'name': pkg_name, 'circular': True}]

        # Check if already shown (unless in deep mode)
        if not deep and pkg_name in global_visited:
            return [{'name': pkg_name, 'already_shown': True}]

        # Find the package - try multiple strategies
        pkg_dict = None

        # Strategy 1: Exact name match
        pkg_dict = next((p for p in all_packages if p['name'] == pkg_name), None)

        # Strategy 2: Path-based match (e.g., api/MidiFile matches uppsrc/api/MidiFile)
        if not pkg_dict and '/' in pkg_name:
            for p in all_packages:
                if p['dir'].endswith(pkg_name) or p['dir'].endswith('/' + pkg_name):
                    pkg_dict = p
                    break

        # Strategy 3: Basename match (extract last component)
        if not pkg_dict and '/' in pkg_name:
            basename = pkg_name.split('/')[-1]
            pkg_dict = next((p for p in all_packages if p['name'] == basename), None)

        if not pkg_dict:
            return [{'name': pkg_name, 'error': 'not_found'}]

        # Mark as visited globally (so we don't expand it again)
        global_visited.add(pkg_name)

        # Get dependencies from parsed .upp or build system metadata
        deps = []
        if pkg_dict.get('upp') and pkg_dict['upp'].get('uses'):
            # U++ package dependencies
            uses_list = pkg_dict['upp']['uses']
            # Handle both old format (list of strings) and new format (list of dicts)
            for use in uses_list:
                if isinstance(use, dict):
                    deps.append({'package': use['package'], 'condition': use.get('condition')})
                else:
                    # Backward compatibility with old format
                    deps.append({'package': use, 'condition': None})
        elif pkg_dict.get('dependencies'):
            # Other build systems (Gradle, Maven, etc.)
            for dep_name in pkg_dict['dependencies']:
                deps.append({'package': dep_name, 'condition': None})

        # Add to current path for circular detection
        path_visited_copy = path_visited.copy()
        path_visited_copy.add(pkg_name)

        tree_node = {
            'name': pkg_name,
            'dependencies': []
        }

        for dep_info in deps:
            dep_name = dep_info['package']
            dep_condition = dep_info.get('condition')

            # If config_flags is provided, filter dependencies based on conditions
            if config_flags is not None and dep_condition:
                # Skip this dependency if condition doesn't match the config flags
                if not match_when(dep_condition, config_flags):
                    continue

            child_tree = build_tree(dep_name, path_visited_copy, global_visited, depth + 1, max_depth)

            # Add condition to each child node
            for child in child_tree:
                if dep_condition:
                    child['condition'] = dep_condition

            tree_node['dependencies'].extend(child_tree)

        return [tree_node]

    tree = build_tree(pkg['name'], set(), set())

    if json_output:
        print(json.dumps(tree, indent=2))
    else:
        print_header(f"DEPENDENCY TREE: {pkg['name']}")

        def print_tree(nodes: List[Dict[str, Any]], prefix: str = ""):
            """Print tree in human-readable format."""
            for i, node in enumerate(nodes):
                is_last = i == len(nodes) - 1
                connector = "└── " if is_last else "├── "

                name = node['name']
                suffix = ""
                condition_text = ""

                # Handle condition display
                if node.get('condition'):
                    # ANSI dark gray color code
                    dark_gray = "\033[90m"
                    reset = "\033[0m"
                    condition_text = f" {dark_gray}({node['condition']}){reset}"

                if node.get('circular'):
                    suffix = " [CIRCULAR]"
                elif node.get('already_shown'):
                    suffix = " [see above]"
                elif node.get('error'):
                    suffix = f" [ERROR: {node['error']}]"

                print(prefix + connector + name + condition_text + suffix)

                if node.get('dependencies') and not node.get('already_shown'):
                    extension = "    " if is_last else "│   "
                    print_tree(node['dependencies'], prefix + extension)

        print_tree(tree)


def handle_repo_pkg_conf(pkg: Dict[str, Any], json_output: bool = False):
    """Show build configurations for a package across all build systems."""
    # Convert the pkg dict to PackageInfo object for compatibility
    # Create groups from the dict data
    groups = []
    for group_data in pkg.get('groups', []):
        groups.append(FileGroup(
            name=group_data.get('name', ''),
            files=group_data.get('files', []),
            readonly=group_data.get('readonly', False),
            auto_generated=group_data.get('auto_generated', False)
        ))

    # Create PackageInfo object from the dictionary
    package_info = PackageInfo(
        name=pkg['name'],
        dir=pkg['dir'],
        upp_path=pkg.get('upp_path', ''),
        files=pkg.get('files', []),
        upp=pkg.get('upp'),
        build_system=pkg.get('build_system', 'upp'),
        dependencies=pkg.get('dependencies', []),
        groups=groups,
        ungrouped_files=pkg.get('ungrouped_files', pkg.get('files', []))
    )

    # Get complete configuration using the build_config module
    config = get_package_config(package_info)

    if json_output:
        print(json.dumps(config, indent=2))
        return

    # Display configuration in a human-readable format
    print(f"Build configurations for package '{pkg['name']}' ({pkg.get('build_system', 'upp').upper()}):")
    print(f"  Directory: {config.get('directory', 'N/A')}")

    # Display U++ specific configurations
    if pkg.get('build_system') == 'upp':
        uses = config.get('uses', [])
        if uses:
            print(f"  Dependencies ({len(uses)}):")
            for dep in uses[:10]:  # Show first 10
                print(f"    - {dep}")
            if len(uses) > 10:
                print(f"    ... and {len(uses) - 10} more")

        mainconfigs = config.get('mainconfigs', [])
        if mainconfigs:
            print(f"  Build configurations:")
            for i, cfg in enumerate(mainconfigs):
                print(f"    [{i+1}] {cfg}")

    # Display CMake specific configurations
    elif pkg.get('build_system') == 'cmake':
        targets = config.get('targets', [])
        if targets:
            print(f"  Build targets ({len(targets)}):")
            for target in targets[:10]:
                print(f"    - {target}")
            if len(targets) > 10:
                print(f"    ... and {len(targets) - 10} more")

        includes = config.get('include_directories', [])
        if includes:
            print(f"  Include directories ({len(includes)}):")
            for inc in includes[:5]:
                print(f"    - {inc}")
            if len(includes) > 5:
                print(f"    ... and {len(includes) - 5} more")

    # Display Gradle specific configurations
    elif pkg.get('build_system') == 'gradle':
        plugins = config.get('plugins', [])
        if plugins:
            print(f"  Plugins ({len(plugins)}):")
            for plugin in plugins[:10]:
                print(f"    - {plugin}")
            if len(plugins) > 10:
                print(f"    ... and {len(plugins) - 10} more")

        dependencies = config.get('dependencies', [])
        if dependencies:
            print(f"  Dependencies ({len(dependencies)}):")
            for dep in dependencies[:10]:
                print(f"    - {dep}")
            if len(dependencies) > 10:
                print(f"    ... and {len(dependencies) - 10} more")

    # Display Maven specific configurations
    elif pkg.get('build_system') == 'maven':
        dependencies = config.get('dependencies', [])
        if dependencies:
            print(f"  Dependencies ({len(dependencies)}):")
            for dep in dependencies[:10]:
                print(f"    - {dep}")
            if len(dependencies) > 10:
                print(f"    ... and {len(dependencies) - 10} more")

        modules = config.get('modules', [])
        if modules:
            print(f"  Modules ({len(modules)}):")
            for module in modules[:10]:
                print(f"    - {module}")
            if len(modules) > 10:
                print(f"    ... and {len(modules) - 10} more")

    # Display generic information for other build systems
    else:
        dependencies = config.get('dependencies', [])
        if dependencies:
            print(f"  Dependencies ({len(dependencies)}):")
            for dep in dependencies[:10]:
                print(f"    - {dep}")
            if len(dependencies) > 10:
                print(f"    ... and {len(dependencies) - 10} more")


def handle_repo_refresh_all(repo_root: str, verbose: bool = False):
    """
    Execute full repository refresh: resolve + conventions + rules analysis.

    Args:
        repo_root: Path to repository root
        verbose: Verbose output flag
    """
    from maestro.repo.repo_scanner import scan_upp_repo_v2
    from maestro.global_index import update_global_repo_index

    print_header("REPOSITORY REFRESH")
    print(f"\nRepository: {repo_root}\n")

    # Step 1: Repo resolve (scan packages, assemblies, build systems)
    print_info("Step 1/3: Repository resolve (scanning packages and build systems)...", 2)
    repo_result = scan_upp_repo_v2(repo_root, verbose=verbose, include_user_config=True)
    write_repo_artifacts(repo_root, repo_result, verbose=verbose)
    print_success(f"  Found {len(repo_result.packages_detected)} packages, {len(repo_result.assemblies_detected)} assemblies", 2)

    # Step 2: Convention detection (placeholder for now - will be implemented in RF3)
    print_info("\nStep 2/3: Convention detection...", 2)
    print_warning("  Convention detection not yet implemented (Phase RF3)", 2)
    print_info("  Placeholder: Would auto-detect naming conventions from codebase", 2)

    # Step 3: Rules analysis (placeholder for now - will be implemented in RF4)
    print_info("\nStep 3/3: Rules analysis...", 2)
    print_info("  docs/RepoRules.md exists and is ready for manual editing", 2)
    rules_file = os.path.join(repo_root, 'docs', 'RepoRules.md')
    if os.path.exists(rules_file):
        print_success(f"  Rules file: {rules_file}", 2)
    else:
        print_warning(f"  Rules file not found. Run 'maestro init' to create it.", 2)

    # Update global index
    update_global_repo_index(repo_root, verbose)

    print("\n" + "─" * 60)
    print_success("Refresh complete!", 2)
    print_info("\nNext steps:", 2)
    print_info("  maestro repo hier              - View repository hierarchy", 3)
    print_info("  maestro repo conventions       - View detected conventions", 3)
    print_info("  maestro repo rules             - View repository rules", 3)


def handle_repo_refresh_help():
    """
    Show what 'maestro repo refresh all' does.
    """
    print_header("REFRESH ALL - WHAT IT DOES")
    print("""
The 'maestro repo refresh all' command performs a complete repository analysis:

Step 1: Repository Resolve
  - Scans for packages across all build systems (U++, CMake, Make, Autoconf, Maven, Gradle, etc.)
  - Detects assemblies and their structure
  - Identifies build configurations
  - Writes scan results to docs/maestro/repo_model.json

Step 2: Convention Detection (Phase RF3 - Not Yet Implemented)
  - Auto-detects naming conventions (camelCase, snake_case, PascalCase, UPPER_CASE)
  - Identifies file organization patterns
  - Detects framework-specific conventions (U++, Qt, etc.)
  - Updates docs/RepoRules.md with detected conventions

Step 3: Rules Analysis (Phase RF4 - Partially Implemented)
  - Ensures docs/RepoRules.md exists
  - Ready for manual editing of architecture, security, performance, and style rules
  - These rules are injected into AI prompts based on context

Global Index Update:
  - Updates $HOME/.maestro/repos.json with this repository's information
  - Enables cross-repository solution sharing

Usage:
  maestro repo refresh all [--path <path>] [-v]

Options:
  --path <path>  - Path to repository (default: auto-detect via docs/maestro/)
  -v, --verbose  - Show detailed output
""")


def handle_repo_hier_edit(repo_root: str):
    """
    Edit hierarchy overrides in $EDITOR.

    Args:
        repo_root: Repository root path
    """
    repo_dir = ensure_repo_truth_dir(repo_root) / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    overrides_file = repo_dir / "hierarchy_overrides.json"

    # Create template if it doesn't exist
    if not os.path.exists(overrides_file):
        template = {
            '_comment': 'Manual hierarchy overrides. Edit this file to customize the repository hierarchy.',
            '_instructions': [
                'This file allows you to override the auto-detected hierarchy.',
                'You can rename assemblies, packages, or reorganize the structure.',
                'Changes here take precedence over auto-detected values.',
                'Run "maestro repo hier --rebuild" after editing to see changes.'
            ],
            'repository': {
                'assemblies': [],
                'standalone_packages': []
            }
        }

        with open(overrides_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)

        print_info(f"Created hierarchy overrides template at {overrides_file}", 2)

    # Open in editor
    editor = os.environ.get('EDITOR', 'nano')

    try:
        subprocess.run([editor, str(overrides_file)], check=True)
        print_success("Hierarchy overrides updated. Run 'maestro repo hier --rebuild' to see changes.", 2)
    except subprocess.CalledProcessError:
        print_error(f"Failed to open editor: {editor}", 2)
        sys.exit(1)
    except FileNotFoundError:
        print_error(f"Editor not found: {editor}. Set $EDITOR environment variable.", 2)
        sys.exit(1)


def handle_repo_hier(repo_root: str, json_output: bool = False, show_files: bool = False, rebuild: bool = False):
    """
    Show AI-analyzed repository hierarchy.

    Args:
        repo_root: Path to repository root
        json_output: Output in JSON format
        show_files: Show file groups in tree view
        rebuild: Force rebuild of hierarchy from scan data
    """
    # Import needed types locally
    from maestro.repo.scanner import AssemblyInfo, RepoScanResult

    # Try to load existing hierarchy unless rebuild requested
    hierarchy = None
    if not rebuild:
        hierarchy = load_hierarchy(repo_root)

    # If no hierarchy exists or rebuild requested, generate it
    if hierarchy is None:
        # Load repo scan results
        model_path = repo_model_path(repo_root, require=True)
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except Exception as e:
            print_error(f"Failed to read repository model: {e}", 2)
            sys.exit(1)

        # Reconstruct RepoScanResult from index data
        packages = []
        for pkg_data in index_data.get('packages_detected', []):
            # Reconstruct FileGroup objects
            groups = []
            for group_data in pkg_data.get('groups', []):
                groups.append(FileGroup(
                    name=group_data.get('name', ''),
                    files=group_data.get('files', []),
                    readonly=group_data.get('readonly', False),
                    auto_generated=group_data.get('auto_generated', False)
                ))

            packages.append(PackageInfo(
                name=pkg_data.get('name', ''),
                dir=pkg_data.get('dir', ''),
                upp_path=pkg_data.get('upp_path', ''),
                files=pkg_data.get('files', []),
                build_system=pkg_data.get('build_system', 'upp'),
                groups=groups,
                ungrouped_files=pkg_data.get('ungrouped_files', [])
            ))

        assemblies = []
        for asm_data in index_data.get('assemblies_detected', []):
            assemblies.append(AssemblyInfo(
                name=asm_data.get('name', ''),
                root_path=asm_data.get('root_path', ''),
                package_folders=asm_data.get('package_folders', []),
                assembly_type=asm_data.get('assembly_type', 'upp')
            ))

        repo_scan = RepoScanResult(
            assemblies_detected=assemblies,
            packages_detected=packages
        )

        # Build hierarchy
        hierarchy = build_repo_hierarchy(repo_scan, repo_root)

        # Save for future use
        save_hierarchy(hierarchy, repo_root, verbose=False)

    # Load and apply overrides if they exist
    overrides = load_hierarchy_overrides(repo_root)
    if overrides:
        hierarchy = merge_hierarchy_overrides(hierarchy, overrides)

    # Output hierarchy
    if json_output:
        print(json.dumps(hierarchy, indent=2))
    else:
        print_header("REPOSITORY HIERARCHY")
        if overrides:
            print(f"{Colors.YELLOW}Note: Manual overrides applied from hierarchy_overrides.json{Colors.RESET}\n")
        print_hierarchy_tree(hierarchy, show_files=show_files)
        print()  # Empty line at end


def handle_repo_conventions_detect(repo_root: str, verbose: bool = False):
    """
    Detect naming conventions from codebase.

    Args:
        repo_root: Path to repository root
        verbose: Verbose output flag
    """
    print_header("CONVENTION DETECTION")
    print(f"\nRepository: {repo_root}\n")

    # Check if RepoRules.md exists
    rules_file = os.path.join(repo_root, 'docs', 'RepoRules.md')
    if not os.path.exists(rules_file):
        print_error("docs/RepoRules.md not found. Run 'maestro init' to create it.", 2)
        sys.exit(1)

    # Placeholder for convention detection
    print_warning("Convention detection not yet fully implemented (Phase RF3)", 2)
    print_info("This command will auto-detect naming conventions from your codebase", 2)


def handle_repo_conventions_show(repo_root: str):
    """
    Show current conventions from docs/RepoRules.md.

    Args:
        repo_root: Path to repository root
    """
    rules_file = os.path.join(repo_root, 'docs', 'RepoRules.md')

    if not os.path.exists(rules_file):
        print_error(f"docs/RepoRules.md not found. Run 'maestro init' to create it.", 2)
        sys.exit(1)

    print_header("REPOSITORY CONVENTIONS")
    print(f"\nFrom: {rules_file}\n")

    # Read and display the conventions section
    with open(rules_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract conventions section
    conventions_match = re.search(r'## Conventions\n(.+?)(?=\n##|\Z)', content, re.DOTALL)

    if conventions_match:
        conventions_text = conventions_match.group(1)
        print(conventions_text.strip())
    else:
        print_warning("No conventions section found in RepoRules.md", 2)

    print("\n" + "─" * 60)
    print_info("To edit conventions:", 2)
    print_info("  maestro repo conventions detect    - Auto-detect (Phase RF3 - not yet implemented)", 3)
    print_info("  maestro repo rules edit            - Edit manually", 3)


def handle_repo_rules_show(repo_root: str):
    """
    Show repository rules from docs/RepoRules.md.

    Args:
        repo_root: Path to repository root
    """
    rules_file = os.path.join(repo_root, 'docs', 'RepoRules.md')

    if not os.path.exists(rules_file):
        print_error(f"docs/RepoRules.md not found. Run 'maestro init' to create it.", 2)
        sys.exit(1)

    print_header("REPOSITORY RULES")
    print(f"\nFrom: {rules_file}\n")

    # Read and display the entire file
    with open(rules_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(content)

    print("\n" + "─" * 60)
    print_info("To edit rules:", 2)
    print_info("  maestro repo rules edit", 3)


def handle_repo_rules_edit(repo_root: str):
    """
    Edit repository rules in $EDITOR.

    Args:
        repo_root: Path to repository root
    """
    rules_file = os.path.join(repo_root, 'docs', 'RepoRules.md')

    if not os.path.exists(rules_file):
        print_error(f"docs/RepoRules.md not found. Run 'maestro init' to create it.", 2)
        sys.exit(1)

    # Use vi as fallback if EDITOR is not set
    editor = os.environ.get('EDITOR', 'vi')

    print_info(f"Opening {rules_file} in {editor}...", 2)

    try:
        subprocess.run([editor, rules_file])
        print_success("Rules file updated", 2)
    except FileNotFoundError:
        print_error(f"Editor '{editor}' not found.", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not open editor: {str(e)}", 2)
        sys.exit(1)


def handle_repo_rules_inject(repo_root: str, context: str = 'general'):
    """
    Show rules formatted for AI injection (for testing/debugging).

    Args:
        repo_root: Path to repository root
        context: Context for rule selection
    """
    print_header("REPOSITORY RULES - AI INJECTION FORMAT")
    print(f"\nContext: {context}\n")

    print_warning("Rule injection formatting not yet fully implemented (Phase RF4)", 2)
    print_info("This command will format rules for AI prompt injection", 2)


