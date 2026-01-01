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
    is_virtual: bool = False  # True if this is a virtual package (e.g., docs, tests, scripts)
    virtual_type: Optional[str] = None  # Type of virtual package: 'docs', 'tests', 'scripts', etc.
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata for the package

    def to_builder_package(self):
        """
        Convert this PackageInfo to a format suitable for builder consumption.

        Returns:
            A dictionary with package information formatted for builder usage.
        """
        from maestro.builders.base import Package as BuilderPackage

        # Create the builder package with essential information
        builder_package = BuilderPackage(
            name=self.name,
            directory=self.dir,
            build_system=self.build_system,
            source_files=self.files,
            dependencies=self.dependencies
        )

        # Add additional metadata based on build system type
        if self.upp:
            builder_package.metadata = self.upp

        # Add file groups information
        builder_package.groups = [
            {
                'name': group.name,
                'files': group.files,
                'readonly': group.readonly,
                'auto_generated': group.auto_generated
            } for group in self.groups
        ]

        builder_package.ungrouped_files = self.ungrouped_files

        # Add virtual package information
        builder_package.is_virtual = self.is_virtual
        builder_package.virtual_type = self.virtual_type

        # Add metadata
        if self.metadata:
            if hasattr(builder_package, 'metadata') and builder_package.metadata:
                builder_package.metadata.update(self.metadata)
            else:
                builder_package.metadata = self.metadata

        return builder_package