from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..builders.config import MethodConfig


class Package:
    """Class representing a package to be built."""

    def __init__(self, name: str, path: str, metadata: Dict[str, Any] = None):
        self.name = name
        self.path = path
        self.metadata = metadata or {}
        self.dependencies = []
        self.files = []
        self.config = {}


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