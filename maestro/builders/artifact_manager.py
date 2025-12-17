"""
Build artifact management module.

Implements artifact registry and management as required in Phase 12:
- Define artifact storage structure
- Create artifact registry .maestro/build/artifacts.json  
- Track targets, timestamps, config hashes
- Manage build outputs
"""

import json
import os
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class ArtifactType(Enum):
    """Types of build artifacts."""
    EXECUTABLE = "executable"
    SHARED_LIBRARY = "shared_library"
    STATIC_LIBRARY = "static_library"
    OBJECT_FILE = "object_file"
    JAR_FILE = "jar"
    APK_FILE = "apk"
    PCH_FILE = "pch"  # Precompiled header
    BLITZ_FILE = "blitz"  # Unity build file
    BRC_FILE = "brc"  # Binary resource file
    OTHER = "other"


@dataclass
class BuildArtifact:
    """Represents a single build artifact."""
    id: str  # Unique identifier for the artifact
    name: str  # Name of the artifact
    path: str  # Full path to the artifact
    type: ArtifactType  # Type of artifact
    size: int  # Size in bytes
    timestamp: float  # Creation timestamp
    package_name: str  # Package that created this artifact
    build_method: str  # Build method used
    config_hash: str  # Hash of build configuration
    dependencies: List[str] = field(default_factory=list)  # Dependencies used
    build_system: str = "upp"  # Build system that created it
    hash: str = ""  # Hash of the artifact file content
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.hash:
            self.hash = self.compute_file_hash()
        if not self.id:
            self.id = self.generate_id()
    
    def compute_file_hash(self) -> str:
        """Compute SHA256 hash of the artifact file."""
        if not os.path.exists(self.path):
            return ""
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(self.path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    def generate_id(self) -> str:
        """Generate a unique ID for this artifact."""
        content = f"{self.name}_{self.path}_{self.timestamp}_{self.config_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def exists(self) -> bool:
        """Check if the artifact file still exists."""
        return os.path.exists(self.path)
    
    def is_stale(self, config_hash: str) -> bool:
        """Check if artifact is stale compared to current config."""
        return self.config_hash != config_hash


@dataclass
class ArtifactRegistry:
    """Registry for tracking build artifacts."""
    
    registry_file: str = ".maestro/build/artifacts.json"
    artifacts: Dict[str, BuildArtifact] = field(default_factory=dict)
    last_updated: float = 0.0
    
    def __post_init__(self):
        """Initialize the registry after dataclass creation."""
        self.load_registry()
    
    def add_artifact(self, artifact: BuildArtifact) -> str:
        """Add an artifact to the registry."""
        self.artifacts[artifact.id] = artifact
        self.last_updated = time.time()
        return artifact.id
    
    def get_artifact(self, artifact_id: str) -> Optional[BuildArtifact]:
        """Get an artifact by ID."""
        return self.artifacts.get(artifact_id)
    
    def remove_artifact(self, artifact_id: str) -> bool:
        """Remove an artifact from the registry."""
        if artifact_id in self.artifacts:
            del self.artifacts[artifact_id]
            self.last_updated = time.time()
            return True
        return False
    
    def get_artifacts_by_package(self, package_name: str) -> List[BuildArtifact]:
        """Get all artifacts for a specific package."""
        return [artifact for artifact in self.artifacts.values() 
                if artifact.package_name == package_name]
    
    def get_artifacts_by_type(self, artifact_type: ArtifactType) -> List[BuildArtifact]:
        """Get all artifacts of a specific type."""
        return [artifact for artifact in self.artifacts.values() 
                if artifact.type == artifact_type]
    
    def get_artifacts_by_build_method(self, build_method: str) -> List[BuildArtifact]:
        """Get all artifacts built with a specific method."""
        return [artifact for artifact in self.artifacts.values() 
                if artifact.build_method == build_method]
    
    def remove_stale_artifacts(self, config_hash: str) -> int:
        """Remove artifacts that don't match the current config hash."""
        stale_ids = []
        for artifact_id, artifact in self.artifacts.items():
            if artifact.is_stale(config_hash):
                stale_ids.append(artifact_id)
        
        for artifact_id in stale_ids:
            del self.artifacts[artifact_id]
        
        if stale_ids:
            self.last_updated = time.time()
        
        return len(stale_ids)
    
    def remove_missing_artifacts(self) -> int:
        """Remove artifacts whose files no longer exist."""
        missing_ids = []
        for artifact_id, artifact in self.artifacts.items():
            if not artifact.exists():
                missing_ids.append(artifact_id)
        
        for artifact_id in missing_ids:
            del self.artifacts[artifact_id]
        
        if missing_ids:
            self.last_updated = time.time()
        
        return len(missing_ids)
    
    def cleanup_old_artifacts(self, days: int = 30) -> int:
        """Remove artifacts older than specified number of days."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        old_ids = []
        for artifact_id, artifact in self.artifacts.items():
            if artifact.timestamp < cutoff_time:
                old_ids.append(artifact_id)
        
        for artifact_id in old_ids:
            del self.artifacts[artifact_id]
        
        if old_ids:
            self.last_updated = time.time()
        
        return len(old_ids)
    
    def save_registry(self, filepath: str = None) -> bool:
        """Save the registry to a file."""
        if filepath is None:
            filepath = self.registry_file
        
        # Ensure directory exists
        registry_path = Path(filepath)
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert artifacts to dictionary format for JSON serialization
        registry_dict = {
            "version": "1.0",
            "last_updated": self.last_updated,
            "artifacts": {}
        }
        
        for artifact_id, artifact in self.artifacts.items():
            registry_dict["artifacts"][artifact_id] = {
                "id": artifact.id,
                "name": artifact.name,
                "path": artifact.path,
                "type": artifact.type.value,
                "size": artifact.size,
                "timestamp": artifact.timestamp,
                "package_name": artifact.package_name,
                "build_method": artifact.build_method,
                "config_hash": artifact.config_hash,
                "dependencies": artifact.dependencies,
                "build_system": artifact.build_system,
                "hash": artifact.hash,
                "metadata": artifact.metadata
            }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(registry_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving artifact registry: {e}")
            return False
    
    def load_registry(self, filepath: str = None) -> bool:
        """Load the registry from a file."""
        if filepath is None:
            filepath = self.registry_file
        
        if not os.path.exists(filepath):
            # Initialize with empty registry
            self.artifacts = {}
            self.last_updated = 0.0
            return True
        
        try:
            with open(filepath, 'r') as f:
                registry_dict = json.load(f)
            
            self.artifacts = {}
            self.last_updated = registry_dict.get("last_updated", 0.0)
            
            for artifact_id, artifact_data in registry_dict.get("artifacts", {}).items():
                # Reconstruct the BuildArtifact object
                artifact = BuildArtifact(
                    id=artifact_data["id"],
                    name=artifact_data["name"],
                    path=artifact_data["path"],
                    type=ArtifactType(artifact_data["type"]),
                    size=artifact_data["size"],
                    timestamp=artifact_data["timestamp"],
                    package_name=artifact_data["package_name"],
                    build_method=artifact_data["build_method"],
                    config_hash=artifact_data["config_hash"],
                    dependencies=artifact_data.get("dependencies", []),
                    build_system=artifact_data.get("build_system", "upp"),
                    hash=artifact_data.get("hash", ""),
                    metadata=artifact_data.get("metadata", {})
                )
                self.artifacts[artifact_id] = artifact
            
            return True
        except Exception as e:
            print(f"Error loading artifact registry: {e}")
            # Initialize with empty registry on error
            self.artifacts = {}
            self.last_updated = 0.0
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about the artifact registry."""
        total_size = sum(artifact.size for artifact in self.artifacts.values())
        
        stats = {
            "total_artifacts": len(self.artifacts),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "by_type": {},
            "by_package": {},
            "by_build_method": {},
            "last_updated": datetime.fromtimestamp(self.last_updated).isoformat() if self.last_updated else "never"
        }
        
        # Count by type
        for artifact in self.artifacts.values():
            type_name = artifact.type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            package_name = artifact.package_name
            stats["by_package"][package_name] = stats["by_package"].get(package_name, 0) + 1
            
            build_method = artifact.build_method
            stats["by_build_method"][build_method] = stats["by_build_method"].get(build_method, 0) + 1
        
        return stats
    
    def find_artifact_by_path(self, path: str) -> Optional[BuildArtifact]:
        """Find an artifact by its file path."""
        for artifact in self.artifacts.values():
            if artifact.path == path:
                return artifact
        return None


class ArtifactManager:
    """High-level manager for build artifacts."""
    
    def __init__(self, build_dir: str = ".maestro/build"):
        self.build_dir = Path(build_dir)
        self.registry = ArtifactRegistry(str(self.build_dir / "artifacts.json"))
        
        # Create build directory if it doesn't exist
        self.build_dir.mkdir(parents=True, exist_ok=True)
    
    def register_artifact(self, 
                         name: str, 
                         path: str, 
                         artifact_type: ArtifactType,
                         package_name: str,
                         build_method: str,
                         config_hash: str,
                         dependencies: List[str] = None,
                         build_system: str = "upp",
                         metadata: Dict[str, Any] = None) -> str:
        """Register a new build artifact."""
        # Get file size
        size = 0
        if os.path.exists(path):
            size = os.path.getsize(path)
        
        # Create artifact object
        artifact = BuildArtifact(
            id="",  # Will be generated
            name=name,
            path=path,
            type=artifact_type,
            size=size,
            timestamp=time.time(),
            package_name=package_name,
            build_method=build_method,
            config_hash=config_hash,
            dependencies=dependencies or [],
            build_system=build_system,
            metadata=metadata or {}
        )
        
        # Add to registry
        artifact_id = self.registry.add_artifact(artifact)
        
        # Save registry
        self.registry.save_registry()
        
        return artifact_id
    
    def get_artifact_output_dir(self, package_name: str, build_method: str) -> Path:
        """Get the output directory for a package with a specific build method."""
        method_dir = self.build_dir / build_method
        package_dir = method_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        return package_dir
    
    def get_artifact_objects_dir(self, package_name: str, build_method: str) -> Path:
        """Get the object files directory for a package."""
        output_dir = self.get_artifact_output_dir(package_name, build_method)
        objects_dir = output_dir / "obj"
        objects_dir.mkdir(parents=True, exist_ok=True)
        return objects_dir
    
    def get_artifact_pch_dir(self, package_name: str, build_method: str) -> Path:
        """Get the precompiled headers directory for a package."""
        output_dir = self.get_artifact_output_dir(package_name, build_method)
        pch_dir = output_dir / "pch"
        pch_dir.mkdir(parents=True, exist_ok=True)
        return pch_dir
    
    def get_artifact_deps_dir(self, package_name: str, build_method: str) -> Path:
        """Get the dependencies directory for a package."""
        output_dir = self.get_artifact_output_dir(package_name, build_method)
        deps_dir = output_dir / "deps"
        deps_dir.mkdir(parents=True, exist_ok=True)
        return deps_dir
    
    def cleanup_artifacts(self, 
                         package_name: str = None, 
                         build_method: str = None,
                         days: int = 30) -> int:
        """Clean up old artifacts."""
        removed_count = 0
        
        # Clean registry first
        if days:
            removed_count += self.registry.cleanup_old_artifacts(days)
        
        # Also remove registry entries for missing files
        removed_count += self.registry.remove_missing_artifacts()
        
        # Save cleaned registry
        self.registry.save_registry()
        
        # Optionally clean up actual build directories
        if package_name:
            # Remove specific package build directory
            for method_dir in self.build_dir.iterdir():
                if method_dir.is_dir():
                    pkg_dir = method_dir / package_name
                    if pkg_dir.exists():
                        import shutil
                        shutil.rmtree(pkg_dir)
        elif build_method:
            # Remove specific build method directory
            method_dir = self.build_dir / build_method
            if method_dir.exists():
                import shutil
                shutil.rmtree(method_dir)
        
        return removed_count
    
    def get_config_hash(self, config_data: Dict[str, Any]) -> str:
        """Generate a hash for build configuration."""
        # Convert config to a consistent string representation
        import json
        config_str = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def is_artifact_fresh(self, 
                         artifact_path: str, 
                         source_files: List[str], 
                         config_hash: str) -> bool:
        """Check if an artifact is fresh compared to sources and config."""
        if not os.path.exists(artifact_path):
            return False
        
        # Check if artifact exists in registry and config matches
        artifact = self.registry.find_artifact_by_path(artifact_path)
        if not artifact:
            return False
        
        if artifact.config_hash != config_hash:
            return False
        
        # Check if source files are newer than artifact
        artifact_time = os.path.getmtime(artifact_path)
        for source_file in source_files:
            if os.path.exists(source_file):
                source_time = os.path.getmtime(source_file)
                if source_time > artifact_time:
                    return False
        
        return True


# Global artifact manager instance
_artifact_manager = None


def get_global_artifact_manager(build_dir: str = ".maestro/build") -> ArtifactManager:
    """Get the global artifact manager instance."""
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager(build_dir)
    return _artifact_manager