"""
Track command implementation for Maestro CLI.

Commands:
- maestro track list - List all tracks
- maestro track add <name> - Add new track
- maestro track remove <id> - Remove track
- maestro track <id> - Show track details
- maestro track <id> show - Show track details
- maestro track <id> list - List phases in track
- maestro track <id> details - Show track details with phases/tasks
- maestro track <id> edit - Edit track in $EDITOR
- maestro track <id> set - Set current track context
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import textwrap
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from maestro.config.settings import get_settings
from maestro.data import parse_todo_md, parse_done_md
from maestro.data.markdown_writer import (
    escape_asterisk_text,
    extract_track_block,
    insert_track_block,
    remove_track_block,
    replace_track_block,
)
from .discuss import handle_track_discuss

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
    stripped = ANSI_ESCAPE_RE.sub("", text)
    return sum(_char_display_width(ch) for ch in stripped)


def _pad_to_width(text: str, width: int) -> str:
    padding = width - _display_width(text)
    if padding <= 0:
        return text
    return text + (" " * padding)


def _truncate(text: str, width: int, unicode_symbols: bool) -> str:
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


def _render_table(
    title: str,
    rows: list[dict[str, str]],
    term_width: int,
    border_color: Optional[str] = None,
) -> list[str]:
    settings = get_settings()
    unicode_symbols = settings.unicode_symbols
    box = _box_chars(unicode_symbols)
    ncol = 4
    max_term_width = max(term_width - 2, 10)

    idx_header = "#"
    id_header = "ID"
    name_header = "Name"
    status_header = "Status"

    idx_content = max(_display_width(idx_header), _display_width(str(len(rows) or 0)))
    id_content = max(_display_width(id_header), max((_display_width(r["id"]) for r in rows), default=0))
    status_content = max(_display_width(status_header), max((_display_width(r["status"]) for r in rows), default=0))
    name_content = max(_display_width(name_header), max((_display_width(r["name"]) for r in rows), default=0))

    min_idx = 1
    min_id = 2
    min_status = 6
    min_name = 6

    idx_content = max(idx_content, min_idx)
    id_content = max(id_content, min_id)
    status_content = max(status_content, min_status)
    name_content = max(name_content, min_name)

    col_content_widths = [idx_content, id_content, name_content, status_content]
    col_widths = [w + 2 for w in col_content_widths]
    content_width = sum(col_widths) + (ncol - 1) * 2
    inner_width = min(max_term_width, max(content_width, 10))

    max_content_width = inner_width
    if content_width > max_content_width:
        available = max_content_width - (ncol - 1) * 2
        name_content = max(min_name, available - (idx_content + id_content + status_content + 2 * ncol))
        col_content_widths = [idx_content, id_content, name_content, status_content]
        col_widths = [w + 2 for w in col_content_widths]

    def border(left: str, sep: str, right: str, horizontal: str) -> str:
        return left + (horizontal * inner_width) + right

    lines = []
    lines.append(_style_text(border(box["top_left"], box["top_sep"], box["top_right"], box["horizontal"]), color=border_color))

    title_text = _truncate(title, inner_width - 2, unicode_symbols)
    title_line = f"{box['vertical']} " + _pad_to_width(title_text, inner_width - 2) + f" {box['vertical']}"
    lines.append(_style_text(title_line, color="bright_white", bold=True))

    headers = [idx_header, id_header, name_header, status_header]
    header_cells = []
    for header, width in zip(headers, col_content_widths):
        header_cells.append(" " + _pad_to_width(header, width) + " ")
    header_content = "  ".join(header_cells)
    header_line = box["vertical"] + _pad_to_width(header_content, inner_width) + box["vertical"]
    lines.append(_style_text(header_line, color="bright_white", bold=True))
    lines.append(_style_text(border(box["mid_left"], box["mid_sep"], box["mid_right"], box["mid_horizontal"]), color=border_color))

    if rows:
        for row in rows:
            row_cells = []
            values = [row["idx"], row["id"], row["name"], row["status"]]
            colors = [None, None, None, row.get("status_color")]
            for value, width, color in zip(values, col_content_widths, colors):
                cell_text = _truncate(value, width, unicode_symbols)
                padded = " " + _pad_to_width(cell_text, width) + " "
                row_cells.append(_style_text(padded, color=color))
            row_content = "  ".join(row_cells)
            line = box["vertical"] + _pad_to_width(row_content, inner_width) + box["vertical"]
            lines.append(line)
    else:
        empty_text = _truncate("(none)", inner_width - 2, unicode_symbols)
        empty_line = f"{box['vertical']} " + _pad_to_width(empty_text, inner_width - 2) + f" {box['vertical']}"
        lines.append(_style_text(empty_line, color="bright_black", dim=True))

    lines.append(_style_text(border(box["bottom_left"], box["bottom_sep"], box["bottom_right"], box["horizontal"]), color=border_color))
    return lines


def resolve_track_identifier(identifier: str) -> Optional[str]:
    """
    Resolve a track identifier (number or ID) to a track ID.

    Args:
        identifier: Either a track number (1, 2, 3) or track ID (umk, cli-tpt)

    Returns:
        Track ID if found, None otherwise
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return None

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])
    if identifier.isdigit():
        index = int(identifier) - 1
        if 0 <= index < len(tracks):
            return tracks[index].get('track_id')
        return None

    for track in tracks:
        if track.get('track_id') == identifier:
            return identifier

    return None


def list_tracks(args) -> int:
    """
    List all tracks from docs/todo.md.
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found. Run 'maestro init' first.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])
    done_path = Path('docs/done.md')
    done_tracks = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])

    if not tracks:
        print("No tracks found.")
        return 0

    print()
    settings = get_settings()
    unicode_symbols = settings.unicode_symbols
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    term_width = max(term_width, 20)
    box = _box_chars(unicode_symbols)
    done_phase_counts = {
        track.get('track_id', ''): len(track.get('phases', []))
        for track in done_tracks
    }

    status_map = {
        "done": ("✅", "green"),
        "in_progress": ("🚧", "yellow"),
        "planned": ("📅", "cyan"),
        "todo": ("📋", "cyan"),
        "proposed": ("💡", "magenta"),
    }

    statuses = []
    for track in tracks:
        status = track.get('status', 'unknown')
        status_display, _ = status_map.get(status, ("❔", "bright_black"))
        statuses.append(status_display)

    idx_w = max(_display_width("#"), _display_width(str(len(tracks))))
    id_w = max(_display_width("Track ID"), max((_display_width(t.get('track_id', '')) for t in tracks), default=0))
    name_w = max(_display_width("Name"), max((_display_width(t.get('name', '')) for t in tracks), default=0))
    st_w = max(_display_width("St"), max((_display_width(s) for s in statuses), default=0))
    ph_w = max(_display_width("Ph"), _display_width(str(len(tracks))))
    todo_w = max(_display_width("Todo"), _display_width(str(len(tracks))))

    col_widths = [idx_w, id_w, name_w, st_w, ph_w, todo_w]
    ncol = len(col_widths)
    content_width = sum(w + 2 for w in col_widths) + (ncol - 1) * 2
    inner_width = min(term_width - 2, max(content_width, 20))
    available = inner_width - (ncol - 1) * 2 - (2 * ncol)
    name_w = max(_display_width("Name"), available - (idx_w + id_w + st_w + ph_w + todo_w))
    col_widths = [idx_w, id_w, name_w, st_w, ph_w, todo_w]

    header_cells = [
        " " + _pad_to_width("#", idx_w) + " ",
        " " + _pad_to_width("Track ID", id_w) + " ",
        " " + _pad_to_width("Name", name_w) + " ",
        " " + _pad_to_width("St", st_w) + " ",
        " " + _pad_to_width("Ph", ph_w) + " ",
        " " + _pad_to_width("Todo", todo_w) + " ",
    ]
    header_line = box["vertical"] + _pad_to_width("  ".join(header_cells), inner_width) + box["vertical"]
    print(_style_text(box["top_left"] + box["horizontal"] * inner_width + box["top_right"], color="yellow"))
    print(_style_text(header_line, color="bright_white", bold=True))
    print(_style_text(box["mid_left"] + box["mid_horizontal"] * inner_width + box["mid_right"], color="yellow"))

    for i, track in enumerate(tracks, 1):
        track_id = track.get('track_id', 'N/A')
        name = track.get('name', 'Unnamed Track')
        status = track.get('status', 'unknown')
        phases = track.get('phases', [])
        todo_count = sum(
            1
            for phase in phases
            if phase.get('status') in ('planned', 'proposed', 'in_progress')
        )
        done_in_todo_count = sum(
            1
            for phase in phases
            if phase.get('status') == 'done'
        )
        done_phase_count = done_phase_counts.get(track_id, 0)
        phase_count = todo_count + done_in_todo_count + done_phase_count

        status_display, status_color = status_map.get(status, ("❔", "bright_black"))
        track_id = _truncate(track_id, id_w, unicode_symbols)
        name = _truncate(name, name_w, unicode_symbols)

        if todo_count == 0:
            todo_color = "green"
        elif todo_count == phase_count:
            todo_color = "red"
        else:
            todo_color = "yellow"
        status_cell = _style_text(" " + _pad_to_width(status_display, st_w) + " ", color=status_color)
        todo_cell = _style_text(" " + _pad_to_width(str(todo_count), todo_w) + " ", color=todo_color)
        row_cells = [
            " " + _pad_to_width(str(i), idx_w) + " ",
            " " + _pad_to_width(track_id, id_w) + " ",
            " " + _pad_to_width(name, name_w) + " ",
            status_cell,
            " " + _pad_to_width(str(phase_count), ph_w) + " ",
            todo_cell,
        ]
        row_content = "  ".join(row_cells)
        row_line = box["vertical"] + _pad_to_width(row_content, inner_width) + box["vertical"]
        print(row_line)

    print(_style_text(box["bottom_left"] + box["horizontal"] * inner_width + box["bottom_right"], color="yellow"))
    print(_style_text(f"Total: {len(tracks)} tracks", color="bright_black", dim=True))
    print(_style_text("Use 'maestro track <#>' or 'maestro track <id>' to view details", color="bright_black", dim=True))

    return 0


def show_track(track_identifier: str, args) -> int:
    """
    Show detailed information about a specific track.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    done_path = Path('docs/done.md')
    done_phases = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])
        for done_track in done_tracks:
            if done_track.get('track_id') == track_id:
                done_phases = done_track.get('phases', [])
                break

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    settings = get_settings()
    unicode_symbols = settings.unicode_symbols
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    term_width = max(term_width, 20)
    box = _box_chars(unicode_symbols)
    inner_width = term_width - 2

    print()
    header_title = f"🧭 Track: {track.get('name', 'Unnamed')}" if unicode_symbols else f"Track: {track.get('name', 'Unnamed')}"
    completion = track.get('completion', 0)
    if isinstance(completion, str) and completion.endswith("%"):
        completion_text = completion
    else:
        completion_text = f"{completion}%"
    header_lines = [
        f"ID: {track.get('track_id', 'N/A')}",
        f"Priority: {track.get('priority', 'N/A')}",
        f"Status: {track.get('status', 'N/A')}",
        f"Completion: {completion_text}",
    ]

    print(_style_text(box["top_left"] + box["horizontal"] * inner_width + box["top_right"], color="cyan"))
    title_text = _truncate(header_title, inner_width - 2, unicode_symbols)
    title_line = f"{box['vertical']} " + _pad_to_width(title_text, inner_width - 2) + f" {box['vertical']}"
    print(_style_text(title_line, color="bright_white", bold=True))
    for line in header_lines:
        content = _truncate(line, inner_width - 2, unicode_symbols)
        padded = f"{box['vertical']} " + _pad_to_width(content, inner_width - 2) + f" {box['vertical']}"
        print(padded)
    print(_style_text(box["bottom_left"] + box["horizontal"] * inner_width + box["bottom_right"], color="cyan"))

    description = track.get('description', [])
    if description:
        desc_title = "📝 Description" if unicode_symbols else "Description"
        print(_style_text(box["top_left"] + box["horizontal"] * inner_width + box["top_right"], color="blue"))
        title_text = _truncate(desc_title, inner_width - 2, unicode_symbols)
        title_line = f"{box['vertical']} " + _pad_to_width(title_text, inner_width - 2) + f" {box['vertical']}"
        print(_style_text(title_line, color="bright_white", bold=True))
        wrapped_lines = []
        for line in description:
            wrapped_lines.extend(textwrap.wrap(line, width=max(inner_width - 2, 10)) or [""])
        if not wrapped_lines:
            wrapped_lines = ["(none)"]
        for line in wrapped_lines:
            content = _truncate(line, inner_width - 2, unicode_symbols)
            padded = f"{box['vertical']} " + _pad_to_width(content, inner_width - 2) + f" {box['vertical']}"
            print(padded)
        print(_style_text(box["bottom_left"] + box["horizontal"] * inner_width + box["bottom_right"], color="blue"))

    phases = track.get('phases', [])
    todo_phases = [phase for phase in phases if phase.get('status') != 'done']
    done_from_todo = [phase for phase in phases if phase.get('status') == 'done']
    seen_done_ids = {phase.get('phase_id') for phase in done_phases if phase.get('phase_id')}
    for phase in done_from_todo:
        phase_id = phase.get('phase_id')
        if not phase_id or phase_id in seen_done_ids:
            continue
        done_phases.append(phase)
        seen_done_ids.add(phase_id)

    todo_rows = []
    for i, phase in enumerate(todo_phases, 1):
        phase_id = phase.get('phase_id', 'N/A')
        phase_name = phase.get('name', 'Unnamed')
        phase_status = phase.get('status', 'unknown')
        status_label, status_color = _status_display(phase_status, unicode_symbols)
        todo_rows.append({
            "idx": str(i),
            "id": phase_id,
            "name": phase_name,
            "status": status_label,
            "status_color": status_color,
        })

    todo_title = f"Todo phases ({len(todo_rows)})"
    todo_title = f"🧭 {todo_title}" if unicode_symbols else todo_title
    for line in _render_table(todo_title, todo_rows, term_width, border_color="yellow"):
        print(line)

    total_done = len(done_phases)
    visible_done = done_phases[-10:] if done_phases else []
    if total_done > len(visible_done):
        done_title = f"Done phases ({len(visible_done)} of {total_done})"
    else:
        done_title = f"Done phases ({len(visible_done)})"
    done_title = f"✅ {done_title}" if unicode_symbols else done_title

    done_rows = []
    for i, phase in enumerate(visible_done, 1):
        phase_id = phase.get('phase_id', 'N/A')
        phase_name = phase.get('name', 'Unnamed')
        phase_status = phase.get('status', 'done')
        status_label, status_color = _status_display(phase_status, unicode_symbols)
        done_rows.append({
            "idx": str(i),
            "id": phase_id,
            "name": phase_name,
            "status": status_label,
            "status_color": status_color,
        })
    for line in _render_table(done_title, done_rows, term_width, border_color="green"):
        print(line)

    return 0


def show_track_details(track_identifier: str, args) -> int:
    """
    Show detailed information about a specific track with all phases and their sub-tasks.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    done_path = Path('docs/done.md')
    done_phases = []
    if done_path.exists():
        done_data = parse_done_md(str(done_path))
        done_tracks = done_data.get('tracks', [])
        for done_track in done_tracks:
            if done_track.get('track_id') == track_id:
                done_phases = done_track.get('phases', [])
                break

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    print()
    print("=" * 80)
    print(f"TRACK: {track.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    print(f"ID:          {track.get('track_id', 'N/A')}")
    print(f"Priority:    {track.get('priority', 'N/A')}")
    print(f"Status:      {track.get('status', 'N/A')}")
    print(f"Completion:  {track.get('completion', 0)}%")
    print()

    description = track.get('description', [])
    if description:
        print("Description:")
        for line in description:
            print(f"  {line}")
        print()

    all_phases = track.get('phases', []) + done_phases

    print("=" * 80)
    print("PHASES")
    print("=" * 80)
    print()

    sorted_phases = sorted(
        all_phases,
        key=lambda p: (p.get('status', 'planned') != 'done', p.get('phase_id', '')),
    )

    for phase in sorted_phases:
        phase_id = phase.get('phase_id', 'N/A')
        phase_name = phase.get('name', 'Unnamed')
        phase_status = phase.get('status', 'unknown')
        phase_completion = phase.get('completion', 0)

        if phase_status == 'done':
            status_emoji = "✅"
        elif phase_status == 'planned':
            status_emoji = "📋"
        elif phase_status == 'in_progress':
            status_emoji = "🚧"
        else:
            status_emoji = "💡"

        print(f"{status_emoji} Phase {phase_id}: {phase_name} [{phase_status.title()}]")
        print(f"   Completion: {phase_completion}%")
        print()

        tasks = phase.get('tasks', [])
        if tasks:
            print(f"   Tasks ({len(tasks)}):")
            for task in tasks:
                task_id = task.get('task_id', task.get('task_number', 'N/A'))
                task_name = task.get('name', 'Unnamed')
                task_completed = task.get('completed', False)

                task_status_emoji = "✅" if task_completed else "⬜"
                print(f"     {task_status_emoji} [{task_id}] {task_name}")

                task_description = task.get('description', [])
                if task_description:
                    for desc_line in task_description:
                        if desc_line.strip() and not desc_line.startswith('- [') and not desc_line.startswith('  - '):
                            cleaned_desc = desc_line.replace(f"**{task_id}**", "").strip()
                            if cleaned_desc.startswith('-'):
                                cleaned_desc = cleaned_desc[1:].strip()
                            if cleaned_desc:
                                print(f"         - {cleaned_desc}")
            print()
        else:
            print("   Tasks: (none)")
            print()

    print()
    return 0


def _slugify_track_id(name: str) -> str:
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in name.strip())
    slug = re.sub(r'-{2,}', '-', slug).strip('-')
    return slug


def _resolve_text_input(args) -> str:
    if getattr(args, 'text_file', None):
        return Path(args.text_file).read_text(encoding='utf-8')
    return sys.stdin.read()


def add_track(name: str, args) -> int:
    """
    Add a new track to docs/todo.md.
    """
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    track_id = getattr(args, 'track_id', None) or _slugify_track_id(name)
    if track_id.isdigit():
        print("Error: Track ID cannot be purely numeric.")
        return 1

    data = parse_todo_md(str(todo_path))
    if any(t.get('track_id') == track_id for t in data.get('tracks', [])):
        print(f"Error: Track ID '{track_id}' already exists.")
        return 1

    desc_lines = getattr(args, 'desc', None) or [
        "Ensure track/phase/task entries can be created, edited, and reorganized from the CLI.",
        "Provide both editor and direct text workflows for quick updates."
    ]

    escaped_track_id = escape_asterisk_text(track_id)
    block_lines = [
        f"## Track: {name}\n",
        "\n",
        f"- *track_id*: *{escaped_track_id}*\n",
        f"- *priority*: {getattr(args, 'priority', 0)}\n",
        "- *status*: *planned*\n",
        "- *completion*: 0%\n",
        "\n",
    ]
    for line in desc_lines:
        if line.strip():
            block_lines.append(f"{line.strip()}\n")
    block_lines.append("\n")

    inserted = insert_track_block(
        todo_path,
        "".join(block_lines),
        after_track_id=getattr(args, 'after', None),
        before_track_id=getattr(args, 'before', None),
    )
    if not inserted:
        print("Error: Unable to insert track block.")
        return 1

    print(f"Added track '{track_id}' ({name}).")
    return 0


def remove_track(track_identifier: str, args) -> int:
    """
    Remove a track from docs/todo.md.
    """
    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    if not remove_track_block(todo_path, track_id):
        print(f"Error: Track '{track_id}' not found in docs/todo.md.")
        return 1

    print(f"Removed track: {track_id}")
    return 0


def edit_track(track_identifier: str, args) -> int:
    """
    Edit a track in $EDITOR.
    """
    import os
    import subprocess

    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    block = extract_track_block(todo_path, track_id)
    if not block:
        print(f"Error: Track '{track_id}' not found in docs/todo.md.")
        return 1

    editor = os.environ.get('EDITOR', 'vim')
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
            tmp.write(block.encode('utf-8'))
            tmp_path = tmp.name
        subprocess.run([editor, tmp_path])
        new_block = Path(tmp_path).read_text(encoding='utf-8')
        Path(tmp_path).unlink(missing_ok=True)
        if new_block == block:
            print("No changes made.")
            return 0
        if not replace_track_block(todo_path, track_id, new_block):
            print("Error: Failed to update track block.")
            return 1
        print(f"Updated track '{track_id}'.")
        return 0
    except Exception as exc:
        print(f"Error opening editor: {exc}")
        return 1


def set_track_context(track_identifier: str, args) -> int:
    """
    Set the current track context.
    """
    from maestro.config.settings import get_settings

    track_id = resolve_track_identifier(track_identifier)
    if not track_id:
        print(f"Error: Track '{track_identifier}' not found.")
        print("Use 'maestro track list' to see available tracks.")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        return 1

    data = parse_todo_md(str(todo_path))
    tracks = data.get('tracks', [])

    track = next((t for t in tracks if t.get('track_id') == track_id), None)
    if not track:
        print(f"Error: Track '{track_identifier}' not found.")
        return 1

    settings = get_settings()
    settings.current_track = track_id
    settings.current_phase = None
    settings.current_task = None
    settings.save()

    print(f"Context set to track: {track_id} ({track.get('name', 'Unnamed')})")
    print("Use 'maestro phase list' to see phases in this track.")
    return 0


def handle_track_command(args) -> int:
    """
    Main handler for track commands.
    """
    if hasattr(args, 'track_subcommand') and args.track_subcommand:
        subcommand = args.track_subcommand

        if subcommand in ['list', 'ls', 'l']:
            return list_tracks(args)

        if subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Track name required. Usage: maestro track add <name>")
                return 1
            name = " ".join(args.name) if isinstance(args.name, list) else args.name
            return add_track(name, args)

        if subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track remove <id>")
                return 1
            return remove_track(args.track_id, args)

        if subcommand in ['discuss', 'd']:
            return handle_track_discuss(getattr(args, 'track_id', None), args)

        if subcommand in ['show', 'sh', 's']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track show <id>")
                return 1
            if getattr(args, 'track_item_action', None) in ['help', 'h']:
                print_track_item_help()
                return 0
            if getattr(args, 'track_item_action', None) in ['list', 'ls', 'l']:
                track_id = resolve_track_identifier(args.track_id)
                if not track_id:
                    print(f"Error: Track '{args.track_id}' not found.")
                    print("Use 'maestro track list' to see available tracks.")
                    return 1
                from .phase import list_phases
                return list_phases(SimpleNamespace(track_id=track_id))
            return show_track(args.track_id, args)

        if subcommand in ['details', 'dt']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track details <id>")
                return 1
            return show_track_details(args.track_id, args)

        if subcommand in ['edit', 'e']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track edit <id>")
                return 1
            return edit_track(args.track_id, args)

        if subcommand in ['text', 'raw']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track text <id>")
                return 1
            todo_path = Path('docs/todo.md')
            block = extract_track_block(todo_path, args.track_id)
            if not block:
                print(f"Error: Track '{args.track_id}' not found in docs/todo.md.")
                return 1
            print(block.rstrip())
            return 0

        if subcommand in ['set-text', 'setraw']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track set-text <id> [--file path]")
                return 1
            todo_path = Path('docs/todo.md')
            new_block = _resolve_text_input(args)
            if not new_block.strip():
                print("Error: Replacement text is empty.")
                return 1
            if not replace_track_block(todo_path, args.track_id, new_block):
                print(f"Error: Track '{args.track_id}' not found in docs/todo.md.")
                return 1
            print(f"Updated track '{args.track_id}'.")
            return 0

        if subcommand in ['set', 'st']:
            if not hasattr(args, 'track_id') or not args.track_id:
                print("Error: Track ID required. Usage: maestro track set <id>")
                return 1
            return set_track_context(args.track_id, args)

        if subcommand in ['help', 'h']:
            print_track_help()
            return 0

    print_track_help()
    return 0


def print_track_help() -> None:
    """Print help for track commands."""
    help_text = """
maestro track - Manage project tracks

USAGE:
    maestro track list                    List all tracks
    maestro track add <name>              Add new track
    maestro track remove <id|#>           Remove a track
    maestro track discuss [id|#]          Discuss tracks with AI
    maestro track <id|#>                  Show track details
    maestro track <id|#> show             Show track details
    maestro track <id|#> list             List phases in this track
    maestro track <id|#> details          Show track details with phases/tasks
    maestro track <id|#> edit             Edit track in $EDITOR
    maestro track <id|#> set              Set current track context
    maestro track text <id|#>             Show raw track block
    maestro track set-text <id|#>         Replace track block (stdin or --file)

TRACK IDENTIFIERS:
    You can use either the track ID (e.g., 'umk') or the track number (e.g., '2')
    from the track list. Both work identically.

ALIASES:
    list:   ls, l
    add:    a
    remove: rm, r
    discuss: d
    show:   s, sh
    details: dt
    edit:   e
    set:    st
    text:   raw
    set-text: setraw

EXAMPLES:
    maestro track list
    maestro track 2
    maestro track umk
    maestro track 2 list
    maestro track umk details
    maestro track umk set
    maestro track discuss
    maestro track umk discuss
    maestro track add --id cli-editing --after cleanup-migration "CLI Editing"
"""
    print(help_text)


def print_track_item_help() -> None:
    """Print help for track item commands."""
    help_text = """
maestro track <id> - Manage a specific track

USAGE:
    maestro track <id> show               Show track details
    maestro track <id> list               List phases in this track
    maestro track <id> details            Show track details with phases/tasks
    maestro track <id> edit               Edit track in $EDITOR
    maestro track <id> discuss            Discuss track with AI
    maestro track <id> set                Set current track context

ALIASES:
    show: s, sh
    list: l, ls
    details: dt
    edit: e
    discuss: d
    set: st

EXAMPLES:
    maestro track cli-tpt show
    maestro track cli-tpt list
    maestro track cli-tpt details
    maestro track cli-tpt edit
    maestro track cli-tpt discuss
    maestro track cli-tpt set
"""
    print(help_text)


def add_track_parsers(subparsers):
    """
    Add track command parser to the main argument parser.
    """
    if len(sys.argv) >= 3 and sys.argv[1] in ['track', 'tr', 't']:
        arg = sys.argv[2]
        known_subcommands = [
            'list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'discuss', 'd',
            'help', 'h', 'show', 'sh', 's', 'details', 'dt', 'edit', 'e', 'set', 'st',
            'text', 'raw', 'set-text', 'setraw'
        ]
        if arg not in known_subcommands:
            if len(sys.argv) >= 4 and sys.argv[3] in ['show', 'sh', 's', 'details', 'dt', 'edit', 'e', 'discuss', 'd', 'set', 'st', 'text', 'raw', 'set-text', 'setraw']:
                subcommand = sys.argv[3]
                track_id = sys.argv[2]
                sys.argv[2] = subcommand
                sys.argv[3] = track_id
            else:
                sys.argv.insert(2, 'show')

    track_parser = subparsers.add_parser(
        'track',
        aliases=['tr', 't'],
        help='Manage project tracks'
    )

    track_subparsers = track_parser.add_subparsers(
        dest='track_subcommand',
        help='Track subcommands'
    )

    track_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all tracks'
    )

    track_add_parser = track_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new track'
    )
    track_add_parser.add_argument('name', nargs='+', help='Track name')
    track_add_parser.add_argument('--id', dest='track_id', help='Track ID (default: slugified name)')
    track_add_parser.add_argument('--after', help='Insert after track ID')
    track_add_parser.add_argument('--before', help='Insert before track ID')
    track_add_parser.add_argument('--priority', type=int, default=0, help='Track priority number')
    track_add_parser.add_argument('--desc', action='append', help='Description line (repeatable)')

    track_remove_parser = track_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a track'
    )
    track_remove_parser.add_argument('track_id', help='Track ID to remove')

    track_discuss_parser = track_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss tracks with AI'
    )
    track_discuss_parser.add_argument('track_id', nargs='?', help='Track ID to discuss')

    track_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for track commands'
    )

    track_show_parser = track_subparsers.add_parser(
        'show',
        aliases=['s', 'sh'],
        help='Show track details'
    )
    track_show_parser.add_argument('track_id', help='Track ID to show')
    track_show_parser.add_argument(
        'track_item_action',
        nargs='?',
        choices=['help', 'h', 'list', 'ls', 'l'],
        help='Show help or list phases for a track'
    )

    track_details_parser = track_subparsers.add_parser(
        'details',
        aliases=['dt'],
        help='Show track details with all phases and tasks'
    )
    track_details_parser.add_argument('track_id', help='Track ID to show details for')

    track_edit_parser = track_subparsers.add_parser(
        'edit',
        aliases=['e'],
        help='Edit track in $EDITOR'
    )
    track_edit_parser.add_argument('track_id', help='Track ID to edit')

    track_text_parser = track_subparsers.add_parser(
        'text',
        aliases=['raw'],
        help='Show raw track block from docs/todo.md'
    )
    track_text_parser.add_argument('track_id', help='Track ID to show')

    track_set_text_parser = track_subparsers.add_parser(
        'set-text',
        aliases=['setraw'],
        help='Replace track block from stdin or a file'
    )
    track_set_text_parser.add_argument('track_id', help='Track ID to replace')
    track_set_text_parser.add_argument('--file', dest='text_file', help='Read replacement text from file')

    track_set_parser = track_subparsers.add_parser(
        'set',
        aliases=['st'],
        help='Set current track context'
    )
    track_set_parser.add_argument('track_id', help='Track ID to set as current')

    track_parser.add_argument(
        '--mode',
        choices=['editor', 'terminal'],
        help='Discussion mode (editor or terminal)'
    )
    track_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )

    return track_parser
