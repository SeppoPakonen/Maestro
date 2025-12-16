"""
Tolerant parser for U++ IDE .var assembly configuration files.

Reads assembly definitions from ~/.config/u++/ide/*.var files
and maps them to repository paths.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any


class VarFileParser:
    """
    Parser for U++ IDE .var configuration files.

    Format example:
        UPP = "/path/to/assembly1;/path/to/assembly2";
        OUTPUT = "/path/to/output";
        INCLUDE = "";
        _all = "0";
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset parser state for a new file."""
        self.vars = {}
        self.unparsed_lines = []
        self.raw_lines = []

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a .var file and return structured data."""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        return self.parse(content)

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse .var file content and return structured data.

        Returns:
            dict with keys:
            - vars: dict of key-value pairs
            - unparsed_lines: lines we didn't recognize
            - raw_lines: all original lines
        """
        self.reset()

        lines = content.split('\n')
        self.raw_lines = lines

        for line in lines:
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                continue

            # Parse key = "value"; format
            # Pattern: KEY = "value";
            match = re.match(r'(\w+)\s*=\s*"([^"]*)"\s*;?', stripped)
            if match:
                key = match.group(1)
                value = match.group(2)
                self.vars[key] = value
            else:
                self.unparsed_lines.append(line)

        return {
            'vars': self.vars,
            'unparsed_lines': [l for l in self.unparsed_lines if l.strip()],
            'raw_lines': self.raw_lines
        }


class UppAssemblyReader:
    """
    Reader for U++ IDE assembly configurations.

    Finds and parses .var files, extracts assembly paths,
    and maps them to repository roots.
    """

    def __init__(self, ide_config_dir: Optional[str] = None):
        """
        Initialize assembly reader.

        Args:
            ide_config_dir: Path to U++ IDE config directory
                           (default: ~/.config/u++/ide)
        """
        if ide_config_dir is None:
            home = os.path.expanduser('~')
            ide_config_dir = os.path.join(home, '.config', 'u++', 'ide')

        self.ide_config_dir = ide_config_dir
        self.parser = VarFileParser()

    def read_all_assemblies(self, repo_root: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read all assembly configurations from IDE config directory.

        Args:
            repo_root: Optional repository root to filter assemblies
                      that overlap with this repository

        Returns:
            List of assembly info dicts with:
            - var_file: path to .var file
            - var_filename: basename of .var file
            - assembly_name: name extracted from filename (without .var)
            - upp_paths: list of all UPP paths from the .var file
            - existing_paths: paths that exist on filesystem
            - repo_paths: paths that are inside repo_root (if provided)
            - vars: all parsed variables
        """
        if not os.path.isdir(self.ide_config_dir):
            return []

        assemblies = []

        # Find all .var files
        var_files = sorted(Path(self.ide_config_dir).glob('*.var'))

        for var_file in var_files:
            var_file_str = str(var_file)

            try:
                parsed = self.parser.parse_file(var_file_str)
            except Exception:
                # Skip files we can't parse
                continue

            # Extract assembly name from filename
            var_filename = var_file.name
            assembly_name = var_filename.replace('.var', '')

            # Extract UPP paths (semicolon-separated)
            upp_value = parsed['vars'].get('UPP', '')
            upp_paths = [p.strip() for p in upp_value.split(';') if p.strip()]

            # Check which paths exist
            existing_paths = [p for p in upp_paths if os.path.exists(p)]

            # If repo_root provided, find paths inside it
            repo_paths = []
            if repo_root:
                repo_root_resolved = os.path.realpath(repo_root)
                for path in existing_paths:
                    path_resolved = os.path.realpath(path)
                    # Check if path is inside repo or repo is inside path
                    if self._is_path_related(path_resolved, repo_root_resolved):
                        repo_paths.append(path)

            assembly_info = {
                'var_file': var_file_str,
                'var_filename': var_filename,
                'assembly_name': assembly_name,
                'upp_paths': upp_paths,
                'existing_paths': existing_paths,
                'repo_paths': repo_paths,
                'vars': parsed['vars']
            }

            assemblies.append(assembly_info)

        return assemblies

    def _is_path_related(self, path1: str, path2: str) -> bool:
        """
        Check if two paths are related (one contains the other).

        Args:
            path1: First absolute path
            path2: Second absolute path

        Returns:
            True if one path is inside the other
        """
        # Use pathlib for proper containment check
        p1 = Path(path1)
        p2 = Path(path2)

        try:
            # Check if p1 is relative to p2 (p1 inside p2)
            p1.relative_to(p2)
            return True
        except ValueError:
            pass

        try:
            # Check if p2 is relative to p1 (p2 inside p1)
            p2.relative_to(p1)
            return True
        except ValueError:
            pass

        return False


def read_user_assemblies(repo_root: Optional[str] = None,
                         ide_config_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read U++ IDE assembly configurations and map to repository.

    Args:
        repo_root: Optional repository root to filter relevant assemblies
        ide_config_dir: Path to U++ IDE config directory
                       (default: ~/.config/u++/ide)

    Returns:
        List of assembly info dicts
    """
    reader = UppAssemblyReader(ide_config_dir)
    return reader.read_all_assemblies(repo_root)
