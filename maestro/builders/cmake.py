"""
CMake Builder Implementation

This builder implements the CMake build system.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import Builder, Package, BuildConfig
from .console import execute_command


class CMakeBuilder(Builder):
    """CMake builder implementation."""

    def __init__(self):
        super().__init__("cmake")

    def configure(self, package: Package, config: BuildConfig) -> bool:
        """Run cmake configuration."""
        # Determine build directory
        build_dir = os.path.join(config.target_dir, config.method, package.name, "build")
        os.makedirs(build_dir, exist_ok=True)

        # Determine CMake generator based on platform
        cmake_args = [
            'cmake',
            '-S', package.path,  # Source directory containing CMakeLists.txt
            '-B', build_dir,     # Build directory
            f'-DCMAKE_BUILD_TYPE={self._get_cmake_build_type(config.build_type)}',
            f'-DCMAKE_INSTALL_PREFIX={config.install_prefix}',
        ]

        # Add compiler flags if present
        if 'CC' in config.flags:
            cmake_args.append(f'-DCMAKE_C_COMPILER={config.flags["CC"]}')
        if 'CXX' in config.flags:
            cmake_args.append(f'-DCMAKE_CXX_COMPILER={config.flags["CXX"]}')

        # Add custom flags from build method
        if 'CMAKE_C_FLAGS' in config.flags:
            cmake_args.append(f'-DCMAKE_C_FLAGS={config.flags["CMAKE_C_FLAGS"]}')
        if 'CMAKE_CXX_FLAGS' in config.flags:
            cmake_args.append(f'-DCMAKE_CXX_FLAGS={config.flags["CMAKE_CXX_FLAGS"]}')
        if 'CMAKE_EXE_LINKER_FLAGS' in config.flags:
            cmake_args.append(f'-DCMAKE_EXE_LINKER_FLAGS={config.flags["CMAKE_EXE_LINKER_FLAGS"]}')

        # Add verbose flag if enabled
        if config.verbose:
            cmake_args.append('-Wdev')  # Enable developer warnings

        try:
            result = execute_command(cmake_args, cwd=package.path, verbose=config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake configuration failed: {str(e)}")
            return False

    def build_package(self, package: Package, config: BuildConfig) -> bool:
        """Build using cmake --build."""
        # First run configure to ensure cmake files are generated
        if not self.configure(package, config):
            return False

        # Determine build directory
        build_dir = os.path.join(config.target_dir, config.method, package.name, "build")

        # Prepare cmake build arguments
        cmake_args = [
            'cmake',
            '--build', build_dir,
        ]

        # Add configuration for multi-config generators like Visual Studio and Xcode
        # For single-config generators (Makefiles, Ninja), build type is set during configure
        if self._is_multi_config_generator():
            cmake_args.extend(['--config', self._get_cmake_build_type(config.build_type)])

        # Check if a specific target is requested in package config
        target = package.config.get('target')
        if target:
            cmake_args.extend(['--target', target])

        # Add parallel build option
        if config.parallel and config.jobs > 0:
            cmake_args.extend(['--parallel', str(config.jobs)])

        # Execute the build
        try:
            result = execute_command(cmake_args, verbose=config.verbose)
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

    def install_package(self, package: Package, config: BuildConfig) -> bool:
        """Install the package using cmake --install."""
        build_dir = os.path.join(config.target_dir, config.method, package.name, "build")

        cmake_install_args = [
            'cmake',
            '--install', build_dir,
            '--prefix', config.install_prefix
        ]

        # Add configuration for multi-config generators
        if self._is_multi_config_generator():
            cmake_install_args.extend([
                '--config', self._get_cmake_build_type(config.build_type)
            ])

        try:
            result = execute_command(cmake_install_args, verbose=config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake install failed: {str(e)}")
            return False

    def build_target(self, package: Package, target: str, config: BuildConfig) -> bool:
        """Build a specific CMake target."""
        # First run configure to ensure cmake files are generated
        if not self.configure(package, config):
            return False

        # Determine build directory
        build_dir = os.path.join(config.target_dir, config.method, package.name, "build")

        # Prepare cmake build arguments for specific target
        cmake_args = [
            'cmake',
            '--build', build_dir,
            '--target', target,
        ]

        # Add configuration for multi-config generators like Visual Studio and Xcode
        if self._is_multi_config_generator():
            cmake_args.extend(['--config', self._get_cmake_build_type(config.build_type)])

        # Add parallel build option
        if config.parallel and config.jobs > 0:
            cmake_args.extend(['--parallel', str(config.jobs)])

        # Execute the build
        try:
            result = execute_command(cmake_args, verbose=config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"CMake build for target '{target}' failed: {str(e)}")
            return False

    def get_available_targets(self, package: Package, config: BuildConfig) -> List[str]:
        """Get list of available CMake targets."""
        # First run configure to ensure cmake files are generated
        if not self.configure(package, config):
            return []

        build_dir = os.path.join(config.target_dir, config.method, package.name, "build")

        # Use cmake --build to get target list (on some generators)
        # Alternative: parse the build files directly or use cmake --target help
        try:
            # Use verbose makefile output or check build system files to get targets
            # For now, we'll return a common list based on CMake conventions
            # In a full implementation, we would parse the actual build files
            common_targets = ['all', 'clean', 'install', 'test']

            # For Makefiles, we can try to get targets using make help
            import platform
            system = platform.system().lower()
            if system in ['linux', 'darwin']:
                # Try to get actual targets from Makefile
                makefile_path = os.path.join(build_dir, 'Makefile')
                if os.path.exists(makefile_path):
                    targets = self._parse_makefile_targets(makefile_path)
                    return targets or common_targets

            return common_targets
        except Exception as e:
            print(f"Could not retrieve CMake targets: {str(e)}")
            return []

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

    def _is_multi_config_generator(self) -> bool:
        """Detect if the current system uses multi-config generators by default.

        Multi-config generators (Visual Studio, Xcode) allow multiple build types
        in the same build directory, while single-config generators (Makefiles, Ninja)
        require separate build directories per build type.
        """
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