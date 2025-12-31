"""
MSBuild Builder Implementation

This builder implements the MSBuild (Visual Studio) build system.
Supports building .vcxproj, .csproj, .vbproj, and .sln files.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import Builder, Package
from .config import MethodConfig, BuildConfig


class MsBuildBuilder(Builder):
    """
    MSBuild builder implementation for Visual Studio projects.

    Supports:
    - Configuration selection (Debug, Release)
    - Platform selection (Win32, x64, ARM, ARM64)
    - Solution builds (.sln files)
    - Project dependency resolution
    - Modern (.vcxproj) and legacy (.vcproj) project formats
    """

    def __init__(self, config: MethodConfig = None):
        super().__init__("msbuild", config)
        self.msbuild_cmd = self._find_msbuild()

    def _find_msbuild(self) -> Optional[str]:
        """
        Find the MSBuild executable on the system.
        On Windows: Look for MSBuild in Visual Studio installation
        On other platforms: Check for xbuild or msbuild in PATH
        """
        # Define possible MSBuild paths on Windows
        possible_paths = [
            shutil.which("msbuild"),  # Standard PATH lookup
            shutil.which("dotnet")    # dotnet build command
        ]

        # Check for Visual Studio installations on Windows
        if sys.platform.startswith("win"):
            # Common VS installation paths
            vs_paths = [
                r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Enterprise\MSBuild\15.0\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\MSBuild.exe",
            ]

            for vs_path in vs_paths:
                if os.path.exists(vs_path):
                    return vs_path

        # Check standard paths found
        for path in possible_paths:
            if path:
                return path

        # Return None if no MSBuild found
        return None

    def _find_project_file(self, package_dir: str) -> Optional[str]:
        """
        Find the appropriate project or solution file in the package directory.

        Looks for:
        - .sln files (solutions)
        - .vcxproj files (C++ projects)
        - .csproj files (C# projects)
        - .vbproj files (VB.NET projects)
        - .vcproj files (legacy C++ projects)
        """
        package_path = Path(package_dir)

        # Define priority order for project files
        project_extensions = ['.sln', '.vcxproj', '.csproj', '.vbproj', '.vcproj']

        for ext in project_extensions:
            project_files = list(package_path.glob(f'*{ext}'))
            if project_files:
                # If multiple files exist, prefer files named after the package
                for proj_file in project_files:
                    if package_path.name.lower() in proj_file.name.lower():
                        return str(proj_file)

                # Otherwise, return the first file found
                return str(project_files[0])

        return None

    def _extract_solution_projects(self, solution_file: str) -> List[str]:
        """
        Extract project information from a solution file (.sln).
        This helps with dependency resolution in multi-project solutions.

        Args:
            solution_file: Path to the solution file

        Returns:
            List of project file paths referenced in the solution
        """
        project_paths = []
        try:
            with open(solution_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for Project entries in the solution file
            import re
            # Split the content by 'EndProject' and then look for the project line in each section
            sections = content.split('EndProject')

            for section in sections:
                # Look for the project path in each section
                project_match = re.search(r'Project\([^)]*\)\s*=\s*"[^"]*"\s*,\s*"([^"]+)"\s*,\s*"[^"]*"', section)
                if project_match:
                    project_ref = project_match.group(1)
                    # Resolve the relative path from solution directory
                    project_path = (Path(solution_file).parent / project_ref).resolve()
                    # Always add the resolved path, but warn if it doesn't exist
                    resolved_path = str(project_path)
                    if not project_path.exists():
                        print(f"[msbuild] Warning: Project file {resolved_path} referenced in solution does not exist")
                    project_paths.append(resolved_path)

        except Exception as e:
            print(f"[msbuild] Warning: Could not parse solution file {solution_file}: {str(e)}")

        return project_paths

    def _get_configuration_from_build_type(self, build_type: str) -> str:
        """Map build_type to Visual Studio configuration."""
        mapping = {
            'debug': 'Debug',
            'release': 'Release',
            'relwithdebinfo': 'RelWithDebInfo',
            'minsizerel': 'MinSizeRel'
        }
        return mapping.get(build_type.lower(), 'Debug')

    def _get_platform_from_config(self, config: Optional["BuildConfig"] = None) -> str:
        """Get platform from build config, with defaults."""
        platform_map = {
            'x86': 'Win32',
            'x64': 'x64',
            'arm': 'ARM',
            'arm64': 'ARM64'
        }

        platform = None
        if config and getattr(config, "flags", None):
            platform = config.flags.get('platform')

        if platform is None:
            # Check if platform is specified in config custom properties
            platform = self.config.custom.get('platform', 'x64')

            # Check if platform is in platform config
            if hasattr(self.config.platform, 'arch') and self.config.platform.arch:
                platform = self.config.platform.arch

        # Return mapped platform or platform as-is if not in map
        return platform_map.get(platform.lower(), platform)

    def configure(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Configure the MSBuild project.
        Creates or updates project settings based on config.
        """
        # For MSBuild, configuration is typically handled via command line args
        # So we just verify we can find the project file
        project_file = self._find_project_file(package.path)
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        # Store the project file in the package metadata for later use
        package.metadata['project_file'] = project_file
        return True

    def build_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Build the Visual Studio project using MSBuild.

        Args:
            package: Package to build

        Returns:
            True if build succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Please install Visual Studio or build tools.")
            return False

        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        # Determine configuration and platform
        build_type = config.build_type if config else self.config.config.build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config)

        # Handle solution files specially (for multi-project builds)
        is_solution = project_file.lower().endswith('.sln')

        # Build command arguments
        jobs = 0
        if config and getattr(config, "jobs", 0) > 0:
            jobs = config.jobs
        elif self.config.config.jobs > 0:
            jobs = self.config.config.jobs
        else:
            jobs = os.cpu_count() or 4
        msbuild_args = [
            self.msbuild_cmd,
            project_file,
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
            f'/m:{jobs}',  # equivalent to -j for parallel builds
        ]

        # Add verbosity if requested
        if self.config.config.verbose:
            msbuild_args.append('/v:detailed')
        else:
            msbuild_args.append('/v:minimal')

        # Add any custom properties from config
        if 'msbuild_properties' in self.config.custom:
            for prop in self.config.custom['msbuild_properties']:
                msbuild_args.append(f'/p:{prop}')

        # Execute the build
        print(f"[msbuild] Building {package.name} with command: {' '.join(msbuild_args)}")
        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(project_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"[msbuild] Build succeeded for {package.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[msbuild] Build failed for {package.name}: {e.stderr}")
            return False
        except Exception as e:
            print(f"[msbuild] Unexpected error building {package.name}: {str(e)}")
            return False

    def build_solution(self, solution_file: str) -> bool:
        """
        Build all projects in a Visual Studio solution with proper dependency ordering.

        Args:
            solution_file: Path to the solution file (.sln)

        Returns:
            True if build succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot build solution.")
            return False

        # Extract project dependencies from solution
        solution_projects = self._extract_solution_projects(solution_file)

        if not solution_projects:
            print(f"[msbuild] No projects found in solution {solution_file}")
            # Fall back to building the solution directly
            return self._build_solution_direct(solution_file)

        print(f"[msbuild] Building solution {solution_file} with {len(solution_projects)} projects")

        # Build each project in the solution
        for project_file in solution_projects:
            print(f"[msbuild] Building project: {project_file}")
            # Create a temporary package for this project
            project_package = Package(
                name=Path(project_file).stem,
                path=str(Path(project_file).parent),
                metadata={'project_file': project_file}
            )

            if not self.build_package(project_package):
                print(f"[msbuild] Failed to build project {project_file}")
                return False

        print(f"[msbuild] Solution build completed successfully")
        return True

    def _build_solution_direct(self, solution_file: str) -> bool:
        """
        Build a solution file directly using MSBuild.

        Args:
            solution_file: Path to the solution file (.sln)

        Returns:
            True if build succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            return False

        build_config = self._get_configuration_from_build_type(self.config.config.build_type.value)
        platform = self._get_platform_from_config()

        # Build command arguments for solution
        jobs = self.config.config.jobs if self.config.config.jobs > 0 else os.cpu_count() or 4
        msbuild_args = [
            self.msbuild_cmd,
            solution_file,
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
            f'/m:{jobs}',
        ]

        if self.config.config.verbose:
            msbuild_args.append('/v:minimal')

        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(solution_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """
        Link final executable/library using MSBuild.

        Args:
            linkfiles: List of files to link
            linkoptions: Linker options

        Returns:
            True if linking succeeded, False otherwise
        """
        # For MSBuild, linking is part of the build process
        # This method exists for interface compatibility
        print("[msbuild] Linking is handled during build process")
        return True

    def clean_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Clean package build artifacts using MSBuild.

        Args:
            package: Package to clean

        Returns:
            True if clean succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot clean.")
            return False

        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        # Determine configuration and platform
        build_type = config.build_type if config else BuildConfig().build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config or BuildConfig())

        # Clean command arguments
        msbuild_args = [
            self.msbuild_cmd,
            project_file,
            '/t:Clean',  # Clean target
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
        ]

        print(f"[msbuild] Cleaning {package.name} with command: {' '.join(msbuild_args)}")
        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(project_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"[msbuild] Clean succeeded for {package.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[msbuild] Clean failed for {package.name}: {e.stderr}")
            return False
        except Exception as e:
            print(f"[msbuild] Unexpected error cleaning {package.name}: {str(e)}")
            return False

    def get_target_ext(self) -> str:
        """
        Return target file extension based on platform.

        Returns:
            String with appropriate file extension
        """
        # On Windows, executables end with .exe, libraries with .dll or .lib
        # For simplicity, return .exe as the primary executable extension
        return ".exe"

    def install(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Install the built package by copying output files to destination.
        For MSBuild projects, this typically involves copying built binaries
        from the output directory to the configured install prefix.

        Args:
            package: Package to install

        Returns:
            True if install succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot install.")
            return False

        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project file found for {package.name}")
            return False

        # Determine configuration and platform for output path
        build_type = config.build_type if config else self.config.config.build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config)

        # Determine the output directory based on project type and config
        project_dir = Path(project_file).parent
        output_patterns = [
            project_dir / build_config,  # Classic MSBuild output format
            project_dir / f"{platform}/{build_config}",  # Platform-specific output
            project_dir / f"bin/{build_config}",  # Alternative bin structure
            project_dir / f"bin/{platform}/{build_config}"  # Full path structure
        ]

        # Find the output directory that exists
        output_dir = None
        for pattern in output_patterns:
            if pattern.exists():
                output_dir = pattern
                break

        if not output_dir:
            print(f"[msbuild] Output directory not found for {package.name}, attempting to build first...")
            # Try to run a build to generate the outputs
            if not self.build_package(package, config):
                print(f"[msbuild] Build failed, cannot proceed with install for {package.name}")
                return False
            # Re-check for output directory after build
            for pattern in output_patterns:
                if pattern.exists():
                    output_dir = pattern
                    break
            if not output_dir:
                print(f"[msbuild] Output directory still not found after build for {package.name}")
                return False

        # Destination directory
        install_prefix = config.install_prefix if config else self.config.config.install_prefix
        install_dir = Path(install_prefix) / package.name
        install_dir.mkdir(parents=True, exist_ok=True)

        # Copy built files to install location
        import shutil

        print(f"[msbuild] Installing {package.name} from {output_dir} to {install_dir}")

        # Copy all relevant output files (executables, DLLs, etc.)
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                # Only copy certain file types that are typically output files
                if file_path.suffix.lower() in ['.exe', '.dll', '.lib', '.pdb', '.ilk', '.exp']:
                    dest_path = install_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
                    print(f"[msbuild] Copied {file_path.name} to {dest_path}")

        print(f"[msbuild] Install completed for {package.name}")
        return True

    def rebuild_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Rebuild the package (clean + build).

        Args:
            package: Package to rebuild

        Returns:
            True if rebuild succeeded, False otherwise
        """
        print(f"[msbuild] Rebuilding {package.name}...")
        if not self.clean_package(package, config):
            print(f"[msbuild] Clean failed during rebuild for {package.name}")
            return False
        return self.build_package(package, config)
