"""Unified build configuration system for all build systems."""

import os
import sys
import toml
import json
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from enum import Enum


class BuildType(str, Enum):
    DEBUG = "Debug"
    RELEASE = "Release"


class OSFamily(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


@dataclass
class CompilerConfig:
    """Compiler-specific configuration."""
    cc: str = ""
    cxx: str = ""
    cflags: List[str] = field(default_factory=list)
    cxxflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)


@dataclass
class BuildConfig:
    """Build execution configuration."""
    build_type: BuildType = BuildType.DEBUG
    parallel: bool = True
    jobs: int = 0  # 0 means use CPU count
    clean_first: bool = False
    verbose: bool = False
    skip_tests: bool = False
    offline: bool = False
    profile: Optional[str] = None


@dataclass
class PlatformConfig:
    """Platform-specific configuration."""
    os: OSFamily = OSFamily.LINUX
    arch: str = "x86_64"
    toolchain_file: Optional[str] = None
    sysroot: Optional[str] = None


@dataclass
class MethodConfig:
    """Top-level method configuration."""
    name: str
    builder: str  # Name of the builder class to use
    inherit: Optional[str] = None  # Name of parent method to inherit from
    
    compiler: CompilerConfig = field(default_factory=CompilerConfig)
    config: BuildConfig = field(default_factory=BuildConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    
    # Additional custom properties
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildMethod:
    """
    Lightweight wrapper used in early-phase tests.
    Stores raw config data and exposes a MethodConfig view.
    """
    name: str
    config_data: Dict[str, Any]

    def to_method_config(self) -> MethodConfig:
        """Convert to MethodConfig with best-effort defaults."""
        builder = self.config_data.get("builder", "unknown")
        return MethodConfig(name=self.name, builder=builder)


class MethodManager:
    """Manages build methods, including loading, saving, and auto-detection."""
    
    def __init__(self, methods_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the method manager.
        
        Args:
            methods_dir: Directory where methods are stored. If None, uses ~/.maestro/methods/
        """
        if methods_dir is None:
            self.methods_dir = Path.home() / '.maestro' / 'methods'
        else:
            self.methods_dir = Path(methods_dir)
        
        # Create methods directory if it doesn't exist
        self.methods_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to hold loaded methods
        self._methods: Dict[str, MethodConfig] = {}
        self._loaded = False
        
    def _get_default_methods_dir(self) -> Path:
        """Get the default directory for storing build methods."""
        return Path.home() / '.maestro' / 'methods'
    
    def detect_compilers(self) -> Dict[str, Dict[str, str]]:
        """Auto-detect available compilers and build tools on the system."""
        compilers = {}
        
        # Detect C/C++ compilers
        if platform.system() == "Windows":
            # Check for MSVC
            msvc_path = self._detect_msvc()
            if msvc_path:
                compilers['msvc'] = {
                    'cc': os.path.join(msvc_path, 'cl.exe'),
                    'cxx': os.path.join(msvc_path, 'cl.exe'),
                    'version': self._get_msvc_version(msvc_path)
                }
            
            # Check for MinGW or Clang
            if self._find_executable('gcc'):
                compilers['gcc'] = {
                    'cc': self._find_executable('gcc'),
                    'cxx': self._find_executable('g++'),
                    'version': self._get_compiler_version('gcc')
                }
            if self._find_executable('clang'):
                compilers['clang'] = {
                    'cc': self._find_executable('clang'),
                    'cxx': self._find_executable('clang++'),
                    'version': self._get_compiler_version('clang')
                }
        else:
            # Unix-like systems
            if self._find_executable('gcc'):
                compilers['gcc'] = {
                    'cc': self._find_executable('gcc'),
                    'cxx': self._find_executable('g++'),
                    'version': self._get_compiler_version('gcc')
                }
            if self._find_executable('clang'):
                compilers['clang'] = {
                    'cc': self._find_executable('clang'),
                    'cxx': self._find_executable('clang++'),
                    'version': self._get_compiler_version('clang')
                }
        
        # Detect build tools
        if self._find_executable('cmake'):
            compilers['cmake'] = {
                'path': self._find_executable('cmake'),
                'version': self._get_cmake_version()
            }
        
        if self._find_executable('make'):
            compilers['make'] = {
                'path': self._find_executable('make'),
                'version': self._get_make_version()
            }
        
        if platform.system() == "Windows":
            if self._find_executable('msbuild') or self._find_executable('dotnet'):
                compilers['msbuild'] = {
                    'path': self._find_executable('msbuild') or self._find_executable('dotnet'),
                    'version': self._get_msbuild_version()
                }
        
        if self._find_executable('mvn'):
            compilers['maven'] = {
                'path': self._find_executable('mvn'),
                'version': self._get_maven_version()
            }
        
        return compilers
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Find an executable in PATH."""
        for path in os.environ.get('PATH', '').split(os.pathsep):
            exe = Path(path) / name
            if platform.system() == "Windows":
                exe = exe.with_suffix('.exe')
            if exe.is_file() and os.access(exe, os.X_OK):
                return str(exe)
        return None
    
    def _get_compiler_version(self, compiler: str) -> str:
        """Get version of a compiler."""
        import subprocess
        try:
            result = subprocess.run([compiler, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Take the first line of output as version
                return result.stdout.split('\n')[0].strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_cmake_version(self) -> str:
        """Get version of cmake."""
        import subprocess
        try:
            result = subprocess.run(['cmake', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Take the first line of output as version
                return result.stdout.split('\n')[0].strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_make_version(self) -> str:
        """Get version of make."""
        import subprocess
        try:
            result = subprocess.run(['make', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Take the first line of output as version
                return result.stdout.split('\n')[0].strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_maven_version(self) -> str:
        """Get version of maven."""
        import subprocess
        try:
            result = subprocess.run(['mvn', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Look for version line
                for line in result.stderr.split('\n') + result.stdout.split('\n'):
                    if 'Apache Maven' in line:
                        return line.strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_msbuild_version(self) -> str:
        """Get version of MSBuild."""
        import subprocess
        try:
            # Try MSBuild.exe
            if self._find_executable('msbuild'):
                result = subprocess.run(['msbuild', '/version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout.split('\n')[0].strip()
            # Try dotnet msbuild
            elif self._find_executable('dotnet'):
                result = subprocess.run(['dotnet', 'msbuild', '/version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout.split('\n')[0].strip()
        except Exception:
            pass
        return "unknown"
    
    def _detect_msvc(self) -> Optional[str]:
        """Detect MSVC installation on Windows."""
        if platform.system() != "Windows":
            return None
            
        # Common installation paths for MSVC
        common_paths = [
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Professional\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Enterprise\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\VC\Tools\MSVC",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Enterprise\VC\Tools\MSVC",
        ]
        
        for path in common_paths:
            try:
                msvc_root = Path(path)
                if msvc_root.exists():
                    # Get the latest version folder
                    versions = [d.name for d in msvc_root.iterdir() if d.is_dir()]
                    if versions:
                        latest_version = max(versions)  # Pick the highest version number
                        compiler_path = msvc_root / latest_version / 'bin' / 'Hostx64' / 'x64'
                        if (compiler_path / 'cl.exe').exists():
                            return str(compiler_path / 'cl.exe').replace('cl.exe', '')
            except Exception:
                continue
        return None
    
    def _get_msvc_version(self, msvc_path: str) -> str:
        """Get version information for MSVC."""
        # For now, just return a generic version
        return "MSVC"
    
    def create_default_methods(self) -> List[str]:
        """Create default build methods based on detected tools."""
        detected_tools = self.detect_compilers()
        created_methods = []
        
        # Create GCC debug method
        if 'gcc' in detected_tools:
            gcc_debug_config = MethodConfig(
                name="gcc-debug",
                builder="gcc",
                compiler=CompilerConfig(
                    cc=detected_tools['gcc']['cc'],
                    cxx=detected_tools['gcc']['cxx'],
                    cflags=["-g", "-O0", "-Wall"],
                    cxxflags=["-g", "-O0", "-Wall", "-std=c++17"],
                    ldflags=["-g"]
                ),
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily(platform.system().lower()),
                    arch=platform.machine().lower()
                )
            )
            self.save_method(gcc_debug_config)
            created_methods.append("gcc-debug")
            
            # Create GCC release method
            gcc_release_config = MethodConfig(
                name="gcc-release",
                builder="gcc",
                inherit="gcc-debug",
                compiler=CompilerConfig(
                    cflags=["-O2", "-DNDEBUG"],
                    cxxflags=["-O2", "-DNDEBUG", "-std=c++17"],
                    ldflags=[]
                ),
                config=BuildConfig(
                    build_type=BuildType.RELEASE,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                )
            )
            self.save_method(gcc_release_config)
            created_methods.append("gcc-release")
        
        # Create Clang debug method
        if 'clang' in detected_tools:
            clang_debug_config = MethodConfig(
                name="clang-debug",
                builder="gcc",  # Use GCC builder with Clang
                compiler=CompilerConfig(
                    cc=detected_tools['clang']['cc'],
                    cxx=detected_tools['clang']['cxx'],
                    cflags=["-g", "-O0", "-Wall"],
                    cxxflags=["-g", "-O0", "-Wall", "-std=c++17"],
                    ldflags=["-g"]
                ),
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily(platform.system().lower()),
                    arch=platform.machine().lower()
                )
            )
            self.save_method(clang_debug_config)
            created_methods.append("clang-debug")
            
            # Create Clang release method
            clang_release_config = MethodConfig(
                name="clang-release",
                builder="gcc",
                inherit="clang-debug",
                compiler=CompilerConfig(
                    cflags=["-O2", "-DNDEBUG"],
                    cxxflags=["-O2", "-DNDEBUG", "-std=c++17"],
                    ldflags=[]
                ),
                config=BuildConfig(
                    build_type=BuildType.RELEASE,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                )
            )
            self.save_method(clang_release_config)
            created_methods.append("clang-release")
        
        # Create MSVC debug method
        if 'msvc' in detected_tools:
            msvc_debug_config = MethodConfig(
                name="msvc-debug",
                builder="msvc",
                compiler=CompilerConfig(
                    cc=detected_tools['msvc']['cc'],
                    cxx=detected_tools['msvc']['cc'],  # MSVC uses cl.exe for both
                    cflags=["/Zi", "/Od", "/MDd"],
                    cxxflags=["/Zi", "/Od", "/MDd"],
                    ldflags=["/DEBUG:FULL"]
                ),
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily.WINDOWS,
                    arch="x64"
                )
            )
            self.save_method(msvc_debug_config)
            created_methods.append("msvc-debug")
            
            # Create MSVC release method
            msvc_release_config = MethodConfig(
                name="msvc-release",
                builder="msvc",
                inherit="msvc-debug",
                compiler=CompilerConfig(
                    cflags=["/O2", "/Ob2", "/DNDEBUG", "/MD"],
                    cxxflags=["/O2", "/Ob2", "/DNDEBUG", "/MD"],
                    ldflags=[]
                ),
                config=BuildConfig(
                    build_type=BuildType.RELEASE,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                )
            )
            self.save_method(msvc_release_config)
            created_methods.append("msvc-release")
        
        # Create CMake method
        if 'cmake' in detected_tools:
            cmake_config = MethodConfig(
                name="cmake-default",
                builder="cmake",
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily(platform.system().lower()),
                    arch=platform.machine().lower()
                )
            )
            self.save_method(cmake_config)
            created_methods.append("cmake-default")
        
        # Create MSBuild method
        if 'msbuild' in detected_tools:
            msbuild_config = MethodConfig(
                name="msbuild-default",
                builder="msbuild",
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily.WINDOWS,
                    arch="x64"
                )
            )
            self.save_method(msbuild_config)
            created_methods.append("msbuild-default")
        
        # Create Maven method
        if 'maven' in detected_tools:
            maven_config = MethodConfig(
                name="maven-default",
                builder="maven",
                config=BuildConfig(
                    build_type=BuildType.DEBUG,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily(platform.system().lower()),
                    arch=platform.machine().lower()
                )
            )
            self.save_method(maven_config)
            created_methods.append("maven-default")
        
        return created_methods
    
    def load_method(self, name: str) -> Optional[MethodConfig]:
        """Load a method by name."""
        if not self._loaded:
            self.load_all_methods()

        if name in self._methods:
            # Return resolved config with inheritance applied
            return self._resolve_inheritance(self._methods[name])

        # If method not found, try to load it from file
        method_file = self.methods_dir / f"{name}.toml"
        if method_file.exists():
            config = self._load_method_from_file(method_file)
            if config:
                return self._resolve_inheritance(config)

        return None
    
    def _load_method_from_file(self, file_path: Path) -> Optional[MethodConfig]:
        """Load a method configuration from a TOML file."""
        try:
            with open(file_path, 'r') as f:
                data = toml.load(f)
            
            method_config = self._parse_method_config(data)
            self._methods[method_config.name] = method_config
            return method_config
        except Exception as e:
            print(f"Error loading method from {file_path}: {e}", file=sys.stderr)
            return None
    
    def _parse_method_config(self, data: dict) -> MethodConfig:
        """Parse method config data with inheritance support."""
        # Handle inheritance - prevent circular inheritance
        method_name = data.get('method', {}).get('name', 'unnamed')
        inherit_name = data.get('method', {}).get('inherit')

        # For now, create a basic config without inheritance resolution
        # to avoid recursion issues during loading
        config = MethodConfig(
            name=method_name,
            builder=data.get('method', {}).get('builder', 'gcc'),  # Default builder
            inherit=inherit_name,

            compiler=CompilerConfig(
                cc=data.get('compiler', {}).get('cc', ''),
                cxx=data.get('compiler', {}).get('cxx', ''),
                cflags=data.get('compiler', {}).get('cflags', []),
                cxxflags=data.get('compiler', {}).get('cxxflags', []),
                ldflags=data.get('compiler', {}).get('ldflags', []),
                defines=data.get('compiler', {}).get('defines', []),
                includes=data.get('compiler', {}).get('includes', [])
            ),

            config=BuildConfig(
                build_type=BuildType(data.get('config', {}).get('build_type', 'Debug')),
                parallel=data.get('config', {}).get('parallel', True),
                jobs=data.get('config', {}).get('jobs', os.cpu_count() or 4),
                clean_first=data.get('config', {}).get('clean_first', False),
                verbose=data.get('config', {}).get('verbose', False),
                skip_tests=data.get('config', {}).get('skip_tests', False),
                offline=data.get('config', {}).get('offline', False),
                profile=data.get('config', {}).get('profile', None)
            ),

            platform=PlatformConfig(
                os=OSFamily(data.get('platform', {}).get('os', platform.system().lower())),
                arch=data.get('platform', {}).get('arch', platform.machine().lower()),
                toolchain_file=data.get('platform', {}).get('toolchain_file', None),
                sysroot=data.get('platform', {}).get('sysroot', None)
            )
        )

        # Add custom properties
        config.custom = data.get('custom', {})

        return config

    def _resolve_inheritance(self, config: MethodConfig) -> MethodConfig:
        """Resolve inheritance chain for a method config."""
        visited = set()
        current = config
        resolved_config = config

        # Follow inheritance chain
        while current.inherit and current.inherit not in visited:
            visited.add(current.inherit)

            # Load parent config
            parent = self.load_method(current.inherit)
            if not parent:
                # If parent doesn't exist, stop inheritance resolution
                break

            # Create a new config with parent values as defaults
            resolved_config = MethodConfig(
                name=resolved_config.name,
                builder=resolved_config.builder or parent.builder,
                inherit=resolved_config.inherit,

                compiler=CompilerConfig(
                    cc=resolved_config.compiler.cc or parent.compiler.cc,
                    cxx=resolved_config.compiler.cxx or parent.compiler.cxx,
                    cflags=resolved_config.compiler.cflags if resolved_config.compiler.cflags else parent.compiler.cflags.copy(),
                    cxxflags=resolved_config.compiler.cxxflags if resolved_config.compiler.cxxflags else parent.compiler.cxxflags.copy(),
                    ldflags=resolved_config.compiler.ldflags if resolved_config.compiler.ldflags else parent.compiler.ldflags.copy(),
                    defines=resolved_config.compiler.defines if resolved_config.compiler.defines else parent.compiler.defines.copy(),
                    includes=resolved_config.compiler.includes if resolved_config.compiler.includes else parent.compiler.includes.copy()
                ),

                config=BuildConfig(
                    build_type=resolved_config.config.build_type if resolved_config.config.build_type != BuildType.DEBUG else parent.config.build_type,
                    parallel=resolved_config.config.parallel,
                    jobs=resolved_config.config.jobs,
                    clean_first=resolved_config.config.clean_first,
                    verbose=resolved_config.config.verbose,
                    skip_tests=resolved_config.config.skip_tests,
                    offline=resolved_config.config.offline,
                    profile=resolved_config.config.profile
                ),

                platform=PlatformConfig(
                    os=resolved_config.platform.os,
                    arch=resolved_config.platform.arch,
                    toolchain_file=resolved_config.platform.toolchain_file,
                    sysroot=resolved_config.platform.sysroot
                )
            )

            # For non-empty/override values, use the child's values
            # For cflags, cxxflags, ldflags, defines, includes - extend parent arrays
            if resolved_config.compiler.cflags == []:
                resolved_config.compiler.cflags = parent.compiler.cflags.copy()
            else:
                # If child has its own flags, we may want to extend/merge
                pass

            if resolved_config.compiler.cxxflags == []:
                resolved_config.compiler.cxxflags = parent.compiler.cxxflags.copy()
            else:
                # If child has its own flags, we may want to extend/merge
                pass

            if resolved_config.compiler.ldflags == []:
                resolved_config.compiler.ldflags = parent.compiler.ldflags.copy()
            else:
                # If child has its own flags, we may want to extend/merge
                pass

            if resolved_config.compiler.defines == []:
                resolved_config.compiler.defines = parent.compiler.defines.copy()
            else:
                # If child has its own defines, we may want to extend/merge
                pass

            if resolved_config.compiler.includes == []:
                resolved_config.compiler.includes = parent.compiler.includes.copy()
            else:
                # If child has its own includes, we may want to extend/merge
                pass

            # For other fields, use child if set, otherwise parent
            resolved_config.compiler.cc = resolved_config.compiler.cc or parent.compiler.cc
            resolved_config.compiler.cxx = resolved_config.compiler.cxx or parent.compiler.cxx
            resolved_config.builder = resolved_config.builder or parent.builder
            resolved_config.config.build_type = resolved_config.config.build_type if resolved_config.config.build_type != BuildType.DEBUG else parent.config.build_type
            resolved_config.platform.os = resolved_config.platform.os if resolved_config.platform.os != OSFamily.LINUX else parent.platform.os
            resolved_config.platform.arch = resolved_config.platform.arch or parent.platform.arch
            resolved_config.platform.toolchain_file = resolved_config.platform.toolchain_file or parent.platform.toolchain_file
            resolved_config.platform.sysroot = resolved_config.platform.sysroot or parent.platform.sysroot

            # Move to parent for next iteration
            current = parent

        return resolved_config
    
    def load_all_methods(self):
        """Load all method configurations from the methods directory."""
        if not self.methods_dir.exists():
            return
        
        for toml_file in self.methods_dir.glob("*.toml"):
            try:
                with open(toml_file, 'r') as f:
                    data = toml.load(f)
                
                method_name = data.get('method', {}).get('name', toml_file.stem)
                method_config = self._parse_method_config(data)
                self._methods[method_name] = method_config
            except Exception as e:
                print(f"Error loading method from {toml_file}: {e}", file=sys.stderr)
        
        self._loaded = True
    
    def save_method(self, config: MethodConfig):
        """Save a method configuration to a TOML file."""
        method_file = self.methods_dir / f"{config.name}.toml"
        
        data = {
            'method': {
                'name': config.name,
                'builder': config.builder
            },
            'compiler': {
                'cc': config.compiler.cc,
                'cxx': config.compiler.cxx,
                'cflags': config.compiler.cflags,
                'cxxflags': config.compiler.cxxflags,
                'ldflags': config.compiler.ldflags,
                'defines': config.compiler.defines,
                'includes': config.compiler.includes
            },
            'config': {
                'build_type': config.config.build_type.value,
                'parallel': config.config.parallel,
                'jobs': config.config.jobs,
                'clean_first': config.config.clean_first,
                'verbose': config.config.verbose,
                'skip_tests': config.config.skip_tests,
                'offline': config.config.offline,
                'profile': config.config.profile
            },
            'platform': {
                'os': config.platform.os.value,
                'arch': config.platform.arch,
                'toolchain_file': config.platform.toolchain_file,
                'sysroot': config.platform.sysroot
            }
        }
        
        if config.inherit:
            data['method']['inherit'] = config.inherit
        
        if config.custom:
            data['custom'] = config.custom
        
        with open(method_file, 'w') as f:
            toml.dump(data, f)
        
        # Update internal cache
        self._methods[config.name] = config
    
    def get_available_methods(self) -> List[str]:
        """Get list of available method names."""
        if not self._loaded:
            self.load_all_methods()
        return list(self._methods.keys())


# Global method manager instance
_method_manager = None


def get_global_method_manager(methods_dir: Optional[Union[str, Path]] = None) -> MethodManager:
    """Get the global method manager instance."""
    global _method_manager
    if _method_manager is None:
        _method_manager = MethodManager(methods_dir)
    return _method_manager


def get_method(name: str) -> Optional[MethodConfig]:
    """Get a method by name using the global method manager."""
    manager = get_global_method_manager()
    return manager.load_method(name)


def list_methods() -> List[str]:
    """List all available methods."""
    manager = get_global_method_manager()
    return manager.get_available_methods()


def create_default_methods() -> List[str]:
    """Create default build methods based on detected tools."""
    manager = get_global_method_manager()
    return manager.create_default_methods()


def detect_and_create_methods() -> List[str]:
    """Detect available tools and create corresponding default methods."""
    manager = get_global_method_manager()
    return manager.create_default_methods()


class PackageMethodManager:
    """Manages per-package method overrides."""

    def __init__(self, packages_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the package method manager.

        Args:
            packages_dir: Directory where per-package configs are stored (default: ~/.maestro/packages/)
        """
        if packages_dir is None:
            self.packages_dir = Path.home() / '.maestro' / 'packages'
        else:
            self.packages_dir = Path(packages_dir)

        # Create packages directory if it doesn't exist
        self.packages_dir.mkdir(parents=True, exist_ok=True)

    def get_package_config(self, package_name: str) -> Optional[MethodConfig]:
        """Get per-package configuration override.

        Args:
            package_name: Name of the package

        Returns:
            MethodConfig if override exists, None otherwise
        """
        config_file = self.packages_dir / package_name / 'method.toml'
        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r') as f:
                data = toml.load(f)

            # Parse as MethodConfig
            config = self._parse_method_config(data)
            config.name = f"{package_name}-override"
            return config
        except Exception as e:
            print(f"Error loading package config from {config_file}: {e}", file=sys.stderr)
            return None

    def set_package_config(self, package_name: str, config: MethodConfig):
        """Set per-package configuration override.

        Args:
            package_name: Name of the package
            config: MethodConfig to save
        """
        package_dir = self.packages_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)

        config_file = package_dir / 'method.toml'
        self._save_method_config(config, config_file)

    def _parse_method_config(self, data: dict) -> MethodConfig:
        """Parse method config data for package overrides."""
        # For package overrides, we don't support inheritance at this level
        # Package overrides are meant to be applied on top of a base method
        config = MethodConfig(
            name=data.get('method', {}).get('name', 'default'),
            builder=data.get('method', {}).get('builder', 'gcc'),  # Default builder

            compiler=CompilerConfig(
                cc=data.get('compiler', {}).get('cc', ''),
                cxx=data.get('compiler', {}).get('cxx', ''),
                cflags=data.get('compiler', {}).get('cflags', []),
                cxxflags=data.get('compiler', {}).get('cxxflags', []),
                ldflags=data.get('compiler', {}).get('ldflags', []),
                defines=data.get('compiler', {}).get('defines', []),
                includes=data.get('compiler', {}).get('includes', [])
            ),

            config=BuildConfig(
                build_type=BuildType(data.get('config', {}).get('build_type', 'Debug')),
                parallel=data.get('config', {}).get('parallel', True),
                jobs=data.get('config', {}).get('jobs', os.cpu_count() or 4),
                clean_first=data.get('config', {}).get('clean_first', False),
                verbose=data.get('config', {}).get('verbose', False),
                skip_tests=data.get('config', {}).get('skip_tests', False),
                offline=data.get('config', {}).get('offline', False),
                profile=data.get('config', {}).get('profile', None)
            ),

            platform=PlatformConfig(
                os=OSFamily(data.get('platform', {}).get('os', platform.system().lower())),
                arch=data.get('platform', {}).get('arch', platform.machine().lower()),
                toolchain_file=data.get('platform', {}).get('toolchain_file', None),
                sysroot=data.get('platform', {}).get('sysroot', None)
            )
        )

        # Add custom properties
        config.custom = data.get('custom', {})

        return config

    def _save_method_config(self, config: MethodConfig, config_file: Path):
        """Save method config to file."""
        data = {
            'method': {
                'name': config.name,
                'builder': config.builder
            },
            'compiler': {
                'cc': config.compiler.cc,
                'cxx': config.compiler.cxx,
                'cflags': config.compiler.cflags,
                'cxxflags': config.compiler.cxxflags,
                'ldflags': config.compiler.ldflags,
                'defines': config.compiler.defines,
                'includes': config.compiler.includes
            },
            'config': {
                'build_type': config.config.build_type.value,
                'parallel': config.config.parallel,
                'jobs': config.config.jobs,
                'clean_first': config.config.clean_first,
                'verbose': config.config.verbose,
                'skip_tests': config.config.skip_tests,
                'offline': config.config.offline,
                'profile': config.config.profile
            },
            'platform': {
                'os': config.platform.os.value,
                'arch': config.platform.arch,
                'toolchain_file': config.platform.toolchain_file,
                'sysroot': config.platform.sysroot
            }
        }

        if config.custom:
            data['custom'] = config.custom

        with open(config_file, 'w') as f:
            toml.dump(data, f)


# Global package method manager instance
_package_method_manager = None


def get_global_package_method_manager(packages_dir: Optional[Union[str, Path]] = None) -> PackageMethodManager:
    """Get the global package method manager instance."""
    global _package_method_manager
    if _package_method_manager is None:
        _package_method_manager = PackageMethodManager(packages_dir)
    return _package_method_manager


def get_package_method_override(package_name: str) -> Optional[MethodConfig]:
    """Get per-package method override."""
    manager = get_global_package_method_manager()
    return manager.get_package_config(package_name)


def set_package_method_override(package_name: str, config: MethodConfig):
    """Set per-package method override."""
    manager = get_global_package_method_manager()
    manager.set_package_config(package_name, config)
