"""
Repository UI facade for the TUI to interact with repository functionality.

This module provides a clean interface for the TUI to access repository-related
functionality from the CLI layer.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

from maestro.main import (
    scan_upp_repo_v2 as scan_upp_repo,
    load_repo_index,
    find_repo_root,
    RepoScanResult,
    PackageInfo,
    AssemblyInfo,
    UnknownPath,
    InternalPackage
)


@dataclass
class RepoPackageInfo:
    """Information about a detected repository package for TUI."""
    name: str
    dir: str
    upp_path: str
    files: List[str] = field(default_factory=list)
    upp: Optional[Dict[str, Any]] = None
    type: str = "upp"  # "upp" or "internal"


@dataclass
class RepoAssemblyInfo:
    """Information about a detected repository assembly for TUI."""
    name: str
    root_path: str
    package_folders: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class RepoScanSummary:
    """Summary of a repository scan for TUI display."""
    path: str
    packages_found: int
    assemblies_found: int
    unknown_paths: int
    internal_packages: int
    scanned_at: str
    status: str = "completed"  # "completed", "failed", "in_progress"


@dataclass
class RepoScanDetails:
    """Detailed results of a repository scan for TUI."""
    path: str
    assemblies_detected: List[RepoAssemblyInfo] = field(default_factory=list)
    packages_detected: List[RepoPackageInfo] = field(default_factory=list)
    unknown_paths: List[UnknownPath] = field(default_factory=list)
    user_assemblies: List[Dict[str, Any]] = field(default_factory=list)
    internal_packages: List[InternalPackage] = field(default_factory=list)
    scan_time: Optional[str] = None


def resolve_repository(path: Optional[str] = None, include_user_config: bool = True, 
                      no_write: bool = False, verbose: bool = False) -> RepoScanSummary:
    """
    Scan a U++ repository for packages, assemblies, and internal packages.
    
    Args:
        path: Path to repository to scan (default: auto-detect)
        include_user_config: Whether to include user assemblies from ~/.config/u++/ide/*.var
        no_write: Skip writing artifacts to .maestro/repo/
        verbose: Show verbose scan information
    
    Returns:
        RepoScanSummary with scan results
    """
    from datetime import datetime
    
    # Use the CLI's scan_upp_repo function
    try:
        scan_path = path or find_repo_root()
        if not scan_path:
            raise ValueError("Could not find repository root")
        
        # Call the underlying scan functionality
        result = scan_upp_repo(
            scan_path,
            verbose=verbose,
            include_user_config=include_user_config
        )
        
        summary = RepoScanSummary(
            path=scan_path,
            packages_found=len(result.packages_detected),
            assemblies_found=len(result.assemblies_detected),
            unknown_paths=len(result.unknown_paths),
            internal_packages=len(result.internal_packages),
            scanned_at=datetime.now().isoformat(),
            status="completed"
        )
        
        return summary
        
    except Exception as e:
        return RepoScanSummary(
            path=path or "",
            packages_found=0,
            assemblies_found=0,
            unknown_paths=0,
            internal_packages=0,
            scanned_at=datetime.now().isoformat(),
            status="failed"
        )


def get_repo_scan_results(path: Optional[str] = None) -> Optional[RepoScanDetails]:
    """
    Get repository scan results from .maestro/repo/ for display in TUI.
    
    Args:
        path: Path to repository root (default: auto-detect)
    
    Returns:
        RepoScanDetails with detailed scan results
    """
    from datetime import datetime
    
    try:
        repo_path = path or find_repo_root()
        if not repo_path:
            raise ValueError("Could not find repository root")
        
        # Load existing scan artifacts
        scan_result = scan_upp_repo(repo_path, verbose=False)
        
        # Convert from internal dataclasses to TUI dataclasses
        assembly_infos = []
        for asm in scan_result.assemblies_detected:
            assembly_infos.append(RepoAssemblyInfo(
                name=asm.name,
                root_path=asm.root_path,
                package_folders=asm.package_folders,
                evidence_refs=asm.evidence_refs
            ))
        
        package_infos = []
        for pkg in scan_result.packages_detected:
            package_infos.append(RepoPackageInfo(
                name=pkg.name,
                dir=pkg.dir,
                upp_path=pkg.upp_path,
                files=pkg.files,
                upp=pkg.upp,
                type="upp"
            ))
        
        # Add internal packages as special package type
        for internal_pkg in scan_result.internal_packages:
            package_infos.append(RepoPackageInfo(
                name=internal_pkg.name,
                dir=internal_pkg.root_path,
                upp_path="",
                files=internal_pkg.members,
                upp=None,
                type="internal"
            ))
        
        details = RepoScanDetails(
            path=repo_path,
            assemblies_detected=assembly_infos,
            packages_detected=package_infos,
            unknown_paths=scan_result.unknown_paths,
            user_assemblies=scan_result.user_assemblies,
            internal_packages=scan_result.internal_packages,
            scan_time=datetime.now().isoformat()
        )
        
        return details
        
    except Exception as e:
        # If scanning fails, try to load existing index
        try:
            repo_path = path or find_repo_root()
            if repo_path:
                index_data = load_repo_index(repo_path)
                # Create basic details from index data
                details = RepoScanDetails(
                    path=repo_path,
                    assemblies_detected=[],
                    packages_detected=[],
                    unknown_paths=[],
                    user_assemblies=[],
                    internal_packages=[],
                    scan_time=datetime.now().isoformat()
                )
                return details
        except:
            pass
        return None


def list_repo_packages(path: Optional[str] = None) -> List[RepoPackageInfo]:
    """
    List packages detected in the repository.
    
    Args:
        path: Path to repository root (default: auto-detect)
    
    Returns:
        List of RepoPackageInfo
    """
    details = get_repo_scan_results(path)
    if details:
        return details.packages_detected
    return []


def get_repo_package_info(package_name: str, path: Optional[str] = None) -> Optional[RepoPackageInfo]:
    """
    Get detailed information about a specific package.
    
    Args:
        package_name: Name of package to look up
        path: Path to repository root (default: auto-detect)
    
    Returns:
        RepoPackageInfo or None if not found
    """
    packages = list_repo_packages(path)
    
    # Try exact match first
    for pkg in packages:
        if pkg.name.lower() == package_name.lower():
            return pkg
    
    # Try partial match
    for pkg in packages:
        if package_name.lower() in pkg.name.lower():
            return pkg
    
    return None


def search_repo_packages(query: str, path: Optional[str] = None) -> List[RepoPackageInfo]:
    """
    Search for packages by name or other criteria.
    
    Args:
        query: Search query string
        path: Path to repository root (default: auto-detect)
    
    Returns:
        List of matching RepoPackageInfo
    """
    packages = list_repo_packages(path)
    results = []
    
    query_lower = query.lower()
    for pkg in packages:
        if (query_lower in pkg.name.lower() or 
            any(query_lower in f.lower() for f in pkg.files) or
            (pkg.upp_path and query_lower in pkg.upp_path.lower())):
            results.append(pkg)
    
    return results


def get_repo_assemblies(path: Optional[str] = None) -> List[RepoAssemblyInfo]:
    """
    Get assemblies detected in the repository.
    
    Args:
        path: Path to repository root (default: auto-detect)
    
    Returns:
        List of RepoAssemblyInfo
    """
    details = get_repo_scan_results(path)
    if details:
        return details.assemblies_detected
    return []


def find_repo_root_from_path(start_path: str = ".") -> Optional[str]:
    """
    Find the repository root starting from a given path.
    
    Args:
        start_path: Path to start searching from (default: current directory)
    
    Returns:
        Path to repository root or None if not found
    """
    return find_repo_root(start_path)


# Additional helper functions for TUI display
def get_unknown_path_summary(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get summary information about unknown paths in the repository.
    
    Args:
        path: Path to repository root (default: auto-detect)
    
    Returns:
        Dictionary with summary information
    """
    details = get_repo_scan_results(path)
    if not details:
        return {
            "total_unknown": 0,
            "by_type": {},
            "examples": []
        }
    
    by_type = {}
    for unknown_path in details.unknown_paths:
        if unknown_path.type not in by_type:
            by_type[unknown_path.type] = 0
        by_type[unknown_path.type] += 1
    
    return {
        "total_unknown": len(details.unknown_paths),
        "by_type": by_type,
        "examples": [str(unknown_path.path) for unknown_path in details.unknown_paths[:5]]  # First 5 as examples
    }