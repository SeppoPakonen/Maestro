"""
JDK detection and management for Maestro.

Implements JDK location detection, validation, and tool management for Java builds.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import shutil


@dataclass
class JDKConfig:
    """Configuration for JDK."""
    jdk_path: Optional[str] = None  # Path to JDK
    version: str = "default"  # Preferred version
    auto_detect: bool = True  # Whether to auto-detect JDK
    java_home_required: bool = True  # Whether JAVA_HOME is required


class JDK:
    """Manages JDK detection and validation."""
    
    def __init__(self, config: JDKConfig = None):
        self.config = config or JDKConfig()
        self.jdk_path = self.config.jdk_path
        self.version = self.config.version
        
        if self.config.auto_detect and not self.jdk_path:
            self.jdk_path = self.auto_detect_jdk()
    
    @staticmethod
    def auto_detect_jdk() -> Optional[str]:
        """
        Auto-detect JDK location from common environment variables and paths.
        
        Returns:
            Path to JDK, or None if not found
        """
        # Check JAVA_HOME environment variable first
        java_home = os.environ.get('JAVA_HOME')
        if java_home and os.path.exists(java_home):
            return java_home
        
        # On macOS, use /usr/libexec/java_home to find JDK
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(['/usr/libexec/java_home'], capture_output=True, text=True)
                if result.returncode == 0:
                    java_home = result.stdout.strip()
                    if os.path.exists(java_home):
                        return java_home
            except:
                pass
        
        # Check for common JDK paths
        common_paths = []
        
        # Linux and macOS paths
        if platform.system() in ["Linux", "Darwin"]:
            common_paths.extend([
                # Common on Linux
                "/usr/lib/jvm/default-java",
                "/usr/lib/jvm/java-11-openjdk",
                "/usr/lib/jvm/java-8-openjdk", 
                "/usr/lib/jvm/java-17-openjdk",
                "/usr/lib/jvm/java-18-openjdk",
                "/usr/lib/jvm/java-19-openjdk",
                "/usr/lib/jvm/java-20-openjdk",
                # Paths with version numbers
                "/usr/lib/jvm/java-11-openjdk-amd64",
                "/usr/lib/jvm/java-8-openjdk-amd64", 
                "/usr/lib/jvm/java-17-openjdk-amd64",
                # User installations
                os.path.expanduser("~/jdk-11"),
                os.path.expanduser("~/jdk-8"),
                os.path.expanduser("~/jdk-17"),
                os.path.expanduser("~/.sdkman/candidates/java/current"),
            ])
        
        # Windows paths
        elif platform.system() == "Windows":
            common_paths.extend([
                # Common Windows installations
                "C:/Program Files/Java/jdk-11",
                "C:/Program Files/Java/jdk-8",
                "C:/Program Files/Java/jdk-17",
                "C:/Program Files/Java/jdk-18",
                "C:/Program Files/Eclipse Adoptium/jdk-11.0.0",
                "C:/Program Files/Eclipse Adoptium/jdk-8.0.0",
                "C:/Program Files/Eclipse Adoptium/jdk-17.0.0",
                # User installations
                os.path.expanduser("~/jdk-11"),
                os.path.expanduser("~/jdk-8"),
                os.path.expanduser("~/jdk-17"),
            ])
        
        # Try to find a JDK executable in PATH
        java_cmd = shutil.which('java')
        if java_cmd:
            # Try to get JAVA_HOME from java command
            try:
                result = subprocess.run([java_cmd, '-XshowSettings:properties', '-version'], 
                                      capture_output=True, text=True)
                for line in result.stderr.split('\n'):
                    if 'java.home' in line:
                        java_home_path = line.split('=')[1].strip()
                        if os.path.exists(java_home_path):
                            return java_home_path
            except:
                pass
        
        # Check common paths
        for path in common_paths:
            if os.path.exists(path):
                # Validate that this is actually a JDK
                bin_dir = os.path.join(path, 'bin')
                java_exe = os.path.join(bin_dir, 'java')
                if platform.system() == "Windows":
                    java_exe += '.exe'
                
                if os.path.exists(java_exe):
                    return path
        
        return None
    
    def is_valid(self) -> bool:
        """
        Validates if the JDK installation is valid.
        
        Returns:
            True if JDK is valid, False otherwise
        """
        if not self.jdk_path or not os.path.exists(self.jdk_path):
            return False
        
        # Check for required directories and executables
        required_dirs = [
            os.path.join(self.jdk_path, "bin"),
            os.path.join(self.jdk_path, "lib"),
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                return False
        
        # Check for key Java tools
        required_tools = ["java", "javac", "jar"]
        
        for tool_name in required_tools:
            if platform.system() == "Windows":
                tool_name += ".exe"
            
            tool_path = os.path.join(self.jdk_path, "bin", tool_name)
            if not os.path.exists(tool_path):
                return False
        
        # Validate that java works
        try:
            java_path = os.path.join(self.jdk_path, "bin", "java")
            if platform.system() == "Windows":
                java_path += ".exe"
                
            result = subprocess.run([java_path, "-version"], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """
        Get the path to a JDK tool.
        
        Args:
            tool_name: Name of the tool (java, javac, jar, etc.)
            
        Returns:
            Path to the tool, or None if not found
        """
        if platform.system() == "Windows":
            tool_name += ".exe"
        
        tool_path = os.path.join(self.jdk_path, "bin", tool_name)
        
        if os.path.exists(tool_path):
            return tool_path
        
        return None
    
    def get_version(self) -> Optional[str]:
        """
        Get the JDK version.
        
        Returns:
            JDK version string, or None if cannot be determined
        """
        java_path = self.get_tool_path("java")
        if not java_path:
            return None
        
        try:
            result = subprocess.run([java_path, "-version"], 
                                  capture_output=True, text=True)
            
            # Java version output goes to stderr
            version_output = result.stderr
            
            # Look for version in the output
            version_match = re.search(r'version "([^"]+)"', version_output)
            if version_match:
                return version_match.group(1)
            
        except Exception:
            pass
        
        return None
    
    def get_java_version_number(self) -> Optional[int]:
        """
        Get the JDK major version number.
        
        Returns:
            Major version number, or None if cannot be determined
        """
        version_str = self.get_version()
        if not version_str:
            return None
        
        # Extract major version (e.g., "1.8.0_292" -> 8, "11.0.12" -> 11)
        try:
            if version_str.startswith("1."):
                # Old version format (1.8, 1.7, etc.) - get the second number
                return int(version_str.split(".")[1])
            else:
                # New version format (11, 12, etc.) - get the first number
                return int(version_str.split(".")[0])
        except (ValueError, IndexError):
            return None
    
    def get_classpath_separator(self) -> str:
        """
        Get the classpath separator for the current platform.
        
        Returns:
            ':' for Unix-like systems, ';' for Windows
        """
        return ";" if platform.system() == "Windows" else ":"
    
    def get_jni_include_paths(self) -> List[str]:
        """
        Get the paths for JNI headers.
        
        Returns:
            List of JNI include paths
        """
        if not self.jdk_path:
            return []
        
        include_paths = [os.path.join(self.jdk_path, "include")]
        
        # Add platform-specific include directory
        platform_name = platform.system().lower()
        if platform_name == "linux":
            include_paths.append(os.path.join(self.jdk_path, "include", "linux"))
        elif platform_name == "darwin":
            include_paths.append(os.path.join(self.jdk_path, "include", "darwin"))
        elif platform_name == "windows":
            include_paths.append(os.path.join(self.jdk_path, "include", "win32"))
        
        # Filter to only existing paths
        return [path for path in include_paths if os.path.exists(path)]


def find_system_jdk() -> Optional[JDK]:
    """
    Find any JDK installed on the system using which/shutil.
    
    Returns:
        JDK instance if found, None otherwise
    """
    java_cmd = shutil.which('java')
    if java_cmd:
        try:
            # Try to determine JAVA_HOME from the java command
            result = subprocess.run([java_cmd, '-XshowSettings:properties', '-version'], 
                                  capture_output=True, text=True)
            for line in result.stderr.split('\n'):
                if 'java.home' in line:
                    java_home_path = line.split('=')[1].strip()
                    if os.path.exists(java_home_path):
                        config = JDKConfig(jdk_path=java_home_path, auto_detect=False)
                        jdk = JDK(config)
                        if jdk.is_valid():
                            return jdk
        except:
            pass
    
    return None


def get_all_detected_jdks() -> List[JDK]:
    """
    Get all JDKs detected on the system.
    
    Returns:
        List of detected JDK instances
    """
    jdks = []
    
    # First, try auto-detection (checking JAVA_HOME, common paths)
    auto_jdk = JDK()
    if auto_jdk.is_valid():
        jdks.append(auto_jdk)
    
    # Then try system-wide detection
    system_jdk = find_system_jdk()
    if system_jdk and system_jdk.jdk_path != auto_jdk.jdk_path:
        jdks.append(system_jdk)
    
    # If on macOS, check for multiple installations
    if platform.system() == "Darwin":
        try:
            # List all installed JDKs
            result = subprocess.run(['/usr/libexec/java_home', '-V'], 
                                  capture_output=True, text=True)
            for line in result.stderr.split('\n'):
                if '//' in line:  # This indicates a path
                    match = re.search(r'/(.*)\s+\[', line)
                    if match:
                        path = match.group(1).strip()
                        if os.path.exists(path):
                            config = JDKConfig(jdk_path=path, auto_detect=False)
                            jdk = JDK(config)
                            if jdk.is_valid() and not any(j.jdk_path == path for j in jdks):
                                jdks.append(jdk)
        except:
            pass
    
    return jdks


def is_valid_jdk_path(path: str) -> bool:
    """
    Check if the given path is a valid JDK installation.
    
    Args:
        path: Path to check
        
    Returns:
        True if valid JDK, False otherwise
    """
    if not os.path.exists(path):
        return False
    
    # Check for required directories
    required_dirs = [os.path.join(path, "bin"), os.path.join(path, "lib")]
    for directory in required_dirs:
        if not os.path.exists(directory):
            return False
    
    # Check for required executables
    required_tools = ["java", "javac"]
    for tool_name in required_tools:
        if platform.system() == "Windows":
            tool_name += ".exe"
        
        tool_path = os.path.join(path, "bin", tool_name)
        if not os.path.exists(tool_path):
            return False
    
    return True