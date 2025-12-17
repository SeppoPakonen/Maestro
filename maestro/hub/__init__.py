"""
MaestroHub - Universal package hub system for automatic dependency resolution
across all build systems (U++, CMake, Autotools, Maven, Visual Studio).
"""

# Export key classes and functions
from .client import MaestroHub
from .resolver import HubResolver

__all__ = ['MaestroHub', 'HubResolver']