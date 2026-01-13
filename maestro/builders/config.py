"""Unified build configuration system for all build systems."""

import os
import sys
import toml
import json
import platform
import copy
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from enum import Enum


def load_var_file(file_path: str) -> Dict[str, str]:
    """
    Load a .bm (build method) file similar to U++'s LoadVarFile function.

    Args:
        file_path: Path to the .bm file to load

    Returns:
        Dictionary containing key-value pairs from the file
    """
    variables = {}

    if not os.path.exists(file_path):
        return variables

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # Skip empty lines and comments

            # Look for assignment pattern: KEY = "value";
            if '=' in line and line.endswith(';'):
                # Split on the first '=' to handle values that might contain '='
                key, value_part = line.split('=', 1)
                key = key.strip()

                # Extract value between quotes
                value_part = value_part.strip()[:-1]  # Remove trailing semicolon
                value_part = value_part.strip()

                # Handle quoted values
                if value_part.startswith('"') and value_part.endswith('"'):
                    value = value_part[1:-1]  # Remove surrounding quotes
                else:
                    value = value_part  # Use as-is if not quoted

                variables[key] = value

    return variables


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
    method: str = ""
    build_type: BuildType = BuildType.DEBUG
    parallel: bool = True
    jobs: int = 0  # 0 means use CPU count
    clean_first: bool = False
    verbose: bool = False
    quiet: bool = False
    skip_tests: bool = False
    offline: bool = False
    profile: Optional[str] = None
    target_dir: str = ".maestro/build"
    install_prefix: str = ".maestro/install"
    flags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Accept string build_type values like "debug"/"release".
        if isinstance(self.build_type, str):
            normalized = self.build_type.strip().lower()
            if normalized == "debug":
                self.build_type = BuildType.DEBUG
            elif normalized == "release":
                self.build_type = BuildType.RELEASE


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
        
        # Create MSC debug method
        if 'msvc' in detected_tools:
            msc_debug_config = MethodConfig(
                name="msc-debug",
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
            self.save_method(msc_debug_config)
            created_methods.append("msc-debug")
            
            # Create MSC release method
            msc_release_config = MethodConfig(
                name="msc-release",
                builder="msvc",
                inherit="msc-debug",
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
            self.save_method(msc_release_config)
            created_methods.append("msc-release")
        
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
        
        # Create MSBuild methods
        if 'msbuild' in detected_tools:
            msbuild_debug_config = MethodConfig(
                name="msbuild-debug",
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
            self.save_method(msbuild_debug_config)
            created_methods.append("msbuild-debug")

            msbuild_release_config = MethodConfig(
                name="msbuild-release",
                builder="msbuild",
                config=BuildConfig(
                    build_type=BuildType.RELEASE,
                    parallel=True,
                    jobs=os.cpu_count() or 4
                ),
                platform=PlatformConfig(
                    os=OSFamily.WINDOWS,
                    arch="x64"
                )
            )
            self.save_method(msbuild_release_config)
            created_methods.append("msbuild-release")
        
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

    def detect_default_method(self) -> Optional[str]:
        """Detect the best default build method based on available tools."""
        available_methods = self.get_available_methods()
        
        # On Windows, prioritize MSVS*x64
        if platform.system() == "Windows":
             msvs_methods = [m for m in available_methods if m.startswith("MSVS") and m.endswith("x64")]
             if msvs_methods:
                 return sorted(msvs_methods, reverse=True)[0]

        detected_tools = self.detect_compilers()

        # Prioritize methods based on common preferences
        priority_order = [
            ("msvc", "msc-debug"),
            ("gcc", "gcc-debug"),
            ("clang", "clang-debug"),
            ("cmake", "cmake-default"),
            ("msbuild", "msbuild-debug"),
            ("maven", "maven-default")
        ]

        # Check for existing methods first
        for tool_key, method_name in priority_order:
            if tool_key in detected_tools and method_name in available_methods:
                return method_name
        if "msbuild" in detected_tools and "msbuild-default" in available_methods:
            return "msbuild-default"

        # If no pre-existing method found, try to create default methods
        if not available_methods:
            self.create_default_methods()
            available_methods = self.get_available_methods()

        # Try again with newly created methods
        for tool_key, method_name in priority_order:
            if tool_key in detected_tools and method_name in available_methods:
                return method_name
        if "msbuild" in detected_tools and "msbuild-default" in available_methods:
            return "msbuild-default"

        # If still no method found, return the first available method
        if available_methods:
            return available_methods[0]

        return None

    def load_method(self, name: str) -> Optional[MethodConfig]:
        """Load a method by name."""
        if not self._loaded:
            self.load_all_methods()

        if name in ("msbuild-debug", "msbuild-release") and "msbuild-default" in self._methods:
            self._ensure_msbuild_variants()

        if name == "msbuild-default":
            if "msbuild-debug" in self._methods:
                return self._resolve_inheritance(self._methods["msbuild-debug"])
            if "msbuild-release" in self._methods:
                return self._resolve_inheritance(self._methods["msbuild-release"])

        if name in self._methods:
            # Return resolved config with inheritance applied
            return self._resolve_inheritance(self._methods[name])

        # If method not found, try to load it from file
        method_file = self.methods_dir / f"{name}.toml"
        if method_file.exists():
            config = self._load_method_from_file(method_file)
            if config:
                return self._resolve_inheritance(config)

        # Try to load U++ .bm files if not found in standard locations
        config = self._load_upp_build_method(name)
        if config:
            return config

        return None

    def _load_upp_build_method(self, name: str) -> Optional[MethodConfig]:
        """Load U++ build method from .bm file."""
        # Check for U++ build method files in standard locations
        upp_config_dirs = [
            Path.home() / "upp",
            Path.home() / ".config" / "u++" / "theide",
            Path.home() / ".config" / "upp" / "theide",
            Path("/usr/local/share/upp/theide"),
            Path("/usr/share/upp/theide")
        ]

        for config_dir in upp_config_dirs:
            bm_file = config_dir / f"{name}.bm"
            if bm_file.exists():
                return self._parse_bm_file_to_method_config(bm_file, name)

        return None

    def _parse_bm_file_to_method_config(self, bm_file: Path, method_name: str) -> Optional[MethodConfig]:
        """Parse a .bm file to create a MethodConfig."""
        try:
            variables = load_var_file(str(bm_file))

            # Determine compiler paths from PATH variable in .bm file
            compiler_cc = ""
            compiler_cxx = ""

            # Get builder type and compiler from .bm file
            builder_type = variables.get("BUILDER", "").upper()
            compiler_name = variables.get("COMPILER", "").strip()
            
            if not compiler_name:
                if builder_type.startswith("MSC"):
                    compiler_name = "cl"
                elif builder_type.startswith("GCC"):
                    compiler_name = "g++"
                elif builder_type.startswith("CLANG"):
                    compiler_name = "clang++"
                elif platform.system() == "Windows" and ("msvc" in method_name.lower() or "msvs" in method_name.lower()):
                    compiler_name = "cl"
                else:
                    compiler_name = "clang++"

            # Parse PATH from .bm file to find actual compiler executable
            if "PATH" in variables:
                paths = variables["PATH"].split(';')
                for path_dir in paths:
                    path_dir = path_dir.strip()
                    if path_dir:
                        # On Windows, compilers might be cl.exe, clang++.exe, etc.
                        cxx_exe = compiler_name
                        if not cxx_exe.endswith('.exe') and platform.system() == "Windows":
                            cxx_exe += '.exe'
                        
                        try:
                            cxx_path = Path(path_dir) / cxx_exe
                            if cxx_path.exists() and os.access(cxx_path, os.X_OK):
                                compiler_cxx = str(cxx_path)
                                # For C compiler, if it's cl.exe, it's the same
                                if "cl" in compiler_name.lower():
                                    compiler_cc = compiler_cxx
                                else:
                                    cc_exe = compiler_name.replace("++", "").replace("g++", "gcc")
                                    if not cc_exe.endswith('.exe') and platform.system() == "Windows":
                                        cc_exe += '.exe'
                                    cc_path = Path(path_dir) / cc_exe
                                    if cc_path.exists():
                                        compiler_cc = str(cc_path)
                                break
                        except Exception:
                            continue
                        
                        # Special case for cl.exe if not explicitly found yet
                        if not compiler_cxx and platform.system() == "Windows":
                             cl_path = Path(path_dir) / "cl.exe"
                             if cl_path.exists():
                                 compiler_cxx = str(cl_path)
                                 compiler_cc = str(cl_path)
                                 break

            # Fallback: try to find compiler in system PATH
            if not compiler_cxx:
                compiler_cxx = self._find_executable(compiler_name)
            if not compiler_cc:
                compiler_cc = self._find_executable(compiler_name.replace("++", "").replace("g++", "gcc"))

            # Build flags based on .bm file content
            cxxflags = []
            cflags = []
            ldflags = []
            includes = []
            defines = []

            # Add common C++ options
            if "COMMON_CPP_OPTIONS" in variables:
                cxxflags.extend(variables["COMMON_CPP_OPTIONS"].split())

            # Add debug options if this is a debug method
            if "DEBUG" in method_name.upper() or "DEBUG" in variables:
                if "DEBUG_OPTIONS" in variables:
                    cxxflags.extend(variables["DEBUG_OPTIONS"].split())
                if "DEBUG_FLAGS" in variables:
                    cxxflags.extend(variables["DEBUG_FLAGS"].split())
                if "DEBUG_INFO" in variables:
                    debug_info = variables["DEBUG_INFO"]
                    if debug_info == "2":
                        cxxflags.extend(["-ggdb", "-g2"])
                    elif debug_info == "1":
                        cxxflags.append("-g")

                # Add debug defines
                defines.extend(["_DEBUG", "DEBUG"])

            # Add release options if this is a release method
            if "RELEASE" in method_name.upper() or "RELEASE" in variables:
                if "RELEASE_OPTIONS" in variables:
                    cxxflags.extend(variables["RELEASE_OPTIONS"].split())
                if "RELEASE_FLAGS" in variables:
                    cxxflags.extend(variables["RELEASE_FLAGS"].split())

            # Add common options
            if "COMMON_OPTIONS" in variables:
                cxxflags.extend(variables["COMMON_OPTIONS"].split())
                cflags.extend(variables["COMMON_OPTIONS"].split())

            # Add common flags
            if "COMMON_FLAGS" in variables:
                cxxflags.extend(variables["COMMON_FLAGS"].split())
                cflags.extend(variables["COMMON_FLAGS"].split())

            # Add includes from .bm file
            if "INCLUDE" in variables:
                include_paths = variables["INCLUDE"].split(';')
                for inc_path in include_paths:
                    inc_path = inc_path.strip()
                    if inc_path:
                        includes.append(inc_path)

            # Add library paths to linker flags
            if "LIB" in variables:
                lib_paths = variables["LIB"].split(';')
                for lib_path in lib_paths:
                    lib_path = lib_path.strip()
                    if lib_path:
                        if platform.system() == "Windows" and ("msvc" in method_name.lower() or "msvs" in method_name.lower()):
                            ldflags.append(f"/LIBPATH:{lib_path}")
                        else:
                            ldflags.extend(["-L" + lib_path])

            # Add common linker options
            if "COMMON_LINK" in variables:
                ldflags.extend(variables["COMMON_LINK"].split())

            # Add debug linker options
            if "DEBUG" in method_name.upper() and "DEBUG_LINK" in variables:
                ldflags.extend(variables["DEBUG_LINK"].split())

            # Add release linker options
            if "RELEASE" in method_name.upper() and "RELEASE_LINK" in variables:
                ldflags.extend(variables["RELEASE_LINK"].split())

            # Add defines based on BUILDER name
            if "BUILDER" in variables:
                builder_name = variables["BUILDER"]
                defines.append(f"flag{builder_name.upper()}")
            
            # Add the method name itself as a flag (e.g., flagMSC22X64)
            method_flag = f"flag{method_name.upper()}"
            if method_flag not in defines:
                defines.append(method_flag)

            # Add debug/release defines
            is_debug = "RELEASE" not in method_name.upper() and "RELEASE" not in variables
            if is_debug:
                defines.extend(["flagDEBUG", "flagDEBUG_FULL"])
            else:
                defines.append("flagRELEASE")

            # Add platform defines
            current_os = platform.system().lower()
            if current_os == "linux":
                defines.extend(["flagPOSIX", "flagLINUX"])
            elif current_os == "darwin":
                defines.extend(["flagPOSIX", "flagMACOS"])
            elif current_os == "windows":
                defines.extend(["flagWIN32", "flagMSC"])

            # Create MethodConfig from parsed data
            config = MethodConfig(
                name=method_name,
                builder="upp",  # Use U++ builder for .bm methods
                compiler=CompilerConfig(
                    cc=compiler_cc,
                    cxx=compiler_cxx,
                    cflags=cflags,
                    cxxflags=cxxflags,
                    ldflags=ldflags,
                    defines=defines,
                    includes=includes
                ),
                config=BuildConfig(
                    build_type=BuildType.DEBUG if is_debug else BuildType.RELEASE,
                    parallel=True,
                    jobs=os.cpu_count() or 4,
                    verbose=False
                ),
                platform=PlatformConfig(
                    os=OSFamily(current_os),
                    arch=platform.machine().lower()
                )
            )

            # Cache the config
            self._methods[method_name] = config
            return config

        except Exception as e:
            print(f"Error parsing .bm file {bm_file}: {e}", file=sys.stderr)
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
        self._ensure_msbuild_variants()
        self._loaded = True

    def _clone_method_with_build_type(self, base: MethodConfig, name: str, build_type: BuildType) -> MethodConfig:
        clone = copy.deepcopy(base)
        clone.name = name
        clone.config.build_type = build_type
        return clone

    def _ensure_msbuild_variants(self) -> None:
        if "msbuild-default" not in self._methods:
            return
        base = self._methods["msbuild-default"]
        if "msbuild-debug" not in self._methods:
            self._methods["msbuild-debug"] = self._clone_method_with_build_type(
                base, "msbuild-debug", BuildType.DEBUG
            )
        if "msbuild-release" not in self._methods:
            self._methods["msbuild-release"] = self._clone_method_with_build_type(
                base, "msbuild-release", BuildType.RELEASE
            )
    
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
        self._ensure_msbuild_variants()
        methods = list(self._methods.keys())
        if "msbuild-default" in methods and ("msbuild-debug" in methods or "msbuild-release" in methods):
            methods = [m for m in methods if m != "msbuild-default"]
        
        # Also add U++ build methods
        upp_config_dirs = [
            Path.home() / "upp",
            Path.home() / ".config" / "u++" / "theide",
            Path.home() / ".config" / "upp" / "theide",
            Path("/usr/local/share/upp/theide"),
            Path("/usr/share/upp/theide")
        ]

        for config_dir in upp_config_dirs:
            if config_dir.exists():
                for bm_file in config_dir.glob("*.bm"):
                    if bm_file.stem not in methods:
                        methods.append(bm_file.stem)
        
        return methods


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
