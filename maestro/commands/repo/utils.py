"""
Shared utilities for repository commands.

Contains helper functions used across multiple repo subcommands.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Import from maestro.modules
from maestro.modules.utils import (
    print_debug,
    Colors
)

# Import from maestro.repo
from maestro.repo.package import FileGroup
from maestro.repo.storage import (
    find_repo_root as find_repo_root_v3,
    ensure_repo_truth_dir,
    write_repo_model,
    write_repo_state,
    default_repo_state,
    load_repo_model,
)
from maestro.repo.pathnorm import (
    normalize_path_to_posix,
    normalize_relpath,
    normalize_repo_model_paths,
    normalize_repo_path,
)


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
        assembly_by_root: dict[str, list[dict]] = {}  # Map from root path to list of assemblies
        assembly_by_kind: dict[str, dict] = {}  # Map from kind to assembly for virtual package routing
        for asm in scan_result.assemblies_detected:
            root_path = Path(asm.root_path).resolve()
            root_relpath, _ = normalize_repo_path(repo_root, str(root_path))
            if str(root_relpath).startswith("<external>"):
                continue
            if root_relpath == '.':
                root_relpath = '.'
            assembly_id = _stable_id(f"assembly:{asm.name}:{root_relpath}:{getattr(asm, 'assembly_type', 'upp')}")
            entry = {
                "assembly_id": assembly_id,
                "name": asm.name,
                "root_relpath": root_relpath,
                "kind": getattr(asm, "assembly_type", "upp"),
                "package_ids": [],
            }
            assemblies.append(entry)

            # Add to path-based lookup (multiple assemblies can have same path)
            root_path_key = os.path.normpath(str(root_path))
            if root_path_key not in assembly_by_root:
                assembly_by_root[root_path_key] = []
            assembly_by_root[root_path_key].append(entry)

            # Add to kind-based lookup (for virtual package routing)
            kind = entry["kind"]
            if kind:
                assembly_by_kind[kind] = entry

        package_entries_by_assembly: dict[str, list[dict]] = {a["assembly_id"]: [] for a in assemblies}
        unassigned_packages: list[dict] = []

        for pkg in scan_result.packages_detected:
            pkg_path = Path(pkg.dir).resolve()
            pkg_dir_rel, _ = normalize_repo_path(repo_root, str(pkg_path))

            # Find the best matching assembly for this package
            # Priority order:
            # 1. If package is virtual, prefer assembly with matching kind
            # 2. Otherwise, use best path match (longest path prefix match)
            best_assembly_entry = None

            # Check if this is a virtual package with a specific type
            is_virtual = getattr(pkg, 'is_virtual', False)
            virtual_type = getattr(pkg, 'virtual_type', None)

            if is_virtual and virtual_type:
                # First, try to find an assembly with matching kind
                if virtual_type in assembly_by_kind:
                    kind_matching_asm = assembly_by_kind[virtual_type]
                    # Convert the relative root path to an absolute path
                    asm_path_obj = (repo_root_path / kind_matching_asm["root_relpath"]).resolve()
                    try:
                        # If the package path is the same as assembly path, it belongs to that assembly
                        if pkg_path == asm_path_obj:
                            best_assembly_entry = kind_matching_asm
                        # If the package path is under the assembly path, it belongs to that assembly
                        rel_path = pkg_path.relative_to(asm_path_obj)
                        if not str(rel_path).startswith('..'):
                            best_assembly_entry = kind_matching_asm
                    except ValueError:
                        # pkg_path is not under asm_path_obj, don't assign to this assembly
                        pass

            # If no kind-matching assembly found or package is not virtual, use path matching
            if best_assembly_entry is None:
                best_match_length = -1
                best_assembly_entry = None
                # Look for assemblies that contain this package path
                pkg_path_norm = os.path.normpath(str(pkg_path))
                assemblies_to_check = []

                # Check if there are assemblies with the exact same path
                if pkg_path_norm in assembly_by_root:
                    assemblies_to_check.extend(assembly_by_root[pkg_path_norm])

                # Also check parent directories for assemblies
                current_path = pkg_path.parent
                while current_path != repo_root_path.parent:  # Stop at filesystem root
                    current_path_norm = os.path.normpath(str(current_path))
                    if current_path_norm in assembly_by_root:
                        assemblies_to_check.extend(assembly_by_root[current_path_norm])
                    if current_path == current_path.parent:  # Reached filesystem root
                        break
                    current_path = current_path.parent

                if assemblies_to_check:
                    # For non-virtual packages: choose the deepest matching assembly, preferring non-root assemblies
                    if not is_virtual:
                        # Find the deepest matching assemblies (longest path)
                        deepest_assemblies = []
                        for asm_entry in assemblies_to_check:
                            asm_path_obj = (repo_root_path / asm_entry["root_relpath"]).resolve()
                            try:
                                # Check if the package path is under the assembly path
                                if pkg_path == asm_path_obj:
                                    # Exact match - this is a candidate
                                    if not deepest_assemblies or len(str(asm_path_obj)) > best_match_length:
                                        deepest_assemblies = [asm_entry]
                                        best_match_length = len(str(asm_path_obj))
                                    elif len(str(asm_path_obj)) == best_match_length:
                                        deepest_assemblies.append(asm_entry)
                                else:
                                    rel_path = pkg_path.relative_to(asm_path_obj)
                                    if not str(rel_path).startswith('..'):
                                        # This assembly contains the package - it's a candidate
                                        if not deepest_assemblies or len(str(asm_path_obj)) > best_match_length:
                                            deepest_assemblies = [asm_entry]
                                            best_match_length = len(str(asm_path_obj))
                                        elif len(str(asm_path_obj)) == best_match_length:
                                            deepest_assemblies.append(asm_entry)
                            except ValueError:
                                # pkg_path is not under asm_path_obj, continue to next assembly
                                continue

                        # If we have multiple assemblies at the same depth:
                        # For packages in the same directory as multiple assemblies, prefer root assembly for non-virtual packages
                        # This handles the case where both root assembly and kind-specific assembly (like scripts) are at the same path
                        root_assemblies_at_depth = [asm for asm in deepest_assemblies if asm["kind"] == "root"]
                        non_root_assemblies_at_depth = [asm for asm in deepest_assemblies if asm["kind"] != "root"]

                        if not is_virtual and root_assemblies_at_depth:
                            # For non-virtual packages, prefer root assembly when available at same depth
                            best_assembly_entry = root_assemblies_at_depth[0]
                        elif non_root_assemblies_at_depth:
                            # For virtual packages or when no root assembly is at this depth, prefer non-root assemblies
                            best_assembly_entry = non_root_assemblies_at_depth[0]
                        elif deepest_assemblies:
                            # Fallback to first assembly if no specific preference applies
                            best_assembly_entry = deepest_assemblies[0]
                    else:
                        # For virtual packages or if no root assembly exists, use path matching logic
                        for asm_entry in assemblies_to_check:
                            asm_path_obj = (repo_root_path / asm_entry["root_relpath"]).resolve()
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
            if best_assembly_entry:
                asm_root_abs = (repo_root_path / best_assembly_entry["root_relpath"]).resolve()
                package_relpath = normalize_relpath(str(asm_root_abs), str(pkg_path))
            else:
                package_relpath = pkg_dir_rel
            package_id_seed = f"package:{assembly_id}:{package_relpath}:{pkg.name}"
            package_entry = {
                "package_id": _stable_id(package_id_seed),
                "name": pkg.name,
                "dir_relpath": normalize_path_to_posix(pkg_dir_rel),
                "package_relpath": normalize_path_to_posix(package_relpath),
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
            # Remove duplicates while preserving order
            seen_ids = set()
            unique_pkg_entries = []
            for pkg in pkg_entries:
                if pkg["package_id"] not in seen_ids:
                    unique_pkg_entries.append(pkg)
                    seen_ids.add(pkg["package_id"])
            assembly["package_ids"] = [pkg["package_id"] for pkg in unique_pkg_entries]
            packages.extend(unique_pkg_entries)

        if unassigned_packages:
            # Also deduplicate unassigned packages
            seen_ids = set()
            unique_unassigned = []
            for pkg in sorted(unassigned_packages, key=lambda p: p["dir_relpath"]):
                if pkg["package_id"] not in seen_ids:
                    unique_unassigned.append(pkg)
                    seen_ids.add(pkg["package_id"])
            packages.extend(unique_unassigned)

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
                "root_path": normalize_repo_path(repo_root, asm.root_path)[0],
                "package_folders": [
                    normalize_repo_path(repo_root, folder)[0]
                    for folder in asm.package_folders
                ],
                "evidence_refs": getattr(asm, 'evidence_refs', []),
                "assembly_type": getattr(asm, 'assembly_type', 'upp'),
                "packages": getattr(asm, 'packages', []),
                "package_dirs": [
                    normalize_repo_path(repo_root, pkg_dir)[0]
                    for pkg_dir in getattr(asm, 'package_dirs', [])
                ],
                "build_systems": getattr(asm, 'build_systems', []),
                "metadata": getattr(asm, 'metadata', {})
            } for asm in scan_result.assemblies_detected
        ],
        "packages_detected": [
            {
                "name": pkg.name,
                "dir": normalize_repo_path(repo_root, pkg.dir)[0],
                "upp_path": normalize_repo_path(repo_root, pkg.upp_path)[0] if pkg.upp_path else "",
                "files": [normalize_path_to_posix(path) for path in pkg.files],
                "upp": _serialize_upp_payload(getattr(pkg, 'upp', None)),
                "build_system": pkg.build_system,
                "dependencies": getattr(pkg, 'dependencies', []),
                "groups": [
                    {
                        "name": group.name,
                        "files": [normalize_path_to_posix(path) for path in group.files],
                        "readonly": getattr(group, 'readonly', False),
                        "auto_generated": getattr(group, 'auto_generated', False)
                    } for group in pkg.groups
                ],
                "ungrouped_files": [
                    normalize_path_to_posix(path)
                    for path in pkg.ungrouped_files
                ]
            } for pkg in scan_result.packages_detected
        ],
        "unknown_paths": [
            {
                "path": normalize_path_to_posix(unknown.path),
                "type": unknown.type,
                "guessed_kind": getattr(unknown, 'guessed_kind', '')
            } for unknown in getattr(scan_result, 'unknown_paths', [])
        ],
        "user_assemblies": getattr(scan_result, 'user_assemblies', []),
        "internal_packages": [
            {
                "name": ipkg.name,
                "root_path": normalize_repo_path(repo_root, ipkg.root_path)[0],
                "guessed_type": ipkg.guessed_type,
                "members": [normalize_path_to_posix(path) for path in ipkg.members],
                "groups": [
                    {
                        "name": group.name,
                        "files": [normalize_path_to_posix(path) for path in group.files],
                        "readonly": getattr(group, 'readonly', False),
                        "auto_generated": getattr(group, 'auto_generated', False)
                    } for group in getattr(ipkg, '_groups', [])
                ],
                "ungrouped_files": [
                    normalize_path_to_posix(path)
                    for path in getattr(ipkg, '_ungrouped_files', ipkg.members)
                ]
            } for ipkg in getattr(scan_result, 'internal_packages', [])
        ]
    }

    index_data, _ = normalize_repo_model_paths(index_data, repo_root)
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
