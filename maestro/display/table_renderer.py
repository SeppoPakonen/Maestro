"""
Common display utilities for Maestro CLI.

This module provides unified functions for table rendering, styling,
and display formatting that are used across multiple CLI modules.
"""

import re
import shutil
import unicodedata
from typing import List, Dict, Optional, Any

from maestro.config.settings import get_settings

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_white": "\033[97m",
}

EMOJI_WIDTH_2 = {
    "✅",
    "🚧",
    "📅",
    "📋",
    "💡",
    "❔",
    "🧭",
    "📝",
}

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

try:
    from wcwidth import wcwidth as _wcwidth
except ImportError:  # pragma: no cover - optional dependency
    _wcwidth = None


def _style_text(text: str, color: Optional[str] = None, bold: bool = False, dim: bool = False) -> str:
    """Apply ANSI styling to text."""
    settings = get_settings()
    if not settings.color_output:
        return text
    parts = []
    if bold:
        parts.append(ANSI_BOLD)
    if dim:
        parts.append(ANSI_DIM)
    if color:
        parts.append(ANSI_COLORS.get(color, ""))
    if not parts:
        return text
    return "".join(parts) + text + ANSI_RESET


def _char_display_width(char: str) -> int:
    """Get the display width of a character."""
    if char in EMOJI_WIDTH_2:
        return 2
    if _wcwidth is not None:
        width = _wcwidth(char)
        return width if width > 0 else 0
    east_asian = unicodedata.east_asian_width(char)
    if east_asian in ("W", "F"):
        return 2
    if unicodedata.category(char) == "So":
        return 2
    return 1


def _display_width(text: str) -> int:
    """Calculate the display width of text, excluding ANSI escape sequences."""
    stripped = ANSI_ESCAPE_RE.sub("", text)
    return sum(_char_display_width(ch) for ch in stripped)


def _pad_to_width(text: str, width: int) -> str:
    """Pad text to a specified width."""
    padding = width - _display_width(text)
    if padding <= 0:
        return text
    return text + (" " * padding)


def _truncate(text: str, width: int, unicode_symbols: bool) -> str:
    """Truncate text to a specified width with ellipsis."""
    if width <= 0:
        return ""
    if _display_width(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    ellipsis = "…" if unicode_symbols else "..."
    ellipsis_width = _display_width(ellipsis)
    if width <= ellipsis_width:
        return text[:width]
    remaining = width - ellipsis_width
    clipped = []
    current = 0
    for ch in text:
        ch_width = _char_display_width(ch)
        if current + ch_width > remaining:
            break
        clipped.append(ch)
        current += ch_width
    return "".join(clipped) + ellipsis


def _status_display(status: str, unicode_symbols: bool) -> tuple[str, str]:
    """Convert status to display string and color."""
    normalized = (status or "unknown").lower()
    status_map = {
        "planned": ("Planned", "cyan", "📅"),
        "proposed": ("Proposed", "magenta", "💡"),
        "in_progress": ("In Progress", "yellow", "🚧"),
        "done": ("Done", "green", "✅"),
    }
    label, color, emoji = status_map.get(normalized, ("Unknown", "bright_black", "❔"))
    if unicode_symbols:
        return f"{emoji} {label}", color
    return label, color


def _box_chars(unicode_symbols: bool) -> dict[str, str]:
    """Get box drawing characters based on unicode support."""
    if unicode_symbols:
        return {
            "top_left": "╭",
            "top_right": "╮",
            "bottom_left": "╰",
            "bottom_right": "╯",
            "horizontal": "─",
            "vertical": "│",
            "top_sep": "┬",
            "mid_left": "├",
            "mid_right": "┤",
            "mid_sep": "┼",
            "mid_horizontal": "─",
            "bottom_sep": "┴",
        }
    return {
        "top_left": "+",
        "top_right": "+",
        "bottom_left": "+",
        "bottom_right": "+",
        "horizontal": "-",
        "vertical": "|",
        "top_sep": "+",
        "mid_left": "+",
        "mid_right": "+",
        "mid_sep": "+",
        "mid_horizontal": "-",
        "bottom_sep": "+",
    }


class TableRenderer:
    """Unified table renderer for consistent display across CLI modules."""
    
    def __init__(self, title: str, headers: List[str], rows: List[Dict[str, Any]], 
                 border_color: Optional[str] = "yellow"):
        self.title = title
        self.headers = headers
        self.rows = rows
        self.border_color = border_color
        
    def render(self) -> List[str]:
        """Render the table as a list of strings."""
        settings = get_settings()
        unicode_symbols = settings.unicode_symbols
        term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
        term_width = max(term_width, 20)
        box = _box_chars(unicode_symbols)
        
        # Calculate column widths
        ncol = len(self.headers)
        header_widths = [_display_width(header) for header in self.headers]
        
        # Calculate content widths for each column
        content_widths = []
        for i, header in enumerate(self.headers):
            col_content_width = max(
                header_widths[i],
                max((_display_width(str(row.get(self.headers[i].lower().replace(' ', '_'), ''))) 
                     for row in self.rows), default=0)
            )
            content_widths.append(col_content_width)
        
        # Apply minimum widths
        min_widths = [1, 2, 6, 6, 6]  # Minimum widths for #, ID, Name, Status, etc.
        for i in range(len(content_widths)):
            content_widths[i] = max(content_widths[i], min_widths[i] if i < len(min_widths) else 6)
        
        # Calculate column widths with padding
        col_widths = [w + 2 for w in content_widths]
        
        # Calculate total content width
        content_width = sum(col_widths) + (ncol - 1) * 2
        max_term_width = max(term_width - 2, 10)
        inner_width = min(max_term_width, max(content_width, 10))
        
        # Adjust column widths if content is too wide
        if content_width > inner_width:
            available = inner_width - (ncol - 1) * 2
            # Keep important columns at minimum width, adjust others
            name_idx = next((i for i, h in enumerate(self.headers) if 'name' in h.lower()), -1)
            if name_idx >= 0:
                other_widths = sum(
                    content_widths[i] + 2 
                    for i in range(len(content_widths)) 
                    if i != name_idx
                ) + (ncol - 1) * 2
                
                if available > other_widths:
                    name_content = available - other_widths + 2
                    content_widths[name_idx] = max(content_widths[name_idx], name_content)
                    col_widths = [w + 2 for w in content_widths]
        
        # Build the table
        lines = []
        lines.append(_style_text(
            box["top_left"] + (box["horizontal"] * inner_width) + box["top_right"], 
            color=self.border_color
        ))

        # Title line
        title_text = _truncate(self.title, inner_width - 2, unicode_symbols)
        title_line = f"{box['vertical']} " + _pad_to_width(title_text, inner_width - 2) + f" {box['vertical']}"
        lines.append(_style_text(title_line, color="bright_white", bold=True))

        # Header line
        header_cells = []
        for header, width in zip(self.headers, content_widths):
            header_cells.append(" " + _pad_to_width(header, width) + " ")
        header_content = "  ".join(header_cells)
        header_line = box["vertical"] + _pad_to_width(header_content, inner_width) + box["vertical"]
        lines.append(_style_text(header_line, color="bright_white", bold=True))
        
        lines.append(_style_text(
            box["mid_left"] + (box["mid_horizontal"] * inner_width) + box["mid_right"], 
            color=self.border_color
        ))

        # Data rows
        if self.rows:
            for row in self.rows:
                row_cells = []
                for i, header in enumerate(self.headers):
                    # Map header to expected key format
                    # Special mapping for headers that don't directly correspond to data keys
                    key_map = {
                        "#": "idx",
                        "Track ID": "track_id",
                        "Phase ID": "phase_id",
                        "Task ID": "task_id",
                        "St": "status",
                        "Ph": "phases",
                        "Todo": "todo"
                    }

                    # Use mapping if available, otherwise convert header to key
                    if header in key_map:
                        key = key_map[header]
                    else:
                        key = header.lower().replace(' ', '_')

                    value = str(row.get(key, ''))

                    # Handle status specifically for coloring
                    if 'status' in header.lower() or header == "St":
                        status_display, status_color = _status_display(value, unicode_symbols)
                        cell_text = _truncate(status_display, content_widths[i], unicode_symbols)
                        padded = " " + _pad_to_width(cell_text, content_widths[i]) + " "
                        row_cells.append(_style_text(padded, color=status_color))
                    else:
                        cell_text = _truncate(value, content_widths[i], unicode_symbols)
                        padded = " " + _pad_to_width(cell_text, content_widths[i]) + " "
                        row_cells.append(padded)

                row_content = "  ".join(row_cells)
                line = box["vertical"] + _pad_to_width(row_content, inner_width) + box["vertical"]
                lines.append(line)
        else:
            empty_text = _truncate("(none)", inner_width - 2, unicode_symbols)
            empty_line = f"{box['vertical']} " + _pad_to_width(empty_text, inner_width - 2) + f" {box['vertical']}"
            lines.append(_style_text(empty_line, color="bright_black", dim=True))

        lines.append(_style_text(
            box["bottom_left"] + (box["horizontal"] * inner_width) + box["bottom_right"], 
            color=self.border_color
        ))
        
        # Add footer with count
        lines.append(_style_text(f"Total: {len(self.rows)} {self.title.lower()}", 
                                color="bright_black", dim=True))
        lines.append(_style_text(f"Use 'maestro {self.title.lower().split()[0]} <#>' or 'maestro {self.title.lower().split()[0]} <id>' to view details", 
                                color="bright_black", dim=True))
        
        return lines
    
    def print_table(self):
        """Print the table directly to stdout."""
        lines = self.render()
        for line in lines:
            print(line)


def render_track_table(tracks: List[Dict[str, Any]]) -> List[str]:
    """Render a table of tracks with consistent styling."""
    # The tracks list should already be properly formatted with correct keys
    # Just pass it through to the table renderer
    return TableRenderer(
        title="Tracks",
        headers=["#", "Track ID", "Name", "St", "Ph", "Todo"],
        rows=tracks
    ).render()


def render_phase_table(phases: List[Dict[str, Any]], track_filter: Optional[str] = None) -> List[str]:
    """Render a table of phases with consistent styling."""
    # The phases list should already be properly formatted with correct keys
    # Just pass it through to the table renderer
    headers = ["#", "Phase ID", "Name", "Track", "Status"] if not track_filter else ["#", "Phase ID", "Name", "Status"]
    return TableRenderer(
        title="Phases",
        headers=headers,
        rows=phases
    ).render()


def render_task_table(tasks: List[Dict[str, Any]]) -> List[str]:
    """Render a table of tasks with consistent styling."""
    # The tasks list should already be properly formatted with correct keys
    # Just pass it through to the table renderer
    return TableRenderer(
        title="Tasks",
        headers=["#", "Task ID", "Name", "Track", "Phase", "Status"],
        rows=tasks
    ).render()