"""
Gradle builder for the Maestro build system.

Implements Phase 5.75: Gradle Builder
- Support gradle/gradlew, multi-module projects, and Kotlin DSL
- Gap: Gradle packages scanned (100%) but can't be built
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import Builder, Package
from .config import MethodConfig
from .console import execute_command


class GradleBuilder(Builder):
    """Gradle builder implementation for building Gradle-based projects."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("gradle", config)
        self.gradle_cmd = self._detect_gradle_command()

    def _detect_gradle_command(self) -> str:
        """Detect the appropriate Gradle command (gradle or gradlew)."""
        # Check for gradlew (Gradle wrapper) first in the package directory
        current_dir = os.getcwd()
        
        # Look for gradlew in the current directory
        gradlew_local = os.path.join(current_dir, "gradlew")
        gradlew_local_sh = os.path.join(current_dir, "gradlew.sh")
        gradlew_local_bat = os.path.join(current_dir, "gradlew.bat")
        
        if os.path.exists(gradlew_local) or os.path.exists(gradlew_local_sh):
            # Make gradlew executable if needed
            if os.path.exists(gradlew_local):
                os.chmod(gradlew_local, 0o755)
            elif os.path.exists(gradlew_local_sh):
                os.chmod(gradlew_local_sh, 0o755)
            return "./gradlew"
        elif os.path.exists(gradlew_local_bat):
            return "gradlew.bat"
        
        # If no wrapper, try system gradle command
        try:
            result = subprocess.run(["gradle", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "gradle"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Default to gradle if nothing found
        return "gradle"

    def build_package(self, package: Package) -> bool:
        """Build a Gradle package.

        Args:
            package: Package to build

        Returns:
            True if build succeeded, False otherwise
        """
        print(f"Building Gradle package: {package.name}")
        
        # Change to package directory
        original_dir = os.getcwd()
        try:
            os.chdir(package.directory)
            
            # Determine build command based on build system configuration
            gradle_cmd = self.gradle_cmd
            
            # Build arguments based on configuration
            build_args = [gradle_cmd]
            
            # Add build type (Debug/Release)
            if self.config.config.build_type == "Release":
                build_args.extend(["-Prelease=true"])
            else:
                build_args.extend(["-Pdebug=true"])
            
            # Add parallel execution if configured
            if self.config.config.parallel and self.config.config.jobs > 1:
                build_args.extend([f"-j{self.config.config.jobs}"])
            
            # Add verbose output if configured
            if self.config.config.verbose:
                build_args.append("--info")
            else:
                build_args.append("--quiet")
            
            # Determine appropriate Gradle tasks based on package type
            # Check if this is an Android project by looking for common indicators
            is_android_project = self._is_android_project()
            
            if is_android_project:
                # For Android projects, build assemble tasks
                build_args.append("assemble")
            else:
                # For regular Java/Kotlin projects, try common build tasks
                build_args.append("build")
            
            # Add offline mode if configured
            if self.config.config.offline:
                build_args.append("--offline")
            
            # Execute the build command
            print(f"Executing: {' '.join(build_args)}")
            success = execute_command(build_args)
            
            if success:
                print(f"Successfully built Gradle package: {package.name}")
            else:
                print(f"Failed to build Gradle package: {package.name}")
            
            return success
            
        finally:
            os.chdir(original_dir)

    def _is_android_project(self) -> bool:
        """Check if the current project is an Android project."""
        # Check for common Android project indicators
        android_indicators = [
            "build.gradle",  # Look for build.gradle that contains Android configuration
            "build.gradle.kts",  # Kotlin DSL version
            "settings.gradle", 
            "settings.gradle.kts",
            "gradle.properties",
            "src/main/AndroidManifest.xml",  # Android manifest
            "src/main/res"  # Android resources directory
        ]
        
        # Check if any of these files exist
        for indicator in android_indicators:
            if os.path.exists(indicator):
                # For build.gradle files, check if they contain Android plugin
                if indicator in ["build.gradle", "build.gradle.kts"]:
                    try:
                        with open(indicator, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            if 'com.android.application' in content or \
                               'com.android.library' in content or \
                               'android' in content:
                                return True
                    except:
                        # If we can't read the file, continue checking
                        continue
        
        # Also check for Android-specific directories
        android_dirs = ["app", "lib"]
        for android_dir in android_dirs:
            if os.path.exists(os.path.join(android_dir, "src", "main", "AndroidManifest.xml")):
                return True
        
        return False

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """Link final executable/library for Gradle projects.
        
        For Gradle projects, linking is typically handled by Gradle tasks.
        This method may be used for custom linking or assembly tasks.

        Args:
            linkfiles: List of files to link
            linkoptions: Linker options

        Returns:
            True if linking succeeded, False otherwise
        """
        print("Linking for Gradle projects is typically handled by Gradle tasks.")
        # For Gradle, linking is usually part of the build process
        # If custom linking is needed, implement specific Gradle tasks
        return True

    def clean_package(self, package: Package) -> bool:
        """Clean package build artifacts.

        Args:
            package: Package to clean

        Returns:
            True if clean succeeded, False otherwise
        """
        print(f"Cleaning Gradle package: {package.name}")
        
        original_dir = os.getcwd()
        try:
            os.chdir(package.directory)
            
            gradle_cmd = self.gradle_cmd
            clean_cmd = [gradle_cmd, "clean"]
            
            if self.config.config.verbose:
                clean_cmd.append("--info")
            else:
                clean_cmd.append("--quiet")
            
            print(f"Executing: {' '.join(clean_cmd)}")
            success = execute_command(clean_cmd)
            
            if success:
                print(f"Successfully cleaned Gradle package: {package.name}")
            else:
                print(f"Failed to clean Gradle package: {package.name}")
            
            return success
            
        finally:
            os.chdir(original_dir)

    def get_target_ext(self) -> str:
        """Return target file extension for Gradle projects.

        Returns:
            Target file extension (typically .jar, .aar, or empty for multi-artifact projects)
        """
        # Gradle projects can produce various outputs (JAR, AAR, APK, etc.)
        # Return .jar as a general default, but this could be customized
        return ".jar"

    def configure(self, package: Package) -> bool:
        """Configure Gradle build settings.

        Args:
            package: Package to configure

        Returns:
            True if configuration succeeded, False otherwise
        """
        print(f"Configuring Gradle package: {package.name}")
        
        # For Gradle projects, configuration is typically handled by build.gradle files
        # But we can set properties based on the method configuration
        properties = {}
        
        # Set build type as a Gradle property
        if self.config.config.build_type == "Release":
            properties["buildType"] = "release"
        else:
            properties["buildType"] = "debug"
        
        # Write or update gradle.properties with Maestro configuration
        gradle_props_path = os.path.join(package.directory, "gradle.properties")
        try:
            with open(gradle_props_path, "a") as f:
                f.write(f"\n# Maestro build configuration\n")
                for key, value in properties.items():
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            print(f"Warning: Could not update gradle.properties: {e}")
            return False

    def detect_multi_module_structure(self, package: Package) -> List[str]:
        """Detect and return list of modules in a multi-module Gradle project.

        Args:
            package: Package to analyze

        Returns:
            List of module names
        """
        modules = []
        
        original_dir = os.getcwd()
        try:
            os.chdir(package.directory)
            
            # Look for settings.gradle or settings.gradle.kts to identify modules
            settings_files = ["settings.gradle", "settings.gradle.kts"]
            
            for settings_file in settings_files:
                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Look for include statements (Gradle DSL)
                        # Pattern: include ':module_name' or include ':path:to:module'
                        import re
                        # Match include statements in both Groovy and Kotlin DSL
                        include_pattern = r"include\s*[('\":]([^)'\":]+)['\"):]?"
                        matches = re.findall(include_pattern, content)
                        
                        for match in matches:
                            # Clean up the module name
                            module = match.strip().strip("'\"")
                            if module and module not in modules:
                                modules.append(module)
                                
                        break  # Found settings file, don't check the other one
                    except Exception as e:
                        print(f"Warning: Could not parse {settings_file}: {e}")
            
            # If no modules found via settings file, look for common module directory patterns
            if not modules:
                for item in os.listdir("."):
                    if os.path.isdir(item):
                        # Check if directory contains build.gradle or build.gradle.kts
                        build_gradle = os.path.join(item, "build.gradle")
                        build_gradle_kts = os.path.join(item, "build.gradle.kts")
                        
                        if os.path.exists(build_gradle) or os.path.exists(build_gradle_kts):
                            modules.append(f":{item}")
            
        except Exception as e:
            print(f"Warning: Error detecting multi-module structure: {e}")
        finally:
            os.chdir(original_dir)
        
        return modules

    def build_multi_module_package(self, package: Package) -> bool:
        """Build all modules in a multi-module Gradle project.

        Args:
            package: Package to build

        Returns:
            True if build succeeded, False otherwise
        """
        print(f"Building multi-module Gradle package: {package.name}")
        
        # Detect modules
        modules = self.detect_multi_module_structure(package)
        
        if not modules:
            # If no modules detected, build as a single module
            return self.build_package(package)
        
        print(f"Detected modules: {modules}")
        
        original_dir = os.getcwd()
        try:
            os.chdir(package.directory)
            
            # Build all modules
            gradle_cmd = self.gradle_cmd
            build_cmd = [gradle_cmd, "build"]
            
            # Add parallel execution if configured
            if self.config.config.parallel and self.config.config.jobs > 1:
                build_cmd.extend([f"-j{self.config.config.jobs}"])
            
            # Add verbose output if configured
            if self.config.config.verbose:
                build_cmd.append("--info")
            else:
                build_cmd.append("--quiet")
            
            # Add offline mode if configured
            if self.config.config.offline:
                build_cmd.append("--offline")
            
            print(f"Executing: {' '.join(build_cmd)}")
            success = execute_command(build_cmd)
            
            if success:
                print(f"Successfully built multi-module Gradle package: {package.name}")
            else:
                print(f"Failed to build multi-module Gradle package: {package.name}")
            
            return success
            
        finally:
            os.chdir(original_dir)