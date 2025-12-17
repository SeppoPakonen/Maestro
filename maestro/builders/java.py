"""
Java builder for Maestro.

Implements Java compilation, JAR packaging, and JNI support.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .base import Builder
from .jdk import JDK, JDKConfig
from .jar import JARBuilder, JARConfig, JNIHeaderGenerator
from ..repo.package import PackageInfo


@dataclass
class JavaConfig:
    """Configuration for Java builds."""
    jdk_path: str = None
    debug: bool = True  # Whether to include debug info
    source_version: str = "8"  # Source compatibility
    target_version: str = "8"  # Target compatibility
    classpath: List[str] = None  # Additional classpath entries
    include_sources: bool = False  # Whether to include source files in JAR
    sign_jar: bool = False  # Whether to sign the JAR
    keystore_path: str = None  # Path to keystore for signing
    keystore_alias: str = None  # Keystore alias
    keystore_password: str = None  # Keystore password
    build_jni: bool = False  # Whether to build JNI components
    generate_jni_headers: bool = False  # Whether to generate JNI headers

    def __post_init__(self):
        if self.classpath is None:
            self.classpath = []


class JavaBuilder(Builder):
    """Java builder implementation for Maestro."""
    
    def __init__(self, config: JavaConfig = None):
        self.config = config or JavaConfig()
        self.jdk = JDK(JDKConfig(
            jdk_path=self.config.jdk_path,
            auto_detect=True
        ))
        
        # Validate JDK
        if not self.jdk.is_valid():
            print(f"Warning: JDK not valid at path: {self.config.jdk_path}")
    
    def build_package(self, package: PackageInfo, build_config: Dict) -> bool:
        """
        Build a Java package.
        
        Args:
            package: Package information
            build_config: Build configuration
            
        Returns:
            True if build was successful, False otherwise
        """
        print(f"Building Java package: {package.name}")
        
        # Find Java source files
        src_dir = self._find_java_sources(package.dir)
        if not src_dir:
            print(f"No Java source files found in {package.dir}")
            return False
        
        # Create temporary directory for build
        with tempfile.TemporaryDirectory(prefix="maestro_java_build_") as temp_dir:
            # Compile Java sources to class files
            class_files = self._compile_java_sources(src_dir, temp_dir)
            if not class_files:
                print("Failed to compile Java sources")
                return False
            
            # Find resource files
            resources = self._find_resources(package.dir)
            
            # If JNI is enabled and native sources exist, compile them too
            if self.config.build_jni:
                native_dir = self._find_native_sources(package.dir)
                if native_dir:
                    self._build_native_components(native_dir, temp_dir)
            
            # Generate JNI headers if requested
            if self.config.generate_jni_headers:
                header_generator = JNIHeaderGenerator(self.jdk.jdk_path)
                try:
                    headers = header_generator.generate_jni_headers(class_files, 
                                                                  os.path.join(package.dir, "jni", "include"))
                    print(f"Generated {len(headers)} JNI headers")
                except Exception as e:
                    print(f"Warning: Failed to generate JNI headers: {str(e)}")
            
            # Create JAR file
            jar_config = JARConfig(
                output_path=os.path.join(package.dir, f"{package.name}.jar"),
                main_class=build_config.get('main_class'),
                classpath=self.config.classpath,
                include_sources=self.config.include_sources,
                sign=self.config.sign_jar,
                keystore_path=self.config.keystore_path,
                keystore_alias=self.config.keystore_alias,
                keystore_password=self.config.keystore_password
            )
            
            jar_builder = JARBuilder(jar_config, self.jdk.jdk_path)
            jar_path = jar_builder.build_jar(class_files, resources)
            
            print(f"JAR built successfully: {jar_path}")
        
        return True
    
    def link(self, linkfiles: List[str], linkoptions: Dict) -> bool:
        """
        Link Java application components (create final executable JAR).
        
        Args:
            linkfiles: List of files to link (JARs, class files)
            linkoptions: Link options
            
        Returns:
            True if linking was successful, False otherwise
        """
        # For Java, linking is part of the JAR build process
        # This is handled in build_package method
        return True
    
    def clean_package(self, package: PackageInfo) -> bool:
        """
        Clean Java package build artifacts.
        
        Args:
            package: Package information
            
        Returns:
            True if clean was successful, False otherwise
        """
        build_dirs = [
            os.path.join(package.dir, "build"),
            os.path.join(package.dir, "target"),
            os.path.join(package.dir, "classes"),
            os.path.join(package.dir, "obj"),
            os.path.join(package.dir, f"{package.name}.jar"),
            os.path.join(package.dir, f"{package.name}-signed.jar")
        ]
        
        for build_dir in build_dirs:
            if os.path.exists(build_dir):
                if os.path.isdir(build_dir):
                    shutil.rmtree(build_dir)
                else:
                    os.remove(build_dir)
        
        # Also remove compiled class files
        for root, dirs, files in os.walk(package.dir):
            for file in files:
                if file.endswith('.class'):
                    os.remove(os.path.join(root, file))
        
        return True
    
    def get_target_ext(self) -> str:
        """
        Get target file extension for Java builds.
        
        Returns:
            Target file extension (.jar)
        """
        return ".jar"
    
    def _find_java_sources(self, package_dir: str) -> Optional[str]:
        """Find Java source directory."""
        possible_paths = [
            os.path.join(package_dir, "src"),
            os.path.join(package_dir, "app", "src", "main", "java"),
            os.path.join(package_dir, "src", "main", "java"),
            os.path.join(package_dir, "java")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                # Check if it contains .java files
                for root, dirs, files in os.walk(path):
                    if any(f.endswith('.java') for f in files):
                        return path
        
        return None
    
    def _find_resources(self, package_dir: str) -> List[str]:
        """Find resource files to include in JAR."""
        resources = []
        
        # Common resource directories
        possible_resource_dirs = [
            os.path.join(package_dir, "resources"),
            os.path.join(package_dir, "res"),
            os.path.join(package_dir, "assets"),
            os.path.join(package_dir, "src", "main", "resources"),
            os.path.join(package_dir, "app", "src", "main", "resources")
        ]
        
        for res_dir in possible_resource_dirs:
            if os.path.exists(res_dir):
                for root, dirs, files in os.walk(res_dir):
                    for file in files:
                        # Include common resource file types
                        if not file.endswith(('.java', '.class', '.jar')):
                            resources.append(os.path.join(root, file))
        
        return resources
    
    def _find_native_sources(self, package_dir: str) -> Optional[str]:
        """Find native C/C++ source directory for JNI."""
        possible_paths = [
            os.path.join(package_dir, "jni"),
            os.path.join(package_dir, "cpp"),
            os.path.join(package_dir, "native"),
            os.path.join(package_dir, "app", "src", "main", "jni")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                # Check if it contains C/C++ files
                for root, dirs, files in os.walk(path):
                    if any(f.endswith(('.cpp', '.c', '.cc', '.cxx')) for f in files):
                        return path
        
        return None
    
    def _compile_java_sources(self, src_dir: str, output_dir: str) -> List[str]:
        """Compile Java sources to class files."""
        if not self.jdk.is_valid():
            print("JDK not valid, cannot compile Java sources")
            return []
        
        javac_path = self.jdk.get_tool_path("javac")
        if not javac_path:
            print("javac not found, cannot compile Java sources")
            return []
        
        # Create classes directory
        classes_dir = os.path.join(output_dir, "classes")
        os.makedirs(classes_dir, exist_ok=True)
        
        # Find all Java source files
        java_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        
        if not java_files:
            return []  # No Java files to compile
        
        # Construct javac command
        javac_cmd = [javac_path]
        
        # Add source and target versions
        javac_cmd.extend([f"-source", self.config.source_version])
        javac_cmd.extend([f"-target", self.config.target_version])
        
        # Add debug info if requested
        if self.config.debug:
            javac_cmd.extend(["-g"])
        else:
            javac_cmd.extend(["-g:none"])
        
        # Add classpath if needed
        classpath_separator = self.jdk.get_classpath_separator()
        all_classpath_entries = self.config.classpath[:]
        
        # Add the classes directory to classpath so we can reference
        # already compiled classes during compilation
        all_classpath_entries.append(classes_dir)
        
        if all_classpath_entries:
            javac_cmd.extend(["-cp", classpath_separator.join(all_classpath_entries)])
        
        # Add output directory
        javac_cmd.extend(["-d", classes_dir])
        
        # Add Java source files
        javac_cmd.extend(java_files)
        
        try:
            result = subprocess.run(javac_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Java compilation failed: {result.stderr}")
                return []
        except Exception as e:
            print(f"Failed to compile Java sources: {str(e)}")
            return []
        
        # Find all compiled class files
        class_files = []
        for root, dirs, files in os.walk(classes_dir):
            for file in files:
                if file.endswith('.class'):
                    class_files.append(os.path.join(root, file))
        
        return class_files
    
    def _build_native_components(self, native_dir: str, output_dir: str):
        """Build native components for JNI."""
        print("Building native JNI components...")
        
        # This would typically involve more complex build logic for native code
        # such as using the system's C/C++ compiler or a build system like CMake
        # For now, we'll just check if there are native components that need
        # to be compiled using the JNI header generator
        if self.config.generate_jni_headers:
            # Find any Java class files to generate JNI headers for
            # In a real implementation, this would be more sophisticated
            pass


def detect_java_project(package_dir: str) -> bool:
    """Detect if a directory contains a Java project."""
    # Check for Java source files
    java_found = False
    
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            if file.endswith('.java'):
                java_found = True
                break
        if java_found:
            break
    
    if not java_found:
        return False
    
    # If Java files exist, consider this a Java project
    return True


def get_java_version_info(jdk_path: str = None) -> Optional[Dict[str, str]]:
    """Get detailed Java version information."""
    if jdk_path:
        jdk = JDK(JDKConfig(jdk_path=jdk_path, auto_detect=False))
    else:
        jdk = JDK()
    
    if not jdk.is_valid():
        return None
    
    return {
        'version': jdk.get_version(),
        'major_version': jdk.get_java_version_number(),
        'path': jdk.jdk_path,
        'vendor': 'unknown'  # Could extract this from version string in real implementation
    }