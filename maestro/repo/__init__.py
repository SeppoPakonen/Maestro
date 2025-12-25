"""
Repository analysis and scanning utilities.
"""

from .grouping import AutoGrouper, FileGroup
from .upp_parser import parse_upp_file, parse_upp_content
from .build_systems import detect_build_system
from .dependency_resolver import kahn_topological_sort, resolve_build_order, find_dependency_cycle
from .scanner import scan_upp_repo_v2, AssemblyInfo, RepoScanResult, UnknownPath, InternalPackage

__all__ = [
    'AutoGrouper',
    'FileGroup',
    'parse_upp_file',
    'parse_upp_content',
    'detect_build_system',
    'kahn_topological_sort',
    'resolve_build_order',
    'find_dependency_cycle',
    'scan_upp_repo_v2',
    'AssemblyInfo',
    'RepoScanResult',
    'UnknownPath',
    'InternalPackage',
]
