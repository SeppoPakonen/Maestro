"""
JAR packaging for Maestro.

Implements JAR creation, manifest generation, and signing functionality.
"""

import os
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import platform
import shutil as shutil_module


@dataclass
class JARConfig:
    """Configuration for JAR packaging."""
    output_path: str = None  # Output JAR path
    main_class: str = None  # Main class for executable JAR
    classpath: List[str] = None  # Additional classpath entries
    manifest_file: str = None  # Custom manifest file
    include_sources: bool = False  # Whether to include source files
    sign: bool = False  # Whether to sign the JAR
    keystore_path: str = None  # Path to keystore for signing
    keystore_alias: str = None  # Keystore alias
    keystore_password: str = None  # Keystore password
    key_password: str = None  # Key password
    jarsigner_path: str = None  # Path to jarsigner tool

    def __post_init__(self):
        if self.classpath is None:
            self.classpath = []


class JARBuilder:
    """Builds JAR files from Java class files."""
    
    def __init__(self, config: JARConfig = None, jdk_path: str = None):
        self.config = config or JARConfig()
        self.jdk_path = jdk_path
        self.temp_dir = None
    
    def build_jar(
        self,
        class_files: List[str],
        resources: List[str] = None,
        output_dir: str = None
    ) -> str:
        """
        Builds a JAR file from the provided components.
        
        Args:
            class_files: List of .class files to include
            resources: List of resource files to include
            output_dir: Directory where to create the JAR file
            
        Returns:
            Path to the created JAR file
        """
        resources = resources or []
        
        # Determine output path
        if not self.config.output_path:
            if output_dir:
                jar_name = "classes.jar"
                if self.config.main_class:
                    jar_name = f"{self.config.main_class.replace('.', '_')}.jar"
                self.config.output_path = os.path.join(output_dir, jar_name)
            else:
                raise ValueError("Either config.output_path or output_dir must be specified")
        
        jar_path = self.config.output_path
        
        # Create temporary directory for building
        self.temp_dir = tempfile.mkdtemp(prefix="maestro_jar_")
        
        try:
            # Create the JAR as a ZIP archive with proper structure
            with zipfile.ZipFile(jar_path, 'w', zipfile.ZIP_DEFLATED) as jar:
                # Add class files preserving directory structure
                for class_path in class_files:
                    if os.path.exists(class_path):
                        # Calculate the internal path relative to the base class directory
                        # Usually classes are in a package structure like com/example/MyClass.class
                        internal_path = self._get_internal_class_path(class_path)
                        jar.write(class_path, internal_path)
                
                # Add resource files
                for res_path in resources:
                    if os.path.exists(res_path):
                        # Calculate internal path for resources
                        internal_path = self._get_internal_resource_path(res_path)
                        jar.write(res_path, internal_path)
                
                # Create and add manifest
                manifest_content = self._generate_manifest()
                jar.writestr("META-INF/MANIFEST.MF", manifest_content)
                
                # Create META-INF directory entries if they don't exist
                jar.writestr("META-INF/", b"")
        
            # Sign the JAR if requested
            if self.config.sign:
                signed_jar_path = self.sign_jar(jar_path)
                return signed_jar_path
            
            return jar_path
            
        finally:
            # Clean up temporary directory if needed
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _get_internal_class_path(self, class_path: str) -> str:
        """Get the internal JAR path for a class file."""
        # If the class is in a directory structure that represents packages,
        # preserve that structure. Otherwise, put it in default location.
        
        # Common pattern: /some/path/com/example/MyClass.class -> com/example/MyClass.class
        abs_class_path = os.path.abspath(class_path)
        
        # Find the first occurrence of a Java package pattern (directory with .java files)
        path_parts = abs_class_path.split(os.sep)
        for i in range(len(path_parts) - 1, -1, -1):
            if path_parts[i] == 'src' or path_parts[i] == 'classes':
                # Start from the next directory which should be the package root
                package_path = os.sep.join(path_parts[i+1:])
                return package_path.replace(os.sep, '/')
        
        # If no clear package structure found, just use the filename
        return os.path.basename(class_path).replace(os.sep, '/')
    
    def _get_internal_resource_path(self, resource_path: str) -> str:
        """Get the internal JAR path for a resource file."""
        # Resources are usually in the same structure relative to a resources directory
        abs_res_path = os.path.abspath(resource_path)
        
        # Common pattern: /some/path/src/main/resources/com/example/config.properties -> com/example/config.properties
        path_parts = abs_res_path.split(os.sep)
        for i in range(len(path_parts) - 1, -1, -1):
            if path_parts[i] in ['resources', 'res', 'assets']:
                # Start from the next directory which should be the resource root
                resource_path = os.sep.join(path_parts[i+1:])
                return resource_path.replace(os.sep, '/')
        
        # If no clear resource structure found, just use the relative path
        return os.path.basename(resource_path).replace(os.sep, '/')
    
    def _generate_manifest(self) -> str:
        """Generate the JAR manifest content."""
        manifest_lines = [
            "Manifest-Version: 1.0",
            "Created-By: Maestro JAR Builder"
        ]
        
        # Add main class if specified
        if self.config.main_class:
            manifest_lines.append(f"Main-Class: {self.config.main_class}")
        
        # Add classpath if specified
        if self.config.classpath:
            classpath = ' '.join(self.config.classpath)
            manifest_lines.append(f"Class-Path: {classpath}")
        
        # Add additional manifest entries from custom manifest if provided
        if self.config.manifest_file and os.path.exists(self.config.manifest_file):
            with open(self.config.manifest_file, 'r') as mf:
                custom_lines = mf.read().strip().split('\n')
                # Skip the standard manifest version entry if present
                for line in custom_lines:
                    if not line.startswith("Manifest-Version:") and line.strip():
                        manifest_lines.append(line)
        
        # Join lines with proper line endings
        manifest_content = '\n'.join(manifest_lines) + '\n'
        
        return manifest_content
    
    def sign_jar(self, jar_path: str) -> str:
        """
        Signs a JAR file using jarsigner.
        
        Args:
            jar_path: Path to the JAR file to sign
            
        Returns:
            Path to the signed JAR file
        """
        if not self.config.keystore_path:
            raise ValueError("Keystore path required for JAR signing")
        
        if not self.config.jarsigner_path:
            # Try to find jarsigner from JDK
            if self.jdk_path:
                jarsigner_path = os.path.join(self.jdk_path, "bin", "jarsigner")
                if platform.system() == "Windows":
                    jarsigner_path += ".exe"
                if os.path.exists(jarsigner_path):
                    self.config.jarsigner_path = jarsigner_path
            else:
                # Try to find jarsigner from PATH
                self.config.jarsigner_path = shutil_module.which("jarsigner")
        
        if not self.config.jarsigner_path or not os.path.exists(self.config.jarsigner_path):
            raise FileNotFoundError("jarsigner not found, cannot sign JAR")
        
        # Create signed JAR path
        signed_jar_path = jar_path.replace('.jar', '-signed.jar')
        
        cmd = [self.config.jarsigner_path]
        
        # Add keystore information
        cmd.extend(["-keystore", self.config.keystore_path])
        
        # Add passwords if provided
        if self.config.keystore_password:
            cmd.extend(["-storepass", self.config.keystore_password])
        
        if self.config.key_password:
            cmd.extend(["-keypass", self.config.key_password])
        
        # Add the JAR file and alias
        cmd.extend([jar_path, self.config.keystore_alias or ""])
        
        # Set output to signed JAR if different from input
        cmd.extend(["-signedjar", signed_jar_path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"JAR signing failed: {result.stderr}")
            
            return signed_jar_path
        except Exception as e:
            raise Exception(f"Failed to sign JAR: {str(e)}")


class JNIHeaderGenerator:
    """Generates JNI headers from Java classes."""
    
    def __init__(self, jdk_path: str = None):
        self.jdk_path = jdk_path
    
    def generate_jni_headers(
        self, 
        class_files: List[str], 
        output_dir: str,
        include_jni_types: bool = True
    ) -> List[str]:
        """
        Generate JNI headers from Java class files using javah or javac -h.
        
        Args:
            class_files: List of .class files or .java files
            output_dir: Directory to output headers to
            include_jni_types: Whether to include JNI types in headers
            
        Returns:
            List of generated header file paths
        """
        if not self.jdk_path:
            if platform.system() != "Windows":
                # Try to find javac in PATH
                javac_path = shutil_module.which("javac")
            else:
                javac_path = None
        else:
            javac_path = os.path.join(self.jdk_path, "bin", "javac")
            if platform.system() == "Windows":
                javac_path += ".exe"
        
        if not javac_path or not os.path.exists(javac_path):
            raise FileNotFoundError("javac not found, cannot generate JNI headers")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Try to use the newer 'javac -h' command first (Java 8+)
        header_files = self._generate_with_javac_h(javac_path, class_files, output_dir)
        
        if not header_files:
            # Fall back to 'javah' if -h option is not available
            header_files = self._generate_with_javah(javac_path, class_files, output_dir)
        
        return header_files
    
    def _generate_with_javac_h(self, javac_path: str, class_files: List[str], output_dir: str) -> List[str]:
        """Generate JNI headers using 'javac -h' command."""
        # Find the directory containing the class files to infer the classpath
        class_dirs = set(os.path.dirname(f) for f in class_files if f.endswith('.class'))
        
        cmd = [javac_path, "-h", output_dir]
        
        # Add all class directories to the classpath
        classpath_separator = ";" if platform.system() == "Windows" else ":"
        if class_dirs:
            classpath = classpath_separator.join(class_dirs)
            cmd.extend(["-cp", classpath])
        
        cmd.extend(class_files)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: javac -h failed: {result.stderr}")
                return []
            
            # Find all generated header files
            headers = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.endswith('.h'):
                        headers.append(os.path.join(root, file))
            
            return headers
        except Exception as e:
            print(f"Error using javac -h: {str(e)}")
            return []
    
    def _generate_with_javah(self, javac_path: str, class_files: List[str], output_dir: str) -> List[str]:
        """Generate JNI headers using 'javah' command."""
        # 'javah' has been deprecated in Java 10 and removed in Java 14,
        # but might still be available in older JDKs
        
        javah_path = javac_path.replace("javac", "javah")
        if platform.system() == "Windows":
            javah_path = javah_path.replace("javac.exe", "javah.exe")
        
        if not os.path.exists(javah_path):
            return []  # javah not available
        
        # Need to extract class names from class files
        class_names = []
        for class_file in class_files:
            if class_file.endswith('.class'):
                # Convert file path to class name
                rel_path = os.path.relpath(class_file, output_dir)
                class_name = rel_path.replace('/', '.').replace('\\', '.').replace('.class', '')
                class_names.append(class_name)
        
        if not class_names:
            return []
        
        cmd = [javah_path, "-o", output_dir]
        
        # Add all class directories to the classpath
        classpath_separator = ";" if platform.system() == "Windows" else ":"
        classpath = classpath_separator.join(set(os.path.dirname(f) for f in class_files))
        cmd.extend(["-cp", classpath])
        
        cmd.extend(class_names)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: javah failed: {result.stderr}")
                return []
            
            # Find all generated header files
            headers = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.endswith('.h'):
                        headers.append(os.path.join(root, file))
            
            return headers
        except Exception as e:
            print(f"Error using javah: {str(e)}")
            return []


def create_executable_jar(
    main_class: str,
    class_files: List[str],
    resources: List[str] = None,
    output_path: str = None,
    classpath: List[str] = None,
    jdk_path: str = None
) -> str:
    """
    Creates an executable JAR file with a main class.
    
    Args:
        main_class: Fully qualified name of the main class
        class_files: List of .class files to include
        resources: List of resource files to include
        output_path: Path where to create the JAR file
        classpath: Additional classpath entries
        jdk_path: Path to JDK (for JAR tool)
        
    Returns:
        Path to the created executable JAR file
    """
    resources = resources or []
    classpath = classpath or []
    
    config = JARConfig(
        output_path=output_path,
        main_class=main_class,
        classpath=classpath
    )
    
    builder = JARBuilder(config, jdk_path)
    return builder.build_jar(class_files, resources)


def is_valid_jar(jar_path: str) -> bool:
    """
    Check if the given file is a valid JAR file.
    
    Args:
        jar_path: Path to the file to check
        
    Returns:
        True if the file is a valid JAR, False otherwise
    """
    if not os.path.exists(jar_path) or not jar_path.lower().endswith('.jar'):
        return False
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # A JAR must contain a manifest
            return 'META-INF/MANIFEST.MF' in jar.namelist()
    except:
        return False


def calculate_jar_checksum(jar_path: str) -> str:
    """
    Calculate the checksum of a JAR file.
    
    Args:
        jar_path: Path to the JAR file
        
    Returns:
        SHA-256 checksum of the JAR file
    """
    sha256_hash = hashlib.sha256()
    with open(jar_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_jar_contents(jar_path: str, output_dir: str) -> bool:
    """
    Extract all contents of a JAR file to a directory.
    
    Args:
        jar_path: Path to the JAR file to extract
        output_dir: Directory where to extract contents
        
    Returns:
        True if extraction was successful, False otherwise
    """
    if not is_valid_jar(jar_path):
        return False
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            jar.extractall(output_dir)
        return True
    except Exception:
        return False