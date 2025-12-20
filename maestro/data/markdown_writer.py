"""
Markdown writer helpers for Maestro data files.

These helpers perform minimal, targeted edits to preserve user-authored content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from .markdown_parser import (
    parse_heading,
    parse_phase_heading,
    parse_task_heading,
    parse_track_heading,
)


def _read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _write_lines(path: Path, lines: List[str]) -> None:
    path.write_text("".join(lines), encoding="utf-8")


def _find_track_bounds(lines: List[str], track_id: str) -> Optional[Tuple[int, int]]:
    # Match both old format ("track_id": "value") and new format (- *track_id*: *value*)
    old_format_re = re.compile(rf'^\s*"track_id"\s*:\s*"{re.escape(track_id)}"\s*$')
    new_format_re = re.compile(rf'^\s*-\s*\*track_id\*\s*:\s*\*{re.escape(track_id)}\*\s*$')
    track_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if old_format_re.match(stripped) or new_format_re.match(stripped):
            track_idx = idx
            break
    if track_idx is None:
        return None

    start_idx = None
    for idx in range(track_idx, -1, -1):
        if parse_track_heading(lines[idx].strip()):
            start_idx = idx
            break
    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        if parse_track_heading(lines[idx].strip()):
            end_idx = idx
            break
    return (start_idx, end_idx)


def _find_phase_bounds(lines: List[str], phase_id: str) -> Optional[Tuple[int, int]]:
    # Match both old format ("phase_id": "value") and new format (- *phase_id*: *value*)
    old_format_re = re.compile(rf'^\s*"phase_id"\s*:\s*"{re.escape(phase_id)}"\s*$')
    new_format_re = re.compile(rf'^\s*-\s*\*phase_id\*\s*:\s*\*{re.escape(phase_id)}\*\s*$')
    phase_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if old_format_re.match(stripped) or new_format_re.match(stripped):
            phase_idx = idx
            break
    if phase_idx is None:
        return None

    start_idx = None
    for idx in range(phase_idx, -1, -1):
        if parse_phase_heading(lines[idx].strip()):
            start_idx = idx
            break
    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx].strip()
        if parse_phase_heading(line) or parse_track_heading(line):
            end_idx = idx
            break
        heading = parse_heading(line)
        if heading and heading[0] == 2:
            end_idx = idx
            break
    return (start_idx, end_idx)


def _find_task_bounds(lines: List[str], task_id: str) -> Optional[Tuple[int, int]]:
    # For tasks, we look for task headings but also handle the metadata format if present
    start_idx = None
    for idx, line in enumerate(lines):
        task = parse_task_heading(line.strip())
        if task and task[0].lower() == task_id.lower():
            start_idx = idx
            break
        # Also check for task_id as a metadata field (for backward compatibility)
        stripped = line.strip()
        old_format_re = re.compile(rf'^\s*"task_id"\s*:\s*"{re.escape(task_id)}"\s*$')
        new_format_re = re.compile(rf'^\s*-\s*\*task_id\*\s*:\s*\*{re.escape(task_id)}\*\s*$')
        if old_format_re.match(stripped) or new_format_re.match(stripped):
            # Find the task heading above this line
            for j in range(idx - 1, -1, -1):
                task = parse_task_heading(lines[j].strip())
                if task:
                    start_idx = j
                    break
            if start_idx is not None:
                break
    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx].strip()
        if parse_task_heading(line):
            end_idx = idx
            break
        heading = parse_heading(line)
        if heading and heading[0] <= 2:
            end_idx = idx
            break
    return (start_idx, end_idx)


def _first_nonempty_before(lines: List[str], idx: int) -> Optional[str]:
    for j in range(idx - 1, -1, -1):
        if lines[j].strip():
            return lines[j].strip()
    return None


def _ensure_separator_before(lines: List[str], insert_idx: int) -> List[str]:
    previous = _first_nonempty_before(lines, insert_idx)
    if previous is None or previous == "---":
        return []
    return ["\n", "---\n", "\n"]


def extract_track_block(path: Path, track_id: str) -> Optional[str]:
    lines = _read_lines(path)
    bounds = _find_track_bounds(lines, track_id)
    if not bounds:
        return None
    start_idx, end_idx = bounds
    return "".join(lines[start_idx:end_idx])


def replace_track_block(path: Path, track_id: str, new_block: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_track_bounds(lines, track_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    new_lines = new_block.splitlines(keepends=True)
    lines[start_idx:end_idx] = new_lines
    _write_lines(path, lines)
    return True


def insert_track_block(
    path: Path,
    block: str,
    *,
    after_track_id: Optional[str] = None,
    before_track_id: Optional[str] = None,
) -> bool:
    lines = _read_lines(path)

    insert_idx = len(lines)
    if after_track_id:
        bounds = _find_track_bounds(lines, after_track_id)
        if not bounds:
            return False
        _, insert_idx = bounds
    elif before_track_id:
        bounds = _find_track_bounds(lines, before_track_id)
        if not bounds:
            return False
        insert_idx, _ = bounds

    prefix = _ensure_separator_before(lines, insert_idx)
    block_lines = block.splitlines(keepends=True)
    lines[insert_idx:insert_idx] = prefix + block_lines
    _write_lines(path, lines)
    return True


def remove_track_block(path: Path, track_id: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_track_bounds(lines, track_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    lines[start_idx:end_idx] = []
    _write_lines(path, lines)
    return True


def extract_phase_block(path: Path, phase_id: str) -> Optional[str]:
    lines = _read_lines(path)
    bounds = _find_phase_bounds(lines, phase_id)
    if not bounds:
        return None
    start_idx, end_idx = bounds
    return "".join(lines[start_idx:end_idx])


def replace_phase_block(path: Path, phase_id: str, new_block: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_phase_bounds(lines, phase_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    new_lines = new_block.splitlines(keepends=True)
    lines[start_idx:end_idx] = new_lines
    _write_lines(path, lines)
    return True


def insert_phase_block(
    path: Path,
    track_id: str,
    block: str,
    *,
    after_phase_id: Optional[str] = None,
    before_phase_id: Optional[str] = None,
) -> bool:
    lines = _read_lines(path)
    track_bounds = _find_track_bounds(lines, track_id)
    if not track_bounds:
        return False
    track_start, track_end = track_bounds

    insert_idx = track_end
    if after_phase_id:
        bounds = _find_phase_bounds(lines[track_start:track_end], after_phase_id)
        if not bounds:
            return False
        _, rel_end = bounds
        insert_idx = track_start + rel_end
    elif before_phase_id:
        bounds = _find_phase_bounds(lines[track_start:track_end], before_phase_id)
        if not bounds:
            return False
        rel_start, _ = bounds
        insert_idx = track_start + rel_start
    else:
        last_phase_end = None
        idx = track_start
        while idx < track_end:
            line = lines[idx].strip()
            if parse_phase_heading(line):
                bounds = _find_phase_bounds(lines[idx:track_end], parse_phase_heading(line)[0])
                if bounds:
                    _, rel_end = bounds
                    last_phase_end = idx + rel_end
                    idx = last_phase_end
                    continue
            idx += 1
        if last_phase_end:
            insert_idx = last_phase_end

    block_lines = block.splitlines(keepends=True)
    lines[insert_idx:insert_idx] = ["\n"] + block_lines if lines and lines[insert_idx - 1].strip() else block_lines
    _write_lines(path, lines)
    return True


def remove_phase_block(path: Path, phase_id: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_phase_bounds(lines, phase_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    lines[start_idx:end_idx] = []
    _write_lines(path, lines)
    return True


def extract_task_block(path: Path, task_id: str) -> Optional[str]:
    lines = _read_lines(path)
    bounds = _find_task_bounds(lines, task_id)
    if not bounds:
        return None
    start_idx, end_idx = bounds
    return "".join(lines[start_idx:end_idx])


def replace_task_block(path: Path, task_id: str, new_block: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_task_bounds(lines, task_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    new_lines = new_block.splitlines(keepends=True)
    lines[start_idx:end_idx] = new_lines
    _write_lines(path, lines)
    return True


def insert_task_block(
    path: Path,
    block: str,
    *,
    after_task_id: Optional[str] = None,
    before_task_id: Optional[str] = None,
) -> bool:
    lines = _read_lines(path)
    insert_idx = len(lines)

    if after_task_id:
        bounds = _find_task_bounds(lines, after_task_id)
        if not bounds:
            return False
        _, insert_idx = bounds
    elif before_task_id:
        bounds = _find_task_bounds(lines, before_task_id)
        if not bounds:
            return False
        insert_idx, _ = bounds
    else:
        for idx in range(len(lines) - 1, -1, -1):
            if lines[idx].strip().lower() == "## tasks":
                insert_idx = idx + 1
                break

    block_lines = block.splitlines(keepends=True)
    lines[insert_idx:insert_idx] = ["\n"] + block_lines if insert_idx > 0 and lines[insert_idx - 1].strip() else block_lines
    _write_lines(path, lines)
    return True


def remove_task_block(path: Path, task_id: str) -> bool:
    lines = _read_lines(path)
    bounds = _find_task_bounds(lines, task_id)
    if not bounds:
        return False
    start_idx, end_idx = bounds
    lines[start_idx:end_idx] = []
    _write_lines(path, lines)
    return True
