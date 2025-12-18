"""
Build configuration discovery system.

Implements Phase 12.4: Phase 6.5 - Build Configuration Discovery
- Implements build configuration extraction for CMake, Autotools, Gradle/Maven, and U++
- Supports 'maestro repo conf [PACKAGE_ID]' command
- Caches configs in .maestro/repo/configs/<package>.json
"""

import os
import re
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..repo.package import PackageInfo


@dataclass
class BuildConfiguration:
    """Represents build configuration for a package."""
    compiler: str = ""                    # Compiler (gcc, clang, cl.exe, etc.)
    cflags: List[str] = field(default_factory=list)      # C compilation flags
    cxxflags: List[str] = field(default_factory=list)    # C++ compilation flags
    ldflags: List[str] = field(default_factory=list)     # Linker flags
    includes: List[str] = field(default_factory=list)    # Include directories
    defines: List[str] = field(default_factory=list)     # Preprocessor defines
    dependencies: List[str] = field(default_factory=list)  # Dependencies
    build_type: str = ""                  # Debug, Release, etc.
    build_system: str = ""                # cmake, autotools, gradle, maven, upp
    source_dirs: List[str] = field(default_factory=list)   # Source directories
    build_dir: str = ""                   # Build output directory
    custom_properties: Dict[str, Any] = field(default_factory=dict)  # Other build properties

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for compatibility with existing system."""
        return {
            'compiler': self.compiler,
            'cflags': self.cflags,
            'cxxflags': self.cxxflags,
            'ldflags': self.ldflags,
            'includes': self.includes,
            'defines': self.defines,
            'dependencies': self.dependencies,
            'build_type': self.build_type,
            'build_system': self.build_system,
            'source_dirs': self.source_dirs,
            'build_dir': self.build_dir,
            'custom_properties': self.custom_properties
        }


class ConfigDiscoverer(ABC):
    """Abstract base class for build configuration discovery."""

    @abstractmethod
    def can_discover(self, package: PackageInfo) -> bool:
        """Check if this discoverer can handle the given package."""
        pass

    @abstractmethod
    def discover_config(self, package: PackageInfo) -> Optional[BuildConfiguration]:
        """Discover build configuration for the given package."""
        pass


class CMakeConfigDiscoverer(ConfigDiscoverer):
    """Discover C++ build configuration from CMake projects."""

    def can_discover(self, package: PackageInfo) -> bool:
        """Check if this is a CMake project."""
        cmake_files = ["CMakeLists.txt", "cmake", "CMakeCache.txt"]
        package_path = Path(package.dir)
        
        for cmake_file in cmake_files:
            if (package_path / cmake_file).exists():
                return True
        return False

    def discover_config(self, package: PackageInfo) -> Optional[BuildConfiguration]:
        """Discover CMake build configuration."""
        package_path = Path(package.dir)
        
        # Look for CMakeLists.txt
        cmake_lists = package_path / "CMakeLists.txt"
        if not cmake_lists.exists():
            return None

        # Extract information from CMakeLists.txt
        config = BuildConfiguration()
        config.build_system = "cmake"
        
        try:
            with open(cmake_lists, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract common CMake variables and settings
            # Look for compiler settings
            if "CMAKE_C_COMPILER" in content:
                # Parse from CMakeCache.txt if available
                cache_file = package_path / "CMakeCache.txt"
                if cache_file.exists():
                    with open(cache_file, 'r', encoding='utf-8') as cf:
                        cache_content = cf.read()
                        compiler_match = re.search(r'CMAKE_CXX_COMPILER:FILEPATH=(.+)', cache_content)
                        if compiler_match:
                            config.compiler = compiler_match.group(1).strip()

            # Look for include directories
            include_matches = re.findall(r'include_directories\s*\(\s*([^\)]+)\s*\)', content, re.IGNORECASE)
            for match in include_matches:
                # Basic parsing - would need more sophisticated parsing for complex cases
                paths = [p.strip().strip('"') for p in match.split()]
                for path in paths:
                    if path.startswith('${') or path.startswith('$ENV{'):  # Handle variables
                        continue  # Skip variable-based paths for now
                    if not Path(path).is_absolute():
                        path = str(package_path / path)
                    config.includes.append(path)

            # Look for compile definitions
            def_matches = re.findall(r'add_definitions\s*\(\s*([^\)]+)\s*\)', content, re.IGNORECASE)
            for match in def_matches:
                # Basic parsing - would need more sophisticated parsing for complex cases
                definitions = [d.strip().strip('-D').strip('"') for d in match.split() if d.strip().startswith('-D')]
                config.defines.extend(definitions)

            # Look for target compile features and options (CMake 3.1+)
            target_compile_defines = re.findall(r'target_compile_definitions\s*\([^)]+\s+([^\)]+)\s*\)', content, re.IGNORECASE)
            for match in target_compile_defines:
                # Extract definitions from target_compile_definitions
                parts = match.split()
                for part in parts:
                    if part.startswith('PRIVATE') or part.startswith('PUBLIC') or part.startswith('INTERFACE'):
                        continue
                    if part.startswith('-D'):
                        config.defines.append(part[2:].strip())
                    else:
                        config.defines.append(part.strip())

            # Check for build type
            if "CMAKE_BUILD_TYPE:STRING=Debug" in content:
                config.build_type = "Debug"
            elif "CMAKE_BUILD_TYPE:STRING=Release" in content:
                config.build_type = "Release"

            # Add source directories based on common CMake patterns
            if "src" in os.listdir(package_path) and os.path.isdir(package_path / "src"):
                config.source_dirs.append(str(package_path / "src"))
            else:
                config.source_dirs.append(str(package_path))

        except Exception as e:
            print(f"Warning: Could not parse CMakeLists.txt: {e}")

        return config


class AutotoolsConfigDiscoverer(ConfigDiscoverer):
    """Discover build configuration from Autotools projects."""

    def can_discover(self, package: PackageInfo) -> bool:
        """Check if this is an Autotools project."""
        autotools_files = ["configure.ac", "configure.in", "Makefile.am", "Makefile.in", "configure", "Makefile"]
        package_path = Path(package.dir)
        
        for tool_file in autotools_files:
            if (package_path / tool_file).exists():
                return True
        return False

    def discover_config(self, package: PackageInfo) -> Optional[BuildConfiguration]:
        """Discover Autotools build configuration."""
        package_path = Path(package.dir)
        config = BuildConfiguration()
        config.build_system = "autotools"

        # Look for the configure script or configure.ac
        configure_script = package_path / "configure"
        configure_ac = package_path / "configure.ac"
        makefile_am = package_path / "Makefile.am"
        
        # Extract info from configure.ac if available
        if configure_ac.exists():
            try:
                with open(configure_ac, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for CFLAGS, CXXFLAGS, etc. in the configure.ac
                # Autotools doesn't typically store compilation flags in configure.ac directly
                # They're usually in Makefile.am or passed to configure at runtime
                pass
            except Exception:
                pass

        # Extract information from Makefile.am if available
        if makefile_am.exists():
            try:
                with open(makefile_am, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for AM_CFLAGS, AM_CXXFLAGS, etc.
                cflags_match = re.search(r'AM_CFLAGS\s*=\s*([^\n]+)', content)
                if cflags_match:
                    flags = cflags_match.group(1).strip()
                    config.cflags.extend(flags.split())

                cxxflags_match = re.search(r'AM_CXXFLAGS\s*=\s*([^\n]+)', content)
                if cxxflags_match:
                    flags = cxxflags_match.group(1).strip()
                    config.cxxflags.extend(flags.split())

                # Look for include paths
                includes_match = re.search(r'AM_CPPFLAGS\s*=\s*([^\n]+)', content)
                if includes_match:
                    flags = includes_match.group(1).strip()
                    for flag in flags.split():
                        if flag.startswith('-I'):
                            config.includes.append(flag[2:].strip())

            except Exception:
                pass

        # If there's a generated Makefile, try to extract from that
        makefile = package_path / "Makefile"
        if makefile.exists():
            try:
                with open(makefile, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for variable definitions
                cflags_match = re.search(r'^CFLAGS\s*[:+]?=\s*([^\n]+)', content, re.MULTILINE)
                if cflags_match:
                    flags = cflags_match.group(1).strip()
                    config.cflags.extend(flags.split())

                cxxflags_match = re.search(r'^CXXFLAGS\s*[:+]?=\s*([^\n]+)', content, re.MULTILINE)
                if cxxflags_match:
                    flags = cxxflags_match.group(1).strip()
                    config.cxxflags.extend(flags.split())

                cppflags_match = re.search(r'^CPPFLAGS\s*[:+]?=\s*([^\n]+)', content, re.MULTILINE)
                if cppflags_match:
                    flags = cppflags_match.group(1).strip()
                    for flag in flags.split():
                        if flag.startswith('-I'):
                            config.includes.append(flag[2:].strip())
                        elif flag.startswith('-D'):
                            config.defines.append(flag[2:].strip())

            except Exception:
                pass

        # Add source directories
        if "src" in os.listdir(package_path) and os.path.isdir(package_path / "src"):
            config.source_dirs.append(str(package_path / "src"))
        else:
            config.source_dirs.append(str(package_path))

        return config


class GradleMavenConfigDiscoverer(ConfigDiscoverer):
    """Discover build configuration from Gradle and Maven projects."""

    def can_discover(self, package: PackageInfo) -> bool:
        """Check if this is a Gradle or Maven project."""
        package_path = Path(package.dir)
        
        # Check for Gradle files
        gradle_files = ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew", "gradle.properties"]
        for gradle_file in gradle_files:
            if (package_path / gradle_file).exists():
                return True
                
        # Check for Maven files
        maven_files = ["pom.xml", "build.xml"]
        for maven_file in maven_files:
            if (package_path / maven_file).exists():
                return True

        return False

    def discover_config(self, package: PackageInfo) -> Optional[BuildConfiguration]:
        """Discover Gradle/Maven build configuration."""
        package_path = Path(package.dir)
        config = BuildConfiguration()
        
        # Check for Gradle
        build_gradle = package_path / "build.gradle"
        build_gradle_kts = package_path / "build.gradle.kts"
        
        if build_gradle.exists() or build_gradle_kts.exists():
            config.build_system = "gradle"
            gradle_file = build_gradle if build_gradle.exists() else build_gradle_kts
            
            try:
                with open(gradle_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                # Look for Java/Kotlin version settings
                java_version_match = re.search(r'java\.version\s*[:=]\s*[\'"]?(\d+)[\'"]?', content)
                if java_version_match:
                    java_version = java_version_match.group(1)
                    config.defines.append(f"JAVA_VERSION={java_version}")

                # Look for source compatibility
                source_compat_match = re.search(r'sourcecompatibility\s*[:=]\s*[\'"]?(\d+)[\'"]?', content)
                if source_compat_match:
                    source_version = source_compat_match.group(1)
                    config.defines.append(f"SOURCE_COMPATIBILITY={source_version}")

                # Look for target compatibility
                target_compat_match = re.search(r'targetcompatibility\s*[:=]\s*[\'"]?(\d+)[\'"]?', content)
                if target_compat_match:
                    target_version = target_compat_match.group(1)
                    config.defines.append(f"TARGET_COMPATIBILITY={target_version}")

                # Look for compile options (Java compiler flags)
                compile_options_match = re.search(r'compileoptions\s*{([^}]*)}', content, re.DOTALL)
                if compile_options_match:
                    compile_options = compile_options_match.group(1)
                    if 'debug' in compile_options or 'debuggable' in compile_options:
                        config.build_type = "Debug"
                    elif 'release' in compile_options or 'minifyenabled' in compile_options:
                        config.build_type = "Release"

                # Add source directories (common for Gradle projects)
                if "src" in os.listdir(package_path) and os.path.isdir(package_path / "src"):
                    config.source_dirs.append(str(package_path / "src"))

            except Exception:
                pass

        # Check for Maven
        elif (package_path / "pom.xml").exists():
            config.build_system = "maven"
            pom_file = package_path / "pom.xml"
            
            try:
                with open(pom_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for Java version in Maven pom.xml
                java_version_match = re.search(r'<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>', content)
                if java_version_match:
                    java_version = java_version_match.group(1)
                    config.defines.append(f"JAVA_VERSION={java_version}")

                java_target_match = re.search(r'<maven\.compiler\.target>([^<]+)</maven\.compiler\.target>', content)
                if java_target_match:
                    java_target = java_target_match.group(1)
                    config.defines.append(f"JAVA_TARGET={java_target}")

                # Check packaging type
                packaging_match = re.search(r'<packaging>([^<]+)</packaging>', content)
                if packaging_match:
                    packaging = packaging_match.group(1)
                    config.custom_properties['packaging'] = packaging

                # Add source directories (common for Maven projects)
                if "src" in os.listdir(package_path) and os.path.isdir(package_path / "src"):
                    config.source_dirs.append(str(package_path / "src"))

            except Exception:
                pass

        return config


class UppConfigDiscoverer(ConfigDiscoverer):
    """Discover build configuration from U++ packages."""

    def can_discover(self, package: PackageInfo) -> bool:
        """Check if this is a U++ package."""
        if package.build_system == 'upp':
            return True
        
        # Also check if the package dir contains .upp files
        package_path = Path(package.dir)
        for file in os.listdir(package_path):
            if file.endswith('.upp'):
                return True
                
        return False

    def discover_config(self, package: PackageInfo) -> Optional[BuildConfiguration]:
        """Discover U++ build configuration."""
        config = BuildConfiguration()
        config.build_system = "upp"
        
        # Use the parsed .upp metadata from the PackageInfo
        if package.upp:
            # Extract uses (dependencies and include paths)
            uses_list = package.upp.get('uses', [])
            config.dependencies.extend(uses_list)
            
            # For U++ packages, the includes are usually the package directories
            for use in uses_list:
                # In U++, packages are typically found based on package name
                # This would need to be resolved based on the workspace
                pass

            # Extract flags if present
            flags = package.upp.get('flags', [])
            config.cxxflags.extend(flags)

            # Extract files
            files = package.upp.get('files', [])
            for file_obj in files:
                if isinstance(file_obj, dict):
                    filename = file_obj.get('file', '')
                    if filename:
                        config.source_dirs.append(os.path.dirname(os.path.join(package.dir, filename)))
                else:
                    config.source_dirs.append(os.path.dirname(os.path.join(package.dir, file_obj)))

        # Add the package directory as a source directory
        config.source_dirs.append(package.dir)

        # Default U++ compiler settings (would be resolved based on method)
        config.compiler = "g++"  # Default for U++
        config.cxxflags.extend(["-std=c++17", "-pthread"])

        return config


# Global discoverer registry
DISCOVERERS = [
    CMakeConfigDiscoverer(),
    AutotoolsConfigDiscoverer(),
    GradleMavenConfigDiscoverer(),
    UppConfigDiscoverer(),
]


def discover_build_config(package: PackageInfo) -> Optional[BuildConfiguration]:
    """Discover build configuration for a package using appropriate discoverer."""
    for discoverer in DISCOVERERS:
        if discoverer.can_discover(package):
            return discoverer.discover_config(package)
    
    return None


def get_package_config_cache_path(package_name: str) -> Path:
    """Get the cache file path for a package's build configuration."""
    cache_dir = Path.home() / '.maestro' / 'repo' / 'configs'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{package_name}.json"


def load_cached_config(package_name: str) -> Optional[BuildConfiguration]:
    """Load cached build configuration for a package."""
    cache_file = get_package_config_cache_path(package_name)
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Convert dict back to BuildConfiguration
            return BuildConfiguration(**data)
        except Exception:
            pass
    return None


def cache_config(package_name: str, config: BuildConfiguration):
    """Cache build configuration for a package."""
    cache_file = get_package_config_cache_path(package_name)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            # Convert BuildConfiguration to dict for JSON serialization
            config_dict = {
                'compiler': config.compiler,
                'cflags': config.cflags,
                'cxxflags': config.cxxflags,
                'ldflags': config.ldflags,
                'includes': config.includes,
                'defines': config.defines,
                'dependencies': config.dependencies,
                'build_type': config.build_type,
                'build_system': config.build_system,
                'source_dirs': config.source_dirs,
                'build_dir': config.build_dir,
                'custom_properties': config.custom_properties
            }
            json.dump(config_dict, f, indent=2)
    except Exception:
        pass  # Fail silently on cache errors