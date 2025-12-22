"""
Utility functions for Maestro.
"""
import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from .dataclasses import Colors


def styled_print(text, color=None, style=None, indent=0):
    """
    Print styled text with optional color, style, and indentation.

    Args:
        text (str): Text to print
        color (str): Color from Colors class
        style (str): Style from Colors class
        indent (int): Number of spaces to indent
    """
    indent_str = " " * indent
    color_code = color or ""
    style_code = style or ""

    # Only apply colors if we're in a terminal that supports them
    if not (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
        color_code = style_code = ""

    formatted_text = f"{indent_str}{color_code}{style_code}{text}{Colors.RESET}"
    print(formatted_text)


def print_header(text):
    """Print a styled header with separator lines."""
    styled_print("\n" + "="*60, Colors.BRIGHT_CYAN, Colors.BOLD)
    styled_print(text.center(60), Colors.BRIGHT_CYAN, Colors.BOLD)
    styled_print("="*60, Colors.BRIGHT_CYAN, Colors.BOLD)


def print_subheader(text):
    """Print a styled subheader."""
    styled_print(f"\n{text}", Colors.CYAN, Colors.BOLD, 2)


def print_success(text, indent=0):
    """Print success message in green."""
    styled_print(text, Colors.GREEN, Colors.BOLD, indent)


def print_warning(text, indent=0):
    """Print warning message in yellow."""
    styled_print(text, Colors.YELLOW, Colors.BOLD, indent)


def print_error(text, indent=0):
    """Print error message in red."""
    styled_print(text, Colors.RED, Colors.BOLD, indent)


def print_info(text, indent=0):
    """Print info message in blue."""
    styled_print(text, Colors.BLUE, None, indent)


def print_debug(text, indent=0):
    """Print debug message in magenta."""
    styled_print(text, Colors.MAGENTA, None, indent)


def print_ai_response(text):
    """Print AI response with special styling."""
    styled_print(f"[AI]: {text}", Colors.BRIGHT_GREEN, None, 2)


def print_user_input(text):
    """Print user input with special styling."""
    styled_print(f"[USER]: {text}", Colors.BRIGHT_BLUE, Colors.BOLD, 2)


def log_verbose(verbose, message: str):
    """Simple logging helper for verbose mode."""
    if verbose:
        print_info(f"orchestrator: {message}", 2)


def get_maestro_dir(session_path: str) -> str:
    """
    Get the .maestro directory path for the given session.
    If the session file is already in a .maestro directory, use that directory.
    Otherwise, create/use the .maestro directory in the same directory as the session file.

    Args:
        session_path: Path to the session file

    Returns:
        Path to the .maestro directory
    """
    session_abs_path = os.path.abspath(session_path)
    session_dir = os.path.dirname(session_abs_path)

    # If the session directory is a .maestro directory, use it.
    # Otherwise, use/create .maestro subdirectory in the session's directory.
    if os.path.basename(session_dir) == ".maestro":
        # The session file is already in a .maestro directory, so use that directory
        maestro_dir = session_dir
    else:
        # The session file is not in .maestro, create/use .maestro in the same directory
        maestro_dir = os.path.join(session_dir, ".maestro")

    os.makedirs(maestro_dir, exist_ok=True)
    return maestro_dir


def get_maestro_sessions_dir(session_path: str = None) -> str:
    """
    Get the .maestro/sessions directory path.
    If session_path is provided, uses that directory; otherwise, uses current working directory.

    Args:
        session_path: Optional path to session file (to determine directory)

    Returns:
        Path to the .maestro/sessions directory
    """
    if session_path:
        base_dir = os.path.dirname(os.path.abspath(session_path))
    else:
        base_dir = os.getcwd()

    # Check if MAESTRO_DIR environment variable is set
    maestro_dir = os.environ.get('MAESTRO_DIR', os.path.join(base_dir, '.maestro'))

    sessions_dir = os.path.join(maestro_dir, 'sessions')
    os.makedirs(sessions_dir, exist_ok=True)
    return sessions_dir


def get_user_config_dir() -> str:
    """
    Get the user configuration directory for maestro (~/.config/maestro).

    Returns:
        Path to the user configuration directory
    """
    config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    user_config_dir = os.path.join(config_home, 'maestro')
    os.makedirs(user_config_dir, exist_ok=True)
    return user_config_dir


def get_project_config_file(base_dir: str = None) -> str:
    """
    Get the path to the project-level configuration file.
    This stores project-specific settings like the unique project ID.

    Args:
        base_dir: Base directory for the project (defaults to current directory)

    Returns:
        Path to the project configuration file
    """
    if base_dir is None:
        base_dir = os.getcwd()

    maestro_dir = os.environ.get('MAESTRO_DIR', os.path.join(base_dir, '.maestro'))
    return os.path.join(maestro_dir, 'config.json')


def get_user_projects_config_file() -> str:
    """
    Get the path to the user-level projects configuration file.
    This stores project IDs without requiring a .maestro directory.
    """
    return os.path.join(get_user_config_dir(), 'projects.json')


def get_user_session_config_file() -> str:
    """
    Get the path to the user-level session configuration file.
    This stores which project session is currently active.

    Returns:
        Path to the user session configuration file
    """
    user_config_dir = get_user_config_dir()
    return os.path.join(user_config_dir, 'sessions.json')


def get_project_id(base_dir: str = None) -> str:
    """
    Get or create a unique project ID for the current project directory.
    This ID links the project to the user's configuration.

    Args:
        base_dir: Base directory for the project (defaults to current directory)

    Returns:
        Unique project ID
    """
    if base_dir is None:
        base_dir = os.getcwd()

    config_file = get_project_config_file(base_dir)
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('project_id', str(uuid.uuid4()))

    projects_file = get_user_projects_config_file()
    projects = {}
    if os.path.exists(projects_file):
        with open(projects_file, 'r', encoding='utf-8') as f:
            projects = json.load(f)

    base_dir_key = os.path.abspath(base_dir)
    project_id = projects.get(base_dir_key)
    if not project_id:
        project_id = str(uuid.uuid4())
        projects[base_dir_key] = project_id
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2)

    return project_id


def get_active_session_name() -> Optional[str]:
    """
    Get the name of the currently active session from user configuration.

    Returns:
        Name of the active session, or None if not set
    """
    project_id = get_project_id()
    config_file = get_user_session_config_file()

    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get(project_id, {}).get('active_session')
    return None


def set_active_session_name(session_name: str) -> bool:
    """
    Set the active session name in user configuration.

    Args:
        session_name: Name of the session to set as active

    Returns:
        True if successful, False otherwise
    """
    project_id = get_project_id()
    config_file = get_user_session_config_file()

    # Load existing config
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}

    # Create or update entry for this project
    if project_id not in config:
        config[project_id] = {}

    config[project_id]['active_session'] = session_name

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def find_repo_root_from_path(start_path: str, verbose: bool = False) -> str:
    """
    Find the repository root which is the nearest directory containing .maestro/

    Args:
        start_path: Path to start searching from (can be file or directory)
        verbose: If True, print verbose information about the discovery process

    Returns:
        Path to the repository root directory containing .maestro/,
        or the starting path if no .maestro directory is found upward
    """
    start_dir = os.path.abspath(os.path.dirname(start_path)) if os.path.isfile(start_path) else os.path.abspath(start_path)
    current_dir = start_dir

    if verbose:
        print_info(f"Detecting repository root starting from: {start_dir}", 2)

    # Walk up the directory tree
    while True:
        maestro_dir = os.path.join(current_dir, '.maestro')
        if os.path.exists(maestro_dir) and os.path.isdir(maestro_dir):
            if verbose:
                print_info(f"Found .maestro directory at: {maestro_dir}", 2)
                print_info(f"Repository root: {current_dir}", 2)
            return current_dir

        parent_dir = os.path.dirname(current_dir)
        # If we've reached the root of the filesystem, stop
        if parent_dir == current_dir:
            # If no .maestro directory found, return the start directory
            if verbose:
                print_warning(f"No .maestro directory found. Using start directory: {start_dir}", 2)
            return start_dir

        current_dir = parent_dir


def is_under_any(path: str, roots: set) -> bool:
    """
    Check if a path is under any of the given root directories.

    Args:
        path: Path to check
        roots: Set of root directories

    Returns:
        True if path is equal to or under any root, False otherwise
    """
    from pathlib import Path

    # Normalize the path
    path_obj = Path(path).resolve()

    for root in roots:
        root_obj = Path(root).resolve()
        # Check if path equals root or is a child of root
        if path_obj == root_obj:
            return True
        try:
            # This will raise ValueError if path is not relative to root
            path_obj.relative_to(root_obj)
            return True
        except ValueError:
            continue


def parse_upp_list(text: str) -> List[str]:
    """
    Parse a comma-separated list of values from UPP format.
    Handles quoted strings properly.
    """
    if not text.strip():
        return []

    # Split by comma, but respect quotes
    values = []
    current = ""
    in_quotes = False
    quote_char = None
    i = 0

    while i < len(text):
        c = text[i]

        if c in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = c
            current += c
        elif c == quote_char and in_quotes:
            # Check if it's escaped
            if i > 0 and text[i-1] == '\\':
                current += c
            else:
                in_quotes = False
                quote_char = None
                current += c
        elif c == ',' and not in_quotes:
            values.append(current.strip())
            current = ""
        else:
            current += c
        i += 1

    if current.strip():
        values.append(current.strip())

    # Clean up the values (remove quotes, extra whitespace)
    clean_values = []
    for val in values:
        val = val.strip()
        if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
            val = val[1:-1]  # Remove surrounding quotes
        if val:
            clean_values.append(val)

    return clean_values


def parse_mainconfig_list(text: str) -> List[Dict[str, str]]:
    """
    Parse mainconfig list of format: "name1" = "value1", "name2" = "value2"
    """
    configs = []

    if not text.strip():
        return configs

    # Find each name=value pair by tracking quotes and equal signs
    i = 0
    while i < len(text):
        # Skip whitespace
        while i < len(text) and text[i].isspace():
            i += 1

        if i >= len(text):
            break

        # Parse name (expected to be in quotes)
        name = ""
        if text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while i < len(text) and text[i] != quote:
                name += text[i]
                i += 1
            if i < len(text):  # Skip closing quote
                i += 1
        else:
            # Name not in quotes, consume until = or whitespace
            while i < len(text) and text[i] != '=' and not text[i].isspace():
                name += text[i]
                i += 1

        # Skip whitespace after name
        while i < len(text) and text[i].isspace():
            i += 1

        # Expect '=' sign
        if i < len(text) and text[i] == '=':
            i += 1  # Skip '='
        else:
            # Malformed, skip this config
            break

        # Skip whitespace after '='
        while i < len(text) and text[i].isspace():
            i += 1

        # Parse value (expected to be in quotes)
        value = ""
        if i < len(text) and text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while i < len(text) and text[i] != quote:
                value += text[i]
                i += 1
            if i < len(text):  # Skip closing quote
                i += 1
        else:
            # Value not in quotes, consume until comma or end
            while i < len(text) and text[i] != ',':
                value += text[i]
                i += 1

        configs.append({"name": name.strip(), "param": value.strip()})

        # Skip whitespace after value
        while i < len(text) and text[i].isspace():
            i += 1

        # Expect comma or end
        if i < len(text) and text[i] == ',':
            i += 1  # Skip comma

    return configs


def parse_file_list(text: str) -> List[Dict[str, Any]]:
    """
    Parse file list with options like: "file1.cpp", "file2.cpp" readonly
    """
    files = []

    if not text.strip():
        return files

    # This is a simplified parsing - in the real U++ parser, file parsing is more complex
    # For now, split by comma and handle basic options
    items = parse_upp_list(text)

    for item_text in items:
        # Each item may have options attached
        parts = item_text.split()
        file_path = parts[0] if parts else ""

        # Create file object
        upp_file = {
            "path": file_path,
            "separator": False,
            "readonly": False,
            "pch": False,
            "nopch": False,
            "noblitz": False
        }

        # Check for options in the remaining parts
        for part in parts[1:]:
            if part.lower() == "readonly":
                upp_file["readonly"] = True
            elif part.lower() == "separator":
                upp_file["separator"] = True
            elif part.lower() == "pch":
                upp_file["pch"] = True
            elif part.lower() == "nopch":
                upp_file["nopch"] = True
            elif part.lower() == "noblitz":
                upp_file["noblitz"] = True
            # Add more option parsing as needed

        files.append(upp_file)

    return files


def render_upp(project: Dict[str, Any]) -> str:
    """
    Render a UppProject object back to .upp file format.
    Preserves original formatting and structure as much as possible.

    Args:
        project: UppProject to render as dictionary

    Returns:
        str: Rendered .upp file content
    """
    lines = []

    # Add description with color encoding if present
    if project.get('description') or project.get('description_bold') or project.get('description_italic') or project.get('description_ink'):
        desc_str = project.get('description', '')
        # Add color/formatting information if present
        if project.get('description_ink') or project.get('description_bold') or project.get('description_italic'):
            desc_str += '\377'  # Character 255 separator
            if project.get('description_bold'):
                desc_str += 'B'
            if project.get('description_italic'):
                desc_str += 'I'
            if project.get('description_ink'):
                r, g, b = project['description_ink']
                desc_str += f"{r},{g},{b}"

        if desc_str:
            # Use quotes for description to handle special characters
            lines.append(f'description "{desc_str}";')

    # Add charset if present
    if project.get('charset'):
        lines.append(f'charset "{project["charset"]}";')

    # Add tabsize if present
    if project.get('tabsize') is not None:
        lines.append(f'tabsize {project["tabsize"]};')

    # Add noblitz if True
    if project.get('noblitz'):
        lines.append('noblitz;')

    # Add nowarnings option if True
    if project.get('nowarnings'):
        lines.append('options(BUILDER_OPTION) NOWARNINGS;')

    # Add accepts flags if present
    if project.get('accepts'):
        accepts_quoted = ['"' + val + '"' for val in project['accepts']]
        accepts_str = ', '.join(accepts_quoted)
        lines.append(f'acceptflags {accepts_str};')

    # Add flags if present
    if project.get('flags'):
        flags_quoted = ['"' + val + '"' for val in project['flags']]
        flags_str = ', '.join(flags_quoted)
        lines.append(f'flags {flags_str};')

    # Add uses if present
    if project.get('uses'):
        uses_quoted = ['"' + val + '"' for val in project['uses']]
        uses_str = ', '.join(uses_quoted)
        lines.append(f'uses {uses_str};')

    # Add target if present
    if project.get('target'):
        target_quoted = ['"' + val + '"' for val in project['target']]
        target_str = ', '.join(target_quoted)
        lines.append(f'target {target_str};')

    # Add library if present
    if project.get('library'):
        library_quoted = ['"' + val + '"' for val in project['library']]
        library_str = ', '.join(library_quoted)
        lines.append(f'library {library_str};')

    # Add static_library if present
    if project.get('static_library'):
        static_library_quoted = ['"' + val + '"' for val in project['static_library']]
        static_library_str = ', '.join(static_library_quoted)
        lines.append(f'static_library {static_library_str};')

    # Add options if present
    if project.get('options'):
        options_quoted = ['"' + val + '"' for val in project['options']]
        options_str = ', '.join(options_quoted)
        lines.append(f'options {options_str};')

    # Add link if present
    if project.get('link'):
        link_quoted = ['"' + val + '"' for val in project['link']]
        link_str = ', '.join(link_quoted)
        lines.append(f'link {link_str};')

    # Add include if present
    if project.get('include'):
        include_quoted = ['"' + val + '"' for val in project['include']]
        include_str = ', '.join(include_quoted)
        lines.append(f'include {include_str};')

    # Add pkg_config if present
    if project.get('pkg_config'):
        pkg_config_quoted = ['"' + val + '"' for val in project['pkg_config']]
        pkg_config_str = ', '.join(pkg_config_quoted)
        lines.append(f'pkg_config {pkg_config_str};')

    # Add files if present
    if project.get('files'):
        file_parts = []
        for upp_file in project['files']:
            part = f'"{upp_file["path"]}"'
            if upp_file.get('readonly'):
                part += " readonly"
            if upp_file.get('separator'):
                part += " separator"
            if upp_file.get('pch'):
                part += " pch"
            if upp_file.get('nopch'):
                part += " nopch"
            if upp_file.get('noblitz'):
                part += " noblitz"
            if upp_file.get('charset'):
                part += f' charset "{upp_file["charset"]}"'
            if upp_file.get('tabsize', 0) > 0:
                part += f" tabsize {upp_file['tabsize']}"
            if upp_file.get('font', 0) > 0:
                part += f" font {upp_file['font']}"
            if upp_file.get('highlight'):
                part += f' highlight "{upp_file["highlight"]}"'
            file_parts.append(part)

        if file_parts:
            files_str = ',\n\t'.join(file_parts)
            lines.append(f"file\n\t{files_str};")

    # Add mainconfig if present
    if project.get('mainconfig'):
        config_parts = []
        for config in project['mainconfig']:
            config_parts.append(f'"{config["name"]}" = "{config["param"]}"')

        if config_parts:
            configs_str = ',\n\t'.join(config_parts)
            lines.append(f"mainconfig\n\t{configs_str};")

    # Add spellcheck_comments if present
    if project.get('spellcheck_comments'):
        lines.append(f' spellcheck_comments "{project["spellcheck_comments"]}"')

    # Add custom steps if present (simplified)
    for custom_step in project.get('custom_steps', []):
        # This is a simplified representation - actual custom steps have more complex format
        pass

    # Add unknown blocks if present
    for unknown_block in project.get('unknown_blocks', []):
        lines.append(unknown_block)

    # Join lines with double newline between major sections
    result = ';\n\n'.join(lines) + ';' if lines else ''

    # Normalize to original line endings if needed
    # Note: For round-trip compatibility, we might want to maintain original format
    return result


def capitalize_first_letter(s):
    """Capitalize first letter of string, keeping the rest as is."""
    if not s:
        return s
    return s[0].upper() + s[1:]


def update_subtask_summary_paths(session: Any, session_path: str):
    """
    Update subtask summary paths to point to the .maestro directory for backward compatibility.
    If summary files exist in the old location (relative to session file), move them to the new location.

    Args:
        session: The session object
        session_path: Path to the session file
    """
    import shutil

    maestro_dir = get_maestro_dir(session_path)
    outputs_dir = os.path.join(maestro_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    session_dir = os.path.dirname(os.path.abspath(session_path))

    for subtask in session.subtasks:
        # If the summary_file path doesn't already contain .maestro, update it
        if subtask.summary_file and ".maestro" not in subtask.summary_file:
            # Extract just the filename from the old path
            filename = os.path.basename(subtask.summary_file)
            # Create the new path in the .maestro directory
            new_path = os.path.join(outputs_dir, filename)

            # Check if the old file exists relative to the session file's directory
            # The old path from the session file would be relative to where the session was created
            old_path_relative_to_session = os.path.join(session_dir, subtask.summary_file)

            # If the old file exists (either at the direct path from session or relative to session dir), move it to the new location
            old_path_to_use = None
            if os.path.exists(subtask.summary_file):
                # Old path is accessible as-is (relative to current working directory)
                old_path_to_use = subtask.summary_file
            elif os.path.exists(old_path_relative_to_session):
                # Old path is relative to session file directory
                old_path_to_use = old_path_relative_to_session

            if old_path_to_use and not os.path.exists(new_path):
                try:
                    # Ensure the new directory exists
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    # Move the file to the new location
                    shutil.move(old_path_to_use, new_path)
                    print_debug(f"Moved summary file from {old_path_to_use} to {new_path}", 2)
                except Exception as e:
                    print_warning(f"Could not move summary file from {old_path_to_use} to {new_path}: {e}", 2)

            # Update the path in the session to point to the new location
            subtask.summary_file = new_path


def has_legacy_plan(subtasks):
    """
    Check if the given subtasks represent the legacy 3-task hard-coded plan.

    Args:
        subtasks: List of subtask objects with 'title' attribute

    Returns:
        bool: True if legacy 3-task plan is detected, False otherwise
    """
    titles = {getattr(st, 'title', '') for st in subtasks if hasattr(st, 'title')}
    return LEGACY_TITLES.issubset(titles)


def assert_no_legacy_subtasks(subtasks):
    """
    Assert that no legacy hard-coded subtasks are present in the plan.

    Args:
        subtasks: List of subtask objects with 'title' attribute

    Raises:
        AssertionError: If all three legacy titles are detected together
    """
    titles = {getattr(st, 'title', '') for st in subtasks if hasattr(st, 'title')}
    if LEGACY_TITLES.issubset(titles):
        raise AssertionError(
            "Legacy hard-coded subtasks detected in plan: "
            f"{sorted(titles.intersection(LEGACY_TITLES))}"
        )


def check_git_hygiene():
    """
    Check git hygiene and warn about potential issues in shared repository.
    Only produces output when verbose flag is set.
    """
    import subprocess
    import os

    try:
        # Check if we're in a git repository
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'],
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            # Not in a git repo, skip checks
            return

        # Check if working tree is dirty
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0 and result.stdout.strip():
            print_warning("Working tree is dirty. Consider committing or stashing changes before proceeding.", 2)
            print_warning("Files with changes:", 3)
            for line in result.stdout.strip().split('\n')[:10]:  # Show first 10 files
                print_info(f"  {line}", 4)
            if len(result.stdout.strip().split('\n')) > 10:
                print_info("  ... and more", 4)

        # Check if local is behind upstream (optional check)
        try:
            # Get current branch name
            branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                         capture_output=True, text=True, cwd=os.getcwd())
            if branch_result.returncode == 0:
                current_branch = branch_result.stdout.strip()

                # Check if remote tracking branch exists
                upstream_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', f'@{{u}}'],
                                               capture_output=True, text=True, cwd=os.getcwd())
                if upstream_result.returncode == 0:
                    # Check if local is behind upstream
                    upstream_branch = upstream_result.stdout.strip()
                    merge_base_result = subprocess.run(['git', 'merge-base', f'{upstream_branch}', 'HEAD'],
                                                     capture_output=True, text=True, cwd=os.getcwd())
                    rev_parse_result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                                    capture_output=True, text=True, cwd=os.getcwd())

                    if merge_base_result.returncode == 0 and rev_parse_result.returncode == 0:
                        merge_base = merge_base_result.stdout.strip()
                        current_commit = rev_parse_result.stdout.strip()

                        if merge_base != current_commit:
                            # Check if we're behind (upstream has commits we don't have)
                            rev_list_result = subprocess.run(['git', 'rev-list', '--count', f'HEAD..{upstream_branch}'],
                                                           capture_output=True, text=True, cwd=os.getcwd())
                            if rev_list_result.returncode == 0 and rev_list_result.stdout.strip() != '0':
                                behind_count = rev_list_result.stdout.strip()
                                print_warning(f"Local branch is {behind_count} commit(s) behind upstream '{upstream_branch}'. Consider running 'git pull' or 'git rebase'.", 2)
        except Exception:
            # If upstream check fails, just skip it without error
            pass

    except Exception:
        # If git is not available or any other error occurs, skip checks
        pass


def clean_json_response(response_text: str) -> str:
    """
    Clean up JSON response by removing markdown code block wrappers and other formatting.

    Args:
        response_text: Raw response text from the planner

    Returns:
        Cleaned JSON string ready for parsing
    """
    import re

    # Remove markdown code block markers (both with and without language specification)
    # Pattern matches ```json, ```JSON, ``` or just ```
    cleaned = re.sub(r'^\s*```\s*(json|JSON)?\s*\n?', '', response_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.IGNORECASE)

    # Also handle cases where there are multiple code blocks or trailing text
    # Find the first JSON object between code blocks
    if not cleaned.strip().startswith('{') and not cleaned.strip().startswith('['):
        # Look for JSON object within the response
        matches = re.findall(r'\{.*\}', response_text, re.DOTALL)
        if matches:
            # Get the most likely JSON response (longest match that looks like JSON)
            potential_jsons = [match for match in matches if '"version"' in match or '"subtasks"' in match or '"clean_text"' in match]
            if potential_jsons:
                # Take the first one that looks like our expected JSON format
                cleaned = potential_jsons[0]

    return cleaned.strip()


def save_prompt_for_traceability(prompt: str, session_path: str = None, prompt_type: str = "generic", engine_name: str = "unknown") -> str:
    """
    Save the constructed prompt to enable traceability and debugging.

    Args:
        prompt: The constructed prompt string
        session_path: Path to the session directory (optional - if None, uses appropriate config directories)
        prompt_type: Type of prompt (e.g., 'planner', 'worker', 'build_target_planner', etc.)
        engine_name: Name of the engine that will process this prompt

    Returns:
        Path to the saved prompt file
    """
    import time
    import os

    # Determine the appropriate directory based on prompt type for the three planner types
    if "build" in prompt_type.lower():
        # Build target planner -> .maestro/build/inputs/
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            inputs_dir = os.path.join(maestro_dir, "build", "inputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            inputs_dir = os.path.join(user_config_dir, "build", "inputs")
    elif "fix" in prompt_type.lower() or "rulebook" in prompt_type.lower():
        # Fix rulebook planner -> ~/.config/maestro/fix/inputs/
        user_config_dir = get_user_config_dir()
        inputs_dir = os.path.join(user_config_dir, "fix", "inputs")
    elif "convert" in prompt_type.lower() or "conversion" in prompt_type.lower():
        # Conversion pipeline planner -> .maestro/convert/inputs/
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            inputs_dir = os.path.join(maestro_dir, "convert", "inputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            inputs_dir = os.path.join(user_config_dir, "convert", "inputs")
    else:
        # Default to general inputs directory for other types
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            inputs_dir = os.path.join(maestro_dir, "inputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            inputs_dir = os.path.join(user_config_dir, "inputs")

    os.makedirs(inputs_dir, exist_ok=True)

    # Create timestamp
    timestamp = int(time.time())

    # Create filename with type, engine, and timestamp
    prompt_filename = os.path.join(inputs_dir, f"{prompt_type}_{engine_name}_{timestamp}.txt")

    # Write the prompt to the file
    with open(prompt_filename, "w", encoding="utf-8") as f:
        f.write(prompt)

    return prompt_filename


def save_ai_output(output: str, session_path: str = None, output_type: str = "generic", engine_name: str = "unknown") -> str:
    """
    Save the AI output to enable traceability and debugging.

    Args:
        output: The AI output string
        session_path: Path to the session directory (optional - if None, uses appropriate config directories)
        output_type: Type of output (e.g., 'planner', 'worker', etc.)
        engine_name: Name of the engine that generated this output

    Returns:
        Path to the saved output file
    """
    import time
    import os

    # Determine the appropriate directory based on output type for the three planner types
    if "build" in output_type.lower():
        # Build target planner -> .maestro/build/outputs/
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            outputs_dir = os.path.join(maestro_dir, "build", "outputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            outputs_dir = os.path.join(user_config_dir, "build", "outputs")
    elif "fix" in output_type.lower() or "rulebook" in output_type.lower():
        # Fix rulebook planner -> ~/.config/maestro/fix/outputs/
        user_config_dir = get_user_config_dir()
        outputs_dir = os.path.join(user_config_dir, "fix", "outputs")
    elif "convert" in output_type.lower() or "conversion" in output_type.lower():
        # Conversion pipeline planner -> .maestro/convert/outputs/
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            outputs_dir = os.path.join(maestro_dir, "convert", "outputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            outputs_dir = os.path.join(user_config_dir, "convert", "outputs")
    else:
        # Default to general outputs directory for other types
        if session_path:
            maestro_dir = get_maestro_dir(session_path)
            outputs_dir = os.path.join(maestro_dir, "outputs")
        else:
            # Fallback to user config if no session_path provided
            user_config_dir = get_user_config_dir()
            outputs_dir = os.path.join(user_config_dir, "outputs")

    os.makedirs(outputs_dir, exist_ok=True)

    # Create timestamp
    timestamp = int(time.time())

    # Create filename with type, engine, and timestamp
    output_filename = os.path.join(outputs_dir, f"{output_type}_{engine_name}_{timestamp}.txt")

    # Write the output to the file
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(output)

    return output_filename


def build_prompt(
    goal: str,
    context: str | None,
    requirements: str | None,
    acceptance: str | None,
    deliverables: str | None,
) -> str:
    """
    Centralized prompt builder with strict validation. All sections are mandatory.
    If a section is not applicable, use the literal text "None".

    Args:
        goal: The main goal/task objective
        context: Background context and current state
        requirements: Specific requirements that must be met
        acceptance: Acceptance criteria for completion
        deliverables: Expected deliverables from the task

    Returns:
        The complete structured prompt string
    """
    # Validate inputs and set defaults if needed
    goal = goal if goal is not None else "None"
    context = context if context is not None else "None"
    requirements = requirements if requirements is not None else "None"
    acceptance = acceptance if acceptance is not None else "None"
    deliverables = deliverables if deliverables is not None else "None"

    # Construct the prompt with required sections
    prompt = f"[GOAL]\n{goal}\n\n"
    prompt += f"[CONTEXT]\n{context}\n\n"
    prompt += f"[REQUIREMENTS]\n{requirements}\n\n"
    prompt += f"[ACCEPTANCE CRITERIA]\n{acceptance}\n\n"
    prompt += f"[DELIVERABLES]\n{deliverables}\n\n"

    # Validate that all required sections exist
    missing_sections = []
    if "[GOAL]" not in prompt:
        missing_sections.append("[GOAL]")
    if "[CONTEXT]" not in prompt:
        missing_sections.append("[CONTEXT]")
    if "[REQUIREMENTS]" not in prompt:
        missing_sections.append("[REQUIREMENTS]")
    if "[ACCEPTANCE CRITERIA]" not in prompt:
        missing_sections.append("[ACCEPTANCE CRITERIA]")
    if "[DELIVERABLES]" not in prompt:
        missing_sections.append("[DELIVERABLES]")

    if missing_sections:
        raise ValueError(f"Prompt validation failed: Missing required sections: {', '.join(missing_sections)}")

    # Validate that each section has content (not empty after the header)
    sections = prompt.split('\n\n')
    for i, section in enumerate(sections):
        if section.startswith('[GOAL]'):
            content = section[len('[GOAL]\n'):].strip()
            if not content:
                raise ValueError("GOAL section cannot be empty")
        elif section.startswith('[CONTEXT]'):
            content = section[len('[CONTEXT]\n'):].strip()
            if not content:
                raise ValueError("CONTEXT section cannot be empty")
        elif section.startswith('[REQUIREMENTS]'):
            content = section[len('[REQUIREMENTS]\n'):].strip()
            if not content:
                raise ValueError("REQUIREMENTS section cannot be empty")
        elif section.startswith('[ACCEPTANCE CRITERIA]'):
            content = section[len('[ACCEPTANCE CRITERIA]\n'):].strip()
            if not content:
                raise ValueError("ACCEPTANCE CRITERIA section cannot be empty")
        elif section.startswith('[DELIVERABLES]'):
            content = section[len('[DELIVERABLES]\n'):].strip()
            if not content:
                raise ValueError("DELIVERABLES section cannot be empty")

    return prompt


def _filter_suppressed_help(help_text: str) -> str:
    """
    Remove suppressed help sections from help text.

    Args:
        help_text: The help text to filter

    Returns:
        Filtered help text with suppressed sections removed
    """
    # This function filters out help sections that have been marked for suppression
    # by looking for specific markers in the help text
    lines = help_text.split('\n')
    filtered_lines = []

    for line in lines:
        # Filter out lines that contain suppressed help markers
        if 'SUPPRESS' not in line:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def build_structured_prompt(goal: str = "None", requirements: str = "None", acceptance_criteria: str = "None", deliverables: str = "None") -> str:
    """
    Build a structured prompt with required sections.
    If a section is irrelevant, use "None" as the value.
    This function is maintained for backward compatibility.

    Args:
        goal: The main goal of the task
        requirements: Requirements for the task
        acceptance_criteria: Acceptance criteria for the task
        deliverables: Expected deliverables from the task

    Returns:
        The structured prompt string with all required sections
    """
    # For backward compatibility, map the old format to the new one
    context = "None"  # Using context as a placeholder since old format doesn't have it
    return build_prompt(
        goal=goal,
        context=context,
        requirements=requirements,
        acceptance=acceptance_criteria,
        deliverables=deliverables
    )