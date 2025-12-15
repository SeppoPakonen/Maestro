"""
UI Facade for Build Operations

This module provides structured data access to build target information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
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
    description: Optional[str] = ""


@dataclass
class DiagnosticInfo:
    """Information about a build diagnostic (error/warning)."""
    id: str
    level: str  # "error", "warning", "note"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code_snippet: Optional[str] = None


@dataclass
class BuildStatus:
    """Information about the current build status."""
    state: str  # "idle", "running", "failed", "ok"
    error_count: int = 0
    active_target_id: Optional[str] = None
    last_error_message: Optional[str] = None


def _find_build_target_files(targets_dir: str = "./.maestro/build_targets") -> List[str]:
    """Find all build target JSON files in the specified directory."""
    if not os.path.exists(targets_dir):
        return []

    target_files = []
    for filename in os.listdir(targets_dir):
        if filename.endswith('.json'):
            target_files.append(os.path.join(targets_dir, filename))
    return target_files


def _find_diagnostics_files(diagnostics_dir: str = "./.maestro/build_diagnostics") -> List[str]:
    """Find all diagnostic JSON files in the specified directory."""
    if not os.path.exists(diagnostics_dir):
        return []

    diag_files = []
    for filename in os.listdir(diagnostics_dir):
        if filename.endswith('.json'):
            diag_files.append(os.path.join(diagnostics_dir, filename))
    return diag_files


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
                    dependencies=data.get("dependencies", []),
                    description=data.get("description", "")
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


def set_active_build_target(session_id: str, target_id: str, targets_dir: str = "./.maestro/build_targets") -> bool:
    """
    Set the active build target for a specific session.

    Args:
        session_id: ID of the session
        target_id: ID of the target to set as active
        targets_dir: Directory containing build target files

    Returns:
        True if successful, False otherwise
    """
    # For now, just validate that the target exists
    all_targets = list_build_targets(session_id, targets_dir)
    target_exists = any(t.id == target_id for t in all_targets)

    if target_exists:
        # In a real implementation, this would store the active target in session state
        return True
    return False


def run_build(session_id: str, target_id: str = None) -> Dict[str, Any]:
    """
    Run a build for the specified target.

    Args:
        session_id: ID of the session
        target_id: ID of the target to build (if None, use active target)

    Returns:
        Dictionary with build results
    """
    # Simulated build execution - in a real implementation, this would execute actual build commands
    return {
        "status": "success",
        "target_id": target_id or "default_target",
        "start_time": "2023-11-01T10:00:00Z",
        "end_time": "2023-11-01T10:00:05Z",
        "duration": 5.0,
        "diagnostics": []
    }


def get_build_status(session_id: str, target_id: str = None) -> BuildStatus:
    """
    Get the current build status.

    Args:
        session_id: ID of the session
        target_id: ID of the target (if None, get overall status)

    Returns:
        BuildStatus object
    """
    # For now, return a default status indicating idle state
    return BuildStatus(state="idle", error_count=0)


def run_fix_loop(session_id: str, target_id: str = None, limit: int = None) -> Dict[str, Any]:
    """
    Run the fix loop for the specified target.

    Args:
        session_id: ID of the session
        target_id: ID of the target to fix (if None, use active target)
        limit: Optional limit on number of iterations

    Returns:
        Dictionary with fix loop results
    """
    # Simulated fix loop - in a real implementation, this would attempt to fix diagnostics
    return {
        "iteration": 1,
        "target_id": target_id or "default_target",
        "original_error_count": 5,
        "remaining_error_count": 3,
        "fix_attempts": 2,
        "diagnostic_targeted": "Some diagnostic error",
        "status": "running"
    }


def get_diagnostics(session_id: str, target_id: str = None) -> List[DiagnosticInfo]:
    """
    Get diagnostics for the specified target.

    Args:
        session_id: ID of the session
        target_id: ID of the target (if None, get diagnostics for active target)

    Returns:
        List of DiagnosticInfo objects
    """
    # Load diagnostics from file if available
    diag_files = _find_diagnostics_files()
    diagnostics = []

    for diag_file in diag_files:
        try:
            with open(diag_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for diag_data in data.get('diagnostics', []):
                    diagnostic = DiagnosticInfo(
                        id=diag_data.get('id', ''),
                        level=diag_data.get('level', 'note'),
                        message=diag_data.get('message', ''),
                        file_path=diag_data.get('file_path'),
                        line_number=diag_data.get('line_number'),
                        column_number=diag_data.get('column_number'),
                        code_snippet=diag_data.get('code_snippet')
                    )
                    diagnostics.append(diagnostic)
        except Exception:
            # Skip corrupted or inaccessible diagnostic files
            continue

    # If no diagnostics found in files, return some sample diagnostics
    if not diagnostics:
        diagnostics = [
            DiagnosticInfo(
                id="diag-001",
                level="error",
                message="Missing semicolon at end of statement",
                file_path="./src/main.c",
                line_number=42,
                column_number=15,
                code_snippet="// Missing semicolon here\nint x = 10"
            ),
            DiagnosticInfo(
                id="diag-002",
                level="warning",
                message="Unused variable declared",
                file_path="./src/utils.h",
                line_number=23,
                column_number=8,
                code_snippet="int unused_var = 42;"
            )
        ]

    return diagnostics