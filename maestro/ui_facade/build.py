"""
UI Facade for Build Operations

This module provides structured data access to build target information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os


@dataclass
class BuildTargetInfo:
    """Information about a build target."""
    id: str
    name: str
    path: str
    status: str  # e.g., "built", "pending", "failed", "unknown"
    last_build_time: Optional[str]
    dependencies: List[str]


def _find_build_target_files(targets_dir: str = "./.maestro/build_targets") -> List[str]:
    """Find all build target JSON files in the specified directory."""
    if not os.path.exists(targets_dir):
        return []
    
    target_files = []
    for filename in os.listdir(targets_dir):
        if filename.endswith('.json'):
            target_files.append(os.path.join(targets_dir, filename))
    return target_files


def list_build_targets(session_id: str, targets_dir: str = "./.maestro/build_targets") -> List[BuildTargetInfo]:
    """
    List all build targets for a specific session.
    
    Args:
        session_id: ID of the session to get build targets for
        targets_dir: Directory containing build target files
        
    Returns:
        List of build target information
    """
    target_files = _find_build_target_files(targets_dir)
    targets_info = []
    
    for target_file in target_files:
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filter targets by session if needed, though exact implementation depends on data structure
                target_info = BuildTargetInfo(
                    id=data.get("id", os.path.basename(target_file).replace('.json', '')),
                    name=data.get("name", "Unknown"),
                    path=data.get("path", target_file),
                    status=data.get("status", "unknown"),
                    last_build_time=data.get("last_build_time"),
                    dependencies=data.get("dependencies", [])
                )
                targets_info.append(target_info)
        except Exception:
            # Skip corrupted or inaccessible target files
            continue
    
    return targets_info


def get_active_build_target(session_id: str, targets_dir: str = "./.maestro/build_targets") -> Optional[BuildTargetInfo]:
    """
    Get the active build target for a specific session.
    
    Args:
        session_id: ID of the session
        targets_dir: Directory containing build target files
        
    Returns:
        Information about the active build target or None
    """
    all_targets = list_build_targets(session_id, targets_dir)
    
    # For now, return the first target as "active" - in a real implementation,
    # this would identify the target that's currently being built or most recently built
    if all_targets:
        return all_targets[0]
    
    return None