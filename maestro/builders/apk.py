"""
APK packaging and signing for Maestro.

Implements APK assembly, alignment, and signing functionality.
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


@dataclass
class APKConfig:
    """Configuration for APK packaging."""
    output_path: str = None  # Output APK path
    debug: bool = True  # Whether to build debug APK
    keystore_path: str = None  # Path to keystore for signing
    keystore_alias: str = None  # Keystore alias
    keystore_password: str = None  # Keystore password
    key_password: str = None  # Key password
    zipalign_path: str = None  # Path to zipalign tool
    apksigner_path: str = None  # Path to apksigner tool
    jarsigner_path: str = None  # Path to jarsigner as fallback


class APKBuilder:
    """Builds APK files from Android project resources."""
    
    def __init__(self, config: APKConfig = None, sdk_path: str = None):
        self.config = config or APKConfig()
        self.sdk_path = sdk_path
        self.temp_dir = None
    
    def build_apk(
        self,
        project_dir: str,
        dex_files: List[str],
        resource_files: List[str],
        manifest_path: str,
        native_libs: List[str] = None,
        assets_dir: str = None
    ) -> str:
        """
        Builds an APK file from the provided components.
        
        Args:
            project_dir: Root directory of the Android project
            dex_files: List of DEX files to include
            resource_files: List of compiled resource files (resources.arsc, etc.)
            manifest_path: Path to AndroidManifest.xml
            native_libs: List of native library files to include
            assets_dir: Directory containing assets to include
            
        Returns:
            Path to the created APK file
        """
        native_libs = native_libs or []
        
        # Create temporary directory for building
        self.temp_dir = tempfile.mkdtemp(prefix="maestro_apk_")
        
        try:
            # Create the basic APK structure
            apk_output = self.config.output_path or os.path.join(
                project_dir, 
                "app-debug.apk" if self.config.debug else "app-release.apk"
            )
            
            # Create APK as ZIP archive
            with zipfile.ZipFile(apk_output, 'w', zipfile.ZIP_DEFLATED) as apk:
                # Add AndroidManifest.xml
                apk.write(manifest_path, "AndroidManifest.xml")
                
                # Add DEX files
                for i, dex_path in enumerate(dex_files):
                    dex_name = f"classes{'2' if i > 0 else ''}.dex"
                    apk.write(dex_path, dex_name)
                
                # Add resource files (from aapt output)
                for res_path in resource_files:
                    # Calculate internal path relative to project resources
                    if res_path.startswith(os.path.join(project_dir, "res")):
                        internal_path = os.path.relpath(res_path, project_dir)
                    else:
                        internal_path = os.path.basename(res_path)
                    apk.write(res_path, internal_path)
                
                # Add native libraries
                for lib_path in native_libs:
                    # Determine the appropriate lib directory
                    lib_filename = os.path.basename(lib_path)
                    # Find the architecture from the library path or default to armeabi-v7a
                    lib_dir = "lib/armeabi-v7a"  # Default
                    if "arm64" in lib_path.lower():
                        lib_dir = "lib/arm64-v8a"
                    elif "x86_64" in lib_path.lower():
                        lib_dir = "lib/x86_64"
                    elif "x86" in lib_path.lower():
                        lib_dir = "lib/x86"
                    
                    internal_path = os.path.join(lib_dir, lib_filename)
                    apk.write(lib_path, internal_path)
                
                # Add assets if provided
                if assets_dir and os.path.exists(assets_dir):
                    for root, dirs, files in os.walk(assets_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            internal_path = os.path.join("assets", os.path.relpath(file_path, assets_dir))
                            apk.write(file_path, internal_path)
                
                # Add any other necessary files from the project
                # This could include resources, etc.
                
            # Align the APK using zipalign
            aligned_apk_path = self.align_apk(apk_output)
            
            # Sign the APK (if not debug or if signing is requested)
            if not self.config.debug or self.config.keystore_path:
                signed_apk_path = self.sign_apk(aligned_apk_path)
                return signed_apk_path
            else:
                # For debug builds, we might need to sign with debug key
                return aligned_apk_path
                
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def align_apk(self, apk_path: str) -> str:
        """
        Aligns an APK using zipalign.
        
        Args:
            apk_path: Path to the unaligned APK
            
        Returns:
            Path to the aligned APK
        """
        if not self.config.zipalign_path:
            # Try to find zipalign in SDK
            from .android_sdk import AndroidSDK
            if self.sdk_path:
                sdk = AndroidSDK()
                sdk.sdk_path = self.sdk_path
                self.config.zipalign_path = sdk.get_tool_path("zipalign")
        
        if not self.config.zipalign_path:
            print("Warning: zipalign not found, skipping alignment")
            return apk_path
        
        aligned_apk_path = apk_path.replace('.apk', '-aligned.apk')
        
        try:
            cmd = [self.config.zipalign_path, "-v", "4", apk_path, aligned_apk_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"zipalign failed: {result.stderr}")
            
            # Replace the original APK with the aligned one
            os.replace(aligned_apk_path, apk_path)
            return apk_path
            
        except Exception as e:
            print(f"Warning: zipalign failed, continuing with unaligned APK: {str(e)}")
            # If alignment fails, return the original APK
            return apk_path
    
    def sign_apk(self, apk_path: str) -> str:
        """
        Signs an APK using either apksigner or jarsigner.
        
        Args:
            apk_path: Path to the APK to sign
            
        Returns:
            Path to the signed APK
        """
        # First check if apksigner is available
        if not self.config.apksigner_path:
            # Try to find apksigner in SDK
            from .android_sdk import AndroidSDK
            if self.sdk_path:
                sdk = AndroidSDK()
                sdk.sdk_path = self.sdk_path
                self.config.apksigner_path = sdk.get_tool_path("apksigner")
        
        if not self.config.jarsigner_path and not self.config.apksigner_path:
            # Try to find jarsigner (usually from JDK)
            import shutil
            self.config.jarsigner_path = shutil.which("jarsigner")
        
        # Use apksigner if available (preferred for Android)
        if self.config.apksigner_path and self.config.keystore_path:
            return self.sign_with_apksigner(apk_path)
        # Fallback to jarsigner
        elif self.config.jarsigner_path and self.config.keystore_path:
            return self.sign_with_jarsigner(apk_path)
        else:
            # No signing tools available or no keystore, return the same APK
            return apk_path
    
    def sign_with_apksigner(self, apk_path: str) -> str:
        """
        Signs an APK using apksigner.
        
        Args:
            apk_path: Path to the APK to sign
            
        Returns:
            Path to the signed APK
        """
        signed_apk_path = apk_path.replace('.apk', '-signed.apk')
        
        cmd = [
            self.config.apksigner_path,
            "sign",
            "--ks", self.config.keystore_path,
            "--out", signed_apk_path
        ]
        
        if self.config.keystore_alias:
            cmd.extend(["--ks-key-alias", self.config.keystore_alias])
        
        if self.config.keystore_password:
            cmd.extend(["--ks-pass", f"pass:{self.config.keystore_password}"])
        
        if self.config.key_password:
            cmd.extend(["--key-pass", f"pass:{self.config.key_password}"])
        
        cmd.append(apk_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"apksigner failed: {result.stderr}")
            
            return signed_apk_path
        except Exception as e:
            raise Exception(f"Failed to sign APK with apksigner: {str(e)}")
    
    def sign_with_jarsigner(self, apk_path: str) -> str:
        """
        Signs an APK using jarsigner (fallback method).
        
        Args:
            apk_path: Path to the APK to sign
            
        Returns:
            Path to the signed APK
        """
        cmd = [
            self.config.jarsigner_path,
            "-keystore", self.config.keystore_path,
            "-signedjar", apk_path,
            apk_path,  # input APK
        ]
        
        if self.config.keystore_password:
            cmd.extend(["-storepass", self.config.keystore_password])
        
        if self.config.key_password:
            cmd.extend(["-keypass", self.config.key_password])
        
        if self.config.keystore_alias:
            cmd.append(self.config.keystore_alias)
        else:
            # If no alias specified, we need to list and choose one
            list_cmd = [self.config.jarsigner_path, "-keystore", self.config.keystore_path, "-list"]
            list_result = subprocess.run(list_cmd, capture_output=True, text=True)
            if list_result.returncode == 0:
                # Extract first alias from the list (just as a fallback)
                aliases = [line.split()[0] for line in list_result.stdout.split('\n') if line.strip() and not line.startswith('Keystore')]
                if aliases:
                    cmd.append(aliases[0])
                else:
                    raise Exception("No key aliases found in keystore")
            else:
                raise Exception("Could not list keystore aliases")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"jarsigner failed: {result.stderr}")
            
            return apk_path
        except Exception as e:
            raise Exception(f"Failed to sign APK with jarsigner: {str(e)}")


class APKInstaller:
    """Installs APKs to connected Android devices."""
    
    def __init__(self, adb_path: str = None):
        self.adb_path = adb_path or self.find_adb()
    
    def find_adb(self) -> Optional[str]:
        """Find ADB (Android Debug Bridge) tool."""
        from .android_sdk import AndroidSDK
        sdk = AndroidSDK()
        return sdk.get_tool_path("adb")
    
    def list_devices(self) -> List[Dict[str, str]]:
        """List connected Android devices."""
        if not self.adb_path:
            return []
        
        try:
            result = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True)
            devices = []
            
            # Parse the output
            lines = result.stdout.strip().split('\n')[1:]  # Skip the first line ("List of devices attached")
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        device_id, status = parts[0], parts[1]
                        devices.append({"id": device_id, "status": status})
            
            return devices
        except Exception:
            return []
    
    def install_apk(self, apk_path: str, device_id: str = None) -> bool:
        """
        Install an APK to a connected device.
        
        Args:
            apk_path: Path to the APK file to install
            device_id: Specific device ID to install to (if None, uses first available device)
            
        Returns:
            True if installation was successful, False otherwise
        """
        if not os.path.exists(apk_path):
            print(f"APK file does not exist: {apk_path}")
            return False
        
        if not self.adb_path:
            print("ADB not found, cannot install APK")
            return False
        
        cmd = [self.adb_path]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["install", "-r", apk_path])  # -r allows reinstallation
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully installed {apk_path}")
                return True
            else:
                print(f"Failed to install APK: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error installing APK: {str(e)}")
            return False
    
    def run_app(self, package_name: str, activity_name: str = None, device_id: str = None) -> bool:
        """
        Run an installed app on the device.
        
        Args:
            package_name: Package name of the app to run
            activity_name: Name of the activity to launch (if None, uses main activity)
            device_id: Specific device ID (if None, uses first available device)
            
        Returns:
            True if launch was successful, False otherwise
        """
        if not self.adb_path:
            print("ADB not found, cannot launch app")
            return False
        
        if not activity_name:
            # Try to use the .MainActivity as default
            activity_name = "MainActivity"
        
        # If activity doesn't start with a dot, assume it's part of the package
        if not activity_name.startswith('.'):
            full_activity = f"{package_name}/{activity_name}"
        else:
            full_activity = f"{package_name}/{activity_name}"
        
        cmd = [self.adb_path]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["shell", "am", "start", "-n", full_activity])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully launched {full_activity}")
                return True
            else:
                print(f"Failed to launch app: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error launching app: {str(e)}")
            return False


def calculate_apk_checksum(apk_path: str) -> str:
    """
    Calculate the checksum of an APK file.
    
    Args:
        apk_path: Path to the APK file
        
    Returns:
        SHA-256 checksum of the APK file
    """
    sha256_hash = hashlib.sha256()
    with open(apk_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def is_valid_apk(apk_path: str) -> bool:
    """
    Check if the given file is a valid APK.
    
    Args:
        apk_path: Path to the file to check
        
    Returns:
        True if the file is a valid APK, False otherwise
    """
    if not os.path.exists(apk_path) or not apk_path.lower().endswith('.apk'):
        return False
    
    try:
        with zipfile.ZipFile(apk_path, 'r') as apk:
            # An APK must contain AndroidManifest.xml
            return 'AndroidManifest.xml' in apk.namelist()
    except:
        return False