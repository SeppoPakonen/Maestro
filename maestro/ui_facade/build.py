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
    categories: List[str] = None
    pipeline: Dict[str, Any] = None
    patterns: Dict[str, Any] = None
    environment: Dict[str, Any] = None
    why: Optional[str] = None
    created_at: Optional[str] = None


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
class BuildMethod:
    """Information about a build method."""
    id: str
    name: str
    builder: str  # e.g., "gcc", "msvc", "cmake", etc.
    description: str = ""
    available: bool = True

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


def _active_target_path(targets_dir: str = "./.maestro/build_targets") -> str:
    return os.path.join(targets_dir, "active_target.txt")


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
                target_id = data.get("id") or data.get("target_id") or os.path.basename(target_file).replace('.json', '')
                target_info = BuildTargetInfo(
                    id=target_id,
                    name=data.get("name", "Unknown"),
                    path=data.get("path", target_file),
                    status=data.get("status", "unknown"),
                    last_build_time=data.get("last_build_time"),
                    dependencies=data.get("dependencies", []),
                    description=data.get("description", ""),
                    categories=data.get("categories", []) or [],
                    pipeline=data.get("pipeline", {}) or {},
                    patterns=data.get("patterns", {}) or {},
                    environment=data.get("environment", {}) or {},
                    why=data.get("why"),
                    created_at=data.get("created_at"),
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

    if not all_targets:
        return None

    active_path = _active_target_path(targets_dir)
    if os.path.exists(active_path):
        try:
            with open(active_path, "r", encoding="utf-8") as handle:
                active_id = handle.read().strip()
            if active_id:
                for target in all_targets:
                    if target.id == active_id:
                        return target
        except Exception:
            pass

    # Fall back to first target if no active marker stored.
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

    if not target_exists:
        return False
    try:
        os.makedirs(targets_dir, exist_ok=True)
        with open(_active_target_path(targets_dir), "w", encoding="utf-8") as handle:
            handle.write(target_id)
    except Exception:
        return False
    return True


def run_build(session_id: str, target_id: str = None, output_callback=None, parallel_jobs: int = 4, build_type: str = "Debug", verbose: bool = False) -> Dict[str, Any]:
    """
    Run a build for the specified target.

    Args:
        session_id: ID of the session
        target_id: ID of the target to build (if None, use active target)
        output_callback: Optional callback to send build output to UI
        parallel_jobs: Number of parallel jobs to use (default: 4)
        build_type: Build type (Debug/Release) (default: Debug)
        verbose: Enable verbose output (default: False)

    Returns:
        Dictionary with build results
    """
    # Simulated build execution - in a real implementation, this would execute actual build commands
    if output_callback:
        output_callback(f"Starting build process (parallel jobs: {parallel_jobs}, build type: {build_type})...\n")
        if verbose:
            output_callback("Verbose output enabled\n")
        output_callback("Compiling source files...\n")
        output_callback("Linking libraries...\n")
        output_callback("Build completed successfully!\n")

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


def run_fix_loop(session_id: str, target_id: str = None, limit: int = None, parallel_jobs: int = 4, build_type: str = "Debug", verbose: bool = False) -> Dict[str, Any]:
    """
    Run the fix loop for the specified target.

    Args:
        session_id: ID of the session
        target_id: ID of the target to fix (if None, use active target)
        limit: Optional limit on number of iterations
        parallel_jobs: Number of parallel jobs to use (default: 4)
        build_type: Build type (Debug/Release) (default: Debug)
        verbose: Enable verbose output (default: False)

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


def list_build_methods(session_id: str) -> List[BuildMethod]:
    """
    List all available build methods.

    Args:
        session_id: ID of the session

    Returns:
        List of available build methods
    """
    # For now, return some sample build methods
    # In a real implementation, this would load from actual method configuration files
    methods = [
        BuildMethod(id="gcc-debug", name="GCC Debug", builder="gcc", description="Debug build with GCC", available=True),
        BuildMethod(id="gcc-release", name="GCC Release", builder="gcc", description="Release build with GCC", available=True),
        BuildMethod(id="clang-debug", name="Clang Debug", builder="clang", description="Debug build with Clang", available=True),
        BuildMethod(id="msvc-debug", name="MSVC Debug", builder="msvc", description="Debug build with MSVC", available=False),  # Not available on this system
        BuildMethod(id="cmake-default", name="CMake Default", builder="cmake", description="Default CMake build", available=True),
    ]

    return methods


def detect_build_methods() -> List[BuildMethod]:
    """
    Auto-detect available build methods on the system.

    Returns:
        List of detected build methods
    """
    # In a real implementation, this would scan the system for available compilers and build tools
    import platform
    import subprocess
    import shutil

    detected_methods = []

    # Check for GCC
    if shutil.which("gcc"):
        detected_methods.append(
            BuildMethod(id="gcc-auto", name="Auto-detected GCC", builder="gcc", description="Auto-detected GCC compiler", available=True)
        )

    # Check for Clang
    if shutil.which("clang"):
        detected_methods.append(
            BuildMethod(id="clang-auto", name="Auto-detected Clang", builder="clang", description="Auto-detected Clang compiler", available=True)
        )

    # Check for CMake
    if shutil.which("cmake"):
        detected_methods.append(
            BuildMethod(id="cmake-auto", name="Auto-detected CMake", builder="cmake", description="Auto-detected CMake build system", available=True)
        )

    # On Windows, check for MSVC
    if platform.system() == "Windows":
        if shutil.which("cl"):
            detected_methods.append(
                BuildMethod(id="msvc-auto", name="Auto-detected MSVC", builder="msvc", description="Auto-detected MSVC compiler", available=True)
            )

    # If no methods were detected, return some defaults that could be available
    if not detected_methods:
        detected_methods = [
            BuildMethod(id="gcc-debug", name="GCC Debug", builder="gcc", description="Debug build with GCC", available=False),
            BuildMethod(id="cmake-default", name="CMake Default", builder="cmake", description="Default CMake build", available=False),
        ]

    return detected_methods


def get_active_build_method(session_id: str) -> Optional[BuildMethod]:
    """
    Get the currently active build method for a session.

    Args:
        session_id: ID of the session

    Returns:
        Active build method or None
    """
    # In a real implementation, this would read the session's active build method
    # For now, return the first available method
    methods = list_build_methods(session_id)
    for method in methods:
        if method.available:
            return method
    return None


def set_active_build_method(session_id: str, method_id: str) -> bool:
    """
    Set the active build method for a session.

    Args:
        session_id: ID of the session
        method_id: ID of the method to set as active

    Returns:
        True if successful, False otherwise
    """
    # In a real implementation, this would store the active build method in session state
    methods = list_build_methods(session_id)
    for method in methods:
        if method.id == method_id:
            return True
    return False


def stop_build(session_id: str, target_id: str = None) -> bool:
    """
    Stop the currently running build.

    Args:
        session_id: ID of the session
        target_id: ID of the target (if None, stop active target build)

    Returns:
        True if stop was successful, False otherwise
    """
    # In a real implementation, this would signal the build process to stop
    # For now, we'll simulate the stop functionality
    return True


def get_diagnostics(session_id: str, target_id: str = None, include_samples: bool = True) -> List[DiagnosticInfo]:
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

    # If no diagnostics found in files, return some sample diagnostics if allowed.
    if not diagnostics and include_samples:
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


def list_diagnostics_sources(diagnostics_dir: str = "./.maestro/build_diagnostics") -> List[str]:
    """Return available diagnostics source paths for evidence display."""
    return _find_diagnostics_files(diagnostics_dir)
