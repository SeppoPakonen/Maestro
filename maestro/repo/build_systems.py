"""
Universal build system detection and package scanning.

Supports multiple build systems:
- CMake
- GNU Make
- BSD Make
- Autoconf/Automake

Each build system scanner returns packages in a universal format.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class BuildSystemPackage:
    """Universal package representation for any build system."""
    name: str
    build_system: str  # 'cmake', 'make', 'autoconf', 'upp', etc.
    dir: str
    files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def detect_build_system(repo_root: str) -> List[str]:
    """
    Detect which build systems are present in the repository.
    Returns list of build system identifiers: ['cmake', 'make', 'autoconf', 'upp']
    """
    systems = []

    # Check for CMake
    if os.path.exists(os.path.join(repo_root, 'CMakeLists.txt')):
        systems.append('cmake')

    # Check for Makefiles
    for makefile_name in ['Makefile', 'GNUmakefile', 'makefile']:
        if os.path.exists(os.path.join(repo_root, makefile_name)):
            systems.append('make')
            break

    # Check for Autoconf
    for autoconf_file in ['configure.ac', 'configure.in', 'Makefile.am']:
        if os.path.exists(os.path.join(repo_root, autoconf_file)):
            systems.append('autoconf')
            break

    # Check for U++ (*.upp files)
    for root, dirs, files in os.walk(repo_root):
        if any(f.endswith('.upp') for f in files):
            systems.append('upp')
            break

    return systems


def scan_cmake_packages(repo_root: str, verbose: bool = False) -> List[BuildSystemPackage]:
    """
    Scan CMake build system for packages/targets.

    CMake package detection strategy:
    1. Find all CMakeLists.txt files
    2. Parse for add_executable(), add_library() targets
    3. Extract source file references
    4. Group by CMakeLists.txt location
    """
    packages = []

    # Find all CMakeLists.txt files
    cmake_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file == 'CMakeLists.txt':
                cmake_path = os.path.join(root, file)
                cmake_files.append(cmake_path)

    # Parse each CMakeLists.txt
    for cmake_path in cmake_files:
        cmake_dir = os.path.dirname(cmake_path)
        rel_dir = os.path.relpath(cmake_dir, repo_root)

        try:
            with open(cmake_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Extract targets: add_executable(name ...) or add_library(name ...)
            target_pattern = r'\b(?:add_executable|add_library)\s*\(\s*(\w+)'
            targets = re.findall(target_pattern, content)

            # Extract source files from set() variables and target definitions
            source_files = []

            # Pattern for source files in CMake (*.c, *.cpp, *.cc, *.h, etc.)
            source_pattern = r'(?:^|\s)([\w/.-]+\.(?:c|cpp|cc|cxx|h|hpp|hxx|inl))\b'
            potential_sources = re.findall(source_pattern, content, re.IGNORECASE | re.MULTILINE)

            for src in potential_sources:
                # Resolve relative to cmake_dir
                if not src.startswith('/'):
                    src_path = os.path.normpath(os.path.join(cmake_dir, src))
                    if os.path.exists(src_path):
                        rel_src = os.path.relpath(src_path, repo_root)
                        source_files.append(rel_src)

            # Create packages for each target found
            if targets:
                for target in targets:
                    pkg = BuildSystemPackage(
                        name=target,
                        build_system='cmake',
                        dir=cmake_dir,
                        files=source_files[:],  # Copy source files list
                        metadata={
                            'cmake_file': os.path.relpath(cmake_path, repo_root),
                            'target_type': 'executable/library'
                        }
                    )
                    packages.append(pkg)

                    if verbose:
                        print(f"[cmake] found target '{target}' in {rel_dir}")

            # If no targets found but CMakeLists.txt exists, create a generic package
            elif cmake_dir == repo_root:
                # Root CMakeLists.txt without clear targets - create project-level package
                project_pattern = r'\bproject\s*\(\s*(\w+)'
                projects = re.findall(project_pattern, content)

                pkg_name = projects[0] if projects else os.path.basename(repo_root)

                pkg = BuildSystemPackage(
                    name=pkg_name,
                    build_system='cmake',
                    dir=cmake_dir,
                    files=source_files,
                    metadata={
                        'cmake_file': os.path.relpath(cmake_path, repo_root),
                        'target_type': 'project'
                    }
                )
                packages.append(pkg)

                if verbose:
                    print(f"[cmake] found project '{pkg_name}' in {rel_dir}")

        except Exception as e:
            if verbose:
                print(f"[cmake] error parsing {cmake_path}: {e}")

    return packages


def scan_makefile_packages(repo_root: str, verbose: bool = False) -> List[BuildSystemPackage]:
    """
    Scan Makefile-based build system for packages/targets.

    This is a stub implementation. Full Makefile parsing is complex.
    For now, we just detect presence and create a placeholder package.
    """
    packages = []

    # Find Makefiles
    makefile_names = ['Makefile', 'GNUmakefile', 'makefile']

    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for makefile_name in makefile_names:
            if makefile_name in files:
                makefile_path = os.path.join(root, makefile_name)
                makefile_dir = os.path.dirname(makefile_path)

                # Create a stub package
                pkg_name = os.path.basename(makefile_dir) or os.path.basename(repo_root)

                pkg = BuildSystemPackage(
                    name=f"{pkg_name}-makefile",
                    build_system='make',
                    dir=makefile_dir,
                    files=[],  # TODO: Parse Makefile for sources
                    metadata={
                        'makefile': os.path.relpath(makefile_path, repo_root),
                        'status': 'stub'
                    }
                )
                packages.append(pkg)

                if verbose:
                    print(f"[make] found Makefile in {os.path.relpath(makefile_dir, repo_root)}")

                break  # Only one Makefile per directory

    return packages


def scan_autoconf_packages(repo_root: str, verbose: bool = False) -> List[BuildSystemPackage]:
    """
    Scan Autoconf/Automake build system for packages.

    This is a stub implementation. Full Autoconf parsing is complex.
    For now, we just detect presence and create a placeholder package.
    """
    packages = []

    # Check for Autoconf files in root
    autoconf_files = ['configure.ac', 'configure.in', 'Makefile.am', 'Makefile.in']
    found_files = []

    for ac_file in autoconf_files:
        ac_path = os.path.join(repo_root, ac_file)
        if os.path.exists(ac_path):
            found_files.append(ac_file)

    if found_files:
        # Try to extract package name from configure.ac
        pkg_name = os.path.basename(repo_root)

        for ac_file in ['configure.ac', 'configure.in']:
            ac_path = os.path.join(repo_root, ac_file)
            if os.path.exists(ac_path):
                try:
                    with open(ac_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Look for AC_INIT(package, version)
                    init_pattern = r'AC_INIT\s*\(\s*\[?(\w+)\]?'
                    matches = re.findall(init_pattern, content)
                    if matches:
                        pkg_name = matches[0]
                        break
                except Exception:
                    pass

        pkg = BuildSystemPackage(
            name=pkg_name,
            build_system='autoconf',
            dir=repo_root,
            files=[],  # TODO: Parse Makefile.am for sources
            metadata={
                'autoconf_files': found_files,
                'status': 'stub'
            }
        )
        packages.append(pkg)

        if verbose:
            print(f"[autoconf] found package '{pkg_name}'")

    return packages


def scan_all_build_systems(repo_root: str, verbose: bool = False) -> Dict[str, List[BuildSystemPackage]]:
    """
    Scan all detected build systems and return packages grouped by build system.

    Returns dict: {'cmake': [...], 'make': [...], 'autoconf': [...]}
    """
    results = {}

    detected = detect_build_system(repo_root)

    if verbose:
        print(f"[build-systems] detected: {', '.join(detected) if detected else 'none'}")

    # Scan each detected build system
    if 'cmake' in detected:
        results['cmake'] = scan_cmake_packages(repo_root, verbose)

    if 'make' in detected and 'cmake' not in detected and 'autoconf' not in detected:
        # Only scan plain Makefiles if no higher-level build system found
        results['make'] = scan_makefile_packages(repo_root, verbose)

    if 'autoconf' in detected:
        results['autoconf'] = scan_autoconf_packages(repo_root, verbose)

    # Note: U++ scanning is handled separately in scan_uplusplus_repo()

    return results
