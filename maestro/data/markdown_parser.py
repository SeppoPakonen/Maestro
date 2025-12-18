"""
Markdown parser for Maestro data format.

This module provides functions to parse markdown files containing project data
in a human-readable, machine-parsable format.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


# ============================================================================
# Task 1.1.1: Basic Parsing Infrastructure
# ============================================================================

def parse_quoted_value(line: str) -> Optional[Tuple[str, Any]]:
    """
    Parse a quoted key-value pair from a line.

    Format: "key": value
    - Strings: "key": "value"
    - Numbers: "key": 123 or "key": 45.67
    - Booleans: "key": true or "key": false
    - Null: "key": null

    Args:
        line: Line of text to parse

    Returns:
        Tuple of (key, value) if match found, None otherwise

    Examples:
        >>> parse_quoted_value('"name": "Test Track"')
        ('name', 'Test Track')
        >>> parse_quoted_value('"priority": 1')
        ('priority', 1)
        >>> parse_quoted_value('"enabled": true')
        ('enabled', True)
    """
    # Pattern: "key": value (with flexible whitespace)
    # Key is in quotes, value can be quoted string, number, boolean, or null
    pattern = r'"([^"]+)"\s*:\s*(.+)$'
    match = re.match(pattern, line.strip())

    if not match:
        return None

    key = match.group(1)
    value_str = match.group(2).strip()

    # Parse value based on format
    # Quoted string
    if value_str.startswith('"') and value_str.endswith('"'):
        value = value_str[1:-1]  # Remove quotes
    # Boolean
    elif value_str == 'true':
        value = True
    elif value_str == 'false':
        value = False
    # Null
    elif value_str == 'null':
        value = None
    # Number
    else:
        try:
            # Try int first
            if '.' not in value_str:
                value = int(value_str)
            else:
                value = float(value_str)
        except ValueError:
            # If parsing fails, treat as string
            value = value_str

    return (key, value)


def parse_status_badge(line: str) -> Optional[str]:
    """
    Parse a status badge emoji and text.

    Format: emoji **[status]** or emoji **status**
    - ✅ Done
    - 🚧 In Progress
    - 📋 Planned
    - 💡 Proposed

    Args:
        line: Line of text containing status badge

    Returns:
        Status string ('done', 'in_progress', 'planned', 'proposed') or None

    Examples:
        >>> parse_status_badge('✅ **Done**')
        'done'
        >>> parse_status_badge('🚧 **[In Progress]**')
        'in_progress'
    """
    # Pattern: (emoji) **[?text]?**
    pattern = r'(✅|🚧|📋|💡)\s*\*\*\[?([^\]]+?)\]?\*\*'
    match = re.search(pattern, line)

    if not match:
        return None

    emoji = match.group(1)

    # Map emoji to status
    emoji_map = {
        '✅': 'done',
        '🚧': 'in_progress',
        '📋': 'planned',
        '💡': 'proposed',
    }

    return emoji_map.get(emoji)


def parse_completion(line: str) -> Optional[int]:
    """
    Parse a completion percentage.

    Format: **N%** or **Completion**: N%

    Args:
        line: Line of text containing completion percentage

    Returns:
        Completion percentage (0-100) or None

    Examples:
        >>> parse_completion('**45%**')
        45
        >>> parse_completion('**Completion**: 67%')
        67
    """
    # Try pattern: **N%**
    pattern1 = r'\*\*(\d+)%\*\*'
    match = re.search(pattern1, line)
    if match:
        return int(match.group(1))

    # Try pattern: **Completion**: N%
    pattern2 = r'\*\*Completion\*\*:\s*(\d+)%'
    match = re.search(pattern2, line)
    if match:
        return int(match.group(1))

    return None


# ============================================================================
# Task 1.1.2: Structured Element Parsing
# ============================================================================

def parse_checkbox(line: str) -> Optional[Tuple[int, bool, str]]:
    """
    Parse a GitHub-flavored markdown checkbox.

    Format: - [ ] or - [x] with optional indentation

    Args:
        line: Line of text containing checkbox

    Returns:
        Tuple of (indent_level, is_checked, content) or None

    Examples:
        >>> parse_checkbox('- [ ] Task 1')
        (0, False, 'Task 1')
        >>> parse_checkbox('  - [x] Subtask 1.1')
        (2, True, 'Subtask 1.1')
    """
    pattern = r'^(\s*)- \[([ x])\]\s+(.+)$'
    match = re.match(pattern, line)

    if not match:
        return None

    indent_str = match.group(1)
    check_char = match.group(2)
    content = match.group(3)

    # Calculate indent level (2 spaces = 1 level)
    indent_level = len(indent_str)
    is_checked = (check_char.lower() == 'x')

    return (indent_level, is_checked, content)


def parse_heading(line: str) -> Optional[Tuple[int, str]]:
    """
    Parse a markdown heading.

    Format: # Heading (level 1) to ###### Heading (level 6)

    Args:
        line: Line of text containing heading

    Returns:
        Tuple of (level, text) or None

    Examples:
        >>> parse_heading('## Track Name')
        (2, 'Track Name')
        >>> parse_heading('### Phase 1: Core')
        (3, 'Phase 1: Core')
    """
    pattern = r'^(#{1,6})\s+(.+)$'
    match = re.match(pattern, line.strip())

    if not match:
        return None

    hashes = match.group(1)
    text = match.group(2)
    level = len(hashes)

    return (level, text)


def parse_track_heading(line: str) -> Optional[str]:
    """
    Parse a track heading to extract track name.

    Format: ## Track: Track Name
    or: ## 🔥 TOP PRIORITY Track: Track Name

    Args:
        line: Line of text containing track heading

    Returns:
        Track name or None

    Examples:
        >>> parse_track_heading('## Track: UMK Integration')
        'UMK Integration'
        >>> parse_track_heading('## 🔥 TOP PRIORITY Track: CLI System')
        'CLI System'
    """
    pattern = r'^##\s+(?:🔥\s+)?(?:TOP PRIORITY\s+)?Track:\s+(.+)$'
    match = re.match(pattern, line.strip())

    if not match:
        return None

    # Remove trailing status badges and cleanup
    track_name = match.group(1)
    # Remove status badges like ✅ **Done** at the end
    track_name = re.sub(r'\s+[✅🚧📋💡]\s*\*\*.*?\*\*\s*$', '', track_name)

    return track_name.strip()


def parse_phase_heading(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a phase heading to extract phase ID and name.

    Format: ### Phase ID: Phase Name
    or: ### Phase ID: Phase Name 📋 **[Planned]**

    Args:
        line: Line of text containing phase heading

    Returns:
        Tuple of (phase_id, phase_name) or None

    Examples:
        >>> parse_phase_heading('### Phase CLI1: Markdown Data Backend')
        ('CLI1', 'Markdown Data Backend')
        >>> parse_phase_heading('### Phase 1: Core Builder Abstraction')
        ('1', 'Core Builder Abstraction')
    """
    # Pattern matches:
    # ### Phase CLI1: Name
    # ### Phase 1: Name 📋 **[Planned]**
    pattern = r'^###\s+Phase\s+([\w\d]+):\s+(.+?)(?:\s+[📋🚧✅💡])?\s*(?:\*\*.*?\*\*)?\s*$'
    match = re.match(pattern, line.strip())

    if not match:
        return None

    phase_id = match.group(1)
    phase_name = match.group(2).strip()

    return (phase_id, phase_name)


def parse_task_heading(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a task heading to extract task number and name.

    Format: **Task N.N: Task Name**
    or: - [ ] **Task N.N: Task Name**
    or: ### Task N.N: Task Name (in phase files)

    Args:
        line: Line of text containing task heading

    Returns:
        Tuple of (task_number, task_name) or None

    Examples:
        >>> parse_task_heading('**Task 1.1: Parser Module**')
        ('1.1', 'Parser Module')
        >>> parse_task_heading('- [ ] **Task 1.2: Writer Module**')
        ('1.2', 'Writer Module')
        >>> parse_task_heading('### Task 1.3: Testing')
        ('1.3', 'Testing')
    """
    # Try h3 heading format first (### Task N.N: Name)
    h3_pattern = r'^###\s+Task\s+([\d.]+):\s+(.+?)(?:\s+[📋🚧✅💡])?\s*(?:\*\*.*?\*\*)?\s*$'
    match = re.match(h3_pattern, line.strip())
    if match:
        task_number = match.group(1)
        task_name = match.group(2).strip()
        return (task_number, task_name)

    # Try bold format (** Task N.N: Name **)
    bold_pattern = r'(?:- \[[ x]\]\s+)?\*\*Task\s+([\d.]+):\s+(.+?)\*\*'
    match = re.search(bold_pattern, line)

    if not match:
        return None

    task_number = match.group(1)
    task_name = match.group(2).strip()

    return (task_number, task_name)


# ============================================================================
# Task 1.1.3: High-Level Parsers
# ============================================================================

def parse_metadata_block(lines: List[str], start_idx: int = 0) -> Tuple[Dict[str, Any], int]:
    """
    Parse consecutive quoted key-value pairs into a metadata dict.

    Stops at first non-matching line.

    Args:
        lines: List of lines to parse
        start_idx: Index to start parsing from

    Returns:
        Tuple of (metadata_dict, next_line_index)

    Examples:
        >>> lines = ['"name": "Test"', '"priority": 1', '', 'Next section']
        >>> parse_metadata_block(lines)
        ({'name': 'Test', 'priority': 1}, 2)
    """
    metadata = {}
    idx = start_idx

    while idx < len(lines):
        line = lines[idx].strip()

        # Skip empty lines at the start
        if not line and not metadata:
            idx += 1
            continue

        # Stop at empty line if we have metadata
        if not line and metadata:
            idx += 1
            break

        # Try to parse as quoted value
        result = parse_quoted_value(line)
        if result:
            key, value = result
            metadata[key] = value
            idx += 1
        else:
            # Not a quoted value, stop parsing
            break

    return (metadata, idx)


def parse_track(lines: List[str], start_idx: int) -> Tuple[Dict, int]:
    """
    Parse a track section from markdown lines.

    Args:
        lines: List of lines to parse
        start_idx: Index of track heading line

    Returns:
        Tuple of (track_dict, next_line_index)
    """
    track = {}
    idx = start_idx

    # Parse track heading
    track_name = parse_track_heading(lines[idx])
    if not track_name:
        return (track, idx + 1)

    track['name'] = track_name
    idx += 1

    # Parse metadata block
    metadata, idx = parse_metadata_block(lines, idx)
    track.update(metadata)

    # Parse description and phases
    track['description'] = []
    track['phases'] = []

    while idx < len(lines):
        line = lines[idx].strip()

        # Check for next track (another ## Track:)
        if parse_track_heading(line):
            break

        # Check for phase heading
        if parse_phase_heading(line):
            break

        # Skip separators
        if line == '---':
            idx += 1
            continue

        # Collect description text
        if line and not line.startswith('#'):
            track['description'].append(line)

        idx += 1

    return (track, idx)


def parse_phase(lines: List[str], start_idx: int) -> Tuple[Dict, int]:
    """
    Parse a phase section from markdown lines.

    Args:
        lines: List of lines to parse
        start_idx: Index of phase heading line

    Returns:
        Tuple of (phase_dict, next_line_index)
    """
    phase = {}
    idx = start_idx

    # Parse phase heading
    result = parse_phase_heading(lines[idx])
    if not result:
        return (phase, idx + 1)

    phase_id, phase_name = result
    phase['phase_id'] = phase_id
    phase['name'] = phase_name
    idx += 1

    # Parse metadata block
    metadata, idx = parse_metadata_block(lines, idx)
    phase.update(metadata)

    # Parse description and tasks
    phase['description'] = []
    phase['tasks'] = []

    while idx < len(lines):
        line = lines[idx].strip()

        # Check for next phase or track
        if parse_phase_heading(line) or parse_track_heading(line):
            break

        # Check for major heading (##)
        heading = parse_heading(line)
        if heading and heading[0] == 2:
            break

        # Skip separators
        if line == '---':
            idx += 1
            continue

        # Collect description text
        if line and not line.startswith('#'):
            phase['description'].append(line)

        idx += 1

    return (phase, idx)


def parse_task(lines: List[str], start_idx: int) -> Tuple[Dict, int]:
    """
    Parse a task section from markdown lines.

    Args:
        lines: List of lines to parse
        start_idx: Index of task line

    Returns:
        Tuple of (task_dict, next_line_index)
    """
    task = {}
    idx = start_idx

    line = lines[idx]

    # Parse task heading
    result = parse_task_heading(line)
    if not result:
        return (task, idx + 1)

    task_number, task_name = result
    task['task_number'] = task_number
    task['name'] = task_name

    # Check if it's a checkbox
    checkbox_result = parse_checkbox(line)
    if checkbox_result:
        _, is_checked, _ = checkbox_result
        task['completed'] = is_checked

    idx += 1

    # Parse metadata block
    metadata, idx = parse_metadata_block(lines, idx)
    task.update(metadata)

    # Parse description and subtasks
    task['description'] = []
    task['subtasks'] = []

    while idx < len(lines):
        line = lines[idx]
        line_stripped = line.strip()

        # Check for next task
        if parse_task_heading(line_stripped):
            break

        # Check for heading (stop at any heading)
        if parse_heading(line_stripped):
            break

        # Check for checkbox (subtask) - use non-stripped line to preserve indent
        checkbox_result = parse_checkbox(line)
        if checkbox_result:
            indent, is_checked, content = checkbox_result
            task['subtasks'].append({
                'content': content,
                'completed': is_checked,
                'indent': indent
            })
            idx += 1
            continue

        # Collect description text
        if line_stripped:
            task['description'].append(line_stripped)

        idx += 1

    return (task, idx)


# ============================================================================
# Task 1.1.4: Document Parsers
# ============================================================================

def parse_todo_md(path: str) -> Dict:
    """
    Parse docs/todo.md into structured data.

    Args:
        path: Path to todo.md file

    Returns:
        Dict with 'tracks', 'metadata', and other fields
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return {'tracks': [], 'metadata': {}}

    with open(path_obj, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Strip newlines but keep the lines
    lines = [line.rstrip('\n') for line in lines]

    result = {
        'tracks': [],
        'metadata': {},
    }

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        # Parse track heading
        if parse_track_heading(line):
            track, idx = parse_track(lines, idx)
            if track:
                result['tracks'].append(track)
        else:
            idx += 1

    return result


def parse_done_md(path: str) -> Dict:
    """
    Parse docs/done.md into structured data.

    Args:
        path: Path to done.md file

    Returns:
        Dict with 'tracks', 'metadata', and other fields
    """
    # Same structure as todo.md
    return parse_todo_md(path)


def parse_phase_md(path: str) -> Dict:
    """
    Parse docs/phases/*.md into structured data.

    Args:
        path: Path to phase markdown file

    Returns:
        Dict with phase details, tasks, deliverables, etc.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return {}

    with open(path_obj, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    lines = [line.rstrip('\n') for line in lines]

    # First line should be the phase heading (# Phase ID: Name)
    if not lines:
        return {}

    # Phase files use h1 (# Phase) instead of h3 (### Phase)
    # Temporarily convert to h3 for parsing
    first_line = lines[0]
    if first_line.startswith('# Phase '):
        lines[0] = '##' + first_line  # Convert # to ###

    phase, _ = parse_phase(lines, 0)

    # Continue parsing for tasks
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        # Look for task headings
        if parse_task_heading(line):
            task, next_idx = parse_task(lines, idx)
            if task:
                phase.setdefault('tasks', []).append(task)
                idx = next_idx
        else:
            idx += 1

    return phase


def parse_config_md(path: str) -> Dict:
    """
    Parse docs/config.md into structured data.

    Args:
        path: Path to config.md file

    Returns:
        Dict with configuration settings organized by section
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return {}

    with open(path_obj, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    lines = [line.rstrip('\n') for line in lines]

    config = {}
    current_section = None

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        # Check for section heading (## Section Name)
        heading = parse_heading(line)
        if heading and heading[0] == 2:
            section_name = heading[1]
            current_section = section_name.lower().replace(' ', '_')
            config[current_section] = {}
            idx += 1
            continue

        # Parse quoted values in current section
        if current_section:
            result = parse_quoted_value(line)
            if result:
                key, value = result
                config[current_section][key] = value

        idx += 1

    # Flatten single-level config (for easier access)
    flat_config = {}
    for section, values in config.items():
        if isinstance(values, dict):
            flat_config.update(values)

    return flat_config
