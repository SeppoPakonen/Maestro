"""
Task command implementation for Maestro CLI.

Commands:
- maestro task list [phase_id] - List all tasks (or tasks in phase)
- maestro task add <name> - Add new task
- maestro task remove <id> - Remove task
- maestro task <id> - Show task details
- maestro task <id> show - Show task details
- maestro task <id> edit - Edit task in $EDITOR
- maestro task <id> complete - Mark task as complete
- maestro task <id> set - Set current task context
"""

import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from maestro.data import parse_todo_md, parse_phase_md, parse_config_md
from maestro.data.markdown_writer import (
    extract_phase_block,
    extract_task_block,
    insert_task_block,
    remove_task_block,
    replace_phase_block,
    replace_task_block,
)


def list_tasks(args):
    """
    List all tasks from phase files.

    If phase_id is provided, list only tasks in that phase.
    Otherwise, list tasks from current phase (if set) or show error.
    """
    from maestro.config.settings import get_settings

    # If no phase_id provided and context is set, use context
    phase_filter = getattr(args, 'phase_id', None)
    if not phase_filter:
        settings = get_settings()
        if settings.current_phase:
            phase_filter = settings.current_phase
            print(f"Using current phase context: {phase_filter}")
            print()

    if not phase_filter:
        print("Error: No phase specified and no current phase set.")
        print("Usage: maestro task list <phase_id>")
        print("   or: maestro phase <id> set  (to set current phase)")
        return 1

    # Try to find phase file
    phase_file = Path(f'docs/phases/{phase_filter}.md')

    if not phase_file.exists():
        print(f"Error: Phase file 'docs/phases/{phase_filter}.md' not found.")
        return 1

    phase = parse_phase_md(str(phase_file))
    tasks = phase.get('tasks', [])

    if not tasks:
        print(f"No tasks found in phase '{phase_filter}'.")
        return 0

    # Display header
    print()
    print("=" * 80)
    print(f"TASKS in Phase: {phase.get('name', 'Unnamed')}")
    print("=" * 80)
    print()

    # Table header
    print(f"{'Task ID':<15} {'Name':<35} {'Priority':<10} {'Hours':<8}")
    print("-" * 80)

    # Rows
    for task in tasks:
        task_id = task.get('task_id', task.get('task_number', 'N/A'))
        name = task.get('name', 'Unnamed Task')
        priority = task.get('priority', 'N/A')
        hours = task.get('estimated_hours', '?')

        # Truncate long names
        if len(name) > 35:
            name = name[:32] + '...'

        # Format priority with color/emoji
        priority_display = priority
        if priority == 'P0':
            priority_display = '🔴 P0'
        elif priority == 'P1':
            priority_display = '🟡 P1'
        elif priority == 'P2':
            priority_display = '⚪ P2'

        print(f"{task_id:<15} {name:<35} {priority_display:<10} {hours:<8}")

    print()
    print(f"Total: {len(tasks)} tasks")
    print()

    return 0


def show_task(task_id: str, args):
    """
    Show detailed information about a specific task.

    Searches through all phase files to find the task.
    """
    # Search all phase files
    phases_dir = Path('docs/phases')
    if not phases_dir.exists():
        print("Error: docs/phases/ directory not found.")
        return 1

    task = None
    phase_info = None

    for phase_file in phases_dir.glob('*.md'):
        phase = parse_phase_md(str(phase_file))
        for t in phase.get('tasks', []):
            if t.get('task_id') == task_id or t.get('task_number') == task_id:
                task = t
                phase_info = {
                    'id': phase.get('phase_id', 'N/A'),
                    'name': phase.get('name', 'Unnamed'),
                    'file': phase_file
                }
                break
        if task:
            break

    if not task:
        print(f"Error: Task '{task_id}' not found.")
        return 1

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
    print(f"Status:      {'✅ Complete' if task.get('completed', False) else '⏳ Pending'}")
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


def add_task(name: str, args):
    """
    Add a new task to a phase.

    Args:
        name: Name of the new task
        args: Command arguments
    """
    from maestro.config.settings import get_settings

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
        return 1

    data = parse_todo_md(str(todo_path))
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
        header = [
            f"# Phase {phase_id}: {phase_info.get('name', phase_id)} 📋 **[Planned]**\n",
            "\n",
            f"\"phase_id\": \"{phase_id}\"\n",
            f"\"track\": \"{track_name}\"\n",
            f"\"track_id\": \"{track_info.get('track_id', '') if track_info else ''}\"\n",
            "\"status\": \"planned\"\n",
            "\"completion\": 0\n",
            "\n",
            "## Tasks\n",
            "\n",
        ]
        phase_path.write_text("".join(header), encoding='utf-8')

    task_block = [
        f"### Task {task_id}: {name}\n",
        "\n",
        f"\"task_id\": \"{task_id}\"\n",
        "\"priority\": \"P2\"\n",
        "\"status\": \"planned\"\n",
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
    phase_file = _find_task_file(task_id)
    if not phase_file:
        print(f"Error: Task '{task_id}' not found in any phase file.")
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
    print(f"Marking task as complete: {task_id}")
    print("Note: This requires the Writer module (Task 1.2) to be implemented.")
    print("For now, please edit docs/phases/*.md manually.")
    return 1


def edit_task(task_id: str, args):
    """
    Edit a task in $EDITOR.

    Opens the phase file containing the task.
    """
    import os
    import subprocess

    phase_file = _find_task_file(task_id)
    if not phase_file:
        print(f"Error: Task '{task_id}' not found in any phase file.")
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
        if args.task_subcommand == 'list' or args.task_subcommand == 'ls':
            return list_tasks(args)
        elif args.task_subcommand == 'add':
            if not hasattr(args, 'name') or not args.name:
                print("Error: Task name required. Usage: maestro task add <name>")
                return 1
            name = " ".join(args.name) if isinstance(args.name, list) else args.name
            return add_task(name, args)
        elif args.task_subcommand == 'remove' or args.task_subcommand == 'rm':
            if not hasattr(args, 'task_id') or not args.task_id:
                print("Error: Task ID required. Usage: maestro task remove <id>")
                return 1
            return remove_task(args.task_id, args)
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
        elif args.task_subcommand == 'help' or args.task_subcommand == 'h':
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
            args.phase_id = current_phase
            return list_tasks(args)

    print_task_help()
    return 0


def print_task_help():
    """Print help for task commands."""
    help_text = """
maestro task - Manage project tasks

USAGE:
    maestro task list [phase_id]          List all tasks (or tasks in phase)
    maestro task add <name>               Add new task
    maestro task remove <id>              Remove a task
    maestro task <id>                     Show task details
    maestro task <id> show                Show task details
    maestro task <id> edit                Edit task in $EDITOR
    maestro task <id> complete            Mark task as complete
    maestro task text <id>                Show raw task block
    maestro task set-text <id>            Replace task block (stdin or --file)
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

ALIASES:
    list:     ls, l
    add:      a
    remove:   rm, r
    show:     sh
    edit:     e
    complete: c, done
    discuss:  d
    set:      st
    text:     raw
    set-text: setraw

EXAMPLES:
    maestro task list                     # List tasks in current phase
    maestro task list cli-tpt-1           # List tasks in phase 'cli-tpt-1'
    maestro task cli-tpt-1-1              # Show task details
    maestro task cli-tpt-1-1 edit         # Edit task in $EDITOR
    maestro task cli-tpt-1-1 complete     # Mark task as complete
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
    maestro task <id> discuss             Discuss task with AI
    maestro task <id> set                 Set current task context

ALIASES:
    show:     sh
    edit:     e
    complete: c, done
    discuss:  d
    set:      st

EXAMPLES:
    maestro task cli-tpt-1-1 show
    maestro task cli-tpt-1-1 edit
    maestro task cli-tpt-1-1 complete
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
    # Main task command
    task_parser = subparsers.add_parser(
        'task',
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
        'phase_id',
        nargs='?',
        help='Phase ID to filter tasks (optional)'
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

    # Add task_id argument for 'maestro task <id>' commands
    task_parser.add_argument(
        'task_id_arg',
        nargs='?',
        help='Task ID (for show/edit/complete/discuss commands)'
    )
    task_parser.add_argument(
        'task_item_subcommand',
        nargs='?',
        choices=['show', 'sh', 'edit', 'e', 'complete', 'c', 'done', 'discuss', 'd', 'set', 'st', 'help', 'h'],
        help='Task item subcommand (show/edit/complete/discuss/set)'
    )
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
