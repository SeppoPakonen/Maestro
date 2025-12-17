"""
Cross-compilation support for Maestro.

Implements cross-compilation configuration and toolchain support for various platforms.
"""

import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import MethodConfig


@dataclass
class CrossCompilationConfig:
    """Configuration for cross-compilation."""
    enabled: bool = False
    target_arch: str = None  # Target architecture (e.g., arm, arm64, x86, x86_64)
    target_os: str = None    # Target OS (e.g., linux, windows, android, ios)
    sysroot_path: str = None  # Path to sysroot for target system
    toolchain_file: str = None  # CMake toolchain file
    cross_compiler_prefix: str = None  # Prefix for cross-compilers (e.g., arm-linux-gnueabihf-)
    strip_symbols: bool = True  # Whether to strip symbols in release builds
    extra_flags: List[str] = None  # Extra flags for cross-compilation

    def __post_init__(self):
        if self.extra_flags is None:
            self.extra_flags = []


class CrossCompilationHelper:
    """Helper class for cross-compilation setup."""
    
    @staticmethod
    def detect_cross_compilation_targets() -> List[Dict[str, str]]:
        """
        Detect available cross-compilation targets based on installed toolchains.
        
        Returns:
            List of available target configurations
        """
        targets = []
        
        # Detect available toolchains in standard locations
        toolchain_paths = [
            "/usr/bin",
            "/opt",
            "/opt/cross",
            os.path.expanduser("~/opt/cross"),
            os.environ.get("CROSS_COMPILE_PATH", ""),
        ]
        
        # Common cross-compiler prefixes
        prefixes = [
            "arm-linux-gnueabihf-",
            "aarch64-linux-gnu-",
            "x86_64-w64-mingw32-",
            "i686-w64-mingw32-",
            "arm-linux-androideabi-",
            "aarch64-linux-android-",
        ]
        
        for toolchain_path in toolchain_paths:
            if not os.path.exists(toolchain_path):
                continue
                
            for prefix in prefixes:
                # Check if gcc with this prefix exists
                gcc_path = os.path.join(toolchain_path, prefix + "gcc")
                if os.path.exists(gcc_path):
                    # Determine target from prefix
                    target_os = "linux"
                    target_arch = "arm"
                    
                    if "aarch64" in prefix:
                        target_arch = "arm64"
                    elif "x86_64" in prefix:
                        target_arch = "x86_64"
                    elif "i686" in prefix:
                        target_arch = "x86"
                    
                    if "mingw" in prefix:
                        target_os = "windows"
                    elif "android" in prefix:
                        target_os = "android"
                    
                    targets.append({
                        "prefix": prefix,
                        "target_arch": target_arch,
                        "target_os": target_os,
                        "path": toolchain_path
                    })
        
        return targets
    
    @staticmethod
    def get_c_compiler_for_target(target_os: str, target_arch: str, cross_prefix: str = None) -> Optional[str]:
        """Get the C compiler for a target."""
        if cross_prefix:
            return f"{cross_prefix}gcc"
        
        # Default cross-compilers for common targets
        compilers = {
            ("linux", "arm"): "arm-linux-gnueabihf-gcc",
            ("linux", "arm64"): "aarch64-linux-gnu-gcc",
            ("windows", "x86_64"): "x86_64-w64-mingw32-gcc",
            ("windows", "x86"): "i686-w64-mingw32-gcc",
            ("android", "arm"): "arm-linux-androideabi-gcc",
            ("android", "arm64"): "aarch64-linux-android-gcc",
        }
        
        return compilers.get((target_os, target_arch))
    
    @staticmethod
    def get_cpp_compiler_for_target(target_os: str, target_arch: str, cross_prefix: str = None) -> Optional[str]:
        """Get the C++ compiler for a target."""
        if cross_prefix:
            return f"{cross_prefix}g++"
        
        # Default cross-compilers for common targets
        compilers = {
            ("linux", "arm"): "arm-linux-gnueabihf-g++",
            ("linux", "arm64"): "aarch64-linux-gnu-g++",
            ("windows", "x86_64"): "x86_64-w64-mingw32-g++",
            ("windows", "x86"): "i686-w64-mingw32-g++",
            ("android", "arm"): "arm-linux-androideabi-g++",
            ("android", "arm64"): "aarch64-linux-android-g++",
        }
        
        return compilers.get((target_os, target_arch))
    
    @staticmethod
    def generate_cmake_toolchain_file(target_os: str, target_arch: str, sysroot: str = None, 
                                    output_path: str = None) -> Optional[str]:
        """
        Generate a CMake toolchain file for cross-compilation.
        
        Args:
            target_os: Target OS
            target_arch: Target architecture
            sysroot: Path to sysroot directory
            output_path: Where to save the toolchain file
            
        Returns:
            Path to generated toolchain file
        """
        # Common settings based on target
        settings = {
            "linux": {
                "cmake_system_name": "Linux",
                "cmake_system_processor": target_arch,
            },
            "windows": {
                "cmake_system_name": "Windows",
                "cmake_system_processor": target_arch,
            },
            "android": {
                "cmake_system_name": "Android",
                "android_native_api_level": "21",
            }
        }
        
        target_settings = settings.get(target_os, settings.get("linux", {}))
        
        toolchain_content = f"""# Generated CMake toolchain file for cross-compilation
# Target: {target_os} {target_arch}

set(CMAKE_SYSTEM_NAME {target_settings['cmake_system_name']})
"""
        if "cmake_system_processor" in target_settings:
            toolchain_content += f"set(CMAKE_SYSTEM_PROCESSOR {target_settings['cmake_system_processor']})\n"
        
        if sysroot:
            toolchain_content += f"set(CMAKE_SYSROOT \"{sysroot}\")\n"
        
        if target_os == "android":
            toolchain_content += f"set(ANDROID_NATIVE_API_LEVEL \"{target_settings.get('android_native_api_level', '21')}\")\n"
        
        # Set compilers based on target
        c_compiler = CrossCompilationHelper.get_c_compiler_for_target(target_os, target_arch)
        cpp_compiler = CrossCompilationHelper.get_cpp_compiler_for_target(target_os, target_arch)
        
        if c_compiler:
            toolchain_content += f"set(CMAKE_C_COMPILER \"{c_compiler}\")\n"
        if cpp_compiler:
            toolchain_content += f"set(CMAKE_CXX_COMPILER \"{cpp_compiler}\")\n"
        
        # Set common paths
        toolchain_content += """
# Search for programs only in the target environment
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
"""
        
        if output_path:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(toolchain_content)
            
            return output_path
        else:
            return toolchain_content
    
    @staticmethod
    def get_sysroot_path(target_os: str, target_arch: str, base_path: str = "/usr") -> Optional[str]:
        """
        Get the sysroot path for a target.
        
        Args:
            target_os: Target OS
            target_arch: Target architecture
            base_path: Base path for sysroot
            
        Returns:
            Path to sysroot directory
        """
        sysroot_patterns = {
            ("linux", "arm"): f"{base_path}/arm-linux-gnueabihf",
            ("linux", "arm64"): f"{base_path}/aarch64-linux-gnu",
            ("windows", "x86_64"): f"{base_path}/x86_64-w64-mingw32",
            ("windows", "x86"): f"{base_path}/i686-w64-mingw32",
        }
        
        return sysroot_patterns.get((target_os, target_arch))


def enhance_method_config_with_cross_compilation(config: MethodConfig, cross_config: CrossCompilationConfig) -> MethodConfig:
    """
    Enhance a MethodConfig with cross-compilation settings.
    
    Args:
        config: Original MethodConfig
        cross_config: Cross-compilation configuration
        
    Returns:
        Enhanced MethodConfig with cross-compilation settings
    """
    if not cross_config.enabled:
        return config
    
    # Add cross-compilation settings to the method configuration
    enhanced_config = config
    
    # Add target settings
    if cross_config.target_arch:
        enhanced_config.arch = cross_config.target_arch
    
    # Add sysroot if specified
    if cross_config.sysroot_path:
        if not hasattr(enhanced_config, 'sysroot'):
            enhanced_config.sysroot = cross_config.sysroot_path
        else:
            enhanced_config.sysroot = cross_config.sysroot_path
    
    # Add cross-compilation flags
    if cross_config.cross_compiler_prefix:
        # Add prefix to compiler paths
        if hasattr(enhanced_config, 'cc'):
            enhanced_config.cc = f"{cross_config.cross_compiler_prefix}{enhanced_config.cc}"
        if hasattr(enhanced_config, 'cxx'):
            enhanced_config.cxx = f"{cross_config.cross_compiler_prefix}{enhanced_config.cxx}"
    
    # Add extra flags
    if hasattr(enhanced_config, 'flags'):
        enhanced_config.flags.extend(cross_config.extra_flags)
    else:
        enhanced_config.flags = cross_config.extra_flags[:]
    
    if hasattr(enhanced_config, 'cxxflags'):
        enhanced_config.cxxflags.extend(cross_config.extra_flags)
    else:
        enhanced_config.cxxflags = cross_config.extra_flags[:]
    
    return enhanced_config


def create_cross_compile_method(base_method: str, target_os: str, target_arch: str) -> MethodConfig:
    """
    Create a cross-compilation method based on a base method.
    
    Args:
        base_method: Name of the base method (e.g., 'gcc', 'clang')
        target_os: Target OS
        target_arch: Target architecture
        
    Returns:
        New MethodConfig for cross-compilation
    """
    # This would create a new MethodConfig based on the base method
    # but with cross-compilation settings
    
    # For now, we'll create a minimal cross-compilation config
    cross_config = CrossCompilationConfig(
        enabled=True,
        target_arch=target_arch,
        target_os=target_os,
        cross_compiler_prefix=f"{target_arch.replace('64', '')}-{target_os}-" if target_os != "android" else None
    )
    
    # Create a basic method config with cross-compilation settings
    from .config import MethodConfig, BuildType, OSFamily
    
    method_name = f"{base_method}-{target_os}-{target_arch}"
    
    return MethodConfig(
        name=method_name,
        builder=base_method,
        build_type=BuildType.DEBUG,
        os_family=OSFamily.LINUX if target_os == "linux" else OSFamily.WINDOWS if target_os == "windows" else OSFamily.OTHER,
        flags=[],
        cxxflags=[],
        sysroot=cross_config.sysroot_path,
        toolchain_file=cross_config.toolchain_file
    )