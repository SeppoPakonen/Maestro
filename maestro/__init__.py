"""
Maestro - AI Task Management CLI

This package provides a command-line interface for managing AI task sessions.
"""

__version__ = "1.2.1"

# Import key components for easy access
from .main import main

# Define what gets imported with "from maestro import *"
__all__ = ['main', '__version__']