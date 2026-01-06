"""
U++ Builder implementation for Maestro.

This module implements the U++ builder functionality by porting the essential
umk logic to Python. It handles .upp package files, dependency resolution,
and compilation using GCC/Clang or MSVC based on the build method.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from .base import Builder, Package
from .config import MethodConfig, BuildType, OSFamily
from .console import execute_command, parallel_execute
from .host import Host


@dataclass
class UppPackage(Package):
    """
    U++ package representation extending the base Package class.
    Parses .upp files and manages U++-specific properties.
    """
    # U++ specific properties
    description: str = ""
    mainconfig: str = ""
    files: List[str] = field(default_factory=list)
    uses: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)

    # Conditional configurations
    configs: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, name: str = "", path: str = "", metadata: Dict[str, Any] = None, dir: str = ""):
        super().__init__(name, path, metadata)
        self.dir = dir
        self.description = ""
        self.mainconfig = ""
        self.files = []
        self.uses = []
        self.flags = []
        self.defines = []
        self.configs = {}
        self.build_system = "upp"


class UppBuilder(Builder):
    """
    U++ Builder implementation that ports umk logic to Python.

    Handles U++ package parsing, dependency resolution, and compilation
    using the selected build method (GCC, MSVC, etc).
    """

    def __init__(self, host: Host, config: MethodConfig = None):
        super().__init__("upp", config)
        self.host = host
        self.packages_by_name = {}  # Cache parsed packages
        
    def parse_upp_file(self, upp_file_path: str) -> UppPackage:
        """
        Parse a .upp file and return a UppPackage object.

        This implements the logic similar to U++'s Package file parsing.
        """
        with open(upp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract package name from the .upp file path
        package_name = os.path.splitext(os.path.basename(upp_file_path))[0]

        package = UppPackage(
            name=package_name,
            dir=os.path.dirname(upp_file_path),
            path=upp_file_path
        )
        
        # Simple parser for .upp file format
        # This is a simplified version - real parser would be more robust
        current_section = None
        current_value = []
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Check for section keywords
            if line.startswith('description'):
                # Extract description text
                desc_match = re.match(r'description\s+"([^"]*)"', line)
                if desc_match:
                    package.description = desc_match.group(1)
                    
            elif line.startswith('mainconfig'):
                # Handle multi-line mainconfig section
                # Could be: mainconfig "" = "GUI MT"; (single line)
                # or: mainconfig \n    "" = "GUI MT"; (multi-line as in the test)
                # or: mainconfig { "" = "GUI MT"; } (braced)
                config_match = re.search(r'mainconfig\s+""\s*=\s*"([^"]*)"', line)
                if config_match:
                    package.mainconfig = config_match.group(1)
                elif line == 'mainconfig':
                    # Started a multi-line mainconfig section - need to look for the assignment on next lines
                    current_section = 'mainconfig_waiting_assignment'
                elif '{' in line:
                    current_section = 'mainconfig'
                    current_value = []
                    
            elif line.startswith('file'):
                current_section = 'files'
                # Handle inline file definition
                if line.endswith(','):
                    current_value = [line[5:].strip().rstrip(',').strip('"')]
                elif '"' in line:
                    # Simple case: file "filename.cpp"
                    file_match = re.search(r'"([^"]*)"', line)
                    if file_match:
                        package.files.append(file_match.group(1))
                        
            elif line.startswith('uses'):
                current_section = 'uses'
                # Handle inline uses definition
                if line.endswith(','):
                    current_value = [line[5:].strip().rstrip(',').strip()]
                else:
                    # Handle uses PackageName or uses plugin/z format
                    # This regex captures both regular names and names with slashes
                    uses_match = re.search(r'([a-zA-Z0-9_][a-zA-Z0-9_/]*[a-zA-Z0-9_]|[a-zA-Z0-9_]+)', line[5:])
                    if uses_match:
                        package.uses.append(uses_match.group(1))
                        
            elif line.startswith('flag'):
                current_section = 'flags'
                # Extract flag
                flag_match = re.search(r'(\w+)', line[5:])
                if flag_match:
                    package.flags.append(flag_match.group(1))

            elif line == '{':
                # Handle multi-line sections - if we're waiting for mainconfig, now we have the assignment
                if current_section == 'mainconfig_waiting_assignment':
                    current_section = 'mainconfig'
                    current_value = []
                # Otherwise, continue as before
                continue
            # Handle mainconfig assignment when we're waiting for it
            elif current_section == 'mainconfig_waiting_assignment' and '""' in line and '=' in line:
                # This line should contain the assignment like "   "" = "GUI MT";"
                config_match = re.search(r'""\s*=\s*"([^"]*)"', line)
                if config_match:
                    package.mainconfig = config_match.group(1)
                    current_section = None  # Reset section
                
            elif line == '}':
                # End of multi-line section
                if current_section == 'files':
                    package.files.extend(current_value)
                    current_value = []
                elif current_section == 'uses':
                    package.uses.extend(current_value)
                    current_value = []
                elif current_section == 'flags':
                    package.flags.extend(current_value)
                    current_value = []
                elif current_section == 'mainconfig':
                    # Process mainconfig assignment from collected lines
                    current_value = []
                current_section = None
                
            elif line.endswith(',') and current_section:
                # Continue multi-line values
                if current_section == 'files':
                    file_match = re.search(r'"([^"]*)"', line.rstrip(','))
                    if file_match:
                        current_value.append(file_match.group(1))
                elif current_section == 'uses':
                    # Handle uses with slash format like plugin/z
                    uses_match = re.search(r'([a-zA-Z0-9_][a-zA-Z0-9_/]*[a-zA-Z0-9_]|[a-zA-Z0-9_]+)', line.rstrip(','))
                    if uses_match:
                        current_value.append(uses_match.group(1))
                        
            elif line.endswith(';') and current_section:
                # Last item in multi-line section
                if current_section == 'files':
                    file_match = re.search(r'"([^"]*)"', line.rstrip(';'))
                    if file_match:
                        current_value.append(file_match.group(1))
                        package.files.extend(current_value)
                        current_value = []
                        current_section = None
                elif current_section == 'uses':
                    # Handle uses with slash format like plugin/z
                    uses_match = re.search(r'([a-zA-Z0-9_][a-zA-Z0-9_/]*[a-zA-Z0-9_]|[a-zA-Z0-9_]+)', line.rstrip(';'))
                    if uses_match:
                        current_value.append(uses_match.group(1))
                        package.uses.extend(current_value)
                        current_value = []
                        current_section = None

        return package
    
    def resolve_workspace_dependencies(self, package: UppPackage, all_packages: Dict[str, UppPackage]) -> List[UppPackage]:
        """
        Resolve package dependencies using workspace-like logic similar to U++.
        
        Builds a dependency graph and determines build order.
        """
        visited = set()
        dependency_order = []
        
        def dfs(pkg_name):
            if pkg_name in visited:
                return
            visited.add(pkg_name)
            
            if pkg_name in all_packages:
                pkg = all_packages[pkg_name]
                # Visit dependencies first
                for dep_name in pkg.uses:
                    if dep_name in all_packages:
                        dfs(dep_name)
                
                dependency_order.append(pkg)
        
        dfs(package.name)
        return dependency_order
    
    def get_compiler_flags(self, package: UppPackage, config: Optional[MethodConfig] = None) -> Dict[str, List[str]]:
        """
        Generate compiler flags for the package based on build method and config.

        Maps U++ mainconfig options to actual compiler flags.
        """
        # Use provided config if available, otherwise use default config
        method_config = config if config is not None else self.config

        # Start with config defaults
        cflags = method_config.compiler.cflags.copy()
        cxxflags = method_config.compiler.cxxflags.copy()
        includes = method_config.compiler.includes.copy()
        defines = method_config.compiler.defines.copy()

        # Add package-specific defines
        defines.extend(package.defines)

        # Add U++ specific include paths (uppsrc)
        uppsrc_path = os.path.join(package.dir, "..", "uppsrc")  # Common U++ structure
        if os.path.exists(uppsrc_path):
            includes.append(uppsrc_path)

        # Parse mainconfig and apply appropriate flags
        if package.mainconfig:
            config_parts = [part.strip() for part in package.mainconfig.split()]
            for part in config_parts:
                if part == "GUI":
                    # GUI-specific flags (platform dependent)
                    if self.host.platform == "windows":
                        defines.append("WIN32")
                        defines.append("_WINDOWS")
                    elif self.host.platform in ["linux", "darwin"]:
                        defines.append("GUI_GTK")

        # Add -I flags for dependencies
        for dep_name in package.uses:
            # In a real implementation, this would find actual include paths
            # For now, we'll add a placeholder
            dep_include_path = os.path.join(method_config.config.target_dir, dep_name, "include")
            if os.path.exists(dep_include_path):
                includes.append(dep_include_path)

        # Format defines as -D flags
        define_flags = [f"-D{define}" for define in defines]

        # Format includes as -I flags
        include_flags = [f"-I{inc}" for inc in includes]

        return {
            'cflags': cflags + include_flags[:],  # Copy to avoid mutation
            'cxxflags': cxxflags + define_flags + include_flags,
            'ldflags': method_config.compiler.ldflags.copy()
        }
    
    def build_package(self, package: Union[Package, UppPackage], config: Optional[MethodConfig] = None) -> bool:
        """
        Build a single U++ package.

        Implements the core build logic similar to umk's BuildPackage.
        """
        # Handle both dict and Package object inputs
        if isinstance(package, dict):
            # Convert dict to UppPackage
            package_name = package.get('name', 'unknown')
            package_dir = package.get('dir', package.get('directory', ''))
            package_path = package.get('path', package_dir)
            build_system = package.get('build_system', 'upp')

            upp_pkg = UppPackage(
                name=package_name,
                path=package_path,
                dir=package_dir
            )
            upp_pkg.build_system = build_system

            # Add other attributes from the dict if they exist
            if 'files' in package:
                upp_pkg.files = package['files']
            if 'uses' in package:
                upp_pkg.uses = package['uses']
            if 'description' in package:
                upp_pkg.description = package['description']

            # Parse the .upp file to populate UppPackage
            upp_file = os.path.join(package_dir, f"{package_name}.upp")
            if os.path.exists(upp_file):
                parsed = self.parse_upp_file(upp_file)
                upp_pkg.__dict__.update(parsed.__dict__)
            package = upp_pkg
        elif not isinstance(package, UppPackage):
            # Convert from base package
            upp_pkg = UppPackage(
                name=package.name,
                dir=package.dir,
                path=package.path,
                build_system=package.build_system
            )
            # Parse the .upp file to populate UppPackage
            upp_file = os.path.join(package.dir, f"{package.name}.upp")
            if os.path.exists(upp_file):
                parsed = self.parse_upp_file(upp_file)
                upp_pkg.__dict__.update(parsed.__dict__)
            package = upp_pkg

        # Use provided config if available, otherwise use default config
        method_config = config if config is not None else self.config

        # Get build directory for this package/method combination
        build_dir = os.path.join(
            method_config.config.target_dir,
            method_config.name,
            package.name
        )
        os.makedirs(build_dir, exist_ok=True)

        # Get compiler flags
        flags = self.get_compiler_flags(package, method_config)

        # Determine which compiler to use based on config
        compiler = method_config.compiler.cxx or method_config.compiler.cc

        # Compile each source file
        obj_files = []
        source_extensions = ['.cpp', '.c', '.cxx', '.cc']

        for source_file in package.files:
            source_path = os.path.join(package.dir, source_file)

            # Check if it's a source file
            _, ext = os.path.splitext(source_file.lower())
            if ext in source_extensions:
                # Generate object file path
                obj_name = os.path.splitext(os.path.basename(source_file))[0] + ".o"
                obj_path = os.path.join(build_dir, obj_name)

                # Determine which flags to use based on file type
                if ext in ['.c']:
                    compile_flags = [compiler] + flags['cflags'] + ["-c", source_path, "-o", obj_path]
                else:
                    compile_flags = [compiler] + flags['cxxflags'] + ["-c", source_path, "-o", obj_path]

                # Execute compilation
                success = execute_command(compile_flags, cwd=package.dir)
                if not success:
                    print(f"[ERROR] Failed to compile {source_file} in package {package.name}")
                    return False

                obj_files.append(obj_path)

        # Link the final target
        target_name = f"{package.name}{self.get_target_ext()}"
        target_path = os.path.join(build_dir, target_name)

        link_args = [compiler] + obj_files + flags['ldflags'] + ["-o", target_path]
        success = execute_command(link_args, cwd=build_dir)

        if success:
            print(f"[INFO] Successfully built {target_path}")

        return success
    
    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """
        Link final executable/library from compiled object files.
        """
        # Determine linker based on config
        linker = self.config.compiler.cxx or self.config.compiler.cc or 'g++'

        # Construct link command
        output_file = linkoptions.get('output', 'a.out')
        link_cmd = [linker]

        # Add object files
        link_cmd.extend(linkfiles)

        # Add linker flags from config
        link_cmd.extend(self.config.compiler.ldflags)

        # Add linker flags from linkoptions
        if 'ldflags' in linkoptions:
            link_cmd.extend(linkoptions['ldflags'])

        # Add output file
        link_cmd.extend(['-o', output_file])

        # Execute link command
        return execute_command(link_cmd)
    
    def clean_package(self, package: Union[Package, UppPackage]) -> bool:
        """
        Clean package build artifacts.
        """
        # Cast to UppPackage if needed
        if not isinstance(package, UppPackage):
            package = UppPackage(
                name=package.name,
                dir=package.dir,
                path=package.path,
                build_system=package.build_system
            )

        # Determine build directory for this package/method
        build_dir = os.path.join(
            self.config.config.target_dir,
            self.config.name,
            package.name
        )

        # Remove the entire build directory for this package/method
        if os.path.exists(build_dir):
            import shutil
            try:
                shutil.rmtree(build_dir)
                print(f"[INFO] Cleaned build directory for package {package.name}: {build_dir}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to clean build directory for {package.name}: {e}")
                return False

        print(f"[INFO] No build directory to clean for package {package.name}")
        return True
    
    def get_target_ext(self) -> str:
        """
        Return target file extension based on platform and method.
        """
        # Determine extension based on OS and build type
        if self.host.platform == "windows":
            if self.config.name.endswith("-exe") or self.config.name.endswith("exe"):
                return ".exe"
            else:
                return ".lib"  # Static lib
        else:
            if self.config.name.endswith("-exe") or self.config.name.endswith("exe"):
                return ""      # Unix executables have no extension
            elif self.config.name.endswith("-shared") or self.config.name.endswith("shared"):
                return ".so"   # Shared library on Unix
            else:
                return ".a"    # Static library on Unix
    
    def preprocess_package(self, package: UppPackage) -> bool:
        """
        Preprocess package files (similar to U++'s Preprocess method).

        Handles line ending normalization and other preprocessing tasks.
        """
        # For now, we'll just return True as preprocessing is usually minimal
        # In a full implementation, this would handle U++-specific preprocessing
        return True


class BlitzBuilder:
    """
    Utility class for handling U++'s Blitz build (unity build) functionality.
    
    Creates single translation units by combining multiple .cpp files.
    """
    
    @staticmethod
    def create_blitz_file(source_files: List[str], output_path: str) -> bool:
        """
        Create a blitz (unity) build file combining all source files.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as blitz_file:
                # Add a warning header
                blitz_file.write("// AUTO-GENERATED BLITZ FILE - DO NOT EDIT\n")
                blitz_file.write("// This file combines multiple source files for faster compilation\n\n")
                
                # Include guards to prevent multiple inclusions of headers
                included_headers = set()
                
                for source_file in source_files:
                    with open(source_file, 'r', encoding='utf-8') as src:
                        content = src.read()
                        
                        # Simple heuristic to identify header includes
                        # In reality, U++ has more sophisticated logic
                        lines = content.split('\n')
                        for line in lines:
                            # Look for #include directives
                            include_match = re.match(r'\s*#\s*include\s+[<"]([^">]+)[">]', line)
                            if include_match:
                                header = include_match.group(1)
                                if header not in included_headers:
                                    blitz_file.write(f'#include "{header}"\n')
                                    included_headers.add(header)
                        
                        # Write the actual content
                        blitz_file.write(f"\n//=== BEGIN {os.path.basename(source_file)} ===\n")
                        blitz_file.write(content)
                        blitz_file.write(f"\n//=== END {os.path.basename(source_file)} ===\n\n")
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create blitz file {output_path}: {e}")
            return False


class PPInfo:
    """
    Preprocessor dependency tracker similar to U++'s PPInfo.
    
    Tracks header dependencies and conditional compilation flags.
    """
    
    def __init__(self, cache_dir: str = ".maestro/build/cache"):
        self.cache_dir = cache_dir
        self.deps_cache_path = os.path.join(cache_dir, "deps.json")
        self.dependencies = {}
        self.load_cache()
    
    def load_cache(self):
        """Load dependency cache from disk."""
        if os.path.exists(self.deps_cache_path):
            try:
                with open(self.deps_cache_path, 'r') as f:
                    self.dependencies = json.load(f)
            except Exception:
                self.dependencies = {}
    
    def save_cache(self):
        """Save dependency cache to disk."""
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self.deps_cache_path, 'w') as f:
                json.dump(self.dependencies, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save dependency cache: {e}")
    
    def track_file_deps(self, source_file: str, includes: List[str], defines: List[str]):
        """Track dependencies for a source file."""
        self.dependencies[source_file] = {
            'includes': includes,
            'defines': defines,
            'mtime': os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        }
        self.save_cache()
    
    def needs_rebuild(self, source_file: str) -> bool:
        """Check if a source file needs rebuilding based on dependencies."""
        if source_file not in self.dependencies:
            return True
            
        cached_info = self.dependencies[source_file]
        current_mtime = os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        
        # If source file changed
        if current_mtime != cached_info.get('mtime', 0):
            return True
            
        # Check if any included headers changed
        for header in cached_info.get('includes', []):
            # This is a simplified check; real implementation would check full paths
            if os.path.exists(header) and os.path.getmtime(header) > current_mtime:
                return True
                
        return False