"""
Universal build system detection and package scanning.

Supports multiple build systems:
- CMake
- GNU Make
- BSD Make
- Autoconf/Automake
- Maven
- Visual Studio

Each build system scanner returns packages in a universal format.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET


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
    Returns list of build system identifiers: ['cmake', 'make', 'autoconf', 'upp', 'msvs', 'maven']
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

    # Check for Maven (pom.xml files)
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        if 'pom.xml' in files:
            systems.append('maven')
            break

    # Check for Visual Studio (*.sln files)
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        if any(f.endswith('.sln') for f in files):
            systems.append('msvs')
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

    Autoconf package detection strategy:
    1. Find configure.ac/configure.in to extract package name
    2. Find all Makefile.am files in repository
    3. Parse bin_PROGRAMS and lib_LTLIBRARIES targets
    4. Extract source files from *_SOURCES variables
    5. Resolve source paths relative to Makefile.am location
    """
    packages = []

    # Check for Autoconf files in root
    autoconf_files = ['configure.ac', 'configure.in']
    configure_ac_path = None

    for ac_file in autoconf_files:
        ac_path = os.path.join(repo_root, ac_file)
        if os.path.exists(ac_path):
            configure_ac_path = ac_path
            break

    if not configure_ac_path:
        return packages  # No autoconf detected

    # Extract package name from configure.ac
    pkg_name = os.path.basename(repo_root)
    try:
        with open(configure_ac_path, 'r', encoding='utf-8', errors='ignore') as f:
            configure_content = f.read()

        # Look for AC_INIT(package, version) - handles [brackets] and quotes
        init_pattern = r'AC_INIT\s*\(\s*\[?([^\],\s)]+)\]?'
        matches = re.findall(init_pattern, configure_content)
        if matches:
            pkg_name = matches[0]
    except Exception as e:
        if verbose:
            print(f"[autoconf] warning: could not parse {configure_ac_path}: {e}")

    # Find all Makefile.am files
    makefile_am_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        if 'Makefile.am' in files:
            makefile_am_path = os.path.join(root, 'Makefile.am')
            makefile_am_files.append(makefile_am_path)

    # Parse each Makefile.am for targets
    for makefile_am_path in makefile_am_files:
        makefile_dir = os.path.dirname(makefile_am_path)

        try:
            with open(makefile_am_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Extract bin_PROGRAMS targets (executables)
            # Pattern: bin_PROGRAMS = target1 target2 ...
            bin_programs_pattern = r'bin_PROGRAMS\s*[+]?=\s*([^\n]+)'
            bin_programs_matches = re.findall(bin_programs_pattern, content)

            # Extract lib_LTLIBRARIES targets (libraries)
            lib_pattern = r'lib_LTLIBRARIES\s*[+]?=\s*([^\n]+)'
            lib_matches = re.findall(lib_pattern, content)

            # Combine all targets
            targets = []
            for match in bin_programs_matches:
                # Split on whitespace and filter out line continuations
                targets.extend([t.strip() for t in match.split() if t.strip() and not t.strip().endswith('\\')])

            for match in lib_matches:
                targets.extend([t.strip() for t in match.split() if t.strip() and not t.strip().endswith('\\')])

            # For each target, find its sources
            for target in targets:
                # Clean target name: remove .la suffix from libraries
                target_clean = target.replace('.la', '').replace('-', '_').replace('.', '_')

                # Pattern: target_SOURCES = file1.cpp file2.cpp ...
                # Note: Automake converts - and . to _ in variable names
                sources_pattern = rf'{re.escape(target_clean)}_SOURCES\s*[+]?=\s*([^#]*?)(?=\n\S|\n*$)'
                sources_matches = re.findall(sources_pattern, content, re.DOTALL)

                source_files = []
                for sources_match in sources_matches:
                    # Extract individual source files
                    # Pattern matches file extensions: .c, .cpp, .cc, .cxx, .h, .hpp, etc.
                    file_pattern = r'(?:^|\s)([\w/.-]+\.(?:c|cpp|cc|cxx|C|h|hpp|hxx|hh|H|inl|inc|pkg))(?:\s|\\|\n|$)'
                    source_matches = re.findall(file_pattern, sources_match, re.MULTILINE)

                    for src_file in source_matches:
                        src_file = src_file.strip()
                        if not src_file:
                            continue

                        # Resolve path relative to Makefile.am location or repo root
                        if src_file.startswith('/'):
                            # Absolute path (rare)
                            if os.path.exists(src_file):
                                rel_src = os.path.relpath(src_file, repo_root)
                                source_files.append(rel_src)
                        elif src_file.startswith('$(') or src_file.startswith('@'):
                            # Variable reference - skip
                            continue
                        else:
                            # Relative path - try both repo root and Makefile.am directory
                            # Some projects use repo-relative paths even in subdirectory Makefile.am
                            src_path_from_root = os.path.normpath(os.path.join(repo_root, src_file))
                            src_path_from_makefile = os.path.normpath(os.path.join(makefile_dir, src_file))

                            if os.path.exists(src_path_from_root):
                                # Path is relative to repo root
                                rel_src = os.path.relpath(src_path_from_root, repo_root)
                                source_files.append(rel_src)
                            elif os.path.exists(src_path_from_makefile):
                                # Path is relative to Makefile.am directory
                                rel_src = os.path.relpath(src_path_from_makefile, repo_root)
                                source_files.append(rel_src)

                # Create package for this target
                if source_files or targets:  # Create package even if no sources found (might be generated)
                    pkg = BuildSystemPackage(
                        name=target.replace('.la', ''),  # Clean library names
                        build_system='autoconf',
                        dir=makefile_dir,
                        files=source_files,
                        metadata={
                            'configure_ac': os.path.relpath(configure_ac_path, repo_root),
                            'makefile_am': os.path.relpath(makefile_am_path, repo_root),
                            'target_type': 'executable' if target in bin_programs_matches else 'library',
                            'project_name': pkg_name
                        }
                    )
                    packages.append(pkg)

                    if verbose:
                        target_type = 'executable' if any(target in m for m in bin_programs_matches) else 'library'
                        print(f"[autoconf] found {target_type} '{target}' in {os.path.relpath(makefile_dir, repo_root)} ({len(source_files)} sources)")

        except Exception as e:
            if verbose:
                print(f"[autoconf] error parsing {makefile_am_path}: {e}")

    # If no packages found but autoconf detected, create a project-level package
    if not packages and configure_ac_path:
        pkg = BuildSystemPackage(
            name=pkg_name,
            build_system='autoconf',
            dir=repo_root,
            files=[],
            metadata={
                'configure_ac': os.path.relpath(configure_ac_path, repo_root),
                'target_type': 'project'
            }
        )
        packages.append(pkg)

        if verbose:
            print(f"[autoconf] found project '{pkg_name}' (no targets in Makefile.am)")

    return packages


def scan_msvs_packages(repo_root: str, verbose: bool = False) -> List[BuildSystemPackage]:
    """
    Scan Microsoft Visual Studio build system for packages.

    Visual Studio package detection strategy:
    1. Find all .sln (solution) files
    2. Parse solution files to extract project references
    3. Parse project files (.vcxproj, .vcproj, .csproj) to extract:
       - Project name, GUID, type
       - Configuration platforms (Debug/Release, Win32/x64, etc.)
       - Source files (ClCompile, ClInclude for C++; Compile for C#)
       - Project dependencies
       - Compiler/linker settings
    4. Support both new format (.vcxproj, .csproj - XML-based) and old format (.vcproj)
    """
    packages = []

    # Find all .sln files
    sln_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file.endswith('.sln'):
                sln_path = os.path.join(root, file)
                sln_files.append(sln_path)

    # Parse each solution file
    for sln_path in sln_files:
        sln_dir = os.path.dirname(sln_path)

        try:
            with open(sln_path, 'r', encoding='utf-8', errors='ignore') as f:
                sln_content = f.read()

            # Extract solution format version
            version_match = re.search(r'Format Version\s+([\d.]+)', sln_content)
            format_version = version_match.group(1) if version_match else 'unknown'

            # Extract Visual Studio version
            vs_version_match = re.search(r'# Visual Studio (.+)', sln_content)
            vs_version = vs_version_match.group(1).strip() if vs_version_match else 'unknown'

            # Extract project references from solution
            # Pattern: Project("{TYPE-GUID}") = "Name", "Path", "{PROJECT-GUID}"
            project_pattern = r'Project\("{([^}]+)}"\)\s*=\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"{([^}]+)}"'
            project_matches = re.findall(project_pattern, sln_content)

            if verbose:
                print(f"[msvs] found solution '{os.path.basename(sln_path)}' (VS {vs_version}, format {format_version}) with {len(project_matches)} projects")

            # Parse each project file
            for type_guid, proj_name, proj_path, proj_guid in project_matches:
                # Resolve project path relative to solution directory
                if proj_path.startswith('$('):
                    # Skip variable references
                    continue

                # Convert Windows backslash paths to forward slashes
                proj_path_normalized = proj_path.replace('\\', '/')
                proj_file_path = os.path.normpath(os.path.join(sln_dir, proj_path_normalized))

                if not os.path.exists(proj_file_path):
                    if verbose:
                        print(f"[msvs] warning: project file not found: {proj_path}")
                    continue

                proj_dir = os.path.dirname(proj_file_path)
                proj_ext = os.path.splitext(proj_file_path)[1].lower()

                # Parse project file based on extension
                source_files = []
                project_metadata = {
                    'solution': os.path.relpath(sln_path, repo_root),
                    'project_file': os.path.relpath(proj_file_path, repo_root),
                    'project_guid': proj_guid,
                    'type_guid': type_guid,
                    'format_version': format_version,
                    'vs_version': vs_version
                }

                try:
                    if proj_ext in ['.vcxproj', '.csproj']:
                        # New XML-based format
                        source_files = _parse_msbuild_project(proj_file_path, proj_dir, repo_root, verbose)
                        project_metadata['format'] = 'MSBuild'
                    elif proj_ext == '.vcproj':
                        # Old XML format
                        source_files = _parse_vcproj_project(proj_file_path, proj_dir, repo_root, verbose)
                        project_metadata['format'] = 'VC++ 2005/2008'
                    else:
                        if verbose:
                            print(f"[msvs] unsupported project format: {proj_ext}")
                        continue

                    # Determine project type
                    if type_guid.upper() == '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942':
                        project_metadata['project_type'] = 'C++'
                    elif type_guid.upper() == 'FAE04EC0-301F-11D3-BF4B-00C04F79EFBC':
                        project_metadata['project_type'] = 'C#'
                    else:
                        project_metadata['project_type'] = 'unknown'

                    # Create package
                    pkg = BuildSystemPackage(
                        name=proj_name,
                        build_system='msvs',
                        dir=proj_dir,
                        files=source_files,
                        metadata=project_metadata
                    )
                    packages.append(pkg)

                    if verbose:
                        print(f"[msvs] found {project_metadata.get('project_type', 'unknown')} project '{proj_name}' ({len(source_files)} sources)")

                except Exception as e:
                    if verbose:
                        print(f"[msvs] error parsing project {proj_path}: {e}")

        except Exception as e:
            if verbose:
                print(f"[msvs] error parsing solution {sln_path}: {e}")

    return packages


def _parse_msbuild_project(proj_path: str, proj_dir: str, repo_root: str, verbose: bool = False) -> List[str]:
    """
    Parse MSBuild-based project file (.vcxproj, .csproj) to extract source files.

    Returns list of source file paths relative to repo root.
    """
    source_files = []

    try:
        tree = ET.parse(proj_path)
        root = tree.getroot()

        # MSBuild uses XML namespaces
        ns = {'msbuild': 'http://schemas.microsoft.com/developer/msbuild/2003'}

        # Find all source file elements
        # For C++: ClCompile (C++ source), ClInclude (headers)
        # For C#: Compile (C# source)
        for elem_name in ['ClCompile', 'ClInclude', 'Compile']:
            for elem in root.findall(f'.//msbuild:{elem_name}', ns):
                include = elem.get('Include')
                if include:
                    source_files.append(include)

            # Also try without namespace (some files don't use it)
            for elem in root.findall(f'.//{elem_name}'):
                include = elem.get('Include')
                if include:
                    source_files.append(include)

        # Resolve paths and convert to repo-relative
        resolved_files = []
        for src_file in source_files:
            # Skip variable references
            if src_file.startswith('$(') or src_file.startswith('%'):
                continue

            # Convert Windows backslash to forward slash
            src_file_normalized = src_file.replace('\\', '/')

            # Handle wildcards (e.g., "**/*.cs")
            if '*' in src_file_normalized:
                # Expand wildcard pattern relative to project directory
                from pathlib import Path
                proj_path = Path(proj_dir)

                try:
                    # Use glob to expand wildcards
                    for matched_file in proj_path.glob(src_file_normalized):
                        if matched_file.is_file():
                            rel_src = os.path.relpath(str(matched_file), repo_root)
                            resolved_files.append(rel_src)
                except Exception:
                    # Invalid glob pattern - skip
                    pass
            else:
                # Resolve relative to project directory
                src_path = os.path.normpath(os.path.join(proj_dir, src_file_normalized))

                if os.path.exists(src_path):
                    rel_src = os.path.relpath(src_path, repo_root)
                    resolved_files.append(rel_src)

        return resolved_files

    except Exception as e:
        if verbose:
            print(f"[msvs] error parsing MSBuild project {proj_path}: {e}")
        return []


def _parse_vcproj_project(proj_path: str, proj_dir: str, repo_root: str, verbose: bool = False) -> List[str]:
    """
    Parse old Visual C++ project file (.vcproj) to extract source files.

    Returns list of source file paths relative to repo root.
    """
    source_files = []

    try:
        tree = ET.parse(proj_path)
        root = tree.getroot()

        # Find all File elements (no namespace in old format)
        for file_elem in root.findall('.//File'):
            rel_path = file_elem.get('RelativePath')
            if rel_path:
                source_files.append(rel_path)

        # Resolve paths and convert to repo-relative
        resolved_files = []
        for src_file in source_files:
            # Skip variable references
            if src_file.startswith('$(') or src_file.startswith('%'):
                continue

            # Convert Windows backslash to forward slash
            src_file_normalized = src_file.replace('\\', '/')

            # Resolve relative to project directory
            src_path = os.path.normpath(os.path.join(proj_dir, src_file_normalized))

            if os.path.exists(src_path):
                rel_src = os.path.relpath(src_path, repo_root)
                resolved_files.append(rel_src)

        return resolved_files

    except Exception as e:
        if verbose:
            print(f"[msvs] error parsing vcproj project {proj_path}: {e}")
        return []


def scan_maven_packages(repo_root: str, verbose: bool = False) -> List[BuildSystemPackage]:
    """
    Scan Maven build system for packages/modules.

    Maven package detection strategy:
    1. Find all pom.xml files in repository
    2. Parse each pom.xml to extract:
       - groupId, artifactId, version (GAV coordinates)
       - packaging type (jar, war, pom, etc.)
       - parent POM relationships
       - module hierarchy
    3. Extract source files from standard Maven directories (src/main/java, src/main/resources, etc.)
    4. Handle multi-module projects
    """
    packages = []

    # Find all pom.xml files
    pom_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories and common Maven build/target directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['target', 'build']]

        if 'pom.xml' in files:
            pom_path = os.path.join(root, 'pom.xml')
            pom_files.append(pom_path)

    # Parse each pom.xml
    for pom_path in pom_files:
        pom_dir = os.path.dirname(pom_path)
        rel_dir = os.path.relpath(pom_dir, repo_root)

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()

            # Maven POMs use XML namespaces
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

            # Extract project metadata (try with and without namespace)
            def get_text(elem_name, default='unknown'):
                # Try with namespace
                elem = root.find(f'mvn:{elem_name}', ns)
                if elem is not None and elem.text:
                    return elem.text.strip()
                # Try without namespace
                elem = root.find(elem_name)
                if elem is not None and elem.text:
                    return elem.text.strip()
                return default

            group_id = get_text('groupId', '')
            artifact_id = get_text('artifactId', os.path.basename(pom_dir))
            version = get_text('version', '')
            packaging = get_text('packaging', 'jar')

            # Check for parent POM
            parent_elem = root.find('mvn:parent', ns) or root.find('parent')
            parent_group_id = None
            parent_artifact_id = None
            if parent_elem is not None:
                parent_group_elem = parent_elem.find('mvn:groupId', ns) or parent_elem.find('groupId')
                parent_artifact_elem = parent_elem.find('mvn:artifactId', ns) or parent_elem.find('artifactId')
                if parent_group_elem is not None:
                    parent_group_id = parent_group_elem.text.strip()
                if parent_artifact_elem is not None:
                    parent_artifact_id = parent_artifact_elem.text.strip()

            # Check for modules (multi-module project)
            modules = []
            modules_elem = root.find('mvn:modules', ns) or root.find('modules')
            if modules_elem is not None:
                for module_elem in modules_elem.findall('mvn:module', ns) or modules_elem.findall('module'):
                    if module_elem.text:
                        modules.append(module_elem.text.strip())

            # Collect source files from standard Maven directory structure
            source_files = []
            source_dirs = [
                'src/main/java',
                'src/main/resources',
                'src/test/java',
                'src/test/resources'
            ]

            for src_dir in source_dirs:
                src_path = os.path.join(pom_dir, src_dir)
                if os.path.exists(src_path):
                    for src_root, src_dirs, src_files in os.walk(src_path):
                        # Skip hidden directories
                        src_dirs[:] = [d for d in src_dirs if not d.startswith('.')]

                        for file in src_files:
                            file_path = os.path.join(src_root, file)
                            rel_file = os.path.relpath(file_path, repo_root)
                            source_files.append(rel_file)

            # Build package name from groupId:artifactId
            if group_id:
                pkg_name = f"{group_id}:{artifact_id}"
            else:
                pkg_name = artifact_id

            # Metadata
            metadata = {
                'pom_file': os.path.relpath(pom_path, repo_root),
                'group_id': group_id,
                'artifact_id': artifact_id,
                'version': version,
                'packaging': packaging,
            }

            if parent_group_id or parent_artifact_id:
                metadata['parent'] = f"{parent_group_id}:{parent_artifact_id}" if parent_group_id else parent_artifact_id

            if modules:
                metadata['modules'] = modules
                metadata['is_parent'] = True

            # Create package
            pkg = BuildSystemPackage(
                name=pkg_name,
                build_system='maven',
                dir=pom_dir,
                files=source_files,
                metadata=metadata
            )
            packages.append(pkg)

            if verbose:
                module_info = f" (parent with {len(modules)} modules)" if modules else ""
                print(f"[maven] found {packaging} '{pkg_name}'{module_info} in {rel_dir} ({len(source_files)} sources)")

        except Exception as e:
            if verbose:
                print(f"[maven] error parsing {pom_path}: {e}")

    return packages


def scan_all_build_systems(repo_root: str, verbose: bool = False) -> Dict[str, List[BuildSystemPackage]]:
    """
    Scan all detected build systems and return packages grouped by build system.

    Returns dict: {'cmake': [...], 'make': [...], 'autoconf': [...], 'maven': [...]}
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

    if 'maven' in detected:
        results['maven'] = scan_maven_packages(repo_root, verbose)

    if 'msvs' in detected:
        results['msvs'] = scan_msvs_packages(repo_root, verbose)

    # Note: U++ scanning is handled separately in scan_uplusplus_repo()

    return results
