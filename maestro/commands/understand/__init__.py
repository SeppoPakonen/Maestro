"""
Understand command module for Maestro CLI commands.
This is a wrapper that imports from the main understand module.
"""

from maestro.understand.command import handle_understand_dump
from maestro.understand.parser import add_understand_parser

__all__ = [
    'handle_understand_dump',
    'add_understand_parser'
]