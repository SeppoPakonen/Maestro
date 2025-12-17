"""
Android builder for Maestro.

Implements Android application building with SDK/NDK integration,
resource compilation, DEX generation, and APK packaging.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import tempfile
import shutil

from .base import Builder
from .android_sdk import AndroidSDK, AndroidNDK, AndroidSDKConfig
from .android_manifest import AndroidManifestParser, AndroidManifestGenerator
from .apk import APKBuilder, APKInstaller, APKConfig
from ..repo.package import PackageInfo


@dataclass
class AndroidConfig:
    """Configuration for Android builds."""
    sdk_path: str = None
    ndk_path: str = None
    platform_version: str = "android-30"
    build_tools_version: str = None
    architectures: List[str] = None  # e.g., ['armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64']
    keystore_path: str = None
    keystore_alias: str = None
    keystore_password: str = None
    debug: bool = True
    install_after_build: bool = False
    run_after_install: bool = False

    def __post_init__(self):
        if self.architectures is None:
            self.architectures = ['armeabi-v7a', 'arm64-v8a']


class AndroidBuilder(Builder):
    """Android builder implementation for Maestro."""
    
    def __init__(self, config: AndroidConfig = None):
        self.config = config or AndroidConfig()
        self.sdk = AndroidSDK(AndroidSDKConfig(
            sdk_path=self.config.sdk_path,
            platform_version=self.config.platform_version,
            build_tools_version=self.config.build_tools_version
        ))
        self.ndk = AndroidNDK(self.config.ndk_path)
        
        # Validate SDK and NDK
        if not self.sdk.is_valid():
            print(f"Warning: Android SDK not valid at path: {self.config.sdk_path}")
        
        if self.ndk and not self.ndk.is_valid():
            print(f"Warning: Android NDK not valid at path: {self.config.ndk_path}")
    
    def build_package(self, package: PackageInfo, build_config: Dict) -> bool:
        """
        Build an Android package.
        
        Args:
            package: Package information
            build_config: Build configuration
            
        Returns:
            True if build was successful, False otherwise
        """
        print(f"Building Android package: {package.name}")
        
        # Determine the project structure
        # Look for AndroidManifest.xml in common locations
        manifest_path = self._find_manifest(package.dir)
        if not manifest_path:
            print(f"AndroidManifest.xml not found in {package.dir}")
            return False
        
        # Parse the manifest to get package info
        manifest_info = AndroidManifestParser.parse(manifest_path)
        
        # Create temporary directory for build
        with tempfile.TemporaryDirectory(prefix="maestro_android_build_") as temp_dir:
            # Compile Java sources to DEX if they exist
            java_src_dir = self._find_java_sources(package.dir)
            dex_files = []
            
            if java_src_dir:
                # Compile Java to DEX using dx or d8
                dex_files = self._compile_java_to_dex(java_src_dir, temp_dir, manifest_info.package_name)
                if not dex_files:
                    print("Failed to compile Java sources to DEX")
                    return False
            
            # Compile native sources using NDK if C/C++ files exist
            native_libs = []
            if self.ndk.is_valid():
                native_src_dir = self._find_native_sources(package.dir)
                if native_src_dir:
                    native_libs = self._compile_native_to_libs(native_src_dir, temp_dir)
            
            # Compile resources using aapt
            resource_files = self._compile_resources(package.dir, temp_dir)
            
            # Build the APK
            apk_builder = APKBuilder(
                config=APKConfig(
                    output_path=os.path.join(package.dir, f"{package.name}.apk"),
                    debug=self.config.debug,
                    keystore_path=self.config.keystore_path,
                    keystore_alias=self.config.keystore_alias,
                    keystore_password=self.config.keystore_password
                ),
                sdk_path=self.sdk.sdk_path
            )
            
            apk_path = apk_builder.build_apk(
                project_dir=package.dir,
                dex_files=dex_files,
                resource_files=resource_files,
                manifest_path=manifest_path,
                native_libs=native_libs
            )
            
            print(f"APK built successfully: {apk_path}")
            
            # Install APK if requested
            if self.config.install_after_build:
                installer = APKInstaller()
                devices = installer.list_devices()
                if devices:
                    # Use the first available device
                    device_id = devices[0]['id']
                    success = installer.install_apk(apk_path, device_id)
                    if success and self.config.run_after_install:
                        installer.run_app(manifest_info.package_name, manifest_info.main_activity, device_id)
                else:
                    print("No connected Android devices found for installation")
        
        return True
    
    def link(self, linkfiles: List[str], linkoptions: Dict) -> bool:
        """
        Link Android application components.
        
        Args:
            linkfiles: List of files to link
            linkoptions: Link options
            
        Returns:
            True if linking was successful, False otherwise
        """
        # For Android, linking is part of the APK build process
        # This is handled in build_package method
        return True
    
    def clean_package(self, package: PackageInfo) -> bool:
        """
        Clean Android package build artifacts.
        
        Args:
            package: Package information
            
        Returns:
            True if clean was successful, False otherwise
        """
        build_dirs = [
            os.path.join(package.dir, "build"),
            os.path.join(package.dir, "obj"),
            os.path.join(package.dir, "libs"),
            os.path.join(package.dir, "bin"),
            os.path.join(package.dir, f"{package.name}.apk"),
            os.path.join(package.dir, f"{package.name}-debug.apk"),
            os.path.join(package.dir, f"{package.name}-release.apk")
        ]
        
        for build_dir in build_dirs:
            if os.path.exists(build_dir):
                if os.path.isdir(build_dir):
                    shutil.rmtree(build_dir)
                else:
                    os.remove(build_dir)
        
        return True
    
    def get_target_ext(self) -> str:
        """
        Get target file extension for Android builds.
        
        Returns:
            Target file extension (.apk)
        """
        return ".apk"
    
    def _find_manifest(self, package_dir: str) -> Optional[str]:
        """Find AndroidManifest.xml in the package directory."""
        # Common locations for AndroidManifest.xml
        possible_paths = [
            os.path.join(package_dir, "AndroidManifest.xml"),
            os.path.join(package_dir, "app", "src", "main", "AndroidManifest.xml"),
            os.path.join(package_dir, "src", "main", "AndroidManifest.xml"),
            os.path.join(package_dir, "res", "AndroidManifest.xml")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
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
    
    def _find_native_sources(self, package_dir: str) -> Optional[str]:
        """Find native C/C++ source directory."""
        possible_paths = [
            os.path.join(package_dir, "jni"),
            os.path.join(package_dir, "cpp"),
            os.path.join(package_dir, "native"),
            os.path.join(package_dir, "app", "src", "main", "cpp")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                # Check if it contains C/C++ files
                for root, dirs, files in os.walk(path):
                    if any(f.endswith(('.cpp', '.c', '.cc', '.cxx')) for f in files):
                        return path
        
        return None
    
    def _compile_java_to_dex(self, java_src_dir: str, output_dir: str, package_name: str) -> List[str]:
        """Compile Java sources to DEX files."""
        if not self.sdk.is_valid():
            print("Android SDK not valid, cannot compile Java sources")
            return []
        
        # Find javac and dx/d8
        javac_path = self.sdk.get_tool_path("javac")
        if platform.system() != "Windows":
            # In newer SDKs, javac might be from system JDK
            import shutil
            javac_path = shutil.which("javac") or javac_path
        
        # Find dx or d8 (d8 is preferred)
        d8_path = self.sdk.get_tool_path("d8") or self.sdk.get_tool_path("dx")
        if not d8_path:
            print("Neither d8 nor dx found for DEX compilation")
            return []
        
        # Create a temporary directory for class compilation
        classes_dir = os.path.join(output_dir, "classes")
        os.makedirs(classes_dir, exist_ok=True)
        
        # Compile Java sources to .class files
        java_files = []
        for root, dirs, files in os.walk(java_src_dir):
            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))
        
        if not java_files:
            return []  # No Java files to compile
        
        # Compile .java files to .class files
        if javac_path:
            javac_cmd = [
                javac_path,
                "-d", classes_dir,
                "-source", "1.8",
                "-target", "1.8",
                "-bootclasspath", os.path.join(self.sdk.sdk_path, "platforms", self.sdk.platform_version, "android.jar")
            ]
            
            javac_cmd.extend(java_files)
            
            try:
                result = subprocess.run(javac_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Java compilation failed: {result.stderr}")
                    return []
            except Exception as e:
                print(f"Failed to compile Java sources: {str(e)}")
                return []
        else:
            print("Warning: javac not found, skipping Java compilation")
            return []
        
        # Convert .class files to .dex file
        dex_output = os.path.join(output_dir, "classes.dex")
        
        if d8_path.endswith("d8"):
            # Use d8 (newer, preferred)
            d8_cmd = [d8_path, "--output", output_dir]
            # Add all class files
            for root, dirs, files in os.walk(classes_dir):
                for file in files:
                    if file.endswith('.class'):
                        d8_cmd.append(os.path.join(root, file))
        else:
            # Use dx (older)
            android_jar = os.path.join(self.sdk.sdk_path, "platforms", self.sdk.platform_version, "android.jar")
            dx_cmd = [
                d8_path, 
                "--dex",
                f"--output={dex_output}",
                classes_dir
            ]
            
            try:
                result = subprocess.run(dx_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"DEX compilation failed: {result.stderr}")
                    return []
                
                return [dex_output]
            except Exception as e:
                print(f"Failed to convert classes to DEX: {str(e)}")
                return []
        
        try:
            result = subprocess.run(d8_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"DEX compilation failed: {result.stderr}")
                return []
        except Exception as e:
            print(f"Failed to convert classes to DEX: {str(e)}")
            return []
        
        # d8 creates classes.dex in output_dir
        dex_path = os.path.join(output_dir, "classes.dex")
        if os.path.exists(dex_path):
            return [dex_path]
        
        # If using d8 with multiple files, they may be stored differently
        dex_files = []
        for file in os.listdir(output_dir):
            if file.endswith('.dex'):
                dex_files.append(os.path.join(output_dir, file))
        
        return dex_files
    
    def _compile_native_to_libs(self, native_src_dir: str, output_dir: str) -> List[str]:
        """Compile native C/C++ sources to shared libraries."""
        if not self.ndk.is_valid():
            print("Android NDK not valid, skipping native compilation")
            return []
        
        native_libs = []
        
        # For now, we'll copy any existing .so files if they exist
        # Full NDK compilation is complex and would require Android.mk or CMakeLists.txt
        for root, dirs, files in os.walk(native_src_dir):
            for file in files:
                if file.endswith('.so'):
                    lib_path = os.path.join(root, file)
                    # Copy to the appropriate architecture directory within output
                    arch_dir = os.path.join(output_dir, "lib", "armeabi-v7a")
                    os.makedirs(arch_dir, exist_ok=True)
                    dest_path = os.path.join(arch_dir, file)
                    shutil.copy2(lib_path, dest_path)
                    native_libs.append(dest_path)
        
        # If no .so files were found, return empty list
        # In a full implementation, we would compile the native sources using ndk-build
        return native_libs
    
    def _compile_resources(self, package_dir: str, output_dir: str) -> List[str]:
        """Compile resources using aapt."""
        if not self.sdk.is_valid():
            print("Android SDK not valid, cannot compile resources")
            return []
        
        aapt_path = self.sdk.get_tool_path("aapt")
        if not aapt_path:
            print("aapt not found, cannot compile resources")
            return []
        
        # Common resource directories
        res_dir = os.path.join(package_dir, "res")
        if not os.path.exists(res_dir):
            # Try other common locations
            for res_loc in ["app/src/main/res", "src/main/res", "res"]:
                res_path = os.path.join(package_dir, res_loc)
                if os.path.exists(res_path):
                    res_dir = res_path
                    break
            else:
                print("No resources directory found")
                return []
        
        # Create output directory for compiled resources
        compiled_res_dir = os.path.join(output_dir, "compiled_res")
        os.makedirs(compiled_res_dir, exist_ok=True)
        
        # Find AndroidManifest.xml
        manifest_path = self._find_manifest(package_dir)
        if not manifest_path:
            print("AndroidManifest.xml required for resource compilation")
            return []
        
        # Compile resources with aapt
        apk_path = os.path.join(output_dir, "resources.apk")
        
        aapt_cmd = [
            aapt_path,
            "package",
            "-f",  # Force overwrite
            "-m",  # Make package directories
            "-J", os.path.join(output_dir, "gen"),  # Generate R.java in gen dir
            "-S", res_dir,  # Resource directory
            "-M", manifest_path,  # Manifest file
            "-I", os.path.join(self.sdk.sdk_path, "platforms", self.sdk.platform_version, "android.jar"),  # Android jar
            "-F", apk_path,  # Output APK
        ]
        
        try:
            result = subprocess.run(aapt_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Resource compilation failed: {result.stderr}")
                return []
        except Exception as e:
            print(f"Failed to compile resources: {str(e)}")
            return []
        
        # Extract the compiled resources from the temporary APK
        import zipfile
        extracted_files = []
        
        with zipfile.ZipFile(apk_path, 'r') as apk:
            for file_info in apk.filelist:
                # Extract resources.arsc, manifest, and other resource files
                if (file_info.filename.startswith('res/') or
                    file_info.filename == 'AndroidManifest.xml'):
                    extracted_path = os.path.join(output_dir, file_info.filename)
                    os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
                    with open(extracted_path, 'wb') as output_file:
                        output_file.write(apk.read(file_info.filename))
                    extracted_files.append(extracted_path)
        
        # Add the resources.arsc file separately if needed
        resources_arsc = os.path.join(output_dir, "resources.arsc")
        if os.path.exists(resources_arsc):
            extracted_files.append(resources_arsc)
        
        return extracted_files


def detect_android_project(package_dir: str) -> bool:
    """Detect if a directory contains an Android project."""
    # Check for AndroidManifest.xml
    manifest_path = None
    for root, dirs, files in os.walk(package_dir):
        if "AndroidManifest.xml" in files:
            manifest_path = os.path.join(root, "AndroidManifest.xml")
            break
    
    if not manifest_path:
        return False
    
    # Parse manifest to verify it's a valid Android manifest
    try:
        manifest_info = AndroidManifestParser.parse(manifest_path)
        # If parsing succeeds, it's likely a valid Android project
        return True
    except:
        return False