"""
Repository analysis and scanning utilities.
"""

from .grouping import AutoGrouper, FileGroup
from .upp_parser import parse_upp_file, parse_upp_content
from .build_systems import detect_build_system
from .dependency_resolver import kahn_topological_sort, resolve_build_order, find_dependency_cycle
