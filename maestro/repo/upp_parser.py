"""
Tolerant parser for U++ .upp package files.

Extracts structured metadata from .upp files without requiring perfect syntax.
Preserves raw content while extracting known directives.
"""

import re
from typing import Dict, List, Any, Optional


class UppParser:
    """
    Tolerant parser for U++ .upp package descriptor files.

    Parses directives like:
    - description "text\377B<r>,<g>,<b>"
    - uses package1, package2;
    - file "file.cpp" options(...), "file.h";
    - mainconfig "KEY" = "value";
    - acceptflags FLAG1, FLAG2;
    - library(...) "libs";
    - etc.

    The parser is tolerant and preserves unparsed content.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset parser state for a new file."""
        self.description = ""
        self.uses = []
        self.files = []
        self.mainconfigs = []
        self.acceptflags = []
        self.libraries = []
        self.static_libraries = []
        self.links = []
        self.unparsed_lines = []
        self.raw_lines = []

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a .upp file and return structured data."""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        return self.parse(content)

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse .upp content and return structured data.

        Returns:
            dict with keys:
            - raw_description: original description string with color codes
            - description_text: description without color codes
            - description_color: RGB tuple if present
            - uses: list of package dependencies
            - files: list of dicts with {path, options, readonly, separator, highlight, charset}
            - mainconfigs: list of dicts with {name, param} (name can be empty string)
            - acceptflags: list of flag names
            - libraries: list of dicts with {condition, libs}
            - static_libraries: list of dicts with {condition, libs}
            - links: list of dicts with {condition, flags}
            - unparsed_lines: lines we didn't recognize
            - raw_lines: all original lines
        """
        self.reset()

        lines = content.split('\n')
        self.raw_lines = lines

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('//'):
                i += 1
                continue

            # Parse multi-line blocks
            if stripped.startswith('description'):
                i = self._parse_description(lines, i)
            elif stripped.startswith('uses') or stripped.startswith('uses('):
                i = self._parse_uses(lines, i)
            elif stripped.startswith('file'):
                i = self._parse_files(lines, i)
            elif stripped.startswith('mainconfig'):
                i = self._parse_mainconfig(lines, i)
            elif stripped.startswith('acceptflags'):
                i = self._parse_acceptflags(lines, i)
            elif stripped.startswith('library(') or stripped.startswith('library('):
                i = self._parse_library(lines, i)
            elif stripped.startswith('static_library('):
                i = self._parse_static_library(lines, i)
            elif stripped.startswith('link('):
                i = self._parse_link(lines, i)
            else:
                # Unknown directive - preserve it
                self.unparsed_lines.append(line)
                i += 1

        # Extract description components
        desc_text, desc_color = self._extract_description_parts(self.description)

        return {
            'raw_description': self.description,
            'description_text': desc_text,
            'description_color': desc_color,
            'uses': self.uses,
            'files': self.files,
            'mainconfigs': self.mainconfigs,
            'acceptflags': self.acceptflags,
            'libraries': self.libraries,
            'static_libraries': self.static_libraries,
            'links': self.links,
            'unparsed_lines': [l for l in self.unparsed_lines if l.strip()],
            'raw_lines': self.raw_lines
        }

    def _parse_description(self, lines: List[str], start_idx: int) -> int:
        """Parse description directive."""
        line = lines[start_idx].strip()

        # Match: description "text\377B<r>,<g>,<b>";
        match = re.match(r'description\s+"([^"]*)"', line)
        if match:
            self.description = match.group(1)
            return start_idx + 1

        self.unparsed_lines.append(lines[start_idx])
        return start_idx + 1

    def _parse_uses(self, lines: List[str], start_idx: int) -> int:
        """Parse uses directive (can be single line or multi-line)."""
        # Accumulate until we find semicolon
        accumulated = ""
        i = start_idx

        while i < len(lines):
            line = lines[i].strip()
            accumulated += " " + line

            if ';' in line:
                break
            i += 1

        # Extract package names - they can be quoted or unquoted
        content = accumulated.replace('uses', '').replace(';', '').strip()

        # Check for conditional uses: uses(CONDITION) package;
        conditional_match = re.match(r'\(([^)]+)\)\s+(.+)', content)
        if conditional_match:
            condition = conditional_match.group(1).strip()
            packages_part = conditional_match.group(2).strip()

            # Parse packages from the conditional part
            for pkg in self._extract_package_names(packages_part):
                self.uses.append({'package': pkg, 'condition': condition})
        else:
            # No condition - parse normally
            # First, extract all quoted strings
            quoted_packages = re.findall(r'"([^"]+)"', content)
            for pkg in quoted_packages:
                self.uses.append({'package': pkg, 'condition': None})

            # Remove quoted strings to process unquoted identifiers
            content_no_quotes = re.sub(r'"[^"]*"', '', content)

            # Extract unquoted package names
            for pkg in self._extract_package_names(content_no_quotes):
                self.uses.append({'package': pkg, 'condition': None})

        return i + 1

    def _extract_package_names(self, text: str) -> List[str]:
        """Extract package names from text, handling paths and identifiers."""
        packages = []
        for token in re.split(r'[,\s]+', text):
            token = token.strip()
            # Skip empty, operators, and platform flags
            if token and token not in ('', '|', '&', '!', '(', ')') and not token.isupper():
                # Handle qualified paths like plugin\z
                if '\\' in token:
                    token = token.replace('\\', '/')
                packages.append(token)
        return packages

    def _parse_files(self, lines: List[str], start_idx: int) -> int:
        """Parse file directive (can be single-line or multi-line block)."""
        i = start_idx
        line = lines[i].strip()

        # Check if it's single-line: file "a.cpp", "b.h";
        if ';' in line:
            # Single-line format - extract all quoted filenames
            filenames = re.findall(r'"([^"]+)"', line)
            for fname in filenames:
                self.files.append({'path': fname, 'options': None, 'readonly': False,
                                   'separator': False, 'highlight': None, 'charset': None})
            return i + 1

        # Multi-line format
        i += 1  # Skip 'file' keyword line

        while i < len(lines):
            line = lines[i].strip()

            # End of file block
            if not line or line == ';':
                break

            # Parse individual file entry
            # Pattern: "file.cpp" options(...), highlight cpp, readonly separator, charset "UTF-8",
            file_entry = self._parse_file_entry(line)
            if file_entry:
                self.files.append(file_entry)

            if ';' in line:
                break
            i += 1

        return i + 1

    def _parse_file_entry(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single file entry."""
        entry = {
            'path': '',
            'options': None,
            'readonly': False,
            'separator': False,
            'highlight': None,
            'charset': None
        }

        # Extract quoted filename
        match = re.match(r'^"([^"]+)"', line)
        if match:
            entry['path'] = match.group(1)
        else:
            # Unquoted identifier (like separator names)
            match = re.match(r'^([^\s,;]+)', line)
            if match:
                entry['path'] = match.group(1)
            else:
                return None

        # Parse modifiers
        if 'options(' in line:
            # Extract options content
            match = re.search(r'options\(([^)]+)\)', line)
            if match:
                entry['options'] = match.group(1)

        if 'readonly' in line:
            entry['readonly'] = True

        if 'separator' in line:
            entry['separator'] = True

        if 'highlight' in line:
            match = re.search(r'highlight\s+(\w+)', line)
            if match:
                entry['highlight'] = match.group(1)

        if 'charset' in line:
            match = re.search(r'charset\s+"([^"]+)"', line)
            if match:
                entry['charset'] = match.group(1)

        return entry

    def _parse_mainconfig(self, lines: List[str], start_idx: int) -> int:
        """Parse mainconfig directive."""
        i = start_idx

        # Can be single line or multi-line block
        accumulated = ""
        while i < len(lines):
            line = lines[i].strip()
            accumulated += " " + line

            if ';' in line:
                break
            i += 1

        # Pattern: mainconfig "KEY" = "value"; (KEY can be empty string "")
        # Allow empty strings in both key and value
        for match in re.finditer(r'"([^"]*)"\s*=\s*"([^"]*)"', accumulated):
            self.mainconfigs.append({
                'name': match.group(1),  # Changed from 'key' to 'name' to match U++ terminology
                'param': match.group(2)   # Changed from 'value' to 'param' to match U++ terminology
            })

        return i + 1

    def _parse_acceptflags(self, lines: List[str], start_idx: int) -> int:
        """Parse acceptflags directive."""
        i = start_idx

        accumulated = ""
        while i < len(lines):
            line = lines[i].strip()
            accumulated += " " + line

            if ';' in line:
                break
            i += 1

        # Extract flag identifiers
        content = accumulated.replace('acceptflags', '').replace(';', '')
        for token in re.split(r'[,\s]+', content):
            token = token.strip()
            if token:
                self.acceptflags.append(token)

        return i + 1

    def _parse_library(self, lines: List[str], start_idx: int) -> int:
        """Parse library directive with platform conditions."""
        line = lines[start_idx].strip()

        # Pattern: library(CONDITION) "libs";
        match = re.match(r'library\(([^)]+)\)\s+"([^"]+)"', line)
        if match:
            self.libraries.append({
                'condition': match.group(1),
                'libs': match.group(2)
            })
        else:
            # library(...) identifier; (without quotes)
            match = re.match(r'library\(([^)]+)\)\s+(\w+)', line)
            if match:
                self.libraries.append({
                    'condition': match.group(1),
                    'libs': match.group(2)
                })

        return start_idx + 1

    def _parse_static_library(self, lines: List[str], start_idx: int) -> int:
        """Parse static_library directive."""
        line = lines[start_idx].strip()

        match = re.match(r'static_library\(([^)]+)\)\s+(\w+)', line)
        if match:
            self.static_libraries.append({
                'condition': match.group(1),
                'libs': match.group(2)
            })

        return start_idx + 1

    def _parse_link(self, lines: List[str], start_idx: int) -> int:
        """Parse link directive."""
        line = lines[start_idx].strip()

        # Pattern: link(CONDITION) flags;
        match = re.match(r'link\(([^)]+)\)\s+(.+?);', line)
        if match:
            self.links.append({
                'condition': match.group(1),
                'flags': match.group(2)
            })

        return start_idx + 1

    def _extract_description_parts(self, raw_desc: str) -> tuple:
        """
        Extract description text and color from raw description.

        Pattern: "Some text\377B<r>,<g>,<b>"
        Returns: (text, (r, g, b)) or (text, None)
        """
        if not raw_desc:
            return ("", None)

        # Match color code: \377B<r>,<g>,<b> at end
        match = re.search(r'\\377B(\d+),(\d+),(\d+)$', raw_desc)
        if match:
            text = raw_desc[:match.start()]
            color = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return (text, color)

        # Also try octal representation
        match = re.search(r'\377B(\d+),(\d+),(\d+)$', raw_desc)
        if match:
            text = raw_desc[:match.start()]
            color = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return (text, color)

        return (raw_desc, None)


def parse_upp_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a .upp file and return structured metadata.

    Args:
        file_path: Path to .upp file

    Returns:
        Dictionary with parsed .upp metadata
    """
    parser = UppParser()
    return parser.parse_file(file_path)


def parse_upp_content(content: str) -> Dict[str, Any]:
    """
    Parse .upp content string and return structured metadata.

    Args:
        content: .upp file content as string

    Returns:
        Dictionary with parsed .upp metadata
    """
    parser = UppParser()
    return parser.parse(content)
