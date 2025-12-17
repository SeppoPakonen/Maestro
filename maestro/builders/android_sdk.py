"""
Android SDK detection and management for Maestro.

Implements Android SDK location detection, validation, and tool management.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class AndroidSDKConfig:
    """Configuration for Android SDK."""
    sdk_path: Optional[str] = None  # Path to Android SDK
    platform_version: str = "android-30"  # Target platform
    build_tools_version: Optional[str] = None  # Specific build tools version
    min_sdk_version: str = "21"  # Minimum SDK version
    target_sdk_version: str = "30"  # Target SDK version
    auto_detect: bool = True  # Whether to auto-detect SDK


class AndroidSDK:
    """Manages Android SDK detection and validation."""
    
    def __init__(self, config: AndroidSDKConfig = None):
        self.config = config or AndroidSDKConfig()
        self.sdk_path = self.config.sdk_path
        self.platform_version = self.config.platform_version
        self.build_tools_version = self.config.build_tools_version
        self.tools = {}
        
        if self.config.auto_detect and not self.sdk_path:
            self.sdk_path = self.auto_detect_sdk()
    
    @staticmethod
    def auto_detect_sdk() -> Optional[str]:
        """
        Auto-detect Android SDK location from common environment variables and paths.
        
        Returns:
            Path to Android SDK, or None if not found
        """
        # Check ANDROID_HOME environment variable
        android_home = os.environ.get('ANDROID_HOME')
        if android_home and os.path.exists(android_home):
            return android_home
            
        # Check ANDROID_SDK_ROOT environment variable
        android_sdk_root = os.environ.get('ANDROID_SDK_ROOT')
        if android_sdk_root and os.path.exists(android_sdk_root):
            return android_sdk_root
            
        # Check common paths
        common_paths = [
            # Linux
            os.path.expanduser("~/Android/Sdk"),
            os.path.expanduser("~/.local/share/android-sdk"),
            "/opt/android-sdk",
            # macOS
            os.path.expanduser("~/Library/Android/sdk"),
            os.path.expanduser("/usr/local/share/android-sdk"),
            # Windows
            os.path.expanduser("~/AppData/Local/Android/Sdk"),
            "C:/Android/Sdk",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def is_valid(self) -> bool:
        """
        Validates if the Android SDK installation is valid.
        
        Returns:
            True if SDK is valid, False otherwise
        """
        if not self.sdk_path or not os.path.exists(self.sdk_path):
            return False
            
        # Check for required directories
        required_dirs = [
            os.path.join(self.sdk_path, "platforms"),
            os.path.join(self.sdk_path, "build-tools"),
            os.path.join(self.sdk_path, "tools"),
            os.path.join(self.sdk_path, "platform-tools")
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                return False
        
        # Check for key tools
        required_tools = [
            ("adb", "platform-tools"),
            ("aapt", "build-tools"),
            ("zipalign", "build-tools"),
            ("apksigner", "build-tools")  # May be in build-tools or tools/bin
        ]
        
        for tool_name, tool_dir in required_tools:
            tool_path = self.find_tool(tool_name)
            if not tool_path:
                return False
        
        # Validate platform
        platform_path = os.path.join(self.sdk_path, "platforms", self.platform_version)
        if not os.path.exists(platform_path):
            # Try to find a matching platform
            available_platforms = self.list_available_platforms()
            if not available_platforms:
                return False
            # Use the latest available platform
            self.platform_version = available_platforms[-1]
        
        # Validate build tools
        build_tools_path = self.get_build_tools_path()
        if not build_tools_path:
            return False
            
        return True
    
    def find_tool(self, tool_name: str) -> Optional[str]:
        """
        Find an Android SDK tool by name.
        
        Args:
            tool_name: Name of the tool to find
            
        Returns:
            Path to the tool, or None if not found
        """
        # Different platforms have different tool extensions
        if platform.system() == "Windows":
            tool_name += ".exe"
            
        # Search in common SDK directories
        search_paths = [
            os.path.join(self.sdk_path, "platform-tools"),
            os.path.join(self.sdk_path, "tools"),
            os.path.join(self.sdk_path, "tools", "bin"),
        ]
        
        # Check build-tools directory (which may have version subdirectories)
        build_tools_dir = os.path.join(self.sdk_path, "build-tools")
        if os.path.exists(build_tools_dir):
            for build_version in os.listdir(build_tools_dir):
                build_version_path = os.path.join(build_tools_dir, build_version)
                if os.path.isdir(build_version_path):
                    search_paths.append(build_version_path)
        
        for search_path in search_paths:
            tool_path = os.path.join(search_path, tool_name)
            if os.path.exists(tool_path):
                return tool_path
        
        return None
    
    def get_build_tools_path(self) -> Optional[str]:
        """
        Get the path to the build tools directory.
        
        Returns:
            Path to build tools, or None if not found
        """
        build_tools_dir = os.path.join(self.sdk_path, "build-tools")
        if not os.path.exists(build_tools_dir):
            return None
            
        # If a specific build tools version is requested, check for it
        if self.build_tools_version:
            version_path = os.path.join(build_tools_dir, self.build_tools_version)
            if os.path.exists(version_path):
                return version_path
        
        # Otherwise, find the latest build tools version
        available_versions = []
        for item in os.listdir(build_tools_dir):
            item_path = os.path.join(build_tools_dir, item)
            if os.path.isdir(item_path):
                available_versions.append(item)
        
        if not available_versions:
            return None
            
        # Sort versions and return the latest
        # Simple version comparison (could be more sophisticated)
        available_versions.sort(key=lambda x: [int(i) for i in x.split('.') if i.isdigit()], reverse=True)
        return os.path.join(build_tools_dir, available_versions[0])
    
    def list_available_platforms(self) -> List[str]:
        """
        List all available Android platforms.
        
        Returns:
            List of available platform names
        """
        platforms_dir = os.path.join(self.sdk_path, "platforms")
        if not os.path.exists(platforms_dir):
            return []
            
        platforms = []
        for item in os.listdir(platforms_dir):
            item_path = os.path.join(platforms_dir, item)
            if os.path.isdir(item_path) and item.startswith("android-"):
                platforms.append(item)
        
        # Sort platforms numerically
        platforms.sort(key=lambda x: int(x.split('-')[1]) if x.split('-')[1].isdigit() else 0)
        return platforms
    
    def list_available_build_tools(self) -> List[str]:
        """
        List all available build tools versions.
        
        Returns:
            List of available build tools version names
        """
        build_tools_dir = os.path.join(self.sdk_path, "build-tools")
        if not os.path.exists(build_tools_dir):
            return []
            
        versions = []
        for item in os.listdir(build_tools_dir):
            item_path = os.path.join(build_tools_dir, item)
            if os.path.isdir(item_path):
                versions.append(item)
        
        # Sort versions
        versions.sort(key=lambda x: [int(i) for i in x.split('.') if i.isdigit()], reverse=True)
        return versions
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """
        Get the full path to an Android SDK tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Full path to the tool, or None if not found
        """
        tool_path = self.find_tool(tool_name)
        return tool_path
    
    def validate_tools(self) -> Dict[str, bool]:
        """
        Validate all required Android tools.
        
        Returns:
            Dictionary mapping tool names to validation results
        """
        tools_to_check = ["adb", "aapt", "zipalign", "apksigner", "dx", "d8", "avdmanager", "sdkmanager"]
        
        results = {}
        for tool in tools_to_check:
            results[tool] = bool(self.find_tool(tool))
        
        return results


class AndroidNDK:
    """Manages Android NDK detection and validation."""
    
    def __init__(self, ndk_path: Optional[str] = None):
        self.ndk_path = ndk_path or self.auto_detect_ndk()
    
    @staticmethod
    def auto_detect_ndk() -> Optional[str]:
        """
        Auto-detect Android NDK location.
        
        Returns:
            Path to Android NDK, or None if not found
        """
        # Check ANDROID_NDK_ROOT environment variable
        android_ndk_root = os.environ.get('ANDROID_NDK_ROOT')
        if android_ndk_root and os.path.exists(android_ndk_root):
            return android_ndk_root
            
        # Check NDK_ROOT environment variable
        ndk_root = os.environ.get('NDK_ROOT')
        if ndk_root and os.path.exists(ndk_root):
            return ndk_root
            
        # Check if NDK is installed in SDK directory
        sdk_path = AndroidSDK.auto_detect_sdk()
        if sdk_path:
            ndk_in_sdk = os.path.join(sdk_path, "ndk")
            if os.path.exists(ndk_in_sdk):
                # Look for the latest version in the ndk directory
                versions = []
                for item in os.listdir(ndk_in_sdk):
                    item_path = os.path.join(ndk_in_sdk, item)
                    if os.path.isdir(item_path):
                        versions.append(item)
                
                if versions:
                    versions.sort(key=lambda x: [int(i) for i in x.split('.') if i.isdigit()], reverse=True)
                    return os.path.join(ndk_in_sdk, versions[0])
        
        # Check common standalone NDK paths
        common_paths = [
            # Linux/macOS
            os.path.expanduser("~/android-ndk"),
            os.path.expanduser("~/.local/share/android-ndk"),
            # Windows
            os.path.expanduser("~/AppData/Local/Android/android-ndk"),
            "C:/android-ndk",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def is_valid(self) -> bool:
        """
        Validates if the Android NDK installation is valid.
        
        Returns:
            True if NDK is valid, False otherwise
        """
        if not self.ndk_path or not os.path.exists(self.ndk_path):
            return False
            
        # Check for key NDK components
        required_files = [
            os.path.join(self.ndk_path, "ndk-build"),
            os.path.join(self.ndk_path, "source.properties"),
        ]
        
        # On Windows, ndk-build might be a .cmd file
        if platform.system() == "Windows":
            required_files[0] += ".cmd"
            
        for file_path in required_files:
            if not os.path.exists(file_path):
                return False
                
        # Check for toolchains directory
        toolchains_dir = os.path.join(self.ndk_path, "toolchains")
        if not os.path.exists(toolchains_dir):
            return False
            
        return True
    
    def get_toolchain_path(self, arch: str = "arm64-v8a") -> Optional[str]:
        """
        Get the path to the toolchain for a specific architecture.
        
        Args:
            arch: Target architecture ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')
            
        Returns:
            Path to the toolchain, or None if not found
        """
        if not self.ndk_path:
            return None
            
        # Map architecture to toolchain
        arch_to_toolchain = {
            'arm64-v8a': 'aarch64-linux-android',
            'armeabi-v7a': 'arm-linux-androideabi', 
            'x86_64': 'x86_64-linux-android',
            'x86': 'i686-linux-android'
        }
        
        toolchain_name = arch_to_toolchain.get(arch, arch)
        
        # Look for the toolchain in the toolchains directory
        toolchains_dir = os.path.join(self.ndk_path, "toolchains")
        if not os.path.exists(toolchains_dir):
            return None
            
        # Check if it's a standalone toolchain or prebuilt
        # Prebuilt toolchains (LLVM-based) are in different locations
        prebuilt_path = os.path.join(self.ndk_path, "toolchains", "llvm", "prebuilt")
        if os.path.exists(prebuilt_path):
            for host in os.listdir(prebuilt_path):
                host_path = os.path.join(prebuilt_path, host)
                if os.path.isdir(host_path):
                    toolchain_path = os.path.join(host_path, "bin")
                    # Check if the toolchain supports our target architecture
                    if any(tool_file.startswith(toolchain_name) for tool_file in os.listdir(toolchain_path)):
                        return toolchain_path
        
        return None
    
    def get_cpp_runtime(self, runtime: str = "c++_shared") -> str:
        """
        Get the C++ runtime to use.
        
        Args:
            runtime: Runtime type ('c++_shared', 'c++_static', 'system')
            
        Returns:
            Runtime identifier
        """
        return runtime  # For now, just return the runtime name