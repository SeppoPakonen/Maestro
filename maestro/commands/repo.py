"""
Repository analysis and resolution commands for Maestro CLI.

Commands:
- maestro repo resolve - Scan repository for packages across build systems
- maestro repo show - Show repository scan results
- maestro repo pkg - Package query and inspection
- maestro repo conf - Show build configurations
- maestro repo asm - Assembly management
- maestro repo refresh - Refresh repository metadata
- maestro repo hier - Repository hierarchy
- maestro repo conventions - Naming conventions
- maestro repo rules - Repository rules
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from maestro.modules
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
from maestro.repo.package import PackageInfo, FileGroup
from maestro.repo.build_config import get_package_config
from maestro.repo.upp_conditions import match_when
from maestro.repo.storage import (
    find_repo_root as find_repo_root_v3,
    ensure_repo_truth_dir,
    write_repo_model,
    write_repo_state,
    default_repo_state,
    load_repo_model,
    repo_model_path,
    REPO_TRUTH_REL,
)
from maestro.git_guard import check_branch_guard


# Helper functions for repository operations

def find_repo_root(start_path: str = None) -> str:
    """
    Find the repository root by searching for docs/maestro/ directory.

    Args:
        start_path: Directory to start searching from (default: current directory)

    Returns:
        Path to the repository root

    Raises:
        SystemExit: If docs/maestro/ directory is not found
    """
    return find_repo_root_v3(start_path)


def write_repo_artifacts(repo_root: str, scan_result, verbose: bool = False):
    """
    Write repository scan artifacts to docs/maestro/ (repo truth).

    Creates:
    - repo_model.json: Full structured scan result (JSON only)
    - repo_state.json: Repository state metadata (JSON only)

    Args:
        repo_root: Path to repository root
        scan_result: Scan result to persist (RepoScanResult)
        verbose: If True, print paths being written
    """
    ensure_repo_truth_dir(repo_root, create=True)

    def _serialize_upp_payload(upp_payload: Optional[dict]) -> Optional[dict]:
        if not upp_payload or not isinstance(upp_payload, dict):
            return upp_payload
        serialized = dict(upp_payload)
        groups = serialized.get("groups", [])
        if isinstance(groups, list):
            serialized["groups"] = [
                {
                    "name": group.name,
                    "files": group.files,
                    "readonly": getattr(group, "readonly", False),
                    "auto_generated": getattr(group, "auto_generated", False),
                } if isinstance(group, FileGroup) else group
                for group in groups
            ]
        return serialized

    def _stable_id(seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def _build_assemblies_and_packages() -> tuple[list[dict], list[dict]]:
        repo_root_path = Path(repo_root).resolve()
        assemblies: list[dict] = []
        assembly_by_root: dict[str, dict] = {}
        for asm in scan_result.assemblies_detected:
            root_path = Path(asm.root_path).resolve()
            try:
                root_relpath = os.path.relpath(root_path, repo_root_path)
            except ValueError:
                continue
            if root_relpath == '.':
                root_relpath = '.'
            assembly_id = _stable_id(f"assembly:{asm.name}:{root_relpath}")
            entry = {
                "assembly_id": assembly_id,
                "name": asm.name,
                "root_relpath": root_relpath,
                "kind": getattr(asm, "assembly_type", "upp"),
                "package_ids": [],
            }
            assemblies.append(entry)
            assembly_by_root[os.path.normpath(str(root_path))] = entry

        package_entries_by_assembly: dict[str, list[dict]] = {a["assembly_id"]: [] for a in assemblies}
        unassigned_packages: list[dict] = []

        for pkg in scan_result.packages_detected:
            pkg_path = Path(pkg.dir).resolve()
            pkg_dir_rel = os.path.relpath(pkg_path, repo_root_path)

            # Find the best matching assembly for this package
            # A package belongs to an assembly if the package root path is inside the assembly root path
            # Priority: more specific paths first (longest match)
            best_assembly_entry = None
            best_match_length = -1

            for asm_path, asm_entry in assembly_by_root.items():
                asm_path_obj = Path(asm_path).resolve()
                # Check if the package directory is under the assembly directory
                try:
                    # If the package path is the same as assembly path, it belongs to that assembly
                    if pkg_path == asm_path_obj:
                        # Exact match, this is the best possible match
                        best_assembly_entry = asm_entry
                        best_match_length = len(str(asm_path_obj))
                        break
                    # If the package path is under the assembly path, it belongs to that assembly
                    rel_path = pkg_path.relative_to(asm_path_obj)
                    if not str(rel_path).startswith('..'):
                        # This assembly contains the package, check if it's a better match than previous
                        current_match_length = len(str(asm_path_obj))
                        if current_match_length > best_match_length:
                            best_assembly_entry = asm_entry
                            best_match_length = current_match_length
                except ValueError:
                    # pkg_path is not under asm_path_obj, continue to next assembly
                    continue

            assembly_id = best_assembly_entry["assembly_id"] if best_assembly_entry else None
            package_relpath = os.path.relpath(pkg_path, best_assembly_entry["root_relpath"]) if best_assembly_entry else pkg_dir_rel
            package_id_seed = f"package:{assembly_id}:{package_relpath}:{pkg.name}"
            package_entry = {
                "package_id": _stable_id(package_id_seed),
                "name": pkg.name,
                "dir_relpath": pkg_dir_rel,
                "package_relpath": package_relpath,
                "assembly_id": assembly_id,
                "build_system": pkg.build_system,
            }
            if best_assembly_entry:
                package_entries_by_assembly[assembly_id].append(package_entry)
            else:
                unassigned_packages.append(package_entry)

        packages: list[dict] = []
        for assembly in sorted(assemblies, key=lambda a: a["root_relpath"]):
            pkg_entries = sorted(
                package_entries_by_assembly[assembly["assembly_id"]],
                key=lambda p: p["package_relpath"],
            )
            assembly["package_ids"] = [pkg["package_id"] for pkg in pkg_entries]
            packages.extend(pkg_entries)

        if unassigned_packages:
            packages.extend(sorted(unassigned_packages, key=lambda p: p["dir_relpath"]))

        assemblies = sorted(assemblies, key=lambda a: a["root_relpath"])
        return assemblies, packages

    assemblies_v2, packages_v2 = _build_assemblies_and_packages()

    # Prepare JSON data
    index_data = {
        "repo_root": repo_root,
        "scan_timestamp": datetime.now().isoformat(),
        "assemblies": assemblies_v2,
        "packages": packages_v2,
        "assemblies_detected": [
            {
                "name": asm.name,
                "root_path": asm.root_path,
                "package_folders": asm.package_folders,
                "evidence_refs": getattr(asm, 'evidence_refs', []),
                "assembly_type": getattr(asm, 'assembly_type', 'upp'),
                "packages": getattr(asm, 'packages', []),
                "package_dirs": getattr(asm, 'package_dirs', []),
                "build_systems": getattr(asm, 'build_systems', []),
                "metadata": getattr(asm, 'metadata', {})
            } for asm in scan_result.assemblies_detected
        ],
        "packages_detected": [
            {
                "name": pkg.name,
                "dir": pkg.dir,
                "upp_path": pkg.upp_path,
                "files": pkg.files,
                "upp": _serialize_upp_payload(getattr(pkg, 'upp', None)),
                "build_system": pkg.build_system,
                "dependencies": getattr(pkg, 'dependencies', []),
                "groups": [
                    {
                        "name": group.name,
                        "files": group.files,
                        "readonly": getattr(group, 'readonly', False),
                        "auto_generated": getattr(group, 'auto_generated', False)
                    } for group in pkg.groups
                ],
                "ungrouped_files": pkg.ungrouped_files
            } for pkg in scan_result.packages_detected
        ],
        "unknown_paths": [
            {
                "path": unknown.path,
                "type": unknown.type,
                "guessed_kind": getattr(unknown, 'guessed_kind', '')
            } for unknown in getattr(scan_result, 'unknown_paths', [])
        ],
        "user_assemblies": getattr(scan_result, 'user_assemblies', []),
        "internal_packages": [
            {
                "name": ipkg.name,
                "root_path": ipkg.root_path,
                "guessed_type": ipkg.guessed_type,
                "members": ipkg.members,
                "groups": [
                    {
                        "name": group.name,
                        "files": group.files,
                        "readonly": getattr(group, 'readonly', False),
                        "auto_generated": getattr(group, 'auto_generated', False)
                    } for group in getattr(ipkg, '_groups', [])
                ],
                "ungrouped_files": getattr(ipkg, '_ungrouped_files', ipkg.members)
            } for ipkg in getattr(scan_result, 'internal_packages', [])
        ]
    }

    model_path = write_repo_model(repo_root, index_data)
    if verbose:
        print_debug(f"Wrote {model_path}", 2)

    state_data = default_repo_state(
        repo_root,
        model_path,
        {
            "packages": len(scan_result.packages_detected),
            "assemblies": len(scan_result.assemblies_detected),
            "user_assemblies": len(getattr(scan_result, 'user_assemblies', [])),
            "internal_packages": len(getattr(scan_result, 'internal_packages', [])),
            "unknown_paths": len(getattr(scan_result, 'unknown_paths', [])),
        }
    )
    state_path = write_repo_state(repo_root, state_data)
    if verbose:
        print_debug(f"Wrote {state_path}", 2)


def load_repo_index(repo_root: str = None) -> dict:
    """
    Load repository model from docs/maestro/repo_model.json

    Args:
        repo_root: Path to repository root (default: auto-detect)

    Returns:
        Dictionary containing the repo index

    Raises:
        SystemExit: If index file doesn't exist
    """
    if repo_root is None:
        repo_root = find_repo_root()
    return load_repo_model(repo_root)


def build_repo_hierarchy(repo_scan, repo_root: str) -> Dict[str, Any]:
    """
    Build hierarchical representation of repository structure.

    Args:
        repo_scan: Repository scan results (RepoScanResult)
        repo_root: Repository root path

    Returns:
        Dictionary representing hierarchy
    """
    hierarchy = {
        'repository': {
            'name': os.path.basename(repo_root),
            'path': repo_root,
            'assemblies': [],
            'standalone_packages': [],
            'metadata': {
                'total_assemblies': len(repo_scan.assemblies_detected),
                'total_packages': len(repo_scan.packages_detected),
                'total_files': sum(len(p.files) for p in repo_scan.packages_detected)
            }
        }
    }

    # Track which packages are in assemblies
    packages_in_assemblies = set()

    # Build assembly hierarchy
    for assembly in repo_scan.assemblies_detected:
        assembly_packages = []

        # Find packages in this assembly
        for pkg in repo_scan.packages_detected:
            if os.path.dirname(os.path.normpath(pkg.dir)) == os.path.normpath(assembly.root_path):
                packages_in_assemblies.add(pkg.name)

                # Build package structure with groups
                package_structure = {
                    'name': pkg.name,
                    'path': pkg.dir,
                    'build_system': pkg.build_system,
                    'file_count': len(pkg.files),
                    'groups': []
                }

                # Add file groups if they exist
                if pkg.groups:
                    for group in pkg.groups:
                        package_structure['groups'].append({
                            'name': group.name,
                            'separator': getattr(group, 'separator', ''),
                            'files': group.files,
                            'file_count': len(group.files)
                        })

                # Add ungrouped files
                if pkg.ungrouped_files:
                    package_structure['groups'].append({
                        'name': '(ungrouped)',
                        'separator': None,
                        'files': pkg.ungrouped_files,
                        'file_count': len(pkg.ungrouped_files)
                    })

                assembly_packages.append(package_structure)

        assembly_structure = {
            'name': assembly.name,
            'path': assembly.root_path,
            'type': getattr(assembly, 'assembly_type', 'upp'),
            'packages': sorted(assembly_packages, key=lambda p: p['name']),
            'package_count': len(assembly_packages),
            'total_files': sum(p['file_count'] for p in assembly_packages)
        }

        hierarchy['repository']['assemblies'].append(assembly_structure)

    # Add standalone packages (not in any assembly)
    for pkg in repo_scan.packages_detected:
        if pkg.name not in packages_in_assemblies:
            package_structure = {
                'name': pkg.name,
                'path': pkg.dir,
                'build_system': pkg.build_system,
                'file_count': len(pkg.files),
                'groups': []
            }

            if pkg.groups:
                for group in pkg.groups:
                    package_structure['groups'].append({
                        'name': group.name,
                        'separator': getattr(group, 'separator', ''),
                        'files': group.files,
                        'file_count': len(group.files)
                    })

            if pkg.ungrouped_files:
                package_structure['groups'].append({
                    'name': '(ungrouped)',
                    'separator': None,
                    'files': pkg.ungrouped_files,
                    'file_count': len(pkg.ungrouped_files)
                })

            hierarchy['repository']['standalone_packages'].append(package_structure)

    # Sort assemblies and packages by name
    hierarchy['repository']['assemblies'].sort(key=lambda a: a['name'])
    hierarchy['repository']['standalone_packages'].sort(key=lambda p: p['name'])

    return hierarchy


def save_hierarchy(hierarchy: Dict[str, Any], repo_root: str, verbose: bool = False):
    """
    Save hierarchy to docs/maestro/repo/hierarchy.json

    Args:
        hierarchy: Hierarchy dictionary
        repo_root: Repository root path
        verbose: Verbose output flag
    """
    repo_dir = ensure_repo_truth_dir(repo_root) / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    hierarchy_file = repo_dir / "hierarchy.json"

    with open(hierarchy_file, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)

    if verbose:
        print(f"[maestro] Saved hierarchy to {hierarchy_file}")


def load_hierarchy(repo_root: str) -> Optional[Dict[str, Any]]:
    """
    Load hierarchy from docs/maestro/repo/hierarchy.json

    Args:
        repo_root: Repository root path

    Returns:
        Hierarchy dictionary or None if not found
    """
    repo_dir = ensure_repo_truth_dir(repo_root)
    hierarchy_file = repo_dir / "repo" / "hierarchy.json"

    if not hierarchy_file.exists():
        return None

    try:
        with open(hierarchy_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def load_hierarchy_overrides(repo_root: str) -> Optional[Dict[str, Any]]:
    """
    Load hierarchy overrides from docs/maestro/repo/hierarchy_overrides.json

    Args:
        repo_root: Repository root path

    Returns:
        Overrides dictionary or None if not found
    """
    repo_dir = ensure_repo_truth_dir(repo_root)
    overrides_file = repo_dir / "repo" / "hierarchy_overrides.json"

    if not overrides_file.exists():
        return None

    try:
        with open(overrides_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def merge_hierarchy_overrides(hierarchy: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge manual hierarchy overrides with auto-detected hierarchy.

    Args:
        hierarchy: Auto-detected hierarchy
        overrides: Manual overrides

    Returns:
        Merged hierarchy
    """
    import copy

    # Deep copy to avoid modifying original
    merged = copy.deepcopy(hierarchy)

    # Apply overrides
    if 'repository' in overrides:
        override_repo = overrides['repository']

        # Override repository metadata if specified
        if 'metadata' in override_repo:
            merged['repository']['metadata'].update(override_repo['metadata'])

        # Override assemblies
        if 'assemblies' in override_repo:
            for override_asm in override_repo['assemblies']:
                asm_name = override_asm.get('name')
                # Find matching assembly
                for i, asm in enumerate(merged['repository']['assemblies']):
                    if asm['name'] == asm_name:
                        # Merge assembly properties
                        merged['repository']['assemblies'][i].update(override_asm)
                        break

        # Override standalone packages
        if 'standalone_packages' in override_repo:
            for override_pkg in override_repo['standalone_packages']:
                pkg_name = override_pkg.get('name')
                # Find matching package
                for i, pkg in enumerate(merged['repository']['standalone_packages']):
                    if pkg['name'] == pkg_name:
                        # Merge package properties
                        merged['repository']['standalone_packages'][i].update(override_pkg)
                        break

    return merged


def print_hierarchy_tree(hierarchy: Dict[str, Any], show_files: bool = False):
    """
    Print hierarchy in tree view with colors.

    Args:
        hierarchy: Hierarchy dictionary
        show_files: Whether to show individual files
    """
    repo = hierarchy['repository']

    print(f"\n{Colors.GREEN}📦 {repo['name']}{Colors.RESET}")
    print(f"   {Colors.DIM}Path: {repo['path']}{Colors.RESET}")
    print(f"   {Colors.DIM}Assemblies: {repo['metadata']['total_assemblies']}, "
          f"Packages: {repo['metadata']['total_packages']}, "
          f"Files: {repo['metadata']['total_files']}{Colors.RESET}\n")

    # Print assemblies
    if repo['assemblies']:
        for i, assembly in enumerate(repo['assemblies']):
            is_last_assembly = (i == len(repo['assemblies']) - 1) and not repo['standalone_packages']
            asm_prefix = "└── " if is_last_assembly else "├── "

            print(f"{asm_prefix}{Colors.BLUE}🏗️  {assembly['name']}{Colors.RESET} "
                  f"{Colors.DIM}({assembly['package_count']} packages, "
                  f"{assembly['total_files']} files){Colors.RESET}")

            # Print packages in assembly
            for j, package in enumerate(assembly['packages']):
                is_last_pkg = (j == len(assembly['packages']) - 1)
                pkg_indent = "    " if is_last_assembly else "│   "
                pkg_prefix = "└── " if is_last_pkg else "├── "

                print(f"{pkg_indent}{pkg_prefix}{Colors.CYAN}📄 {package['name']}{Colors.RESET} "
                      f"{Colors.DIM}({package['file_count']} files){Colors.RESET}")

                # Show file groups if requested
                if show_files and package['groups']:
                    group_indent = pkg_indent + ("    " if is_last_pkg else "│   ")
                    for k, group in enumerate(package['groups']):
                        is_last_group = (k == len(package['groups']) - 1)
                        group_prefix = "└── " if is_last_group else "├── "

                        print(f"{group_indent}{group_prefix}{Colors.YELLOW}{group['name']}{Colors.RESET} "
                              f"{Colors.DIM}({group['file_count']} files){Colors.RESET}")

    # Print standalone packages
    if repo['standalone_packages']:
        print()
        print(f"{Colors.YELLOW}Standalone Packages:{Colors.RESET}")
        for i, package in enumerate(repo['standalone_packages']):
            is_last = (i == len(repo['standalone_packages']) - 1)
            prefix = "└── " if is_last else "├── "

            print(f"{prefix}{Colors.CYAN}📄 {package['name']}{Colors.RESET} "
                  f"{Colors.DIM}({package['file_count']} files){Colors.RESET}")

            # Show file groups if requested
            if show_files and package['groups']:
                group_indent = "    " if is_last else "│   "
                for j, group in enumerate(package['groups']):
                    is_last_group = (j == len(package['groups']) - 1)
                    group_prefix = "└── " if is_last_group else "├── "

                    print(f"{group_indent}{group_prefix}{Colors.YELLOW}{group['name']}{Colors.RESET} "
                          f"{Colors.DIM}({group['file_count']} files){Colors.RESET}")


# Handler functions for repo commands

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
    from maestro.repo.package_info import AssemblyInfo
    from maestro.repo.repo_scanner import RepoScanResult

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


# Parser registration

def add_repo_parser(subparsers):
    """
    Add repo command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    repo_parser = subparsers.add_parser('repo', help='Repository analysis and resolution commands')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_subcommand', help='Repository subcommands')

    # repo resolve
    repo_resolve_parser = repo_subparsers.add_parser('resolve', aliases=['res'], help='Scan repository for packages across build systems')
    repo_resolve_parser.add_argument('--path', help='Path to repository to scan (default: current directory)')
    repo_resolve_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_resolve_parser.add_argument('--no-write', action='store_true', help='Skip writing artifacts to docs/maestro/')
    repo_resolve_parser.add_argument('--no-hub-update', action='store_true', help='Skip updating hub index')
    repo_resolve_parser.add_argument('--find-root', action='store_true', help='Find repository root with docs/maestro instead of scanning current directory')
    repo_resolve_parser.add_argument('--include-user-config', dest='include_user_config', action='store_true', help='Include user assemblies from ~/.config/u++/ide/*.var')
    repo_resolve_parser.add_argument('--no-user-config', dest='include_user_config', action='store_false', default=True, help='Skip reading user assembly config (default)')
    repo_resolve_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose scan information')

    # repo show
    repo_show_parser = repo_subparsers.add_parser('show', aliases=['sh'], help='Show repository scan results from docs/maestro/')
    repo_show_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_show_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')

    # repo pkg
    repo_pkg_parser = repo_subparsers.add_parser('pkg', help='Package query and inspection commands')
    repo_pkg_parser.add_argument('package_name', nargs='?', help='Package name to inspect (supports partial match)')
    repo_pkg_parser.add_argument('action', nargs='?', choices=['info', 'list', 'search', 'tree', 'conf', 'groups'], default='info',
                                 help='Action: info (default), list (files), search (file search), tree (deps), conf (configurations), groups (file groups)')
    repo_pkg_parser.add_argument('query', nargs='?', help='Search query (for search action) or config number (for tree with config filter)')
    repo_pkg_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_pkg_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_pkg_parser.add_argument('--deep', action='store_true', help='Show full tree with all duplicates (for tree action)')
    repo_pkg_parser.add_argument('--show-groups', action='store_true', help='Show package file groups')
    repo_pkg_parser.add_argument('--group', help='Filter to specific group (use with --show-groups)')

    # repo asm
    repo_asm_parser = repo_subparsers.add_parser('asm', aliases=['a', 'assembly'], help='Assembly query commands')
    repo_asm_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_subparsers = repo_asm_parser.add_subparsers(dest='asm_subcommand', help='Assembly subcommands')

    repo_asm_list = repo_asm_subparsers.add_parser('list', aliases=['ls', 'l'], help='List assemblies')
    repo_asm_list.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_list.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_show = repo_asm_subparsers.add_parser('show', aliases=['sh', 's'], help='Show assembly details')
    repo_asm_show.add_argument('assembly_ref', help='Assembly ID or name')
    repo_asm_show.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_show.add_argument('--json', action='store_true', help='Output in JSON format')

    # repo conf
    repo_conf_parser = repo_subparsers.add_parser('conf', aliases=['c'], help='Repo configuration selection and defaults')
    repo_conf_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_conf_subparsers = repo_conf_parser.add_subparsers(dest='conf_subcommand', help='Repo conf subcommands')

    repo_conf_show = repo_conf_subparsers.add_parser('show', help='Show repo configuration defaults')
    repo_conf_show.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_conf_list = repo_conf_subparsers.add_parser('list', help='List configured targets')
    repo_conf_list.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_conf_select = repo_conf_subparsers.add_parser('select-default', help='Select default repo configuration')
    repo_conf_select.add_argument('entity', choices=['target'], help='Entity to select (target)')
    repo_conf_select.add_argument('value', help='Default target value')

    # repo refresh
    repo_refresh_parser = repo_subparsers.add_parser('refresh', help='Refresh repository metadata')
    repo_refresh_subparsers = repo_refresh_parser.add_subparsers(dest='refresh_subcommand', help='Refresh subcommands')

    # repo refresh all
    repo_refresh_all_parser = repo_refresh_subparsers.add_parser('all', help='Full refresh (resolve + conventions + rules)')
    repo_refresh_all_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_refresh_all_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo refresh help
    repo_refresh_subparsers.add_parser('help', aliases=['h'], help='Show what refresh all does')

    # repo hier
    repo_hier_parser = repo_subparsers.add_parser('hier', help='Show/edit repository hierarchy')
    repo_hier_subparsers = repo_hier_parser.add_subparsers(dest='hier_subcommand', help='Hierarchy subcommands')

    # repo hier show (default)
    repo_hier_show_parser = repo_hier_subparsers.add_parser('show', help='Show repository hierarchy')
    repo_hier_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_hier_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hier_show_parser.add_argument('--show-files', action='store_true', help='Show file groups in tree view')
    repo_hier_show_parser.add_argument('--rebuild', action='store_true', help='Force rebuild hierarchy from scan data')

    # repo hier edit
    repo_hier_edit_parser = repo_hier_subparsers.add_parser('edit', help='Edit hierarchy overrides in $EDITOR')
    repo_hier_edit_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # Also add these arguments to the main hier parser for backward compatibility
    repo_hier_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_hier_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hier_parser.add_argument('--show-files', action='store_true', help='Show file groups in tree view')
    repo_hier_parser.add_argument('--rebuild', action='store_true', help='Force rebuild hierarchy from scan data')

    # repo conventions
    repo_conventions_parser = repo_subparsers.add_parser('conventions', help='Show/edit detected conventions')
    repo_conventions_subparsers = repo_conventions_parser.add_subparsers(dest='conventions_subcommand', help='Conventions subcommands')

    # repo conventions detect
    repo_conventions_detect_parser = repo_conventions_subparsers.add_parser('detect', help='Detect naming conventions')
    repo_conventions_detect_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_conventions_detect_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo conventions show (default)
    repo_conventions_show_parser = repo_conventions_subparsers.add_parser('show', help='Show current conventions')
    repo_conventions_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo rules
    repo_rules_parser = repo_subparsers.add_parser('rules', help='Show/edit repository rules')
    repo_rules_subparsers = repo_rules_parser.add_subparsers(dest='rules_subcommand', help='Rules subcommands')

    # repo rules show (default)
    repo_rules_show_parser = repo_rules_subparsers.add_parser('show', help='Show current rules')
    repo_rules_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo rules edit
    repo_rules_edit_parser = repo_rules_subparsers.add_parser('edit', help='Edit rules in $EDITOR')
    repo_rules_edit_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo rules inject
    repo_rules_inject_parser = repo_rules_subparsers.add_parser('inject', help='Show rules for AI injection (testing)')
    repo_rules_inject_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_rules_inject_parser.add_argument('--context', default='general',
                                           choices=['general', 'build', 'refactor', 'security', 'performance', 'fix', 'feature'],
                                           help='Context for rule selection (default: general)')

    # repo hub (cross-repo package discovery and linking)
    repo_hub_parser = repo_subparsers.add_parser('hub', help='Cross-repo package discovery and linking')
    repo_hub_subparsers = repo_hub_parser.add_subparsers(dest='hub_subcommand', help='Hub subcommands')

    # repo hub scan
    repo_hub_scan_parser = repo_hub_subparsers.add_parser('scan', help='Scan repository and add to hub index')
    repo_hub_scan_parser.add_argument('path', nargs='?', help='Path to repository to scan (default: current directory)')
    repo_hub_scan_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub list
    repo_hub_list_parser = repo_hub_subparsers.add_parser('list', aliases=['ls'], help='List all repositories in hub index')
    repo_hub_list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_list_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub show
    repo_hub_show_parser = repo_hub_subparsers.add_parser('show', help='Show repository details')
    repo_hub_show_parser.add_argument('repo_id', help='Repository ID to show')
    repo_hub_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_show_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub find
    repo_hub_find_parser = repo_hub_subparsers.add_parser('find', help='Find packages or repos')
    repo_hub_find_subparsers = repo_hub_find_parser.add_subparsers(dest='find_subcommand', help='Find subcommands')

    # repo hub find package
    repo_hub_find_package_parser = repo_hub_find_subparsers.add_parser('package', aliases=['pkg', 'p'], help='Find package across all repos')
    repo_hub_find_package_parser.add_argument('package_name', help='Package name to search for')
    repo_hub_find_package_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_find_package_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link
    repo_hub_link_parser = repo_hub_subparsers.add_parser('link', help='Manage cross-repo links')
    repo_hub_link_subparsers = repo_hub_link_parser.add_subparsers(dest='link_subcommand', help='Link subcommands')

    # repo hub link package
    repo_hub_link_package_parser = repo_hub_link_subparsers.add_parser('package', aliases=['pkg', 'p'], help='Link to external package')
    repo_hub_link_package_parser.add_argument('package_name', help='Local package name')
    repo_hub_link_package_parser.add_argument('--to', dest='to_package_id', required=True, help='Target package ID')
    repo_hub_link_package_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link show
    repo_hub_link_show_parser = repo_hub_link_subparsers.add_parser('show', help='Show all hub links')
    repo_hub_link_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_link_show_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link remove
    repo_hub_link_remove_parser = repo_hub_link_subparsers.add_parser('remove', aliases=['rm'], help='Remove a link')
    repo_hub_link_remove_parser.add_argument('link_id', help='Link ID to remove')
    repo_hub_link_remove_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo help
    repo_subparsers.add_parser('help', aliases=['h'], help='Show help for repo commands')

    return repo_parser


def handle_repo_command(args):
    """
    Main handler for maestro repo commands.

    Dispatches to appropriate sub-handlers based on repo_subcommand.
    """
    from maestro.repo import scan_upp_repo_v2
    from maestro.repo.assembly_commands import handle_asm_command

    def _find_repo_root_if_truth(path: str) -> Optional[str]:
        current = Path(path).resolve()
        while current != current.parent:
            if (current / REPO_TRUTH_REL).is_dir():
                return str(current)
            current = current.parent
        if (current / REPO_TRUTH_REL).is_dir():
            return str(current)
        return None

    # Handle repository analysis and resolution commands (no session required)
    if hasattr(args, 'repo_subcommand') and args.repo_subcommand:
        if args.repo_subcommand == 'resolve':
            # Get the path to scan - auto-detect or use provided path
            if hasattr(args, 'path') and args.path:
                scan_path = args.path
                # Ensure the path exists
                if not os.path.exists(scan_path):
                    print_error(f"Path does not exist: {scan_path}", 2)
                    sys.exit(1)
                # Ensure the path is a directory
                if not os.path.isdir(scan_path):
                    print_error(f"Path is not a directory: {scan_path}", 2)
                    sys.exit(1)
            else:
                # Use current directory by default, unless --find-root is specified
                if getattr(args, 'find_root', False):
                    scan_path = find_repo_root()
                    if getattr(args, 'verbose', False):
                        print_debug(f"Detected repository root: {scan_path}", 2)
                else:
                    scan_path = os.getcwd()
                    if getattr(args, 'verbose', False):
                        print_debug(f"Scanning current directory: {scan_path}", 2)

            if getattr(args, 'find_root', False):
                repo_root = find_repo_root(scan_path)
            else:
                repo_root = _find_repo_root_if_truth(scan_path) or scan_path
            if not getattr(args, 'json', False):
                branch_guard_error = check_branch_guard(repo_root)
                if branch_guard_error:
                    print_error(branch_guard_error, 2)
                    sys.exit(1)

            # Perform the repo scan
            fast_json = getattr(args, 'json', False)
            repo_result = scan_upp_repo_v2(
                scan_path,
                verbose=getattr(args, 'verbose', False),
                include_user_config=getattr(args, 'include_user_config', False),
                collect_files=not fast_json,
                scan_unknown_paths=not fast_json,
            )

            # Write artifacts unless --no-write is specified
            if not getattr(args, 'no_write', False):
                write_repo_artifacts(repo_root, repo_result, verbose=getattr(args, 'verbose', False))

                # Update hub index with scanned packages (optional)
                if not getattr(args, 'no_hub_update', False):
                    try:
                        from maestro.repo.hub.scanner import HubScanner
                        scanner = HubScanner()
                        repo_record = scanner.scan_repository(repo_root, verbose=getattr(args, 'verbose', False))
                        scanner.update_hub_index(repo_record, verbose=getattr(args, 'verbose', False))
                    except Exception as e:
                        # Hub update is non-critical, don't fail the whole operation
                        print_warning(f"Hub index update failed: {e}", 2)

            # Output format varies based on the flag
            if getattr(args, 'json', False):
                # Output in JSON format
                result = {
                    "assemblies_detected": [
                        {
                            "name": asm.name,
                            "root_path": asm.root_path,
                            "package_folders": getattr(asm, 'package_folders', [])
                        } for asm in repo_result.assemblies_detected
                    ],
                    "packages_detected": [
                        {
                            "name": pkg.name,
                            "dir": pkg.dir,
                            "upp_path": getattr(pkg, 'upp_path', None),
                            "files": pkg.files,
                            "build_system": pkg.build_system
                        } for pkg in repo_result.packages_detected
                    ],
                    "internal_packages": [
                        {
                            "name": ipkg.name,
                            "root_path": ipkg.root_path,
                            "guessed_type": getattr(ipkg, 'guessed_type', None),
                            "members": getattr(ipkg, 'members', [])
                        } for ipkg in repo_result.internal_packages
                    ],
                    "unknown_paths": [
                        {
                            "path": unknown.path,
                            "type": getattr(unknown, 'type', None),
                            "guessed_kind": getattr(unknown, 'guessed_kind', None)
                        } for unknown in repo_result.unknown_paths
                    ]
                }
                print(json.dumps(result, indent=2))
            else:
                # Output in human-readable format
                print_header(f"REPOSITORY SCAN COMPLETE")

                print(f"\nRepository: {scan_path}")
                print(f"Packages: {len(repo_result.packages_detected)}")
                print(f"Assemblies: {len(repo_result.assemblies_detected)}")
                print(f"Internal packages: {len(repo_result.internal_packages)}")
                print(f"Unknown paths: {len(repo_result.unknown_paths)}")

                if not getattr(args, 'no_write', False):
                    model_path = repo_model_path(repo_root, require=False)
                    print(f"\nRepo model written to: {model_path}")

                # Print next steps
                print("\n" + "─" * 60)
                print_info("NEXT STEPS", 2)
                print_info("View detailed results:", 2)
                print_info("  maestro repo show", 3)
                print_info("\nExplore packages:", 2)
                print_info("  maestro repo show --json", 3)
                print_info("\nContinue with build planning or conversion setup", 2)

        elif args.repo_subcommand in ['show', 'sh']:
            # Show repository scan results from docs/maestro/
            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            index_data = load_repo_index(repo_root)

            if getattr(args, 'json', False):
                # Output in JSON format
                print(json.dumps(index_data, indent=2))
            else:
                # Output in human-readable format
                print_header("REPOSITORY MODEL")
                print(f"\nRepository: {index_data.get('repo_root', repo_root or 'unknown')}")
                print(f"Scan time: {index_data.get('scan_timestamp', 'unknown')}")

                packages = index_data.get('packages_detected', [])
                print(f"\nPackages ({len(packages)}):")
                for pkg in packages[:10]:
                    print(f"  - {pkg.get('name', 'unknown')} ({pkg.get('build_system', 'unknown')})")
                if len(packages) > 10:
                    print(f"  ... and {len(packages) - 10} more")

                assemblies = index_data.get('assemblies', [])
                packages_v2 = index_data.get('packages', [])
                if assemblies:
                    package_counts = {}
                    for pkg in packages_v2:
                        asm_id = pkg.get('assembly_id')
                        if not asm_id:
                            continue
                        package_counts[asm_id] = package_counts.get(asm_id, 0) + 1
                    sorted_assemblies = sorted(assemblies, key=lambda a: a.get('root_relpath', ''))
                    print(f"\nAssemblies ({len(sorted_assemblies)}):")
                    for asm in sorted_assemblies[:10]:
                        asm_name = asm.get('name', 'unknown')
                        asm_id = asm.get('assembly_id')
                        asm_count = package_counts.get(asm_id, 0)
                        print(f"  - {asm_name} ({asm_count} packages)")
                    if len(sorted_assemblies) > 10:
                        print(f"  ... and {len(sorted_assemblies) - 10} more")
                else:
                    assemblies_detected = index_data.get('assemblies_detected', [])
                    if assemblies_detected:
                        print(f"\nAssemblies ({len(assemblies_detected)}):")
                        for asm in assemblies_detected[:10]:
                            asm_name = asm.get('name', 'unknown')
                            pkg_count = len(asm.get('package_folders', []))
                            print(f"  - {asm_name} ({pkg_count} packages)")
                        if len(assemblies_detected) > 10:
                            print(f"  ... and {len(assemblies_detected) - 10} more")

        elif args.repo_subcommand == 'pkg':
            # Package inspection commands
            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            index_data = load_repo_index(repo_root)
            packages = index_data.get('packages_detected', [])

            # Get package name (optional)
            pkg_name = getattr(args, 'package_name', None)
            action = getattr(args, 'action', 'info')

            if not pkg_name:
                # List all packages
                handle_repo_pkg_list(packages, getattr(args, 'json', False), repo_root)
            else:
                # Find matching package (partial match)
                matching_pkgs = [p for p in packages if pkg_name.lower() in p.get('name', '').lower()]

                if not matching_pkgs:
                    print_error(f"No package found matching: {pkg_name}", 2)
                    sys.exit(1)
                elif len(matching_pkgs) > 1:
                    print_warning(f"Multiple packages match '{pkg_name}':", 2)
                    for p in matching_pkgs:
                        print(f"  - {p.get('name')}")
                    print_info("\nPlease be more specific", 2)
                    sys.exit(1)

                pkg = matching_pkgs[0]

                # Dispatch to appropriate handler
                if action == 'info':
                    handle_repo_pkg_info(pkg, getattr(args, 'json', False))
                elif action == 'list':
                    handle_repo_pkg_files(pkg, getattr(args, 'json', False))
                elif action == 'groups':
                    handle_repo_pkg_groups(pkg, getattr(args, 'json', False),
                                          getattr(args, 'show_groups', False),
                                          getattr(args, 'group', None))
                elif action == 'search':
                    query = getattr(args, 'query', None)
                    if not query:
                        print_error("Search query is required for search action", 2)
                        sys.exit(1)
                    handle_repo_pkg_search(pkg, query, getattr(args, 'json', False))
                elif action == 'tree':
                    config_flags = None
                    if hasattr(args, 'query') and args.query:
                        try:
                            config_num = int(args.query)
                            # Get config flags for this config number
                            from maestro.repo.build_config import get_package_config
                            pkg_config = get_package_config(pkg)
                            if pkg_config and 0 <= config_num < len(pkg_config.configurations):
                                config_flags = pkg_config.configurations[config_num].flags
                        except (ValueError, AttributeError):
                            pass
                    handle_repo_pkg_tree(pkg, packages, getattr(args, 'json', False),
                                        getattr(args, 'deep', False), config_flags)
                elif action == 'conf':
                    handle_repo_pkg_conf(pkg, getattr(args, 'json', False))

        elif args.repo_subcommand == 'conf':
            from maestro.repo.storage import load_repoconf, save_repoconf

            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            if not repo_root:
                repo_root = find_repo_root()

            conf_sub = getattr(args, 'conf_subcommand', None)
            if conf_sub == 'show':
                repoconf = load_repoconf(repo_root)
                if getattr(args, 'json', False):
                    print(json.dumps(repoconf, indent=2))
                else:
                    print_header("REPO CONFIGURATION")
                    print(json.dumps(repoconf, indent=2))
            elif conf_sub == 'list':
                repoconf = load_repoconf(repo_root)
                targets = repoconf.get("targets", [])
                if repoconf.get("selected_target") and repoconf.get("selected_target") not in targets:
                    targets.append(repoconf["selected_target"])
                if getattr(args, 'json', False):
                    print(json.dumps({
                        "selected_target": repoconf.get("selected_target"),
                        "targets": targets,
                    }, indent=2))
                else:
                    print_header("REPO TARGETS")
                    selected = repoconf.get("selected_target") or "(not set)"
                    print(f"Selected target: {selected}")
                    if targets:
                        for target in targets:
                            selected_marker = " (selected)" if target == repoconf.get("selected_target") else ""
                            print(f"- {target}{selected_marker}")
                    else:
                        print("No targets configured.")
            elif conf_sub == 'select-default':
                branch_guard_error = check_branch_guard(repo_root)
                if branch_guard_error:
                    print_error(branch_guard_error, 2)
                    sys.exit(1)

                if getattr(args, "entity", None) != "target":
                    print_error("Only target selection is supported.", 2)
                    sys.exit(1)
                target = getattr(args, "value", None)
                if not target:
                    print_error("Target value is required.", 2)
                    sys.exit(1)
                repoconf = {
                    "selected_target": target,
                    "targets": [target],
                    "updated_at": datetime.now().isoformat()
                }
                try:
                    existing = load_repoconf(repo_root)
                    targets = existing.get("targets", [])
                    if target not in targets:
                        targets.append(target)
                    repoconf["targets"] = targets
                except SystemExit:
                    pass
                save_repoconf(repo_root, repoconf)
                print_success(f"Selected default target: {target}", 2)
            else:
                print_info("Use 'maestro repo conf --help' for available subcommands.", 2)

        elif args.repo_subcommand == 'asm':
            # Assembly management commands
            handle_asm_command(args)

        elif args.repo_subcommand == 'refresh':
            refresh_sub = getattr(args, 'refresh_subcommand', None)
            if refresh_sub == 'all':
                repo_root = getattr(args, 'path', None)
                if not repo_root:
                    repo_root = find_repo_root()
                handle_repo_refresh_all(repo_root, getattr(args, 'verbose', False))
            elif refresh_sub in ['help', 'h']:
                handle_repo_refresh_help()
            else:
                print_error(f"Unknown refresh subcommand: {refresh_sub}", 2)
                sys.exit(1)

        elif args.repo_subcommand == 'hier':
            hier_sub = getattr(args, 'hier_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if hier_sub == 'edit':
                handle_repo_hier_edit(repo_root)
            else:
                # Default to show
                handle_repo_hier(repo_root,
                               getattr(args, 'json', False),
                               getattr(args, 'show_files', False),
                               getattr(args, 'rebuild', False))

        elif args.repo_subcommand == 'conventions':
            conv_sub = getattr(args, 'conventions_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if conv_sub == 'detect':
                handle_repo_conventions_detect(repo_root, getattr(args, 'verbose', False))
            else:
                # Default to show
                handle_repo_conventions_show(repo_root)

        elif args.repo_subcommand == 'rules':
            rules_sub = getattr(args, 'rules_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if rules_sub == 'edit':
                handle_repo_rules_edit(repo_root)
            elif rules_sub == 'inject':
                context = getattr(args, 'context', 'general')
                handle_repo_rules_inject(repo_root, context)
            else:
                # Default to show
                handle_repo_rules_show(repo_root)

        elif args.repo_subcommand == 'hub':
            # Hub command for cross-repo package discovery and linking
            from maestro.commands.hub import handle_hub_command
            return handle_hub_command(args)

        elif args.repo_subcommand in ['help', 'h']:
            # Print help for repo subcommands (parser should handle this)
            print_info("Use 'maestro repo --help' to see available commands", 2)
        else:
            print_error(f"Unknown repo subcommand: {args.repo_subcommand}", 2)
            sys.exit(1)
    else:
        # If no subcommand specified, show help
        print_info("Use 'maestro repo --help' to see available commands", 2)


# Export handler functions
__all__ = [
    'add_repo_parser',
    'handle_repo_command',
    'find_repo_root',
    'write_repo_artifacts',
    'load_repo_index',
    'build_repo_hierarchy',
    'save_hierarchy',
    'load_hierarchy',
    'handle_repo_pkg_list',
    'handle_repo_pkg_info',
    'handle_repo_pkg_files',
    'handle_repo_pkg_groups',
    'handle_repo_pkg_search',
    'handle_repo_pkg_tree',
    'handle_repo_pkg_conf',
    'handle_repo_refresh_all',
    'handle_repo_refresh_help',
    'handle_repo_hier_edit',
    'handle_repo_hier',
    'handle_repo_conventions_detect',
    'handle_repo_conventions_show',
    'handle_repo_rules_show',
    'handle_repo_rules_edit',
    'handle_repo_rules_inject',
]
