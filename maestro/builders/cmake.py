"""
CMake Builder Implementation

This builder implements the CMake build system.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import Builder, Package
from .config import MethodConfig, BuildConfig
from .console import execute_command


class CMakeBuilder(Builder):
    """CMake builder implementation."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("cmake", config)

    def configure(self, package: Package, config: Optional[BuildConfig] = None) -> bool:
        """Run cmake configuration."""
        if config is not None:
            # Attach provided build config to the existing method config
            if hasattr(config, 'config'):
                # If config is actually a MethodConfig, use its config attribute
                self.config.config = config.config
            else:
                # If config is a BuildConfig directly, assign it
                self.config.config = config

        # Determine if we should use out-of-source build
        use_out_of_source = self.config.custom.get('out_of_source', False) or \
            getattr(self.config.config, "flags", {}).get('out_of_source', False)

        if use_out_of_source:
            # Create build directory for out-of-source build
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
        else:
            # In-source build - use package path
            build_dir = package.path

        os.makedirs(build_dir, exist_ok=True)

        # Determine CMake generator based on platform or user specification
        cmake_args = [
            'cmake',
            '-S', package.path,  # Source directory containing CMakeLists.txt
            '-B', build_dir,     # Build directory
        ]

        # Add build type for single-config generators
        # For multi-config generators, build type is specified at build time
        is_multi_config = self._detect_generator_type(build_dir)
        if not is_multi_config:
            # For single-config generators, set build type during configuration
            cmake_args.append(f'-DCMAKE_BUILD_TYPE={self._get_cmake_build_type(self.config.config.build_type.value)}')

        # Add install prefix
        cmake_args.append(f'-DCMAKE_INSTALL_PREFIX={self.config.config.install_prefix}')

        # Add compiler flags from config
        if self.config.compiler.cc:
            cmake_args.append(f'-DCMAKE_C_COMPILER={self.config.compiler.cc}')
        if self.config.compiler.cxx:
            cmake_args.append(f'-DCMAKE_CXX_COMPILER={self.config.compiler.cxx}')

        # Add custom flags from build method
        # Convert config lists to strings
        c_flags_str = " ".join(self.config.compiler.cflags)
        cxx_flags_str = " ".join(self.config.compiler.cxxflags)
        linker_flags_str = " ".join(self.config.compiler.ldflags)

        if c_flags_str:
            cmake_args.append(f'-DCMAKE_C_FLAGS={c_flags_str}')
        if cxx_flags_str:
            cmake_args.append(f'-DCMAKE_CXX_FLAGS={cxx_flags_str}')
        if linker_flags_str:
            cmake_args.append(f'-DCMAKE_EXE_LINKER_FLAGS={linker_flags_str}')
        if self.config.platform.toolchain_file:
            cmake_args.append(f'-DCMAKE_TOOLCHAIN_FILE={self.config.platform.toolchain_file}')

        # Add custom CMake options from package metadata or config
        cmake_options = package.config.get('cmake_options', {})
        for key, value in cmake_options.items():
            cmake_args.append(f'-D{key}={value}')

        # Add verbose flag if enabled
        if self.config.config.verbose:
            cmake_args.append('-Wdev')  # Enable developer warnings

        try:
            result = execute_command(cmake_args, cwd=package.path, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake configuration failed: {str(e)}")
            return False

    def build_package(self, package: Package, config: Optional[BuildConfig] = None) -> bool:
        """Build using cmake --build."""
        if config is not None:
            # Attach provided build config to the existing method config
            if hasattr(config, 'config'):
                # If config is actually a MethodConfig, use its config attribute
                self.config.config = config.config
            else:
                # If config is a BuildConfig directly, assign it
                self.config.config = config

        # First run configure to ensure cmake files are generated
        if not self.configure(package):
            return False

        # Determine if we should use out-of-source build
        use_out_of_source = self.config.custom.get('out_of_source', False) or \
            getattr(self.config.config, "flags", {}).get('out_of_source', False)

        if use_out_of_source:
            # Create build directory for out-of-source build
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
        else:
            # In-source build - use package path
            build_dir = package.path

        # Prepare cmake build arguments
        cmake_args = [
            'cmake',
            '--build', build_dir,
        ]

        # Add configuration for multi-config generators like Visual Studio and Xcode
        # For single-config generators (Makefiles, Ninja), build type is set during configure
        if self._detect_generator_type(build_dir):
            cmake_args.extend(['--config', self._get_cmake_build_type(self.config.config.build_type.value)])

        # Check if a specific target is requested in package config
        target = package.config.get('target')
        if target:
            cmake_args.extend(['--target', target])

        # Add parallel build option
        jobs = self.config.config.jobs if self.config.config.jobs > 0 else os.cpu_count() or 4
        if self.config.config.parallel:
            cmake_args.extend(['--parallel', str(jobs)])

        # Execute the build
        try:
            result = execute_command(cmake_args, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake build failed: {str(e)}")
            return False

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """For CMake projects, linking is typically handled by cmake --build.

        This method would be called if Maestro needs to perform a custom link step,
        but for typical CMake projects, the build step handles linking.
        """
        # In CMake, linking is usually handled by the build process itself
        # This is just a placeholder implementation for interface compliance
        print("CMake link step: For CMake projects, linking is typically handled by the build process.")
        return True

    def clean_package(self, package: Package) -> bool:
        """Clean package build artifacts using cmake."""
        build_dir = os.path.join('.maestro', 'build', self.name, package.name, 'build')

        if os.path.exists(build_dir):
            cmake_args = [
                'cmake',
                '--build', build_dir,
                '--target', 'clean'
            ]

            try:
                result = execute_command(cmake_args)
                return result.returncode == 0
            except Exception as e:
                print(f"CMake clean failed: {str(e)}")
                return False

        # If build directory doesn't exist, clean is considered successful
        return True

    def install_package(self, package: Package, config: Optional[BuildConfig] = None) -> bool:
        """Install the package using cmake --install."""
        if config is not None:
            # Attach provided build config to the existing method config
            if hasattr(config, 'config'):
                # If config is actually a MethodConfig, use its config attribute
                self.config.config = config.config
            else:
                # If config is a BuildConfig directly, assign it
                self.config.config = config

        # Determine if we should use out-of-source build
        use_out_of_source = self.config.custom.get('out_of_source', False) or \
            getattr(self.config.config, "flags", {}).get('out_of_source', False)

        if use_out_of_source:
            # Create build directory for out-of-source build
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
        else:
            # In-source build - use package path
            build_dir = package.path

        # Ensure the build directory exists and is configured
        if not os.path.exists(build_dir):
            if not self.configure(package):
                return False

        cmake_install_args = [
            'cmake',
            '--install', build_dir,
            '--prefix', self.config.config.install_prefix
        ]

        # Add configuration for multi-config generators
        if self._detect_generator_type(build_dir):
            cmake_install_args.extend([
                '--config', self._get_cmake_build_type(self.config.config.build_type.value)
            ])

        try:
            result = execute_command(cmake_install_args, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake install failed: {str(e)}")
            return False

    def build_target(self, package: Package, target: str, config: Optional[BuildConfig] = None) -> bool:
        """Build a specific CMake target."""
        if config is not None:
            # Attach provided build config to the existing method config
            if hasattr(config, 'config'):
                # If config is actually a MethodConfig, use its config attribute
                self.config.config = config.config
            else:
                # If config is a BuildConfig directly, assign it
                self.config.config = config

        # First run configure to ensure cmake files are generated
        if not self.configure(package):
            return False

        # Determine if we should use out-of-source build
        use_out_of_source = self.config.custom.get('out_of_source', False) or \
            getattr(self.config.config, "flags", {}).get('out_of_source', False)

        if use_out_of_source:
            # Create build directory for out-of-source build
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
        else:
            # In-source build - use package path
            build_dir = package.path

        # Prepare cmake build arguments for specific target
        cmake_args = [
            'cmake',
            '--build', build_dir,
            '--target', target,
        ]

        # Add configuration for multi-config generators like Visual Studio and Xcode
        if self._detect_generator_type(build_dir):
            cmake_args.extend(['--config', self._get_cmake_build_type(self.config.config.build_type.value)])

        # Add parallel build option
        jobs = self.config.config.jobs if self.config.config.jobs > 0 else os.cpu_count() or 4
        if self.config.config.parallel:
            cmake_args.extend(['--parallel', str(jobs)])

        # Execute the build
        try:
            result = execute_command(cmake_args, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake build for target '{target}' failed: {str(e)}")
            return False


    def _parse_makefile_targets(self, makefile_path: str) -> List[str]:
        """Parse Makefile to extract target names."""
        targets = []
        try:
            with open(makefile_path, 'r') as f:
                content = f.read()

            # Simple regex to find targets in Makefile (before ':')
            import re
            target_pattern = r'^([a-zA-Z0-9_-]+):'
            matches = re.findall(target_pattern, content, re.MULTILINE)

            # Filter out common non-targets and duplicates
            exclusions = {'all', 'clean', 'install', 'test'}
            targets = list(set([match for match in matches if match not in exclusions and len(match) > 0]))

            # Add standard targets if found
            standard_targets = []
            for excl in exclusions:
                if excl in matches:
                    standard_targets.append(excl)

            return sorted(standard_targets + targets)
        except Exception:
            return []

    def get_target_ext(self) -> str:
        """Return target file extension based on platform."""
        import platform
        system = platform.system().lower()

        if system == 'windows':
            return '.exe'  # On Windows, executables typically have .exe
        elif system in ['linux', 'darwin']:  # Darwin is macOS
            return ''  # Unix-like systems typically have no extension for executables
        else:
            return ''  # Default case

    def _get_cmake_build_type(self, build_type: str) -> str:
        """Convert Maestro build type to CMake build type."""
        build_type_mapping = {
            'debug': 'Debug',
            'release': 'Release',
            'relwithdebinfo': 'RelWithDebInfo',
            'minsizerel': 'MinSizeRel'
        }

        return build_type_mapping.get(build_type.lower(), 'Debug')

    def _detect_generator_type(self, build_dir: str, config: Optional[BuildConfig] = None) -> bool:
        """Detect if the active CMake generator is multi-config or single-config.

        Multi-config generators (Visual Studio, Xcode) allow multiple build types
        in the same build directory, while single-config generators (Makefiles, Ninja)
        require separate build directories per build type.

        Args:
            config: Build configuration
            build_dir: Build directory where CMake files are generated

        Returns:
            True if generator is multi-config, False if single-config
        """
        # Support legacy call signature where config is passed as the first argument.
        if isinstance(build_dir, (BuildConfig, MethodConfig)) and isinstance(config, str):
            build_dir, config = config, build_dir  # swap
        if isinstance(config, (BuildConfig, MethodConfig)):
            if hasattr(config, "config"):
                self.config.config = getattr(config, "config", config)
            else:
                self.config.config = config

        # Try to determine the generator type by checking the generated files
        # in the build directory after configuration

        # Look for solution files (Visual Studio) or project files (Xcode)
        import os
        cmake_cache_path = os.path.join(build_dir, "CMakeCache.txt")

        if os.path.exists(cmake_cache_path):
            try:
                with open(cmake_cache_path, 'r') as f:
                    content = f.read()

                    # Look for generator information in CMakeCache.txt
                    if "Visual Studio" in content:
                        return True  # Visual Studio is multi-config
                    elif "Xcode" in content:
                        return True  # Xcode is multi-config
                    elif "Ninja Multi-Config" in content:
                        return True  # Ninja Multi-Config is multi-config
                    else:
                        # Most other generators (Unix Makefiles, regular Ninja) are single-config
                        return False
            except:
                # If we can't read the cache, fall back to platform-based detection
                pass

        # Fall back to platform-based detection if cache isn't available yet
        # This is used when detecting before initial configuration
        import platform
        system = platform.system().lower()

        # On Windows, default generator is typically Visual Studio (multi-config)
        # On macOS, default generator could be Xcode (multi-config)
        # On Linux, default generator is typically Make/Ninja (single-config)
        if system == 'windows':
            return True  # Visual Studio is multi-config
        elif system == 'darwin':
            return True  # Xcode is multi-config
        else:
            return False  # Make/Ninja are single-config

    def get_available_targets(self, package: Package, config: Optional[BuildConfig] = None) -> List[str]:
        """Get list of available CMake targets using cmake --build help or parsing generators."""
        if isinstance(config, (BuildConfig, MethodConfig)):
            if hasattr(config, "config"):
                self.config.config = getattr(config, "config", config)
            else:
                self.config.config = config
        # First run configure to ensure cmake files are generated
        if not self.configure(package):
            return []

        build_dir = os.path.join(
            self.config.config.target_dir,
            self.config.name,
            package.name,
            "build"
        )

        try:
            # Try to get targets from CMake if generator supports it
            # For multi-config generators, we need to specify a config
            is_multi_config = self._detect_generator_type(build_dir)
            cmake_args = ['cmake', '--build', build_dir, '--target', 'help']

            if is_multi_config:
                cmake_args.extend(['--config', self._get_cmake_build_type(self.config.config.build_type.value)])

            # Try to execute and parse help output to extract targets
            result = execute_command(cmake_args, verbose=False)

            if result.returncode != 0:
                # If help target doesn't work, try parsing generated files
                return self._get_targets_from_generated_files(build_dir, is_multi_config)

            # Parse the output to extract targets
            output = result.stdout.decode('utf-8') if result.stdout else ""
            return self._parse_targets_from_output(output)

        except Exception as e:
            # If cmake help doesn't work, try parsing generated files directly
            return self._get_targets_from_generated_files(build_dir, is_multi_config)

    def _get_targets_from_generated_files(self, build_dir: str, is_multi_config: bool) -> List[str]:
        """Extract targets from generated build files."""
        import platform
        system = platform.system().lower()

        try:
            # For Makefiles, parse Makefile
            makefile_path = os.path.join(build_dir, 'Makefile')
            if os.path.exists(makefile_path):
                return self._parse_makefile_targets(makefile_path)

            # For Visual Studio solutions
            if system == 'windows':
                for file in os.listdir(build_dir):
                    if file.endswith('.sln'):
                        return self._parse_visual_studio_solution_targets(
                            os.path.join(build_dir, file)
                        )

            # For Xcode projects
            if system == 'darwin':
                xcodeproj_path = os.path.join(build_dir, '*.xcodeproj')
                import glob
                xcode_projects = glob.glob(xcodeproj_path)
                if xcode_projects:
                    return self._parse_xcode_project_targets(xcode_projects[0])

            # Default targets if no specific files found
            return ['all', 'clean', 'install', 'test']
        except:
            return ['all', 'clean', 'install', 'test']

    def _parse_targets_from_output(self, output: str) -> List[str]:
        """Parse CMake output to extract available targets."""
        targets = []
        import re

        # Look for target names in output (varies by generator)
        # Common patterns for target extraction
        lines = output.split('\n')
        for line in lines:
            # Look for lines that mention targets
            if 'target' in line.lower():
                # Extract potential target names
                matches = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]*', line)
                for match in matches:
                    if len(match) > 1 and not match.startswith('-') and match.islower():
                        targets.append(match)

        return list(set(targets))  # Remove duplicates

    def _parse_visual_studio_solution_targets(self, solution_path: str) -> List[str]:
        """Parse Visual Studio solution file to extract targets."""
        # This is a simplified implementation, a full implementation would
        # parse the .sln file structure properly
        try:
            with open(solution_path, 'r') as f:
                content = f.read()
            # Look for project definitions in solution file
            import re
            project_pattern = r'Project\(".*"\)\s*=\s*".*",\s*".*",\s*"{.*}"'
            projects = re.findall(project_pattern, content)
            # Extract project names as targets
            targets = []
            for project in projects:
                # Basic extraction - in practice would be more sophisticated
                targets.extend(['build', 'rebuild', 'clean'])
            return list(set(targets))
        except:
            return ['build', 'rebuild', 'clean']

    def _parse_xcode_project_targets(self, project_path: str) -> List[str]:
        """Parse Xcode project file to extract targets."""
        # This would integrate with Xcode command line tools in a full implementation
        # For now, return common Xcode targets
        return ['build', 'clean', 'install', 'test']
