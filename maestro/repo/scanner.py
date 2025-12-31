"""Repository scanner for U++ packages and assemblies.

This module provides functionality to scan U++ repositories and identify:
- Packages: directories containing <Name>/<Name>.upp files
- Assemblies: directories that contain multiple package folders/packages
- Unknown paths: everything that is not part of any detected package
- User assemblies: from ~/.config/u++/ide/*.var configuration files
- Internal packages: inferred groupings of unknown paths

The scanner uses a pruning strategy to avoid descending into package directories
except along ancestor paths leading to nested package roots.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro.repo.package import PackageInfo


@dataclass
class AssemblyInfo:
    """Information about a detected assembly."""
    name: str
    root_path: str
    package_folders: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)  # References like "found in xyz.var"
    # Additional fields for new assembly features:
    assembly_type: str = 'upp'  # 'upp', 'python', 'java', 'gradle', 'maven', 'misc', 'multi'
    packages: List[str] = field(default_factory=list)  # List of package names contained in this assembly
    package_dirs: List[str] = field(default_factory=list)  # List of package directory paths
    build_systems: List[str] = field(default_factory=list)  # List of build systems used
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnknownPath:
    """Information about an unknown path in the repository."""
    path: str
    type: str  # 'file' or 'dir'
    guessed_kind: str  # 'docs', 'tooling', 'third_party', 'scripts', 'assets', 'config', 'unknown'


@dataclass
class InternalPackage:
    """Maestro internal package grouping for non-U++ paths."""
    name: str
    root_path: str
    guessed_type: str  # 'docs', 'tooling', 'scripts', 'assets', 'third_party', 'misc'
    members: List[str] = field(default_factory=list)  # Relative paths of members


@dataclass
class RepoScanResult:
    """Result of scanning a U++ repository for packages, assemblies, and unknown paths."""
    assemblies_detected: List[AssemblyInfo] = field(default_factory=list)
    packages_detected: List[PackageInfo] = field(default_factory=list)
    unknown_paths: List[UnknownPath] = field(default_factory=list)
    user_assemblies: List[Dict[str, Any]] = field(default_factory=list)  # From ~/.config/u++/ide/*.var
    internal_packages: List[InternalPackage] = field(default_factory=list)  # Inferred from unknown paths


def _is_ignored_path(path: Path, repo_root: Path, skip_dirs: set[str]) -> bool:
    try:
        rel_path = path.relative_to(repo_root)
    except ValueError:
        return True
    for part in rel_path.parts:
        if part.startswith('.'):
            return True
        if part in skip_dirs:
            return True
    return False


def detect_upp_assemblies(
    repo_root: str,
    packages: List[PackageInfo],
    min_packages: int = 1,
    skip_dirs: Optional[set[str]] = None,
    verbose: bool = False,
) -> List[AssemblyInfo]:
    """Detect U++ assemblies based on immediate package children."""
    repo_root_resolved = Path(repo_root).resolve()
    ignore_dirs = set(skip_dirs or set())
    ignore_dirs.update({
        'build', 'dist', 'out', 'target', 'bin', 'obj',
        'Debug', 'Release', 'x64', 'x86',
        'node_modules', '__pycache__', '.maestro',
    })

    assemblies_by_root: Dict[Path, List[PackageInfo]] = {}
    for pkg in packages:
        pkg_path = Path(pkg.dir).resolve()
        try:
            pkg_path.relative_to(repo_root_resolved)
        except ValueError:
            continue
        parent_dir = pkg_path.parent
        if _is_ignored_path(parent_dir, repo_root_resolved, ignore_dirs):
            continue
        assemblies_by_root.setdefault(parent_dir, []).append(pkg)

    assemblies: List[AssemblyInfo] = []
    for asm_root in sorted(assemblies_by_root.keys(), key=lambda p: str(p)):
        packages_in_dir = assemblies_by_root[asm_root]
        if len(packages_in_dir) < min_packages:
            continue
        packages_sorted = sorted(
            packages_in_dir,
            key=lambda pkg: os.path.relpath(pkg.dir, asm_root),
        )
        package_dirs = [str(Path(pkg.dir).resolve()) for pkg in packages_sorted]
        package_names = [pkg.name for pkg in packages_sorted]
        build_systems = sorted({pkg.build_system for pkg in packages_in_dir})
        assembly = AssemblyInfo(
            name=asm_root.name,
            root_path=str(asm_root),
            package_folders=package_dirs,
            assembly_type='upp',
            packages=package_names,
            package_dirs=package_dirs,
            build_systems=build_systems,
            metadata={},
        )
        assemblies.append(assembly)
        if verbose:
            rel_root = os.path.relpath(str(asm_root), str(repo_root_resolved))
            print(f"[maestro] assembly: {rel_root} ({len(package_names)} packages)")

    assemblies.sort(key=lambda asm: asm.root_path)
    return assemblies


def scan_upp_repo_v2(
    root_dir: str,
    verbose: bool = False,
    include_user_config: bool = True,
    collect_files: bool = True,
    scan_unknown_paths: bool = True,
) -> RepoScanResult:
    """
    Scan a U++ repository and identify:
    - packages: directories containing <Name>/<Name>.upp
    - probable assembly roots: directories that contain multiple package folders/packages
    - unknown paths: everything that is not part of any detected package dir
    - user assemblies: from ~/.config/u++/ide/*.var (if include_user_config=True)

    Uses pruning to avoid descending into package directories except along ancestor paths
    leading to nested package roots.

    Args:
        root_dir: Root directory of the U++ repository to scan
        verbose: If True, print verbose scan information
        include_user_config: If True, read user assemblies from ~/.config/u++/ide/*.var

    Returns:
        RepoScanResult: Object containing assemblies_detected, packages_detected, unknown_paths, and user_assemblies
    """
    import os
    from pathlib import Path
    import fnmatch

    # Define source file extensions commonly used in U++
    source_extensions = {'.cpp', '.cppi', '.icpp', '.h', '.hpp', '.inl', '.c', '.cc', '.cxx', '.upl', '.upp', '.t'}

    # Directories to skip during scanning (common non-U++ directories)
    skip_dirs = {
        'node_modules', '.git', '.svn', '.hg', '__pycache__', '.pytest_cache',
        '.tox', '.venv', 'venv', 'env', '.env', 'build', 'dist', '.maestro', '*/venv',
        '.idea', '.vscode', '.vs', 'CMakeFiles', '.mypy_cache', '.coverage',
        'bin', 'obj', 'out', 'target', 'Debug', 'Release', 'x64', 'x86',
        '.cache', 'cache', 'tmp', 'temp', '.tmp', '.temp'
    }

    discovered_packages = []
    all_package_dirs_resolved = set()  # Set of resolved Path objects for package roots
    repo_root_resolved = Path(root_dir).resolve()

    # First pass: scan for packages to identify all package roots
    # We do a full walk first to find all packages, then use that info to prune the unknown scan
    for root, dirs, files in os.walk(root_dir):
        # Prune directories we want to skip
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        # Sort for deterministic order
        dirs.sort()
        files.sort()

        # Extract the package name from the directory name
        pkg_name = os.path.basename(root)

        # Check if this directory contains a .upp file with the same name as the directory
        upp_file_path = os.path.join(root, f"{pkg_name}.upp")

        if os.path.exists(upp_file_path) and os.path.isfile(upp_file_path):
            # This directory is a valid U++ package
            root_resolved = Path(root).resolve()

            if verbose:
                print(f"[maestro] package: {pkg_name} at {root} (from scan root: {root_dir})")

            # Collect source and header files for this package
            pkg_files = []
            if collect_files:
                for pkg_root, pkg_dirs, pkg_files_in_dir in os.walk(root):
                    # Prune directories we want to skip
                    pkg_dirs[:] = [d for d in pkg_dirs if d not in skip_dirs]

                    # Sort for deterministic order
                    pkg_dirs.sort()
                    pkg_files_in_dir.sort()

                    for file in pkg_files_in_dir:
                        _, ext = os.path.splitext(file)
                        rel_path = os.path.relpath(os.path.join(pkg_root, file), root)

                        if ext.lower() in source_extensions:
                            pkg_files.append(rel_path)

            # Parse .upp file to extract metadata
            parsed_upp = None
            groups = []
            ungrouped_files = sorted(pkg_files)  # Default: all files are ungrouped

            try:
                from maestro.repo.upp_parser import parse_upp_file
                parsed_upp = parse_upp_file(upp_file_path)

                # Extract groups and ungrouped files from parsed UPP data
                if parsed_upp and 'groups' in parsed_upp:
                    groups = parsed_upp['groups']

                if parsed_upp and 'ungrouped_files' in parsed_upp:
                    # For ungrouped files, include only those that are also in pkg_files
                    ungrouped_files = [f for f in parsed_upp['ungrouped_files'] if f in pkg_files]

            except Exception as e:
                if verbose:
                    print(f"[maestro] Warning: Failed to parse {upp_file_path}: {e}")

            package_info = PackageInfo(
                name=pkg_name,
                dir=root,
                upp_path=upp_file_path,
                files=sorted(pkg_files),
                upp=parsed_upp,
                groups=groups,
                ungrouped_files=ungrouped_files
            )
            discovered_packages.append(package_info)
            all_package_dirs_resolved.add(root_resolved)

    # Precompute ancestor paths: all directories that are ancestors of any package root
    # This allows us to traverse through parent directories that lead to nested packages
    ancestor_paths_resolved = set()
    for pkg_dir_resolved in all_package_dirs_resolved:
        # Walk up from package dir to repo root, adding all ancestors
        current = pkg_dir_resolved.parent
        while current != repo_root_resolved and current not in ancestor_paths_resolved:
            ancestor_paths_resolved.add(current)
            current = current.parent

    # Second pass: find unknown paths with pruning
    # We prune (skip descending into) package directories unless they're ancestors of other packages
    unknown_paths = []
    if scan_unknown_paths:
        for root, dirs, files in os.walk(root_dir):
            # First, prune common non-U++ directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            # Sort for deterministic order
            dirs.sort()
            files.sort()

            current_resolved = Path(root).resolve()

            # Determine if we should prune this directory's subdirectories
            # We need to check each subdirectory and decide whether to descend into it
            dirs_to_prune = []

            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                dir_resolved = dir_path.resolve()

                # Check if this directory is a package root
                is_package_root = dir_resolved in all_package_dirs_resolved

                # Check if this directory is an ancestor of any package
                is_ancestor = dir_resolved in ancestor_paths_resolved

                # Prune if:
                # - It's a package root AND not an ancestor of another package
                # - It's under a package root (use pathlib containment check)
                if is_package_root and not is_ancestor:
                    # This is a package root with no nested packages -> prune
                    dirs_to_prune.append(dir_name)
                    if verbose:
                        print(f"[maestro] pruning package: {dir_path}")
                else:
                    # Check if this directory is under any package root
                    is_under_package = False
                    for pkg_dir in all_package_dirs_resolved:
                        try:
                            dir_resolved.relative_to(pkg_dir)
                            # If we get here, dir is under pkg_dir
                            # Only prune if it's not an ancestor path
                            if not is_ancestor:
                                is_under_package = True
                                break
                        except ValueError:
                            # Not under this package
                            continue

                    if is_under_package:
                        # This directory is under a package but not an ancestor -> prune
                        dirs_to_prune.append(dir_name)
                        if verbose:
                            print(f"[maestro] pruning under package: {dir_path}")

            # Remove pruned directories from the dirs list (modifies os.walk behavior)
            for dir_to_prune in dirs_to_prune:
                dirs.remove(dir_to_prune)

            # Check if current directory should be marked as unknown
            # A directory is unknown if:
            # - It's not a package root
            # - It's not under any package root
            # - It's not an ancestor of any package root
            # - It's not the repo root itself
            is_package_root = current_resolved in all_package_dirs_resolved
            is_ancestor = current_resolved in ancestor_paths_resolved
            is_under_package_root = False

            for pkg_dir in all_package_dirs_resolved:
                try:
                    current_resolved.relative_to(pkg_dir)
                    is_under_package_root = True
                    break
                except ValueError:
                    continue

            if not is_package_root and not is_under_package_root and not is_ancestor:
                rel_path = os.path.relpath(root, root_dir)
                if rel_path != '.':
                    unknown_paths.append(UnknownPath(
                        path=rel_path,
                        type='dir',
                        guessed_kind=guess_path_kind(rel_path)
                    ))

            # Check files - files are unknown if not under any package root
            for file in files:
                file_path = Path(root) / file
                file_resolved = file_path.resolve()

                is_file_in_package = False
                for pkg_dir in all_package_dirs_resolved:
                    try:
                        file_resolved.relative_to(pkg_dir)
                        is_file_in_package = True
                        break
                    except ValueError:
                        continue

                if not is_file_in_package:
                    rel_file_path = os.path.relpath(file_path, root_dir)
                    unknown_paths.append(UnknownPath(
                        path=rel_file_path,
                        type='file',
                        guessed_kind=guess_path_kind(rel_file_path)
                    ))

    if scan_unknown_paths:
        unknown_paths = [
            unknown
            for unknown in unknown_paths
            if (Path(root_dir) / unknown.path).exists()
        ]

    # Sort results for stability
    discovered_packages.sort(key=lambda x: (x.name, x.dir))
    unknown_paths.sort(key=lambda x: x.path)

    # Scan for other build systems (CMake, Make, Autoconf, etc.)
    build_system_packages = []
    try:
        from maestro.repo.build_systems import scan_all_build_systems

        bs_results = scan_all_build_systems(root_dir, verbose=verbose)

        # Convert BuildSystemPackage to PackageInfo for universal handling
        from maestro.repo.grouping import AutoGrouper

        for build_system, bs_pkgs in bs_results.items():
            for bs_pkg in bs_pkgs:
                # Extract dependencies from metadata
                deps = []
                if bs_pkg.metadata and 'dependencies' in bs_pkg.metadata:
                    # For Gradle: extract project dependency names
                    for dep in bs_pkg.metadata['dependencies']:
                        if dep.get('type') == 'project':
                            deps.append(dep['name'])

                # For non-U++ packages, apply auto-grouping
                groups = []
                ungrouped_files = sorted(bs_pkg.files)

                if bs_pkg.build_system != 'upp':
                    # Apply auto-grouping for non-U++ packages
                    grouper = AutoGrouper()
                    groups = grouper.auto_group(bs_pkg.files)

                    # Identify files that are not in any group
                    grouped_files = set()
                    for group in groups:
                        grouped_files.update(group.files)

                    ungrouped_files = [f for f in bs_pkg.files if f not in grouped_files]

                # Convert to PackageInfo format
                pkg_info = PackageInfo(
                    name=bs_pkg.name,
                    dir=bs_pkg.dir,
                    upp_path=bs_pkg.metadata.get('cmake_file', bs_pkg.metadata.get('makefile', bs_pkg.metadata.get('autoconf_files', [''])[0] if bs_pkg.metadata.get('autoconf_files') else '')) if bs_pkg.metadata else '',
                    files=sorted(bs_pkg.files),
                    build_system=bs_pkg.build_system,  # Store build system type
                    dependencies=deps,
                    groups=groups,
                    ungrouped_files=ungrouped_files
                )
                build_system_packages.append(pkg_info)

    except ImportError as e:
        if verbose:
            print(f"[maestro] Warning: Could not import build_systems: {e}")
    except Exception as e:
        if verbose:
            print(f"[maestro] Warning: Failed to scan build systems: {e}")

    # Keep packages_detected focused on U++ packages to match scan invariants.
    build_system_packages = [
        pkg for pkg in build_system_packages
        if pkg.build_system == 'upp' and pkg.upp_path
    ]
    all_packages = discovered_packages + build_system_packages

    # Identify U++ assemblies based on package layout
    assembly_infos = detect_upp_assemblies(
        root_dir,
        all_packages,
        min_packages=1,
        skip_dirs=skip_dirs,
        verbose=verbose,
    )

    # Read user assemblies from ~/.config/u++/ide/*.var if requested
    user_assemblies = []
    if include_user_config:
        try:
            from maestro.repo.uplusplus_var_reader import read_user_assemblies
            user_assemblies = read_user_assemblies(repo_root=root_dir)

            if verbose and user_assemblies:
                print(f"[maestro] Found {len(user_assemblies)} user assembly configurations")

            # Add evidence_refs to assemblies_detected based on user_assemblies
            for user_asm in user_assemblies:
                for repo_path in user_asm.get('repo_paths', []):
                    # Find matching assembly in assembly_infos
                    repo_path_resolved = os.path.realpath(repo_path)
                    for asm_info in assembly_infos:
                        asm_path_resolved = os.path.realpath(asm_info.root_path)
                        # Check if paths match or are related
                        if repo_path_resolved.startswith(asm_path_resolved) or asm_path_resolved.startswith(repo_path_resolved):
                            evidence_ref = f"found in {user_asm['var_filename']}"
                            if evidence_ref not in asm_info.evidence_refs:
                                asm_info.evidence_refs.append(evidence_ref)
        except ImportError:
            if verbose:
                print("[maestro] Warning: Could not import uplusplus_var_reader")
        except Exception as e:
            if verbose:
                print(f"[maestro] Warning: Failed to read user assemblies: {e}")

    final_assemblies = assembly_infos

    # Infer internal packages from unknown paths
    internal_packages = infer_internal_packages(unknown_paths, root_dir)

    return RepoScanResult(
        assemblies_detected=final_assemblies,
        packages_detected=all_packages,
        unknown_paths=unknown_paths,
        user_assemblies=user_assemblies,
        internal_packages=internal_packages
    )


def guess_path_kind(path: str) -> str:
    """
    Basic heuristics to guess the kind of path.

    Args:
        path: Path to analyze

    Returns:
        Guessed kind: 'docs', 'tooling', 'third_party', 'scripts', 'assets', 'config', 'unknown'
    """
    path_lower = path.lower()

    # Check directory names first
    if 'doc' in path_lower or 'readme' in path_lower:
        return 'docs'
    elif 'tool' in path_lower or 'script' in path_lower or 'bin' in path_lower:
        return 'tooling'
    elif 'third_party' in path_lower or 'vendor' in path_lower or 'external' in path_lower:
        return 'third_party'
    elif 'script' in path_lower or path_lower.endswith('.sh') or path_lower.endswith('.py'):
        return 'scripts'
    elif any(ext in path_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp', '.ico']):
        return 'assets'
    elif any(ext in path_lower for ext in ['.json', '.xml', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf']):
        return 'config'

    return 'unknown'


def infer_internal_packages(unknown_paths: List[UnknownPath], repo_root: str) -> List[InternalPackage]:
    """
    Create Maestro internal packages from unknown paths.

    Groups paths by top-level directory or into 'root_misc' for single files.

    Args:
        unknown_paths: List of unknown paths from repo scan
        repo_root: Repository root path

    Returns:
        List of InternalPackage objects
    """
    from collections import defaultdict
    from pathlib import Path

    # Group paths by top-level directory
    groups = defaultdict(list)

    for unknown in unknown_paths:
        path_parts = Path(unknown.path).parts

        if len(path_parts) == 1:
            # Single file/dir in root - goes to root_misc
            groups['root_misc'].append(unknown)
        else:
            # Group by first directory component
            top_dir = path_parts[0]
            groups[top_dir].append(unknown)

    # Create internal packages from groups
    internal_packages = []

    for group_name, members in sorted(groups.items()):
        # Determine package type from members
        member_kinds = [m.guessed_kind for m in members]

        # Choose dominant type
        kind_counts = {}
        for kind in member_kinds:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

        # Sort by count descending, then by type name
        sorted_kinds = sorted(kind_counts.items(), key=lambda x: (-x[1], x[0]))

        if sorted_kinds:
            dominant_kind = sorted_kinds[0][0]
            # Map 'config' and 'unknown' to 'misc'
            if dominant_kind in ('config', 'unknown'):
                dominant_kind = 'misc'
        else:
            dominant_kind = 'misc'

        # Build root path
        if group_name == 'root_misc':
            root_path = repo_root
        else:
            root_path = str(Path(repo_root) / group_name)

        # Apply auto-grouping to internal packages
        from maestro.repo.grouping import AutoGrouper
        grouper = AutoGrouper()
        groups = grouper.auto_group([m.path for m in members])

        # Identify ungrouped files
        grouped_files = set()
        for group in groups:
            grouped_files.update(group.files)
        ungrouped_files = [m.path for m in members if m.path not in grouped_files]

        internal_pkg = InternalPackage(
            name=group_name,
            root_path=root_path,
            guessed_type=dominant_kind,
            members=[m.path for m in members]
        )

        # Add groups info as additional attributes that will be serialized
        # Since InternalPackage doesn't have groups by default, we need to handle it differently
        # We'll add these as attributes to the dict when serializing
        internal_pkg._groups = groups
        internal_pkg._ungrouped_files = ungrouped_files

        internal_packages.append(internal_pkg)

    return internal_packages


__all__ = [
    'AssemblyInfo',
    'UnknownPath',
    'InternalPackage',
    'RepoScanResult',
    'scan_upp_repo_v2',
    'guess_path_kind',
    'infer_internal_packages',
]
