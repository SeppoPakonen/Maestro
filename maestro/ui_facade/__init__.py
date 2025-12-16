"""
Maestro UI Facade - Backend interface for TUI consumption

This package provides a clean API layer for the TUI to access backend data
without shelling out to the CLI or parsing text output.
"""

import importlib
from typing import Any

__all__ = [
    "sessions",
    "root",
    "plans",
    "tasks",
    "build",
    "convert",
    "semantic",
    "decisions",
    "arbitration",
    "confidence",
    "vault",
    "runs",
    "batch",
    "repo",
]


def __getattr__(name: str) -> Any:
    """Lazily import facade modules to avoid heavy side effects at import time."""
    if name in __all__:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
