"""
Build cache management for incremental builds.

Implements caching mechanisms similar to U++'s build cache and PPInfo
for tracking file dependencies and avoiding unnecessary rebuilds.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class BuildCache:
    """
    Manages build cache for incremental builds and dependency tracking.
    
    Similar to U++'s caching mechanisms, this stores file timestamps,
    dependencies, and build artifacts to avoid unnecessary rebuilds.
    """
    
    def __init__(self, cache_dir: str = ".maestro/build/cache"):
        self.cache_dir = Path(cache_dir)
        self.deps_file = self.cache_dir / "dependencies.json"
        self.artifacts_file = self.cache_dir / "artifacts.json"
        self.methods_file = self.cache_dir / "methods.json"
        
        # Load existing cache data
        self.dependencies: Dict[str, Dict[str, Any]] = self._load_json_file(self.deps_file, {})
        self.artifacts: Dict[str, Dict[str, Any]] = self._load_json_file(self.artifacts_file, {})
        self.methods: Dict[str, Dict[str, Any]] = self._load_json_file(self.methods_file, {})
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_json_file(self, file_path: Path, default_value: Any) -> Any:
        """Load JSON data from file, returning default if file doesn't exist."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not load cache file {file_path}: {e}")
        return default_value
    
    def _save_json_file(self, file_path: Path, data: Any):
        """Save JSON data to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[ERROR] Could not save cache file {file_path}: {e}")
    
    def save(self):
        """Save all cache data to disk."""
        self._save_json_file(self.deps_file, self.dependencies)
        self._save_json_file(self.artifacts_file, self.artifacts)
        self._save_json_file(self.methods_file, self.methods)
    
    def track_file_dependencies(self, source_file: str, dependencies: List[str], 
                               build_method: str, extra_info: Dict[str, Any] = None):
        """
        Track dependencies for a source file.
        
        Args:
            source_file: Path to the source file
            dependencies: List of files this source file depends on
            build_method: Build method used to compile this file
            extra_info: Additional metadata about the build
        """
        mtime = os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        
        self.dependencies[source_file] = {
            'mtime': mtime,
            'dependencies': dependencies,
            'method': build_method,
            'extra': extra_info or {},
            'timestamp': datetime.now().isoformat()
        }
    
    def get_file_dependencies(self, source_file: str) -> Optional[Dict[str, Any]]:
        """Get stored dependency information for a file."""
        return self.dependencies.get(source_file)
    
    def needs_rebuild(self, source_file: str) -> bool:
        """
        Check if a source file needs to be rebuilt.
        
        Returns True if the source file or any of its dependencies
        have been modified since the last build.
        """
        if source_file not in self.dependencies:
            return True  # File not in cache, needs rebuild
        
        cached_info = self.dependencies[source_file]
        current_mtime = os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        
        # Check if source file itself was modified
        if current_mtime != cached_info.get('mtime', 0):
            return True
        
        # Check if any dependencies were modified
        for dep_path in cached_info.get('dependencies', []):
            if os.path.exists(dep_path):
                dep_mtime = os.path.getmtime(dep_path)
                # If this dependency is also tracked, use its cached time
                if dep_path in self.dependencies:
                    cached_dep_mtime = self.dependencies[dep_path].get('mtime', 0)
                    if dep_mtime != cached_dep_mtime:
                        return True
                else:
                    # If dependency is newer than source file, rebuild
                    if dep_mtime > current_mtime:
                        return True
        
        return False
    
    def store_artifact(self, artifact_path: str, source_files: List[str], 
                      build_method: str, extra_info: Dict[str, Any] = None):
        """
        Store information about a built artifact.
        
        Args:
            artifact_path: Path to the built artifact (executable, library, etc.)
            source_files: List of source files used to create this artifact
            build_method: Build method used
            extra_info: Additional build metadata
        """
        mtime = os.path.getmtime(artifact_path) if os.path.exists(artifact_path) else 0
        
        self.artifacts[artifact_path] = {
            'mtime': mtime,
            'sources': source_files,
            'method': build_method,
            'extra': extra_info or {},
            'timestamp': datetime.now().isoformat()
        }
    
    def get_artifact_info(self, artifact_path: str) -> Optional[Dict[str, Any]]:
        """Get stored information about an artifact."""
        return self.artifacts.get(artifact_path)
    
    def is_artifact_valid(self, artifact_path: str, source_files: List[str]) -> bool:
        """
        Check if an artifact is still valid (doesn't need rebuild).
        
        Args:
            artifact_path: Path to the artifact
            source_files: List of source files that should have been used to create it
            
        Returns:
            True if artifact is valid, False if it needs rebuild
        """
        if artifact_path not in self.artifacts:
            return False  # Artifact not in cache
        
        artifact_info = self.artifacts[artifact_path]
        
        # Check if artifact file exists and is newer than all source files
        if not os.path.exists(artifact_path):
            return False
        
        artifact_mtime = os.path.getmtime(artifact_path)
        
        # Check if any source file is newer than the artifact
        for source in source_files:
            if os.path.exists(source):
                source_mtime = os.path.getmtime(source)
                if source_mtime > artifact_mtime:
                    return False
        
        return True
    
    def invalidate_artifact(self, artifact_path: str):
        """Remove an artifact from the cache (mark as invalid)."""
        if artifact_path in self.artifacts:
            del self.artifacts[artifact_path]
    
    def cleanup_old_artifacts(self, preserve_recent: int = 5):
        """
        Clean up old artifacts to save disk space.
        
        Args:
            preserve_recent: Number of recent artifact versions to keep
        """
        # Group artifacts by name to identify versions
        artifact_groups: Dict[str, List[tuple]] = {}
        
        for path, info in self.artifacts.items():
            artifact_name = os.path.basename(path)
            if artifact_name not in artifact_groups:
                artifact_groups[artifact_name] = []
            artifact_groups[artifact_name].append((path, info.get('timestamp', '')))
        
        # For each group, keep only the most recent artifacts
        for name, artifacts in artifact_groups.items():
            # Sort by timestamp (newest first)
            sorted_artifacts = sorted(artifacts, key=lambda x: x[1], reverse=True)
            
            # Mark older ones for removal
            for path, _ in sorted_artifacts[preserve_recent:]:
                if path in self.artifacts:
                    del self.artifacts[path]
    
    def get_cache_size(self) -> int:
        """Get total size of cache in bytes."""
        total_size = 0
        for file_path in [self.deps_file, self.artifacts_file, self.methods_file]:
            if file_path.exists():
                total_size += file_path.stat().st_size
        return total_size


class PPInfoCache:
    """
    Specialized cache for preprocessor dependency information.
    
    Similar to U++'s PPInfo system, tracks header dependencies and
    conditional compilation flags.
    """
    
    def __init__(self, cache_dir: str = ".maestro/build/cache/ppinfo"):
        self.cache_dir = Path(cache_dir)
        self.ppinfo_file = self.cache_dir / "ppinfo.json"
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing PPInfo cache
        self.ppinfo: Dict[str, Dict[str, Any]] = self._load_json_file(self.ppinfo_file, {})
    
    def _load_json_file(self, file_path: Path, default_value: Any) -> Any:
        """Load JSON data from file, returning default if file doesn't exist."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not load PPInfo cache file {file_path}: {e}")
        return default_value
    
    def _save_json_file(self, file_path: Path, data: Any):
        """Save JSON data to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[ERROR] Could not save PPInfo cache file {file_path}: {e}")
    
    def save(self):
        """Save PPInfo cache to disk."""
        self._save_json_file(self.ppinfo_file, self.ppinfo)
    
    def track_preprocessor_info(self, source_file: str, includes: List[str], 
                               defines: List[str], flags: List[str]):
        """
        Track preprocessor information for a source file.
        
        Args:
            source_file: Path to the source file
            includes: List of included headers
            defines: List of preprocessor defines
            flags: List of compiler flags that affect preprocessing
        """
        mtime = os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        
        # Calculate a hash of the defines and flags to detect changes
        defines_hash = hashlib.md5(str(sorted(defines)).encode()).hexdigest()
        flags_hash = hashlib.md5(str(sorted(flags)).encode()).hexdigest()
        
        self.ppinfo[source_file] = {
            'mtime': mtime,
            'includes': includes,
            'defines': defines,
            'flags': flags,
            'defines_hash': defines_hash,
            'flags_hash': flags_hash,
            'timestamp': datetime.now().isoformat()
        }
    
    def needs_preprocess_rerun(self, source_file: str, current_defines: List[str], 
                              current_flags: List[str]) -> bool:
        """
        Check if preprocessing needs to be rerun for this file.
        
        Args:
            source_file: Path to the source file
            current_defines: Current list of preprocessor defines
            current_flags: Current list of compiler flags
            
        Returns:
            True if preprocessing needs to rerun, False otherwise
        """
        if source_file not in self.ppinfo:
            return True  # No cached info, needs preprocessing
        
        cached = self.ppinfo[source_file]
        
        # Check if source file was modified
        current_mtime = os.path.getmtime(source_file) if os.path.exists(source_file) else 0
        if current_mtime != cached.get('mtime', 0):
            return True
        
        # Check if defines changed
        current_defines_hash = hashlib.md5(str(sorted(current_defines)).encode()).hexdigest()
        if current_defines_hash != cached.get('defines_hash'):
            return True
        
        # Check if flags changed
        current_flags_hash = hashlib.md5(str(sorted(current_flags)).encode()).hexdigest()
        if current_flags_hash != cached.get('flags_hash'):
            return True
        
        return False
    
    def get_includes_for_file(self, source_file: str) -> List[str]:
        """Get the list of includes for a source file."""
        info = self.ppinfo.get(source_file)
        return info.get('includes', []) if info else []


class IncrementalBuilder:
    """
    Helper class that coordinates incremental builds using the cache.
    """
    
    def __init__(self, cache: BuildCache):
        self.cache = cache
    
    def should_build_file(self, source_file: str, dependencies: List[str], 
                         build_method: str) -> bool:
        """
        Determine if a source file should be built.
        
        Args:
            source_file: Path to the source file
            dependencies: List of files the source depends on
            build_method: Build method being used
            
        Returns:
            True if file should be built, False if it's up-to-date
        """
        # Check if file needs rebuild based on dependencies
        if self.cache.needs_rebuild(source_file):
            # Track dependencies for future checks
            self.cache.track_file_dependencies(source_file, dependencies, build_method)
            return True
        
        # Update dependency tracking even if no rebuild needed
        self.cache.track_file_dependencies(source_file, dependencies, build_method)
        return False