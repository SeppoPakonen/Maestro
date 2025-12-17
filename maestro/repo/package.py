"""
Package dataclasses for Maestro repository scanning.

This module contains dataclasses that are used across different modules
to avoid circular import issues.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class FileGroup:
    """Internal package file group."""
    name: str                    # Group name/title
    files: List[str]             # Files in this group
    readonly: bool = False       # From separator flags
    auto_generated: bool = False # True if auto-grouped


@dataclass
class PackageInfo:
    """Information about a detected package (U++, CMake, Make, etc.)."""
    name: str
    dir: str
    upp_path: str
    files: List[str] = field(default_factory=list)
    upp: Optional[Dict[str, Any]] = None  # Parsed .upp metadata
    build_system: str = 'upp'  # 'upp', 'cmake', 'make', 'autoconf', 'gradle', 'maven'
    dependencies: List[str] = field(default_factory=list)  # Project dependencies
    groups: List[FileGroup] = field(default_factory=list)  # Internal package groups
    ungrouped_files: List[str] = field(default_factory=list)  # Files not in any group