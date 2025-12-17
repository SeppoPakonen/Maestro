"""
Android Manifest handling for Maestro.

Implements AndroidManifest.xml parsing, validation, and generation.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class AndroidManifestInfo:
    """Information extracted from AndroidManifest.xml."""
    package_name: str
    version_code: int
    version_name: str
    min_sdk_version: int
    target_sdk_version: int
    application_label: str
    main_activity: str
    permissions: List[str]
    activities: List[Dict[str, str]]
    services: List[Dict[str, str]]
    receivers: List[Dict[str, str]]
    uses_features: List[str]
    uses_libraries: List[str]


class AndroidManifestParser:
    """Parses and validates AndroidManifest.xml files."""
    
    @staticmethod
    def parse(manifest_path: str) -> AndroidManifestInfo:
        """
        Parse an AndroidManifest.xml file.
        
        Args:
            manifest_path: Path to the AndroidManifest.xml file
            
        Returns:
            AndroidManifestInfo object with manifest data
        """
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"AndroidManifest.xml not found: {manifest_path}")
        
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            # Extract basic package information
            package_name = root.get('package', 'com.example.app')
            
            # Extract version information
            version_code = int(root.get('{http://schemas.android.com/apk/res/android}versionCode', 1))
            version_name = root.get('{http://schemas.android.com/apk/res/android}versionName', '1.0')
            
            # Extract application information
            application_elem = root.find('application')
            if application_elem is not None:
                application_label = application_elem.get('{http://schemas.android.com/apk/res/android}label', 'App')
            else:
                application_label = 'App'
            
            # Extract SDK versions
            uses_sdk_elem = root.find('uses-sdk')
            if uses_sdk_elem is not None:
                min_sdk_version = int(uses_sdk_elem.get('{http://schemas.android.com/apk/res/android}minSdkVersion', 21))
                target_sdk_version = int(uses_sdk_elem.get('{http://schemas.android.com/apk/res/android}targetSdkVersion', 30))
            else:
                # Extract from manifest attributes if uses-sdk not found
                min_sdk_version = int(root.get('{http://schemas.android.com/apk/res/android}minSdkVersion', 21))
                target_sdk_version = int(root.get('{http://schemas.android.com/apk/res/android}targetSdkVersion', 30))
            
            # Extract permissions
            permissions = []
            for uses_permission in root.findall('uses-permission'):
                permission_name = uses_permission.get('{http://schemas.android.com/apk/res/android}name')
                if permission_name:
                    permissions.append(permission_name)
            
            # Extract activities
            activities = []
            if application_elem is not None:
                for activity in application_elem.findall('activity'):
                    activity_info = {
                        'name': activity.get('{http://schemas.android.com/apk/res/android}name'),
                        'label': activity.get('{http://schemas.android.com/apk/res/android}label'),
                        'theme': activity.get('{http://schemas.android.com/apk/res/android}theme'),
                    }
                    activities.append({k: v for k, v in activity_info.items() if v is not None})
            
            # Find main activity (the one with MAIN/LAUNCHER intent filter)
            main_activity = ""
            for activity in activities:
                activity_elem = None
                if application_elem is not None:
                    for act_elem in application_elem.findall('activity'):
                        if act_elem.get('{http://schemas.android.com/apk/res/android}name') == activity['name']:
                            activity_elem = act_elem
                            break
                
                if activity_elem is not None:
                    # Check for MAIN/LAUNCHER intent filter
                    for intent_filter in activity_elem.findall('intent-filter'):
                        action = intent_filter.find('action')
                        category = intent_filter.find('category')
                        
                        if (action is not None and 
                            action.get('{http://schemas.android.com/apk/res/android}name') == 'android.intent.action.MAIN' and
                            category is not None and 
                            category.get('{http://schemas.android.com/apk/res/android}name') == 'android.intent.category.LAUNCHER'):
                            main_activity = activity['name']
                            break
                    if main_activity:
                        break
            
            # Extract services
            services = []
            if application_elem is not None:
                for service in application_elem.findall('service'):
                    service_info = {
                        'name': service.get('{http://schemas.android.com/apk/res/android}name'),
                        'permission': service.get('{http://schemas.android.com/apk/res/android}permission'),
                    }
                    services.append({k: v for k, v in service_info.items() if v is not None})
            
            # Extract receivers
            receivers = []
            if application_elem is not None:
                for receiver in application_elem.findall('receiver'):
                    receiver_info = {
                        'name': receiver.get('{http://schemas.android.com/apk/res/android}name'),
                        'permission': receiver.get('{http://schemas.android.com/apk/res/android}permission'),
                    }
                    receivers.append({k: v for k, v in receiver_info.items() if v is not None})
            
            # Extract uses-feature
            uses_features = []
            for uses_feature in root.findall('uses-feature'):
                feature_name = uses_feature.get('{http://schemas.android.com/apk/res/android}name')
                if feature_name:
                    uses_features.append(feature_name)
            
            # Extract uses-library
            uses_libraries = []
            if application_elem is not None:
                for uses_library in application_elem.findall('uses-library'):
                    library_name = uses_library.get('{http://schemas.android.com/apk/res/android}name')
                    if library_name:
                        uses_libraries.append(library_name)
            
            return AndroidManifestInfo(
                package_name=package_name,
                version_code=version_code,
                version_name=version_name,
                min_sdk_version=min_sdk_version,
                target_sdk_version=target_sdk_version,
                application_label=application_label,
                main_activity=main_activity,
                permissions=permissions,
                activities=activities,
                services=services,
                receivers=receivers,
                uses_features=uses_features,
                uses_libraries=uses_libraries
            )
        
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse AndroidManifest.xml: {str(e)}")
    
    @staticmethod
    def validate(manifest_info: AndroidManifestInfo) -> List[str]:
        """
        Validates AndroidManifest information for common issues.
        
        Args:
            manifest_info: Parsed manifest information
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check package name format
        package_pattern = r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$'
        if not re.match(package_pattern, manifest_info.package_name):
            issues.append(f"Package name '{manifest_info.package_name}' doesn't follow convention (e.g., com.example.app)")
        
        # Check for main activity
        if not manifest_info.main_activity:
            issues.append("No main activity found (with MAIN/LAUNCHER intent filter)")
        
        # Check SDK versions
        if manifest_info.min_sdk_version > manifest_info.target_sdk_version:
            issues.append("minSdkVersion should not be greater than targetSdkVersion")
        
        # Check version code
        if manifest_info.version_code <= 0:
            issues.append("versionCode should be a positive integer")
        
        # Check version name format
        version_pattern = r'^\d+\.\d+(\.\d+)*$'
        if not re.match(version_pattern, manifest_info.version_name):
            issues.append(f"versionName '{manifest_info.version_name}' should follow semantic versioning (e.g., 1.0.0)")
        
        return issues


class AndroidManifestGenerator:
    """Generates AndroidManifest.xml files."""
    
    @staticmethod
    def generate(
        package_name: str,
        version_code: int,
        version_name: str,
        min_sdk_version: int,
        target_sdk_version: int,
        application_label: str = "App",
        main_activity: str = ".MainActivity",
        permissions: List[str] = None,
        custom_metadata: Dict[str, str] = None
    ) -> str:
        """
        Generate an AndroidManifest.xml content.
        
        Args:
            package_name: Application package name
            version_code: Version code (integer)
            version_name: Version name (string)
            min_sdk_version: Minimum SDK version
            target_sdk_version: Target SDK version
            application_label: Application display label
            main_activity: Main activity class name
            permissions: List of permissions to request
            custom_metadata: Additional metadata to include
            
        Returns:
            Generated AndroidManifest.xml content as string
        """
        permissions = permissions or []
        custom_metadata = custom_metadata or {}
        
        # Build permissions XML
        permissions_xml = ""
        for perm in permissions:
            permissions_xml += f'    <uses-permission android:name="{perm}" />\n'
        
        # Build application metadata XML
        metadata_xml = ""
        for key, value in custom_metadata.items():
            metadata_xml += f'        <meta-data android:name="{key}" android:value="{value}" />\n'
        
        # Generate the manifest
        manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}"
    android:minSdkVersion="{min_sdk_version}"
    android:targetSdkVersion="{target_sdk_version}">

    <uses-permission android:name="android.permission.INTERNET" />
{permissions_xml}
    <application
        android:label="{application_label}"
        android:allowBackup="true"
        android:supportsRtl="true">
        
        {metadata_xml}
        <activity
            android:name="{main_activity}"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
"""
        
        return manifest_content
    
    @staticmethod
    def create_default(package_name: str, output_dir: str) -> str:
        """
        Create a default AndroidManifest.xml file.
        
        Args:
            package_name: Application package name
            output_dir: Directory where to create the manifest file
            
        Returns:
            Path to the created manifest file
        """
        manifest_content = AndroidManifestGenerator.generate(
            package_name=package_name,
            version_code=1,
            version_name="1.0.0",
            min_sdk_version=21,
            target_sdk_version=30,
            application_label="App"
        )
        
        manifest_path = os.path.join(output_dir, "AndroidManifest.xml")
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(manifest_content)
        
        return manifest_path


def validate_manifest_path(manifest_path: str) -> bool:
    """
    Validate that the given path is a proper AndroidManifest.xml file.
    
    Args:
        manifest_path: Path to check
        
    Returns:
        True if it's a valid AndroidManifest.xml path, False otherwise
    """
    if not os.path.exists(manifest_path):
        return False
    
    filename = os.path.basename(manifest_path)
    return filename.lower() == 'androidmanifest.xml'


def get_manifest_package_name(manifest_path: str) -> Optional[str]:
    """
    Quick helper to get just the package name from a manifest file.
    
    Args:
        manifest_path: Path to AndroidManifest.xml
        
    Returns:
        Package name or None if not found
    """
    try:
        tree = ET.parse(manifest_path)
        root = tree.getroot()
        return root.get('package')
    except:
        return None