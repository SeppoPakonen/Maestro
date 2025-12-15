"""
Maestro UI Facade - Backend interface for TUI consumption

This package provides a clean API layer for the TUI to access backend data
without shelling out to the CLI or parsing text output.
"""
from . import sessions, root, plans, tasks, build, convert

__all__ = ['sessions', 'root', 'plans', 'tasks', 'build', 'convert']