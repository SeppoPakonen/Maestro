"""
Repository analysis and scanning utilities.
"""

from .grouping import AutoGrouper, FileGroup
from .upp_parser import parse_upp_file, parse_upp_content
from .build_systems import detect_build_system
