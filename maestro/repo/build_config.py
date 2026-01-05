"""
Build configuration discovery for different build systems.

Phase 6.5: Build Configuration Discovery
- Extract build config from CMake (compile_commands.json)
- Extract config from Autotools (Makefile parsing)  
- Extract config from Gradle/Maven (build file parsing)
- Resolve U++ config (uses, mainconfig)
- Implement `maestro repo conf [PACKAGE]` command
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .package import PackageInfo


def extract_upp_config(upp_file_path: str) -> Dict[str, Any]:
    """
    Extract build configuration from U++ .upp file.
    
    Args:
        upp_file_path: Path to the .upp file
        
    Returns:
        Dictionary containing configuration data
    """
    if not os.path.exists(upp_file_path):
        return {}
    
    try:
        from .upp_parser import parse_upp_file
        parsed_data = parse_upp_file(upp_file_path)
        return parsed_data or {}
    except ImportError:
        # Fallback if parser not available
        with open(upp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple parsing for basic config extraction
        config = {
            'uses': [],
            'mainconfigs': [],
            'files': [],
            'description': '',
            'flags': [],
            'libraries': []
        }
        
        # Extract uses
        uses_match = re.search(r'uses\s+([^;]+);', content, re.IGNORECASE)
        if uses_match:
            uses_content = uses_match.group(1)
            # Simple parsing of comma-separated list, handling quoted strings
            uses_list = [u.strip().strip('"\'') for u in uses_content.split(',')]
            config['uses'] = uses_list
        
        # Extract description
        desc_match = re.search(r'description\s+["\']([^"\']+)["\'];', content, re.IGNORECASE)
        if desc_match:
            config['description'] = desc_match.group(1)
        
        # Extract mainconfig
        mainconfig_match = re.search(r'mainconfig\s+([^;]+);', content, re.IGNORECASE | re.DOTALL)
        if mainconfig_match:
            mainconfig_content = mainconfig_match.group(1)
            # This is a simplified extraction - a full parser would be more complex
            config['mainconfigs'] = mainconfig_content
        
        return config


def extract_cmake_config(cmake_dir: str) -> Dict[str, Any]:
    """
    Extract build configuration from CMake project.
    
    Args:
        cmake_dir: Directory containing CMakeLists.txt
        
    Returns:
        Dictionary containing CMake configuration data
    """
    config = {
        'cmake_files': [],
        'compile_commands': [],
        'targets': [],
        'definitions': [],
        'include_directories': [],
        'compile_options': [],
        'dependencies': []
    }
    
    # Look for CMakeLists.txt files
    for root, dirs, files in os.walk(cmake_dir):
        for file in files:
            if file.lower() == 'cmakelists.txt':
                config['cmake_files'].append(os.path.join(root, file))
    
    # Look for compile_commands.json if it exists
    compile_commands_path = os.path.join(cmake_dir, 'compile_commands.json')
    if os.path.exists(compile_commands_path):
        try:
            with open(compile_commands_path, 'r', encoding='utf-8') as f:
                compile_data = json.load(f)
                config['compile_commands'] = compile_data
        except Exception:
            pass  # File might exist but be malformed
    
    # Parse CMakeLists.txt files for configuration
    for cmake_file in config['cmake_files']:
        try:
            with open(cmake_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract target definitions
            target_pattern = r'add_executable\s*\(\s*([^\s\)]+)'
            targets = re.findall(target_pattern, content, re.IGNORECASE)
            config['targets'].extend(targets)
            
            target_pattern2 = r'add_library\s*\(\s*([^\s\)]+)'
            lib_targets = re.findall(target_pattern2, content, re.IGNORECASE)
            config['targets'].extend(lib_targets)
            
            # Extract definitions (like -D flags)
            def_pattern = r'add_definitions\s*\(\s*([^\)]+)\)'
            definitions = re.findall(def_pattern, content, re.IGNORECASE)
            for def_str in definitions:
                config['definitions'].extend(def_str.split())
            
            # Extract include directories
            include_pattern = r'include_directories\s*\(\s*([^\)]+)\)'
            includes = re.findall(include_pattern, content, re.IGNORECASE)
            for include_str in includes:
                config['include_directories'].extend(include_str.split())
            
            # Extract compile options
            compopt_pattern = r'add_compile_options\s*\(\s*([^\)]+)\)'
            compopts = re.findall(compopt_pattern, content, re.IGNORECASE)
            for compopt_str in compopts:
                config['compile_options'].extend(compopt_str.split())
            
            # Extract find_package calls for dependencies
            dep_pattern = r'find_package\s*\(\s*([^\s\)]+)'
            deps = re.findall(dep_pattern, content, re.IGNORECASE)
            config['dependencies'].extend(deps)
            
        except Exception:
            # Skip files that can't be read
            continue
    
    return config


def extract_autotools_config(autotools_dir: str) -> Dict[str, Any]:
    """
    Extract build configuration from Autotools project.
    
    Args:
        autotools_dir: Directory containing configure.ac/Makefile.am
        
    Returns:
        Dictionary containing Autotools configuration data
    """
    config = {
        'configure_ac': '',
        'makefile_am': [],
        'makefiles': [],
        'defines': [],
        'includes': [],
        'libs': [],
        'dependencies': []
    }
    
    # Look for configure.ac (or configure.in)
    configure_ac_path = os.path.join(autotools_dir, 'configure.ac')
    if not os.path.exists(configure_ac_path):
        configure_ac_path = os.path.join(autotools_dir, 'configure.in')
    
    if os.path.exists(configure_ac_path):
        config['configure_ac'] = configure_ac_path
        
        # Parse configure.ac for package information
        try:
            with open(configure_ac_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract project information
            project_pattern = r'AC_INIT\s*\(\s*\[?([^\],\s]+)\s*\]?,\s*\[?([^\],\s]+)\s*\]?,?\s*([^\)]*)\)?'
            project_match = re.search(project_pattern, content, re.IGNORECASE)
            if project_match:
                config['project_name'] = project_match.group(1)
                config['version'] = project_match.group(2)
                
            # Extract dependencies (find patterns like PKG_CHECK_MODULES, AC_CHECK_LIB, etc.)
            pkg_check_pattern = r'PKG_CHECK_MODULES\s*\(\s*[^\s,]*\s*,\s*([^\)]+)\s*\)'
            pkg_checks = re.findall(pkg_check_pattern, content, re.IGNORECASE)
            for pkg_check in pkg_checks:
                # Extract dependency names from the check
                dep_names = re.findall(r'([a-zA-Z0-9][a-zA-Z0-9_.-]*)', pkg_check)
                config['dependencies'].extend([d for d in dep_names if len(d) > 1])
                
        except Exception:
            pass  # File might not exist or be readable
    
    # Look for Makefile.am files
    for root, dirs, files in os.walk(autotools_dir):
        for file in files:
            if file.lower() == 'makefile.am':
                config['makefile_am'].append(os.path.join(root, file))
    
    # Look for generated Makefiles
    for root, dirs, files in os.walk(autotools_dir):
        for file in files:
            if file.lower() == 'makefile':
                config['makefiles'].append(os.path.join(root, file))
    
    # Parse Makefiles for configuration
    for makefile in config['makefiles']:
        try:
            with open(makefile, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract common variables
            define_pattern = r'^\s*CPPFLAGS\s*[:+]?=\s*(.*)$'
            defines_matches = re.findall(define_pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in defines_matches:
                # Extract -D defines
                d_matches = re.findall(r'-D([A-Za-z_][A-Za-z0-9_]*)', match)
                config['defines'].extend(d_matches)
            
            include_pattern = r'^\s*CPPFLAGS\s*[:+]?=\s*(.*)$'
            include_matches = re.findall(include_pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in include_matches:
                # Extract -I includes
                i_matches = re.findall(r'-I([^\s]+)', match)
                config['includes'].extend(i_matches)
            
            libs_pattern = r'^\s*LIBS?\s*[:+]?=\s*(.*)$'
            libs_matches = re.findall(libs_pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in libs_matches:
                # Extract -l libraries
                l_matches = re.findall(r'-l([^\s]+)', match)
                config['libs'].extend(l_matches)
                
        except Exception:
            # Skip files that can't be read or parsed
            continue
    
    return config


def extract_gradle_config(gradle_dir: str) -> Dict[str, Any]:
    """
    Extract build configuration from Gradle project.
    
    Args:
        gradle_dir: Directory containing build.gradle or build.gradle.kts
        
    Returns:
        Dictionary containing Gradle configuration data
    """
    config = {
        'build_gradle': [],
        'build_gradle_kts': [],
        'settings_gradle': [],
        'settings_gradle_kts': [],
        'dependencies': [],
        'plugins': [],
        'repositories': [],
        'source_sets': {}
    }
    
    # Look for build.gradle files
    for root, dirs, files in os.walk(gradle_dir):
        for file in files:
            if file == 'build.gradle':
                config['build_gradle'].append(os.path.join(root, file))
            elif file == 'build.gradle.kts':
                config['build_gradle_kts'].append(os.path.join(root, file))
            elif file == 'settings.gradle':
                config['settings_gradle'].append(os.path.join(root, file))
            elif file == 'settings.gradle.kts':
                config['settings_gradle_kts'].append(os.path.join(root, file))
    
    # Parse build files for configuration
    gradle_files = config['build_gradle'] + config['build_gradle_kts']
    
    for gradle_file in gradle_files:
        try:
            with open(gradle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract plugins
            # Groovy: plugins { id 'plugin.name' }
            # Kotlin: plugins { id("plugin.name") }
            plugin_pattern = r'(?:plugins\s*\{[^}]*id\s*["\']([^"\']+)["\']|id\s*["\']([^"\']+)["\']\s*[^a-z])'
            # More specific patterns for plugins block
            plugins_block_match = re.search(r'plugins\s*\{([^}]*)\}', content)
            if plugins_block_match:
                plugins_block = plugins_block_match.group(1)
                plugin_names = re.findall(r'id\s*["\']([^"\']+)["\']', plugins_block)
                config['plugins'].extend(plugin_names)
            
            # Direct plugin application (outside of plugins block)
            apply_plugin_pattern = r"apply\s+plugin:\s*['\"]([^'\"]+)['\"]"
            direct_plugins = re.findall(apply_plugin_pattern, content)
            config['plugins'].extend(direct_plugins)
            
            # Extract dependencies
            dependencies_block_match = re.search(r'dependencies\s*\{([^}]*)\}', content, re.DOTALL)
            if dependencies_block_match:
                deps_block = dependencies_block_match.group(1)
                # Look for implementation, api, compile dependencies
                dep_pattern = r'(?:implementation|api|compile|testImplementation)\s*["\']([^"\']+)["\']'
                deps = re.findall(dep_pattern, deps_block)
                config['dependencies'].extend(deps)
                
                # More complex pattern for dependencies like: implementation group: 'a', name: 'b', version: 'c'
                complex_dep_pattern = r'(?:implementation|api|compile|testImplementation)\s*\(\s*group:\s*["\']([^"\']+)["\']\s*,\s*name:\s*["\']([^"\']+)["\']\s*,\s*version:\s*["\']([^"\']+)["\']'
                for match in re.findall(complex_dep_pattern, deps_block):
                    config['dependencies'].append(f"{match[0]}:{match[1]}:{match[2]}")
            
            # Extract repositories
            repos_block_match = re.search(r'repositories\s*\{([^}]*)\}', content, re.DOTALL)
            if repos_block_match:
                repos_block = repos_block_match.group(1)
                repo_pattern = r'(mavenCentral|mavenLocal|google|jcenter|url\s*["\'][^"\']+["\'])'
                repos = re.findall(repo_pattern, repos_block)
                config['repositories'].extend(repos)
                
        except Exception as e:
            # Skip files that can't be read or parsed
            print(f"Warning: Could not parse Gradle file {gradle_file}: {e}")
            continue
    
    return config


def extract_maven_config(maven_dir: str) -> Dict[str, Any]:
    """
    Extract build configuration from Maven project.
    
    Args:
        maven_dir: Directory containing pom.xml
        
    Returns:
        Dictionary containing Maven configuration data
    """
    config = {
        'pom_xml': [],
        'dependencies': [],
        'plugins': [],
        'properties': {},
        'modules': [],
        'repositories': []
    }
    
    # Look for pom.xml files
    for root, dirs, files in os.walk(maven_dir):
        for file in files:
            if file.lower() == 'pom.xml':
                config['pom_xml'].append(os.path.join(root, file))
    
    # Parse pom.xml files for configuration
    import xml.etree.ElementTree as ET
    
    for pom_file in config['pom_xml']:
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            
            # Extract namespace if present
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag[1:root.tag.index('}')]
                namespace = f"{{{namespace}}}"
            else:
                namespace = ''
            
            # Extract modules
            modules_elem = root.find(f"{namespace}modules")
            if modules_elem is not None:
                for module in modules_elem.findall(f"{namespace}module"):
                    config['modules'].append(module.text)
            
            # Extract properties
            properties_elem = root.find(f"{namespace}properties")
            if properties_elem is not None:
                for prop in properties_elem:
                    config['properties'][prop.tag.replace(namespace, '')] = prop.text
            
            # Extract dependencies
            dependencies_elem = root.find(f"{namespace}dependencies")
            if dependencies_elem is not None:
                for dep in dependencies_elem.findall(f"{namespace}dependency"):
                    group_elem = dep.find(f"{namespace}groupId")
                    artifact_elem = dep.find(f"{namespace}artifactId")
                    version_elem = dep.find(f"{namespace}version")
                    
                    if group_elem is not None and artifact_elem is not None:
                        dep_str = f"{group_elem.text}:{artifact_elem.text}"
                        if version_elem is not None:
                            dep_str += f":{version_elem.text}"
                        config['dependencies'].append(dep_str)
            
            # Extract plugins
            build_elem = root.find(f"{namespace}build")
            if build_elem is not None:
                plugins_elem = build_elem.find(f"{namespace}plugins")
                if plugins_elem is not None:
                    for plugin in plugins_elem.findall(f"{namespace}plugin"):
                        group_elem = plugin.find(f"{namespace}groupId")
                        artifact_elem = plugin.find(f"{namespace}artifactId")
                        version_elem = plugin.find(f"{namespace}version")
                        
                        if artifact_elem is not None:
                            plugin_str = artifact_elem.text
                            if group_elem is not None:
                                plugin_str = f"{group_elem.text}:{plugin_str}"
                            if version_elem is not None:
                                plugin_str += f":{version_elem.text}"
                            config['plugins'].append(plugin_str)
            
            # Extract repositories
            repos_elem = root.find(f"{namespace}repositories")
            if repos_elem is not None:
                for repo in repos_elem.findall(f"{namespace}repository"):
                    name_elem = repo.find(f"{namespace}name")
                    if name_elem is not None:
                        config['repositories'].append(name_elem.text)
                        
        except Exception as e:
            # Skip files that can't be read or parsed
            print(f"Warning: Could not parse Maven file {pom_file}: {e}")
            continue
    
    return config


def extract_msbuild_config(msbuild_dir: str) -> Dict[str, Any]:
    """
    Extract build configuration from MSBuild project.
    
    Args:
        msbuild_dir: Directory containing .vcxproj, .csproj, or .sln files
        
    Returns:
        Dictionary containing MSBuild configuration data
    """
    config = {
        'project_files': [],
        'solution_files': [],
        'configurations': [],
        'platforms': [],
        'references': [],
        'packages': []
    }
    
    # Look for project and solution files
    for root, dirs, files in os.walk(msbuild_dir):
        for file in files:
            if file.endswith(('.vcxproj', '.csproj', '.vbproj')):
                config['project_files'].append(os.path.join(root, file))
            elif file.endswith('.sln'):
                config['solution_files'].append(os.path.join(root, file))
    
    # For now, just record the files - detailed parsing would require more specific XML handling
    import xml.etree.ElementTree as ET
    
    for proj_file in config['project_files']:
        try:
            tree = ET.parse(proj_file)
            root = tree.getroot()
            
            # Extract namespace if present
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag[1:root.tag.index('}')]
                namespace = f"{{{namespace}}}"
            else:
                namespace = ''
            
            # Look for PropertyGroup elements that contain configurations
            for prop_group in root.findall(f".//{namespace}PropertyGroup"):
                config_type = prop_group.find(f"{namespace}ConfigurationType")
                if config_type is not None and config_type.text not in config['configurations']:
                    config['configurations'].append(config_type.text)
                
                platform = prop_group.find(f"{namespace}Platform")
                if platform is not None and platform.text not in config['platforms']:
                    config['platforms'].append(platform.text)
            
            # Look for references
            for reference in root.findall(f".//{namespace}Reference"):
                include = reference.get("Include")
                if include and include not in config['references']:
                    config['references'].append(include)
            
            # Look for package references (NuGet)
            for package_ref in root.findall(f".//{namespace}PackageReference"):
                include = package_ref.get("Include")
                version = package_ref.get("Version")
                if include:
                    pkg_str = include
                    if version:
                        pkg_str += f":{version}"
                    if pkg_str not in config['packages']:
                        config['packages'].append(pkg_str)
                        
        except Exception as e:
            # Skip files that can't be read or parsed
            print(f"Warning: Could not parse MSBuild file {proj_file}: {e}")
            continue
    
    return config


def get_package_config(package_info: PackageInfo) -> Dict[str, Any]:
    """
    Extract build configuration from a package based on its build system type.
    
    Args:
        package_info: PackageInfo object containing package metadata
        
    Returns:
        Dictionary containing build configuration data
    """
    config = {
        'package_name': package_info.name,
        'build_system': package_info.build_system,
        'directory': package_info.dir
    }
    
    if package_info.build_system == 'upp':
        if package_info.upp_path and os.path.exists(package_info.upp_path):
            config.update(extract_upp_config(package_info.upp_path))
    elif package_info.build_system == 'cmake':
        config.update(extract_cmake_config(package_info.dir))
    elif package_info.build_system == 'autoconf':
        config.update(extract_autotools_config(package_info.dir))
    elif package_info.build_system == 'gradle':
        config.update(extract_gradle_config(package_info.dir))
    elif package_info.build_system == 'maven':
        config.update(extract_maven_config(package_info.dir))
    elif package_info.build_system == 'msvs':
        config.update(extract_msbuild_config(package_info.dir))
    else:
        # For unknown or other build systems, just return basic info
        config.update({
            'files': package_info.files,
            'dependencies': package_info.dependencies
        })
    
    return config


def discover_build_configs(repo_root: str, package_names: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Discover build configurations for packages in a repository.
    
    Args:
        repo_root: Root directory of the repository
        package_names: List of package names to analyze (None for all packages)
        
    Returns:
        Dictionary mapping package names to their build configurations
    """
    # Load repo model
    import json
    from maestro.repo.storage import repo_model_path

    index_path = repo_model_path(repo_root, require=True)
    with open(index_path, 'r', encoding='utf-8') as f:
        repo_index = json.load(f)
    
    # Get packages to analyze
    packages_to_analyze = repo_index.get('packages_detected', [])
    
    if package_names:
        # Filter to only specified packages
        packages_to_analyze = [pkg for pkg in packages_to_analyze 
                              if pkg['name'] in package_names]
    
    # Extract configurations for each package
    configs = {}
    for pkg in packages_to_analyze:
        # Convert dict to PackageInfo object for consistency
        from .package import PackageInfo, FileGroup
        from maestro.repo.pathnorm import expand_repo_path
        
        # Create groups from the dict data
        groups = []
        for group_data in pkg.get('groups', []):
            groups.append(FileGroup(
                name=group_data.get('name', ''),
                files=group_data.get('files', []),
                readonly=group_data.get('readonly', False),
                auto_generated=group_data.get('auto_generated', False)
            ))
        
        package_info = PackageInfo(
            name=pkg['name'],
            dir=expand_repo_path(repo_root, pkg.get('dir', '')),
            upp_path=expand_repo_path(repo_root, pkg.get('upp_path', '')),
            files=pkg.get('files', []),
            upp=pkg.get('upp'),
            build_system=pkg.get('build_system', 'upp'),
            dependencies=pkg.get('dependencies', []),
            groups=groups,
            ungrouped_files=pkg.get('ungrouped_files', pkg.get('files', []))
        )
        
        config = get_package_config(package_info)
        configs[pkg['name']] = config
    
    return configs
