"""
Parser and writer library for Track/Phase/Task markdown files.

This module implements a strict parser that follows the data contract
defined in docs/specs/track_phase_task_md_contract.md.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from maestro.tracks.models import (
    Track, Phase, Task, TrackIndex, DoneArchive, PhaseRef, ParseError
)


def _parse_asterisk_wrapped_value(value_str: str) -> Optional[str]:
    """Parse a value wrapped in asterisks, handling escaping."""
    if not value_str.startswith('*'):
        return None
    buf = []
    escaped = False
    for idx in range(1, len(value_str)):
        ch = value_str[idx]
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '*':
            return "".join(buf)
        buf.append(ch)
    return None


def _parse_quoted_or_asterisk_value(line: str) -> Optional[Tuple[str, str]]:
    """Parse a key-value pair in either quoted or asterisk format."""
    # Remove leading/trailing whitespace
    stripped = line.strip()
    
    # Match both formats: "key": "value" and - *key*: *value*
    quoted_pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
    asterisk_pattern = r'-\s*\*([^*]+)\*\s*:\s*\*([^*]*)\*'
    
    match = re.match(quoted_pattern, stripped)
    if match:
        return match.group(1), match.group(2)
    
    match = re.match(asterisk_pattern, stripped)
    if match:
        return match.group(1), match.group(2)
    
    return None


def _parse_id_field(line: str, field_name: str) -> Optional[str]:
    """Parse an ID field like *track_id*: *TR-001*."""
    pattern = rf'-\s*\*{field_name}\*\s*:\s*\*([A-Z]+-\d+)\*'
    match = re.match(pattern, line.strip())
    if match:
        return match.group(1)
    return None


def _parse_checkbox(line: str) -> Optional[Tuple[bool, str]]:
    """Parse a checkbox task line like '- [ ] Task name' or '- [x] Task name'."""
    pattern = r'^\s*-\s+\[([ x])\]\s+(.+)$'
    match = re.match(pattern, line)
    if match:
        is_checked = match.group(1).lower() == 'x'
        content = match.group(2)
        return is_checked, content
    return None


def _validate_id_format(id_str: str, expected_prefix: str) -> bool:
    """
    Validate that an ID follows the expected format.

    Accepts both formats:
    - Numbered: TR-001, PH-001, TS-0001
    - Slug: minesweeper-game, game-board-setup, create-game-board-grid
    """
    # Numbered format: PREFIX-###
    numbered_pattern = rf'^{expected_prefix}-\d{{3,5}}$'
    if re.match(numbered_pattern, id_str):
        return True

    # Slug format: lowercase letters, numbers, and hyphens
    slug_pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
    if re.match(slug_pattern, id_str):
        return True

    return False


def _parse_task_from_line(line: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """
    Parse task ID and name from a line.

    Supports two formats:
    - **TS-0001: Task Name** (numbered format)
    - Task Name  #task_id: create-game-board  #status: todo (hashtag format)

    Returns:
        Tuple of (task_id, task_name, status) or None
    """
    # Try numbered format first: **TS-####: Task Name**
    numbered_pattern = r'\*\*(TS-\d{4,5}):\s*([^*]+)\*\*'
    match = re.search(numbered_pattern, line)
    if match:
        task_id = match.group(1)
        task_name = match.group(2).strip()
        return task_id, task_name, None

    # Try hashtag format: Task Name  #task_id: create-game-board  #status: todo
    hashtag_pattern = r'([^#]+)\s+#task_id:\s*([a-zA-Z0-9-]+)(?:\s+#status:\s*(\w+))?'
    match = re.search(hashtag_pattern, line)
    if match:
        task_name = match.group(1).strip()
        task_id = match.group(2).strip()
        status = match.group(3).strip() if match.group(3) else None
        return task_id, task_name, status

    return None


def parse_task_from_block(lines: List[str], start_idx: int) -> Tuple[Optional[Task], int, Optional[ParseError]]:
    """Parse a task from a block of lines starting at start_idx."""
    if start_idx >= len(lines):
        return None, start_idx, None
    
    # Look for task heading like "### Task TS-0001: Task Name"
    task_heading_pattern = r'###\s+Task\s+(TS-\d{4,5}):\s+(.+)$'
    current_idx = start_idx
    
    while current_idx < len(lines):
        line = lines[current_idx].strip()
        match = re.match(task_heading_pattern, line)
        if match:
            task_id = match.group(1)
            task_name = match.group(2)
            
            # Validate ID format
            if not _validate_id_format(task_id, "TS"):
                error = ParseError(
                    file_path="unknown",
                    line_number=current_idx + 1,
                    error_message=f"Invalid task ID format: {task_id}",
                    hint="Task ID must follow format TS-####"
                )
                return None, current_idx + 1, error
            
            # Initialize task with basic info
            task = Task(task_id=task_id, name=task_name)
            
            # Parse metadata lines after the heading
            current_idx += 1
            while current_idx < len(lines):
                line = lines[current_idx].strip()
                
                # Check if we've reached the next heading or task
                if line.startswith('###') or line.startswith('##'):
                    break
                
                # Parse metadata fields
                kv_pair = _parse_quoted_or_asterisk_value(line)
                if kv_pair:
                    key, value = kv_pair
                    if key == 'status':
                        task.status = value
                    elif key == 'priority':
                        task.priority = value
                    elif key == 'estimated_hours':
                        try:
                            task.estimated_hours = int(value)
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid estimated_hours value: {value}",
                                hint="estimated_hours must be a number"
                            )
                            return None, current_idx + 1, error
                    elif key == 'phase_id':
                        task.phase_id = value
                    elif key == 'completed':
                        task.completed = value.lower() == 'true'
                
                # Add non-metadata lines to description
                elif line and not line.startswith('- *'):
                    task.description.append(line)
                
                current_idx += 1
            
            return task, current_idx, None
        
        current_idx += 1
    
    return None, current_idx, None


def parse_phase_from_block(lines: List[str], start_idx: int) -> Tuple[Optional[Phase], int, Optional[ParseError]]:
    """Parse a phase from a block of lines starting at start_idx."""
    if start_idx >= len(lines):
        return None, start_idx, None

    # Look for phase heading in multiple formats:
    # - "### Phase PH-001: Phase Name" (numbered format)
    # - "### Phase game-board-setup: Game Board Setup" (slug format)
    # Pattern captures: phase ID (either PH-### or slug) and phase name
    phase_heading_pattern = r'###\s+Phase\s+([a-zA-Z0-9-]+):\s+(.+)$'
    current_idx = start_idx

    while current_idx < len(lines):
        line = lines[current_idx].strip()
        match = re.match(phase_heading_pattern, line)
        if match:
            phase_id = match.group(1)
            phase_name = match.group(2)
            
            # Validate ID format
            if not _validate_id_format(phase_id, "PH"):
                error = ParseError(
                    file_path="unknown",
                    line_number=current_idx + 1,
                    error_message=f"Invalid phase ID format: {phase_id}",
                    hint="Phase ID must follow format PH-###"
                )
                return None, current_idx + 1, error
            
            # Initialize phase with basic info
            phase = Phase(phase_id=phase_id, name=phase_name)
            
            # Parse metadata lines after the heading
            current_idx += 1
            while current_idx < len(lines):
                line = lines[current_idx].strip()
                
                # Check if we've reached the next heading
                if line.startswith('###') or (line.startswith('##') and not line.startswith('###')):
                    break
                
                # Parse metadata fields
                kv_pair = _parse_quoted_or_asterisk_value(line)
                if kv_pair:
                    key, value = kv_pair
                    if key == 'status':
                        phase.status = value
                    elif key == 'completion':
                        try:
                            completion = int(value.rstrip('%'))
                            if 0 <= completion <= 100:
                                phase.completion = completion
                            else:
                                error = ParseError(
                                    file_path="unknown",
                                    line_number=current_idx + 1,
                                    error_message=f"Completion value out of range: {completion}",
                                    hint="Completion must be between 0-100%"
                                )
                                return None, current_idx + 1, error
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid completion value: {value}",
                                hint="Completion must be a number between 0-100%"
                            )
                            return None, current_idx + 1, error
                    elif key == 'track_id':
                        # Validate track ID format
                        if _validate_id_format(value, "TR"):
                            phase.track_id = value
                        else:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid track ID format: {value}",
                                hint="Track ID must follow format TR-###"
                            )
                            return None, current_idx + 1, error
                    elif key == 'priority':
                        try:
                            phase.priority = int(value)
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid priority value: {value}",
                                hint="Priority must be a number"
                            )
                            return None, current_idx + 1, error
                    elif key == 'order':
                        try:
                            phase.order = int(value)
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid order value: {value}",
                                hint="Order must be a number"
                            )
                            return None, current_idx + 1, error
                
                # Add non-metadata lines to description or try to parse tasks
                elif line and not line.startswith('- *'):
                    # Check if it's a task in checkbox format
                    checkbox_result = _parse_checkbox(line)
                    if checkbox_result:
                        is_checked, content = checkbox_result
                        # Try to parse task ID and name from content
                        task_result = _parse_task_from_line(content)
                        if task_result:
                            task_id, task_name, task_status = task_result
                            # Create a minimal task to add to the phase
                            task = Task(
                                task_id=task_id,
                                name=task_name,
                                completed=is_checked,
                                status=task_status if task_status else ("done" if is_checked else "todo")
                            )
                            phase.tasks.append(task)
                        else:
                            # If it doesn't look like a task, add to description
                            phase.description.append(line)
                    else:
                        phase.description.append(line)
                
                current_idx += 1
            
            return phase, current_idx, None
        
        current_idx += 1
    
    return None, current_idx, None


def parse_track_from_block(lines: List[str], start_idx: int) -> Tuple[Optional[Track], int, Optional[ParseError]]:
    """Parse a track from a block of lines starting at start_idx."""
    if start_idx >= len(lines):
        return None, start_idx, None
    
    # Look for track heading like "## Track: Track Name"
    track_heading_pattern = r'##\s+Track:\s+(.+)$'
    current_idx = start_idx
    
    while current_idx < len(lines):
        line = lines[current_idx].strip()
        match = re.match(track_heading_pattern, line)
        if match:
            track_name = match.group(1)
            
            # Initialize track with basic info
            track = Track(track_id="", name=track_name)  # track_id will be set from metadata
            
            # Parse metadata lines after the heading
            current_idx += 1
            while current_idx < len(lines):
                line = lines[current_idx].strip()
                
                # Check if we've reached the next track or other heading
                if line.startswith('##') and not line.startswith('###'):
                    break
                
                # Parse metadata fields
                kv_pair = _parse_quoted_or_asterisk_value(line)
                if kv_pair:
                    key, value = kv_pair
                    if key == 'track_id':
                        # Validate track ID format
                        if _validate_id_format(value, "TR"):
                            track.track_id = value
                        else:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid track ID format: {value}",
                                hint="Track ID must follow format TR-###"
                            )
                            return None, current_idx + 1, error
                    elif key == 'status':
                        track.status = value
                    elif key == 'completion':
                        try:
                            completion = int(value.rstrip('%'))
                            if 0 <= completion <= 100:
                                track.completion = completion
                            else:
                                error = ParseError(
                                    file_path="unknown",
                                    line_number=current_idx + 1,
                                    error_message=f"Completion value out of range: {completion}",
                                    hint="Completion must be between 0-100%"
                                )
                                return None, current_idx + 1, error
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid completion value: {value}",
                                hint="Completion must be a number between 0-100%"
                            )
                            return None, current_idx + 1, error
                    elif key == 'priority':
                        try:
                            track.priority = int(value)
                        except ValueError:
                            error = ParseError(
                                file_path="unknown",
                                line_number=current_idx + 1,
                                error_message=f"Invalid priority value: {value}",
                                hint="Priority must be a number"
                            )
                            return None, current_idx + 1, error
                    elif key == 'is_top_priority':
                        track.is_top_priority = value.lower() == 'true'
                
                # Add non-metadata lines to description or try to parse phases
                elif line and not line.startswith('- *'):
                    # Check if it's a phase heading
                    phase_result, new_idx, error = parse_phase_from_block(lines, current_idx)
                    if error:
                        return None, new_idx, error
                    elif phase_result:
                        # Add the parsed phase to the track
                        phase_result.track_id = track.track_id  # Link phase to track
                        track.phases.append(phase_result)
                        current_idx = new_idx - 1  # Adjust for the increment at the end of the loop
                    else:
                        track.description.append(line)
                
                current_idx += 1
            
            # Validate that track_id was set
            if not track.track_id:
                error = ParseError(
                    file_path="unknown",
                    line_number=start_idx + 1,
                    error_message="Track missing required track_id field",
                    hint="Add '- *track_id*: *TR-###*' field to track"
                )
                return None, current_idx, error
            
            return track, current_idx, None
        
        current_idx += 1
    
    return None, current_idx, None


def parse_todo_md(path: Path) -> Tuple[Optional[TrackIndex], Optional[ParseError]]:
    """Parse docs/todo.md into a TrackIndex object."""
    path = Path(path)
    if not path.exists():
        return TrackIndex(), None
    
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.splitlines()
    except Exception as e:
        return None, ParseError(
            file_path=str(path),
            error_message=f"Could not read file: {e}",
            hint="Check file permissions and encoding"
        )
    
    track_index = TrackIndex()
    current_idx = 0
    
    while current_idx < len(lines):
        line = lines[current_idx].strip()
        
        # Look for track headings
        if line.startswith('## Track:'):
            track, next_idx, error = parse_track_from_block(lines, current_idx)
            if error:
                error.file_path = str(path)
                if error.line_number is None:
                    error.line_number = current_idx + 1
                return None, error
            if track:
                track_index.tracks.append(track)
                current_idx = next_idx - 1  # Adjust for the increment at the end of the loop
        current_idx += 1
    
    # Set top priority track if one is marked
    for track in track_index.tracks:
        if track.is_top_priority:
            track_index.top_priority_track = track.track_id
            break
    
    return track_index, None


def parse_phase_md(path: Path) -> Tuple[Optional[Phase], Optional[ParseError]]:
    """Parse a phase markdown file into a Phase object."""
    path = Path(path)
    if not path.exists():
        return None, ParseError(
            file_path=str(path),
            error_message="Phase file does not exist",
            hint="Check that the phase file exists in docs/phases/"
        )
    
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.splitlines()
    except Exception as e:
        return None, ParseError(
            file_path=str(path),
            error_message=f"Could not read file: {e}",
            hint="Check file permissions and encoding"
        )
    
    # Parse the phase from the content
    phase, _, error = parse_phase_from_block(lines, 0)
    if error:
        error.file_path = str(path)
        return None, error
    
    # If we couldn't parse a phase from the heading, try looking for tasks
    if not phase:
        # Try to find the phase info in the content
        for i, line in enumerate(lines):
            # Look for phase heading in h1 format (like "# Phase PH-001: Name")
            h1_pattern = r'#\s+Phase\s+(PH-\d{3,5}):\s+(.+)$'
            match = re.match(h1_pattern, line.strip())
            if match:
                phase_id = match.group(1)
                phase_name = match.group(2)
                
                # Validate ID format
                if not _validate_id_format(phase_id, "PH"):
                    return None, ParseError(
                        file_path=str(path),
                        line_number=i + 1,
                        error_message=f"Invalid phase ID format: {phase_id}",
                        hint="Phase ID must follow format PH-###"
                    )
                
                phase = Phase(phase_id=phase_id, name=phase_name)
                
                # Parse the rest of the file for metadata and tasks
                j = i + 1
                while j < len(lines):
                    line = lines[j].strip()
                    
                    # Parse metadata
                    kv_pair = _parse_quoted_or_asterisk_value(line)
                    if kv_pair:
                        key, value = kv_pair
                        if key == 'status':
                            phase.status = value
                        elif key == 'completion':
                            try:
                                completion = int(value.rstrip('%'))
                                if 0 <= completion <= 100:
                                    phase.completion = completion
                                else:
                                    return None, ParseError(
                                        file_path=str(path),
                                        line_number=j + 1,
                                        error_message=f"Completion value out of range: {completion}",
                                        hint="Completion must be between 0-100%"
                                    )
                            except ValueError:
                                return None, ParseError(
                                    file_path=str(path),
                                    line_number=j + 1,
                                    error_message=f"Invalid completion value: {value}",
                                    hint="Completion must be a number between 0-100%"
                                )
                        elif key == 'track_id':
                            if _validate_id_format(value, "TR"):
                                phase.track_id = value
                            else:
                                return None, ParseError(
                                    file_path=str(path),
                                    line_number=j + 1,
                                    error_message=f"Invalid track ID format: {value}",
                                    hint="Track ID must follow format TR-###"
                                )
                        elif key == 'priority':
                            try:
                                phase.priority = int(value)
                            except ValueError:
                                return None, ParseError(
                                    file_path=str(path),
                                    line_number=j + 1,
                                    error_message=f"Invalid priority value: {value}",
                                    hint="Priority must be a number"
                                )
                        elif key == 'order':
                            try:
                                phase.order = int(value)
                            except ValueError:
                                return None, ParseError(
                                    file_path=str(path),
                                    line_number=j + 1,
                                    error_message=f"Invalid order value: {value}",
                                    hint="Order must be a number"
                                )
                    elif line.startswith('## Tasks'):
                        # Parse tasks section
                        j += 1
                        while j < len(lines):
                            task_line = lines[j].strip()
                            if task_line.startswith('## ') and task_line != '## Tasks':
                                break  # New section started
                            
                            checkbox_result = _parse_checkbox(task_line)
                            if checkbox_result:
                                is_checked, content = checkbox_result
                                task_result = _parse_task_from_line(content)
                                if task_result:
                                    task_id, task_name, task_status = task_result
                                    task = Task(
                                        task_id=task_id,
                                        name=task_name,
                                        completed=is_checked,
                                        status=task_status if task_status else ("done" if is_checked else "todo")
                                    )
                                    phase.tasks.append(task)
                            j += 1
                        continue  # Continue with outer loop
                    j += 1
                break
    
    return phase, None


def parse_done_md(path: Path) -> Tuple[Optional[DoneArchive], Optional[ParseError]]:
    """Parse docs/done.md into a DoneArchive object."""
    path = Path(path)
    if not path.exists():
        return DoneArchive(), None
    
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.splitlines()
    except Exception as e:
        return None, ParseError(
            file_path=str(path),
            error_message=f"Could not read file: {e}",
            hint="Check file permissions and encoding"
        )
    
    done_archive = DoneArchive()
    current_idx = 0
    
    while current_idx < len(lines):
        line = lines[current_idx].strip()
        
        # Look for track headings
        if line.startswith('## Track:'):
            track, next_idx, error = parse_track_from_block(lines, current_idx)
            if error:
                error.file_path = str(path)
                if error.line_number is None:
                    error.line_number = current_idx + 1
                return None, error
            if track:
                done_archive.tracks.append(track)
                current_idx = next_idx - 1  # Adjust for the increment at the end of the loop
        current_idx += 1
    
    return done_archive, None


def validate_track(track: Track) -> List[ParseError]:
    """Validate a track object against the data contract."""
    errors = []
    
    # Validate track ID
    if not track.track_id:
        errors.append(ParseError(
            file_path="memory",
            error_message="Track missing required track_id",
            hint="Track must have a valid TR-### format ID"
        ))
    elif not _validate_id_format(track.track_id, "TR"):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid track ID format: {track.track_id}",
            hint="Track ID must follow format TR-###"
        ))
    
    # Validate status
    valid_statuses = {"planned", "in_progress", "done", "proposed"}
    if track.status not in valid_statuses:
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid track status: {track.status}",
            hint=f"Status must be one of {valid_statuses}"
        ))
    
    # Validate completion
    if not (0 <= track.completion <= 100):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Completion value out of range: {track.completion}",
            hint="Completion must be between 0-100%"
        ))
    
    # Validate phase IDs and check for duplicates
    phase_ids = set()
    for i, phase in enumerate(track.phases):
        if phase.phase_id in phase_ids:
            errors.append(ParseError(
                file_path="memory",
                error_message=f"Duplicate phase ID found: {phase.phase_id}",
                hint=f"Phase at index {i} has duplicate ID"
            ))
        phase_ids.add(phase.phase_id)
        
        # Validate phase
        phase_errors = validate_phase(phase)
        errors.extend(phase_errors)
    
    return errors


def validate_phase(phase: Phase) -> List[ParseError]:
    """Validate a phase object against the data contract."""
    errors = []
    
    # Validate phase ID
    if not phase.phase_id:
        errors.append(ParseError(
            file_path="memory",
            error_message="Phase missing required phase_id",
            hint="Phase must have a valid PH-### format ID"
        ))
    elif not _validate_id_format(phase.phase_id, "PH"):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid phase ID format: {phase.phase_id}",
            hint="Phase ID must follow format PH-###"
        ))
    
    # Validate status
    valid_statuses = {"planned", "in_progress", "done", "proposed"}
    if phase.status not in valid_statuses:
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid phase status: {phase.status}",
            hint=f"Status must be one of {valid_statuses}"
        ))
    
    # Validate completion
    if not (0 <= phase.completion <= 100):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Completion value out of range: {phase.completion}",
            hint="Completion must be between 0-100%"
        ))
    
    # Validate track_id if present
    if phase.track_id and not _validate_id_format(phase.track_id, "TR"):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid track ID format in phase: {phase.track_id}",
            hint="Track ID must follow format TR-###"
        ))
    
    # Validate task IDs and check for duplicates
    task_ids = set()
    for i, task in enumerate(phase.tasks):
        if task.task_id in task_ids:
            errors.append(ParseError(
                file_path="memory",
                error_message=f"Duplicate task ID found: {task.task_id}",
                hint=f"Task at index {i} has duplicate ID"
            ))
        task_ids.add(task.task_id)
        
        # Validate task
        task_errors = validate_task(task)
        errors.extend(task_errors)
    
    return errors


def validate_task(task: Task) -> List[ParseError]:
    """Validate a task object against the data contract."""
    errors = []
    
    # Validate task ID
    if not task.task_id:
        errors.append(ParseError(
            file_path="memory",
            error_message="Task missing required task_id",
            hint="Task must have a valid TS-#### format ID"
        ))
    elif not _validate_id_format(task.task_id, "TS"):
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid task ID format: {task.task_id}",
            hint="Task ID must follow format TS-####"
        ))
    
    # Validate status
    valid_statuses = {"todo", "in_progress", "done", "blocked"}
    if task.status not in valid_statuses:
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid task status: {task.status}",
            hint=f"Status must be one of {valid_statuses}"
        ))
    
    # Validate priority
    valid_priorities = {"P1", "P2", "P3", "P4"}
    if task.priority not in valid_priorities:
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Invalid task priority: {task.priority}",
            hint=f"Priority must be one of {valid_priorities}"
        ))
    
    # Validate estimated hours if present
    if task.estimated_hours is not None and task.estimated_hours < 0:
        errors.append(ParseError(
            file_path="memory",
            error_message=f"Estimated hours cannot be negative: {task.estimated_hours}",
            hint="Estimated hours must be a positive number or zero"
        ))
    
    return errors


def render_task(task: Task) -> str:
    """Render a Task object to markdown format."""
    lines = [
        f"### Task {task.task_id}: {task.name}",
        "",
        f"- *task_id*: *{task.task_id}*",
        f"- *status*: *{task.status}*",
        f"- *priority*: *{task.priority}*",
    ]
    
    if task.estimated_hours is not None:
        lines.append(f"- *estimated_hours*: *{task.estimated_hours}*")
    
    if task.phase_id:
        lines.append(f"- *phase_id*: *{task.phase_id}*")
    
    lines.append(f"- *completed*: *{str(task.completed).lower()}*")
    lines.append("")
    
    for desc_line in task.description:
        lines.append(desc_line)
    
    lines.append("")
    return "\n".join(lines)


def render_phase(phase: Phase) -> str:
    """Render a Phase object to markdown format."""
    lines = [
        f"### Phase {phase.phase_id}: {phase.name}",
        "",
        f"- *phase_id*: *{phase.phase_id}*",
        f"- *status*: *{phase.status}*",
        f"- *completion*: *{phase.completion}%*",
    ]
    
    if phase.track_id:
        lines.append(f"- *track_id*: *{phase.track_id}*")
    
    if phase.priority != 0:
        lines.append(f"- *priority*: *{phase.priority}*")
    
    if phase.order is not None:
        lines.append(f"- *order*: *{phase.order}*")
    
    lines.append("")
    
    for desc_line in phase.description:
        lines.append(desc_line)
    
    if phase.tasks:
        lines.append("## Tasks")
        lines.append("")
        for task in phase.tasks:
            status = "x" if task.completed else " "
            lines.append(f"- [{status}] **{task.task_id}: {task.name}**")
            for desc_line in task.description:
                lines.append(f"  - {desc_line}")
        lines.append("")
    
    lines.append("")
    return "\n".join(lines)


def render_track(track: Track) -> str:
    """Render a Track object to markdown format."""
    lines = [
        f"## Track: {track.name}",
        "",
        f"- *track_id*: *{track.track_id}*",
        f"- *status*: *{track.status}*",
        f"- *completion*: *{track.completion}%*",
        f"- *priority*: *{track.priority}*",
        f"- *is_top_priority*: *{str(track.is_top_priority).lower()}*",
        "",
    ]
    
    for desc_line in track.description:
        lines.append(desc_line)
    
    for phase in track.phases:
        lines.append(render_phase(phase))
    
    lines.append("")
    return "\n".join(lines)


def render_track_index(track_index: TrackIndex) -> str:
    """Render a TrackIndex object to markdown format for todo.md."""
    lines = [
        "# Maestro Development TODO",
        "",
        f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    
    for track in track_index.tracks:
        lines.append(render_track(track))
    
    return "\n".join(lines)


def render_done_archive(done_archive: DoneArchive) -> str:
    """Render a DoneArchive object to markdown format for done.md."""
    lines = [
        "# Maestro Development DONE",
        "",
        f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    
    for track in done_archive.tracks:
        lines.append(render_track(track))
    
    return "\n".join(lines)