"""
Task command implementation for Maestro CLI.

Commands:
- maestro task list [filters] - List tasks across all tracks/phases
- maestro task add <name> - Add new task
- maestro task remove <id> - Remove task
- maestro task <id> - Show task details
- maestro task <id> show - Show task details
- maestro task <id> edit - Edit task in $EDITOR
- maestro task <id> complete - Mark task as complete
- maestro task <id> set - Set current task context
"""

import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from maestro.data import parse_todo_md, parse_done_md, parse_phase_md, parse_config_md
from maestro.data.markdown_writer import (
    escape_asterisk_text,
    extract_phase_block,
    extract_task_block,
    insert_task_block,
    remove_task_block,
    replace_phase_block,
    replace_task_block,
    update_task_metadata,
    update_task_heading_status,
)
from .track import (
    _box_chars,
    _display_width,
    _pad_to_width,
    _style_text,
    _truncate,
    _status_display,
    resolve_track_identifier,
)
from .status_utils import allowed_statuses, normalize_status, status_badge, status_timestamp


def _parse_todo_safe(todo_path: Path, verbose: bool = False) -> Optional[dict]:
    try:
        return parse_todo_md(str(todo_path))
    except Exception as exc:
        if verbose:
            print(f"Verbose: Error parsing {todo_path}: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error parsing {todo_path}. Use --verbose for more details.")
        return None


def _parse_done_safe(done_path: Path, verbose: bool = False) -> Optional[dict]:
    try:
        return parse_done_md(str(done_path))
    except Exception as exc:
        if verbose:
            print(f"Verbose: Error parsing {done_path}: {exc}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error parsing {done_path}. Use --verbose for more details.")
        return None


def _available_phase_ids(verbose: bool = False) -> List[str]:
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return []
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return []
    phase_ids = []
    for track in data.get('tracks', []):
        for phase in track.get('phases', []):
            phase_id = phase.get('phase_id')
            if phase_id:
                phase_ids.append(phase_id)
    return phase_ids


def _available_track_ids(verbose: bool = False) -> List[str]:
    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        return []
    data = _parse_todo_safe(todo_path, verbose=verbose)
    if not data:
        return []
    return [track.get('track_id') for track in data.get('tracks', []) if track.get('track_id')]


def _normalize_task_status(status: Optional[str], completed: bool, phase_status: Optional[str]) -> str:
    if completed:
        return "done"
    if status:
        normalized = status.strip().lower().replace("-", "_")
        if normalized in {"done", "completed", "complete"}:
            return "done"
        if normalized in {"in_progress", "inprogress", "in-progress"}:
            return "in_progress"
        if normalized in {"planned", "plan", "todo"}:
            return "planned"
        if normalized in {"proposed", "prop"}:
            return "proposed"
        return normalized
    if phase_status:
        phase_normalized = phase_status.strip().lower()
        if phase_normalized in {"done", "in_progress", "planned", "proposed"}:
            return phase_normalized
    return "planned"


def _collect_phase_index(verbose: bool = False) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    todo_path = Path('docs/todo.md')
    done_path = Path('docs/done.md')
    phase_index: Dict[str, Dict[str, str]] = {}
    phase_order: List[str] = []

    def add_phase(track: Dict, phase: Dict) -> None:
        phase_id = phase.get('phase_id')
        if not phase_id:
            return
        entry = phase_index.setdefault(phase_id, {})
        track_id = track.get('track_id')
        track_name = track.get('name')
        if track_id and not entry.get('track_id'):
            entry['track_id'] = track_id
        if track_name and not entry.get('track_name'):
            entry['track_name'] = track_name
        if phase.get('name') and not entry.get('phase_name'):
            entry['phase_name'] = phase.get('name')
        if phase.get('status') and not entry.get('phase_status'):
            entry['phase_status'] = phase.get('status')
        if phase_id not in phase_order:
            phase_order.append(phase_id)

    if todo_path.exists():
        todo_data = _parse_todo_safe(todo_path, verbose=verbose)
        if todo_data:
            for track in todo_data.get('tracks', []):
                for phase in track.get('phases', []):
                    add_phase(track, phase)

    if done_path.exists():
        done_data = _parse_done_safe(done_path, verbose=verbose)
        if done_data:
            for track in done_data.get('tracks', []):
                for phase in track.get('phases', []):
                    add_phase(track, phase)

    phases_dir = Path('docs/phases')
    if phases_dir.exists():
        for phase_file in sorted(phases_dir.glob('*.md')):
            phase_id = phase_file.stem
            if phase_id not in phase_index:
                phase_index[phase_id] = {}
            if phase_id not in phase_order:
                phase_order.append(phase_id)

    return phase_index, phase_order


def _collect_task_entries(verbose: bool = False) -> List[Dict[str, str]]:
    phases_dir = Path('docs/phases')
    if not phases_dir.exists():
        return []

    phase_index, phase_order = _collect_phase_index(verbose=verbose)
    tasks: List[Dict[str, str]] = []

    for phase_id in phase_order:
        phase_file = phases_dir / f"{phase_id}.md"
        if not phase_file.exists():
            continue
        phase = parse_phase_md(str(phase_file))
        phase_info = phase_index.get(phase_id, {})
        phase_name = phase.get('name') or phase_info.get('phase_name') or phase_id
        phase_status = phase_info.get('phase_status')
        track_id = phase_info.get('track_id') or phase.get('track_id') or "N/A"
        track_name = phase_info.get('track_name') or phase.get('track') or "Unnamed Track"

        for task in phase.get('tasks', []):
            task_id = task.get('task_id') or task.get('task_number') or "N/A"
            completed = bool(task.get('completed', False))
            task_status = _normalize_task_status(task.get('status'), completed, phase_status)
            tasks.append({
                "task_id": task_id,
                "name": task.get('name', 'Unnamed Task'),
                "status": task_status,
                "priority": task.get('priority', 'N/A'),
                "phase_id": phase_id,
                "phase_name": phase_name,
                "phase_status": phase_status,
                "track_id": track_id,
                "track_name": track_name,
                "phase_file": str(phase_file),
                "_task": task,
            })

    for idx, task in enumerate(tasks, 1):
        task["list_number"] = idx

    return tasks


def _parse_task_list_filters(tokens: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    status_filter = None
    track_filter = None
    phase_filter = None
    extras: List[str] = []
    status_aliases = {
        'plan': 'planned',
        'planned': 'planned',
        'prop': 'proposed',
        'proposed': 'proposed',
        'done': 'done',
        'inprogress': 'in_progress',
        'in-progress': 'in_progress',
        'in_progress': 'in_progress',
    }
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        normalized = token.lower()
        if normalized in status_aliases:
            status_filter = status_aliases[normalized]
            idx += 1
            continue
        if normalized in {'track', 'tr'}:
            if idx + 1 >= len(tokens):
                extras.append(token)
                break
            track_filter = tokens[idx + 1]
            idx += 2
            continue
        if normalized in {'phase', 'ph'}:
            if idx + 1 >= len(tokens):
                extras.append(token)
                break
            phase_filter = tokens[idx + 1]
            idx += 2
            continue
        if len(tokens) == 1 and not phase_filter and not track_filter and not status_filter:
            phase_filter = token
            idx += 1
            continue
        if not phase_filter:
            phase_filter = token
            idx += 1
            continue
        extras.append(token)
        idx += 1

    return status_filter, track_filter, phase_filter, extras


def list_tasks(args):
    """
    List all tasks from phase files.

    Supports optional filters:
      - plan/prop/done for status
      - track <id|#> to filter by track
      - phase <id> to filter by phase
    """
    from maestro.config.settings import get_settings

    tokens = getattr(args, 'filters', None) or []
    status_filter, track_filter, phase_filter, extras = _parse_task_list_filters(tokens)
    if extras:
        print(f"Error: Unrecognized filters: {' '.join(extras)}")
        print("Use 'maestro task help' for list filter usage.")
        return 1

    if track_filter:
        verbose = getattr(args, 'verbose', False)
        resolved = resolve_track_identifier(track_filter, verbose=verbose) if track_filter.isdigit() else track_filter
        if track_filter.isdigit() and not resolved:
            print(f"Error: Track '{track_filter}' not found.")
            if verbose:
                available = _available_track_ids(verbose=verbose)
                if available:
                    print(f"Verbose: Available tracks: {', '.join(available)}")
            return 1
        track_filter = resolved

    tasks = _collect_task_entries(verbose=getattr(args, 'verbose', False))

    if phase_filter:
        tasks = [task for task in tasks if task.get('phase_id') == phase_filter]
    if track_filter:
        tasks = [task for task in tasks if task.get('track_id') == track_filter]
    if status_filter:
        tasks = [task for task in tasks if task.get('status') == status_filter]

    if not tasks:
        print("No tasks found.")
        return 0

    settings = get_settings()
    unicode_symbols = settings.unicode_symbols
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    term_width = max(term_width, 20)
    box = _box_chars(unicode_symbols)

    idx_width = max(_display_width('#'), max((_display_width(str(t.get('list_number', ''))) for t in tasks), default=0))
    task_id_width = max(_display_width('Task ID'), max((_display_width(t.get('task_id', 'N/A')) for t in tasks), default=0))
    name_width = max(_display_width('Name'), max((_display_width(t.get('name', 'Unnamed Task')) for t in tasks), default=0))
    track_width = max(_display_width('Track'), max((_display_width(t.get('track_id', 'N/A')) for t in tasks), default=0))
    phase_width = max(_display_width('Phase'), max((_display_width(t.get('phase_id', 'N/A')) for t in tasks), default=0))
    status_width = max(
        _display_width('Status'),
        max((_display_width(_status_display(t.get('status', 'unknown'), unicode_symbols)[0]) for t in tasks), default=0),
    )

    col_widths = [idx_width, task_id_width, name_width, track_width, phase_width, status_width]
    ncol = len(col_widths)
    content_width = sum(w + 2 for w in col_widths) + (ncol - 1) * 2
    inner_width = min(term_width - 2, max(content_width, 20))
    available = inner_width - (ncol - 1) * 2 - (2 * ncol)
    name_width = max(_display_width('Name'), available - (idx_width + task_id_width + track_width + phase_width + status_width))
    col_widths = [idx_width, task_id_width, name_width, track_width, phase_width, status_width]

    headers = ['#', 'Task ID', 'Name', 'Track', 'Phase', 'Status']
    header_cells = []
    for header, width in zip(headers, col_widths):
        header_cells.append(" " + _pad_to_width(header, width) + " ")
    header_line = box['vertical'] + _pad_to_width("  ".join(header_cells), inner_width) + box['vertical']

    print()
    print(_style_text(box['top_left'] + box['horizontal'] * inner_width + box['top_right'], color='yellow'))
    print(_style_text(header_line, color='bright_white', bold=True))
    print(_style_text(box['mid_left'] + box['mid_horizontal'] * inner_width + box['mid_right'], color='yellow'))

    for task in tasks:
        status_display, status_color = _status_display(task.get('status', 'unknown'), unicode_symbols)
        row_cells = [
            " " + _pad_to_width(str(task.get('list_number', '')), idx_width) + " ",
            " " + _pad_to_width(_truncate(task.get('task_id', 'N/A'), task_id_width, unicode_symbols), task_id_width) + " ",
            " " + _pad_to_width(_truncate(task.get('name', 'Unnamed Task'), name_width, unicode_symbols), name_width) + " ",
            " " + _pad_to_width(_truncate(task.get('track_id', 'N/A'), track_width, unicode_symbols), track_width) + " ",
            " " + _pad_to_width(_truncate(task.get('phase_id', 'N/A'), phase_width, unicode_symbols), phase_width) + " ",
            _style_text(" " + _pad_to_width(status_display, status_width) + " ", color=status_color),
        ]
        row_line = box['vertical'] + _pad_to_width("  ".join(row_cells), inner_width) + box['vertical']
        print(row_line)

    print(_style_text(box['bottom_left'] + box['horizontal'] * inner_width + box['bottom_right'], color='yellow'))
    print(_style_text(f"Total: {len(tasks)} tasks", color='bright_black', dim=True))
    print(_style_text("Use 'maestro task <#>' or 'maestro task <id>' to view details", color='bright_black', dim=True))

    return 0


def _resolve_task_identifier(task_identifier: str, verbose: bool = False) -> Optional[Dict[str, str]]:
    tasks = _collect_task_entries(verbose=verbose)

    for task in tasks:
        if task.get('task_id') == task_identifier or task.get('_task', {}).get('task_number') == task_identifier:
            return task

    if task_identifier.isdigit():
        index = int(task_identifier)
        for task in tasks:
            if task.get('list_number') == index:
                return task

    return None


def show_task(task_id: str, args):
    """
    Show detailed information about a specific task.

    Searches through all phase files to find the task.
    """
    verbose = getattr(args, 'verbose', False)
    task_entry = _resolve_task_identifier(task_id, verbose=verbose)
    if not task_entry:
        print(f"Error: Task '{task_id}' not found.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1
    task = task_entry.get('_task', {})
    phase_info = {
        'id': task_entry.get('phase_id', 'N/A'),
        'name': task_entry.get('phase_name', 'Unnamed'),
        'file': task_entry.get('phase_file', 'N/A'),
    }
    completed = bool(task.get('completed', False))
    status_value = _normalize_task_status(task.get('status'), completed, task_entry.get('phase_status'))
    from maestro.config.settings import get_settings
    settings = get_settings()
    status_display, _ = _status_display(status_value, settings.unicode_symbols)

    # Display task details
    print()
    print("=" * 80)
    print(f"TASK: {task.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    # Metadata
    print(f"ID:          {task.get('task_id', task.get('task_number', 'N/A'))}")
    print(f"Phase:       {phase_info['name']} ({phase_info['id']})")
    print(f"Priority:    {task.get('priority', 'N/A')}")
    print(f"Status:      {status_display}")
    print(f"Est. Hours:  {task.get('estimated_hours', 'N/A')}")
    print()

    # Description
    description = task.get('description', [])
    if description:
        print("Description:")
        for line in description:
            if line.strip():
                print(f"  {line}")
        print()

    # Subtasks
    subtasks = task.get('subtasks', [])
    if subtasks:
        print(f"Subtasks ({len(subtasks)}):")
        for i, subtask in enumerate(subtasks, 1):
            status = '✅' if subtask.get('completed', False) else '☐'
            content = subtask.get('content', 'Unnamed')
            indent = subtask.get('indent', 0)
            indent_str = '  ' * (indent // 2)
            print(f"  {indent_str}{status} {content}")
        print()

    # Source file
    print(f"Source: {phase_info['file']}")
    print()

    return 0


def _resolve_text_input(args) -> str:
    if getattr(args, 'text_file', None):
        return Path(args.text_file).read_text(encoding='utf-8')
    return sys.stdin.read()


def _find_task_file(task_id: str) -> Optional[Path]:
    phases_dir = Path('docs/phases')
    if not phases_dir.exists():
        return None
    for phase_file in phases_dir.glob('*.md'):
        phase = parse_phase_md(str(phase_file))
        for task in phase.get('tasks', []):
            if task.get('task_id') == task_id or task.get('task_number') == task_id:
                return phase_file
    return None


def _find_task_line(lines: List[str], task_id: str) -> Optional[int]:
    pattern = re.compile(rf'\*\*{re.escape(task_id)}\s*:', re.IGNORECASE)
    for idx, line in enumerate(lines):
        if pattern.search(line):
            return idx
    return None


def _insert_task_in_todo(
    todo_path: Path,
    phase_id: str,
    task_id: str,
    name: str,
    desc_lines: List[str],
    after_task_id: Optional[str],
    before_task_id: Optional[str],
) -> None:
    block = extract_phase_block(todo_path, phase_id)
    if not block:
        return

    lines = block.splitlines(keepends=True)
    insert_idx = len(lines)

    if after_task_id:
        task_idx = _find_task_line(lines, after_task_id)
        if task_idx is not None:
            insert_idx = task_idx + 1
            while insert_idx < len(lines) and not lines[insert_idx].lstrip().startswith("- ["):
                insert_idx += 1
    elif before_task_id:
        task_idx = _find_task_line(lines, before_task_id)
        if task_idx is not None:
            insert_idx = task_idx

    task_lines = [f"- [ ] **{task_id}: {name}**\n"]
    for line in desc_lines:
        if line.strip():
            task_lines.append(f"  - {line.strip()}\n")

    lines[insert_idx:insert_idx] = task_lines + ["\n"]
    replace_phase_block(todo_path, phase_id, "".join(lines))


def _remove_task_from_todo(todo_path: Path, task_id: str) -> None:
    text = todo_path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf'^\s*-\s+\[[ x]\]\s+\*\*{re.escape(task_id)}\s*:', re.IGNORECASE)
    idx = 0
    while idx < len(lines):
        if pattern.search(lines[idx]):
            start = idx
            idx += 1
            while idx < len(lines):
                if lines[idx].lstrip().startswith("- [") and pattern.search(lines[idx]) is None:
                    break
                if lines[idx].startswith("### Phase") or lines[idx].startswith("## "):
                    break
                idx += 1
            del lines[start:idx]
            break
        idx += 1
    todo_path.write_text("".join(lines), encoding='utf-8')


def _set_task_checkbox(todo_path: Path, task_id: str, checked: bool) -> bool:
    text = todo_path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf'^(\s*-\s+\[)[ x](\]\s+\*\*{re.escape(task_id)}\s*:)', re.IGNORECASE)
    for idx, line in enumerate(lines):
        if pattern.match(line):
            mark = 'x' if checked else ' '
            lines[idx] = pattern.sub(lambda m: f"{m.group(1)}{mark}{m.group(2)}", line)
            todo_path.write_text("".join(lines), encoding='utf-8')
            return True
    return False


def add_task(name: str, args):
    """
    Add a new task to a phase.

    Args:
        name: Name of the new task
        args: Command arguments
    """
    from maestro.config.settings import get_settings

    verbose = getattr(args, 'verbose', False)
    phase_id = getattr(args, 'phase_id', None)
    if not phase_id:
        settings = get_settings()
        phase_id = settings.current_phase
    if not phase_id:
        print("Error: Phase ID required. Usage: maestro task add --phase <phase_id> <name>")
        return 1

    todo_path = Path('docs/todo.md')
    if not todo_path.exists():
        print("Error: docs/todo.md not found.")
        print("Use 'maestro track add' and 'maestro phase add' to create phases first.")
        return 1

    data = _parse_todo_safe(todo_path, verbose=verbose)
    if data is None:
        return 1
    phase_info = None
    track_info = None
    for track in data.get('tracks', []):
        for phase in track.get('phases', []):
            if phase.get('phase_id') == phase_id:
                phase_info = phase
                track_info = track
                break
        if phase_info:
            break
    if not phase_info:
        print(f"Error: Phase '{phase_id}' not found in docs/todo.md.")
        if verbose:
            available = _available_phase_ids(verbose=verbose)
            if available:
                print(f"Verbose: Available phases: {', '.join(available)}")
        return 1

    task_id = getattr(args, 'task_id_opt', None)
    if not task_id:
        task_id = f"{phase_id}.1"

    desc_lines = getattr(args, 'desc', None) or []

    phases_dir = Path('docs/phases')
    phases_dir.mkdir(parents=True, exist_ok=True)
    phase_path = phases_dir / f"{phase_id}.md"
    if not phase_path.exists():
        track_name = track_info.get('name', 'Unknown Track') if track_info else 'Unknown Track'
        escaped_track_name = escape_asterisk_text(track_name)
        escaped_phase_id = escape_asterisk_text(phase_id)
        escaped_track_id = escape_asterisk_text(track_info.get('track_id', '') if track_info else '')
        header = [
            f"# Phase {phase_id}: {phase_info.get('name', phase_id)} 📋 **[Planned]**\n",
            "\n",
            f"- *phase_id*: *{escaped_phase_id}*\n",
            f"- *track*: *{escaped_track_name}*\n",
            f"- *track_id*: *{escaped_track_id}*\n",
            "- *status*: *planned*\n",
            "- *completion*: 0\n",
            "\n",
            "## Tasks\n",
            "\n",
        ]
        phase_path.write_text("".join(header), encoding='utf-8')

    escaped_task_id = escape_asterisk_text(task_id)
    task_block = [
        f"### Task {task_id}: {name}\n",
        "\n",
        f"- *task_id*: *{escaped_task_id}*\n",
        "- *priority*: *P2*\n",
        "- *status*: *planned*\n",
        "\n",
    ]
    for line in desc_lines:
        if line.strip():
            task_block.append(f"- {line.strip()}\n")
    task_block.append("\n")

    inserted = insert_task_block(
        phase_path,
        "".join(task_block),
        after_task_id=getattr(args, 'after', None),
        before_task_id=getattr(args, 'before', None),
    )
    if not inserted:
        print("Error: Unable to insert task block.")
        return 1

    _insert_task_in_todo(todo_path, phase_id, task_id, name, desc_lines, getattr(args, 'after', None), getattr(args, 'before', None))

    print(f"Added task '{task_id}' ({name}) to phase '{phase_id}'.")
    return 0


def remove_task(task_id: str, args):
    """
    Remove a task from a phase.

    Args:
        task_id: Task ID to remove
        args: Command arguments
    """
    verbose = getattr(args, 'verbose', False)
    phase_file = _find_task_file(task_id)
    if not phase_file:
        print(f"Error: Task '{task_id}' not found in any phase file.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1

    if not remove_task_block(phase_file, task_id):
        print(f"Error: Task '{task_id}' not found in {phase_file}.")
        return 1

    todo_path = Path('docs/todo.md')
    if todo_path.exists():
        _remove_task_from_todo(todo_path, task_id)

    print(f"Removed task: {task_id}")
    return 0


def complete_task(task_id: str, args):
    """
    Mark a task as complete.

    Args:
        task_id: Task ID to complete
        args: Command arguments
    """
    setattr(args, 'status', 'done')
    return set_task_status(task_id, args)


def set_task_status(task_id: str, args) -> int:
    """
    Update a task status in its phase file and docs/todo.md checkbox.
    """
    status_value = normalize_status(getattr(args, 'status', None))
    if not status_value:
        print(f"Error: Unknown status. Allowed: {allowed_statuses()}.")
        return 1

    verbose = getattr(args, 'verbose', False)
    phase_file = _find_task_file(task_id)
    if not phase_file:
        print(f"Error: Task '{task_id}' not found in any phase file.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1

    if not update_task_metadata(phase_file, task_id, 'status', status_value):
        print(f"Error: Task '{task_id}' not found in {phase_file}.")
        return 1

    update_task_heading_status(phase_file, task_id, status_badge(status_value))

    summary = getattr(args, 'summary', None)
    if summary:
        update_task_metadata(phase_file, task_id, 'status_summary', summary)
    else:
        print("Note: consider adding --summary to capture the status change context.")

    changed_at = status_timestamp()
    update_task_metadata(phase_file, task_id, 'status_changed', changed_at)

    todo_path = Path('docs/todo.md')
    if todo_path.exists():
        _set_task_checkbox(todo_path, task_id, status_value == 'done')

    print(f"Updated task '{task_id}' status to '{status_value}'.")
    return 0


def edit_task(task_id: str, args):
    """
    Edit a task in $EDITOR.

    Opens the phase file containing the task.
    """
    import os
    import subprocess

    verbose = getattr(args, 'verbose', False)
    phase_file = _find_task_file(task_id)
    if not phase_file:
        print(f"Error: Task '{task_id}' not found in any phase file.")
        if verbose:
            print("Verbose: Use 'maestro task list' to see available task IDs.")
        return 1

    block = extract_task_block(phase_file, task_id)
    if not block:
        print(f"Error: Task '{task_id}' not found in {phase_file}.")
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
        if not replace_task_block(phase_file, task_id, new_block):
            print("Error: Failed to update task block.")
            return 1
        print(f"Updated task '{task_id}'.")
        return 0
    except Exception as e:
        print(f"Error opening editor: {e}")
        return 1


def set_task_context(task_id: str, args):
    """Set the current task context.

    Args:
        task_id: Task ID to set as current
        args: Command arguments
    """
    from maestro.config.settings import get_settings

    # Find task and set context including parent phase and track
    # For now, we'll just set the task ID directly
    # In a more complex implementation, we might want to look up the parent phase and track
    settings = get_settings()
    settings.current_task = task_id
    # We could also set the current_phase and current_track if we had access to the phase/track info
    settings.save()

    print(f"Context set to task: {task_id}")
    return 0


def handle_task_command(args):
    """
    Main handler for task commands.

    Routes to appropriate subcommand handler.
    """
    # Handle 'maestro task discuss <task_id>' (new subcommand format)
    if hasattr(args, 'task_subcommand') and args.task_subcommand in ['discuss', 'd']:
        if hasattr(args, 'task_id_arg'):
            from .discuss import handle_task_discuss
            return handle_task_discuss(args.task_id_arg, args)

    # Handle 'maestro task list [phase_id]'
    if hasattr(args, 'task_subcommand'):
        if args.task_subcommand in ['list', 'ls', 'l']:
            return list_tasks(args)
        elif args.task_subcommand in ['add', 'a']:
            if not hasattr(args, 'name') or not args.name:
                print("Error: Task name required. Usage: maestro task add <name>")
                return 1
            name = " ".join(args.name) if isinstance(args.name, list) else args.name
            return add_task(name, args)
        elif args.task_subcommand in ['remove', 'rm', 'r']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task remove <id>")
                return 1
            return remove_task(args.task_id, args)
        elif args.task_subcommand in ['status', 'set-status']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task status <id> <status>")
                return 1
            if not getattr(args, 'status', None):
                print("Error: Status required. Usage: maestro task status <id> <status>")
                return 1
            return set_task_status(args.task_id, args)
        elif args.task_subcommand in ['text', 'raw']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task text <id>")
                return 1
            phase_file = _find_task_file(args.task_id)
            if not phase_file:
                print(f"Error: Task '{args.task_id}' not found in any phase file.")
                return 1
            block = extract_task_block(phase_file, args.task_id)
            if not block:
                print(f"Error: Task '{args.task_id}' not found in {phase_file}.")
                return 1
            print(block.rstrip())
            return 0
        elif args.task_subcommand in ['set-text', 'setraw']:
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task set-text <id> [--file path]")
                return 1
            phase_file = _find_task_file(args.task_id)
            if not phase_file:
                print(f"Error: Task '{args.task_id}' not found in any phase file.")
                return 1
            new_block = _resolve_text_input(args)
            if not new_block.strip():
                print("Error: Replacement text is empty.")
                return 1
            if not replace_task_block(phase_file, args.task_id, new_block):
                print(f"Error: Task '{args.task_id}' not found in {phase_file}.")
                return 1
            print(f"Updated task '{args.task_id}'.")
            return 0
        elif args.task_subcommand in ['help', 'h']:
            print_task_help()
            return 0

    # Handle 'maestro task <id>' or 'maestro task <id> <subcommand>'
    if hasattr(args, 'task_id_arg') and args.task_id_arg:
        task_id = args.task_id_arg

        # Check if there's a task-specific subcommand
        subcommand = getattr(args, 'task_item_subcommand', None)
        if subcommand:
            if subcommand == 'show':
                return show_task(task_id, args)
            elif subcommand == 'edit':
                return edit_task(task_id, args)
            elif subcommand == 'complete':
                return complete_task(task_id, args)
            elif subcommand == 'discuss':
                from .discuss import handle_task_discuss
                return handle_task_discuss(task_id, args)
            elif subcommand == 'set':
                return set_task_context(task_id, args)
            elif subcommand == 'help' or subcommand == 'h':
                print_task_item_help()
                return 0
        # Default to 'show' if no subcommand
        return show_task(task_id, args)

    # No subcommand - show help or list based on context
    # Check if we have a current phase set
    config_path = Path('docs/config.md')
    if config_path.exists():
        config = parse_config_md(str(config_path))
        current_phase = config.get('current_phase')
        if current_phase:
            # List tasks in current phase
            args.filters = [current_phase]
            return list_tasks(args)

    print_task_help()
    return 0


def print_task_help():
    """Print help for task commands."""
    help_text = """
maestro task - Manage project tasks

USAGE:
    maestro task list [filters]           List tasks across all tracks/phases
    maestro task add <name>               Add new task
    maestro task remove <id>              Remove a task
    maestro task <id>                     Show task details
    maestro task <id> show                Show task details
    maestro task <id> edit                Edit task in $EDITOR
    maestro task <id> complete            Mark task as complete
    maestro task <id> status <status>     Update task status
    maestro task text <id>                Show raw task block
    maestro task set-text <id>            Replace task block (stdin or --file)
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

LIST FILTERS:
    plan | prop | done                    Filter by task status
    track <id|#>                          Filter by track ID or number
    phase <id>                            Filter by phase ID

ALIASES:
    list:     ls, l
    add:      a
    remove:   rm, r
    show:     sh
    edit:     e
    complete: c, done
    status:   set-status
    discuss:  d
    set:      st
    text:     raw
    set-text: setraw

EXAMPLES:
    maestro task list                     # List all tasks
    maestro task list plan                # List planned tasks
    maestro task list track umk           # List tasks in track 'umk'
    maestro task list phase umk1          # List tasks in phase 'umk1'
    maestro task list track umk phase umk1
    maestro task 12                       # Show task by list number
    maestro task cli-tpt-1-1              # Show task details
    maestro task cli-tpt-1-1 edit         # Edit task in $EDITOR
    maestro task cli-tpt-1-1 complete     # Mark task as complete
    maestro task cli-tpt-1-1 status done --summary "Finished validation"
    maestro task cli-tpt-1-1 discuss      # Discuss task with AI
    maestro task cli-tpt-1-1 set          # Set current task context
"""
    print(help_text)


def print_task_item_help():
    """Print help for task item commands."""
    help_text = """
maestro task <id> - Manage a specific task

USAGE:
    maestro task <id> show                Show task details
    maestro task <id> edit                Edit task in $EDITOR
    maestro task <id> complete            Mark task as complete
    maestro task <id> status <status>     Update task status
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

ALIASES:
    show:     sh
    edit:     e
    complete: c, done
    status:   set-status
    discuss:  d
    set:      st

EXAMPLES:
    maestro task cli-tpt-1-1 show
    maestro task cli-tpt-1-1 edit
    maestro task cli-tpt-1-1 complete
    maestro task cli-tpt-1-1 status in_progress
    maestro task cli-tpt-1-1 discuss
    maestro task cli-tpt-1-1 set
"""
    print(help_text)


def add_task_parser(subparsers):
    """
    Add task command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    if len(sys.argv) >= 3 and sys.argv[1] in ['task', 'ta']:
        arg = sys.argv[2]
        known_subcommands = [
            'list', 'ls', 'l', 'add', 'a', 'remove', 'rm', 'r', 'text', 'raw',
            'set-text', 'setraw', 'help', 'h', 'discuss', 'd', 'show', 'sh',
            'status', 'set-status'
        ]
        # Only modify the command if it's not a global argument like --help
        if not arg.startswith('-') and arg not in known_subcommands and arg not in ['--help', '-h']:
            if len(sys.argv) >= 4 and sys.argv[3] in [
                'show', 'sh', 'edit', 'e', 'complete', 'c', 'done', 'discuss', 'd',
                'set', 'st', 'help', 'h', 'status', 'set-status'
            ]:
                subcommand = sys.argv[3]
                task_id = sys.argv[2]
                if subcommand in ['status', 'set-status']:
                    sys.argv[2] = subcommand
                    sys.argv[3] = task_id
                else:
                    sys.argv[2] = 'show'
                    sys.argv[3] = task_id
                    sys.argv.insert(4, subcommand)
            else:
                sys.argv.insert(2, 'show')

    # Main task command
    task_parser = subparsers.add_parser(
        'task',
        aliases=['ta'],
        help='Manage project tasks'
    )

    # Task subcommands
    task_subparsers = task_parser.add_subparsers(
        dest='task_subcommand',
        help='Task subcommands'
    )

    # maestro task list [phase_id]
    task_list_parser = task_subparsers.add_parser(
        'list',
        aliases=['ls', 'l'],
        help='List all tasks (or tasks in phase)'
    )
    task_list_parser.add_argument(
        'filters',
        nargs='*',
        help='Optional filters: [plan|prop|done] [track <id|#>] [phase <id>]'
    )

    # maestro task show <id> [action]
    task_show_parser = task_subparsers.add_parser(
        'show',
        aliases=['sh'],
        help='Show task details'
    )
    task_show_parser.add_argument('task_id_arg', help='Task ID (or list #)')
    task_show_parser.add_argument(
        'task_item_subcommand',
        nargs='?',
        choices=['show', 'sh', 'edit', 'e', 'complete', 'c', 'done', 'discuss', 'd', 'set', 'st', 'help', 'h'],
        help='Task item subcommand (show/edit/complete/discuss/set)'
    )

    # maestro task add <name>
    task_add_parser = task_subparsers.add_parser(
        'add',
        aliases=['a'],
        help='Add new task'
    )
    task_add_parser.add_argument('name', nargs='+', help='Task name')
    task_add_parser.add_argument('--id', dest='task_id_opt', help='Task ID (default: <phase_id>.1)')
    task_add_parser.add_argument('--phase', dest='phase_id', help='Phase ID to add the task to')
    task_add_parser.add_argument('--after', help='Insert after task ID')
    task_add_parser.add_argument('--before', help='Insert before task ID')
    task_add_parser.add_argument('--desc', action='append', help='Description line (repeatable)')

    # maestro task remove <id>
    task_remove_parser = task_subparsers.add_parser(
        'remove',
        aliases=['rm', 'r'],
        help='Remove a task'
    )
    task_remove_parser.add_argument('task_id', help='Task ID to remove')

    task_status_parser = task_subparsers.add_parser(
        'status',
        aliases=['set-status'],
        help='Update task status'
    )
    task_status_parser.add_argument('task_id', help='Task ID to update')
    task_status_parser.add_argument('status', help='Status (planned, in_progress, done, proposed)')
    task_status_parser.add_argument('--summary', help='Status change summary')

    task_text_parser = task_subparsers.add_parser(
        'text',
        aliases=['raw'],
        help='Show raw task block from phase file'
    )
    task_text_parser.add_argument('task_id', help='Task ID to show')

    task_set_text_parser = task_subparsers.add_parser(
        'set-text',
        aliases=['setraw'],
        help='Replace task block from stdin or a file'
    )
    task_set_text_parser.add_argument('task_id', help='Task ID to replace')
    task_set_text_parser.add_argument('--file', dest='text_file', help='Read replacement text from file')

    # maestro task help
    task_subparsers.add_parser(
        'help',
        aliases=['h'],
        help='Show help for task commands'
    )

    # NOTE: task_id_arg is handled via the "show" subcommand to allow "task <id>" parsing.
    task_parser.add_argument(
        '--mode',
        choices=['editor', 'terminal'],
        help='Discussion mode (editor or terminal)'
    )
    task_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )
    task_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose errors and parsing details'
    )

    # maestro task discuss <id>
    task_discuss_parser = task_subparsers.add_parser(
        'discuss',
        aliases=['d'],
        help='Discuss task with AI'
    )
    task_discuss_parser.add_argument('task_id_arg', help='Task ID to discuss')
    task_discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                                     default='editor', help='Discussion mode')
    task_discuss_parser.add_argument('--resume', help='Resume previous discussion session')

    return task_parser


def discuss_task(task_id: str, args):
    """Discuss a specific task with AI."""
    from .discuss import handle_task_discuss
    return handle_task_discuss(task_id, args)
