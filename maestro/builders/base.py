from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
from ..builders.config import MethodConfig, BuildConfig


class Package:
    """Class representing a package to be built."""

    def __init__(
        self,
        name: str,
        directory: str = "",
        path: Optional[str] = None,
        build_system: str = "upp",
        source_files: List[str] = None,
        dependencies: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.name = name
        # Accept legacy 'path' while preferring explicit 'directory' when provided.
        self.directory = directory if directory != "" else (path if path is not None else "")
        # Maintain backward-compatible attribute names
        self.path = self.directory
        self.dir = self.directory
        self.build_system = build_system
        self.source_files = source_files or []
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
        self.config = {}
        self.groups = []  # Will store file groups
        self.ungrouped_files = []  # Will store ungrouped files


class Builder(ABC):
    """Abstract base class for all builders following the U++ Builder pattern."""

    def __init__(self, name: str, config: MethodConfig = None):
        self.name = name
        self.config = config or MethodConfig(name="default", builder="unknown")

    @abstractmethod
    def build_package(self, package: Package) -> bool:
        """Build a single package.

        Args:
            package: Package to build

        Returns:
            True if build succeeded, False otherwise
        """
        pass

    @abstractmethod
    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """Link final executable/library.

        Args:
            linkfiles: List of files to link
            linkoptions: Linker options

        Returns:
            True if linking succeeded, False otherwise
        """
        pass

    @abstractmethod
    def clean_package(self, package: Package) -> bool:
        """Clean package build artifacts.

        Args:
            package: Package to clean

        Returns:
            True if clean succeeded, False otherwise
        """
        pass

    @abstractmethod
    def get_target_ext(self) -> str:
        """Return target file extension (.exe, .so, .a, etc)."""
        pass

    def preprocess(self, package: Package) -> bool:
        """Preprocess package files before building (optional).

        Args:
            package: Package to preprocess

        Returns:
            True if preprocessing succeeded, False otherwise
        """
        # Default implementation does nothing
        return True

    def configure(self, package: Package) -> bool:
        """Configure package build settings (optional).

        Args:
            package: Package to configure

        Returns:
            True if configuration succeeded, False otherwise
        """
        # Default implementation does nothing
        return True

    def update_config(self, config: MethodConfig):
        """Update the builder configuration.

        Args:
            config: New build method configuration
        """
        self.config = config

    def get_executable_path(self, package: Package, method_config: MethodConfig) -> Optional[str]:
        """Find the executable for this package after a successful build.

        Args:
            package: Package to find executable for
            method_config: Build method configuration used for the build

        Returns:
            Path to executable, or None if not found or not applicable

        Note:
            Default implementation searches common output locations.
            Builders can override for build-system-specific logic.
        """
        # Default implementation: check target_dir for executable
        target_dir = getattr(method_config.config, 'target_dir', None)
        if not target_dir:
            return None

        # Common executable names
        pkg_name = package.name
        from ..builders.config import OSFamily
        ext = ".exe" if method_config.platform.os == OSFamily.WINDOWS else ""
        candidates = [
            os.path.join(target_dir, pkg_name + ext),
            os.path.join(target_dir, pkg_name),
        ]

        for candidate in candidates:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate

        return None
