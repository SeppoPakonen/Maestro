"""
Java Builder Implementation

This builder implements the Java/JAR build system.
"""

from .base import Builder, Package
from .config import MethodConfig
from typing import List, Dict, Any


class JavaBuilder(Builder):
    """Java builder implementation."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("java", config)

    def build_package(self, package: Package) -> bool:
        # Implementation will be added in later phases
        raise NotImplementedError("JavaBuilder.build_package not implemented yet")

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        # Implementation will be added in later phases
        raise NotImplementedError("JavaBuilder.link not implemented yet")

    def clean_package(self, package: Package) -> bool:
        # Implementation will be added in later phases
        raise NotImplementedError("JavaBuilder.clean_package not implemented yet")

    def get_target_ext(self) -> str:
        # Implementation will be added in later phases
        raise NotImplementedError("JavaBuilder.get_target_ext not implemented yet")