"""
Maestro - AI Task Management CLI

This package provides a command-line interface for managing AI task sessions.
"""

__version__ = "1.2.1"


def main(*args, **kwargs):
    """Lazy import to avoid CLI startup side effects during help paths."""
    from .main import main as _main

    return _main(*args, **kwargs)


# Define what gets imported with "from maestro import *"
__all__ = ["main", "__version__"]
