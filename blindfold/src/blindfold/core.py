"""Blindfold core module."""

import yaml
import shlex
from . import persistence
from . import cookie
from . import error_log
from . import feedback
from . import mapping
from . import interface_loader
from . import redaction
from . import db
from . import state_db
import os
import json


def run(mode: str, command_argv: list, stdin_text: str):
    """
    Core function that handles the different modes.

    Args:
        mode: The mode to run in ("blind", "admin", "feedback")
        command_argv: List of command line arguments for the command
        stdin_text: Text from stdin

    Returns:
        tuple: (exit_code, stdout_text, stderr_text)
    """
    if mode == "admin":
        # Admin mode - return human-readable message (not YAML)
        return 0, "Admin mode stub\n", ""
    elif mode == "feedback":
        # Feedback mode - validate cookie and store feedback
        if len(command_argv) == 0:
            return 3, "", "missing cookie for --FEEDBACK\n"

        cookie_str = command_argv[0]

        # Validate cookie format
        if not cookie.validate_cookie(cookie_str):
            return 3, "", "invalid cookie format\n"

        # Get paths and ensure directories exist
        paths = persistence.get_default_paths()
        persistence.ensure_dirs(paths)

        # Check that error record exists
        error_file_path = os.path.join(paths["state_dir"], "errors", f"{cookie_str}.json")
        if not os.path.exists(error_file_path):
            return 3, "", "unknown error cookie\n"

        # Parse feedback from stdin
        try:
            feedback_data = feedback.parse_feedback_text(stdin_text)
        except ValueError:
            return 3, "", "invalid feedback payload\n"

        # Load redaction rules
        redaction_rules = redaction.load_redaction_rules(paths["data_dir"])

        # Write feedback
        feedback.write_feedback(paths["state_dir"], cookie_str, feedback_data, redaction_rules=redaction_rules)

        # Return success
        return 0, f"feedback stored for {cookie_str}\n", ""
    elif mode == "blind":
        # Check if this is a blind command attempt (non-empty command_argv)
        if len(command_argv) > 0:
            # Get paths and ensure directories exist
            paths = persistence.get_default_paths()
            persistence.ensure_dirs(paths)

            # Bootstrap packaged data if needed
            persistence.bootstrap_packaged_data(paths["data_dir"])

            # Load redaction rules
            redaction_rules = redaction.load_redaction_rules(paths["data_dir"])

            # Load mappings and check for a match
            mappings_file = os.path.join(paths["data_dir"], "mappings", "mappings.yaml")
            mappings = mapping.load_mappings(mappings_file)
            matched_mapping = mapping.find_mapping(command_argv, mappings)

            # If a mapping matches, return the interface YAML
            if matched_mapping:
                interface_filename = matched_mapping.get("interface")
                if interface_filename:
                    try:
                        interface_text = interface_loader.load_interface_text(paths["data_dir"], interface_filename)
                        return 0, interface_text, ""
                    except FileNotFoundError:
                        # If interface file not found, continue with error cookie flow
                        pass

            # This is an invalid blind command - generate cookie and write error record
            # Generate a unique cookie (try up to 10 times to avoid collisions)
            for _ in range(10):
                cookie_val = cookie.generate_cookie()
                error_file_path = os.path.join(paths["state_dir"], "errors", f"{cookie_val}.json")
                if not os.path.exists(error_file_path):
                    break
            else:
                # If we couldn't find a unique cookie after 10 tries, raise an error
                return 2, "", "Error: Could not generate unique cookie\n"

            # Write error record
            error_log.write_error_record(
                state_dir=paths["state_dir"],
                cookie=cookie_val,
                argv=command_argv,
                cwd=os.getcwd(),
                stdin_text=stdin_text,
                version="0.0.0",
                redaction_rules=redaction_rules
            )

            # Return error message with cookie
            error_msg = f"virheellinen komento. error-cookie-id={cookie_val}\n"
            return 2, "", error_msg
        else:
            # Default blind mode - return YAML document
            yaml_output = yaml.dump({
                "api_version": 0,
                "mode": "blind",
                "message": "stub"
            })
            return 0, yaml_output, ""


def run_admin(subcommand: str, args: list):
    """
    Handle admin subcommands.

    Args:
        subcommand: The admin subcommand to run
        args: List of arguments for the subcommand

    Returns:
        tuple: (exit_code, stdout_text, stderr_text)
    """
    # Get paths and ensure directories exist
    paths = persistence.get_default_paths()
    persistence.ensure_dirs(paths)

    # Handle session and var subcommands that require database
    if subcommand.startswith("session") or subcommand.startswith("var"):
        db_path = db.get_db_path(paths["state_dir"])
        conn = db.connect(db_path)
        state_db.init_db(conn)

        if subcommand == "session":
            result = handle_session_subcommand(conn, args)
        elif subcommand == "var":
            result = handle_var_subcommand(conn, args)
        else:
            result = 4, "", f"unknown admin subcommand: {subcommand}\n"

        conn.close()
        return result
    elif subcommand == "list-errors":
        return admin_list_errors(paths["state_dir"])
    elif subcommand == "show-error":
        if len(args) != 1:
            return 4, "", "show-error requires exactly one cookie argument\n"
        return admin_show_error(paths["state_dir"], args[0])
    elif subcommand == "list-feedback":
        return admin_list_feedback(paths["state_dir"])
    elif subcommand == "show-feedback":
        if len(args) != 1:
            return 4, "", "show-feedback requires exactly one cookie argument\n"
        return admin_show_feedback(paths["state_dir"], args[0])
    elif subcommand == "add-mapping":
        return admin_add_mapping(paths, args)
    elif subcommand == "gc":
        # Handle "gc --older-than <duration>" format
        if len(args) >= 2 and args[0] == "--older-than":
            return admin_gc(paths["state_dir"], args[1])
        else:
            return 4, "", "gc requires --older-than <duration> argument\n"
    else:
        return 4, "", f"unknown admin subcommand: {subcommand}\n"


def handle_session_subcommand(conn, args: list):
    """
    Handle session subcommands.

    Args:
        conn: Database connection
        args: List of arguments for the session subcommand

    Returns:
        tuple: (exit_code, stdout_text, stderr_text)
    """
    if len(args) < 1:
        return 4, "", "session subcommand requires an action (list, create, delete)\n"

    action = args[0]
    action_args = args[1:]

    if action == "list":
        return admin_session_list(conn)
    elif action == "create":
        if len(action_args) != 1:
            return 4, "", "session create requires exactly one name argument\n"
        return admin_session_create(conn, action_args[0])
    elif action == "delete":
        if len(action_args) != 1:
            return 4, "", "session delete requires exactly one name argument\n"
        return admin_session_delete(conn, action_args[0])
    else:
        return 4, "", f"unknown session action: {action}\n"


def handle_var_subcommand(conn, args: list):
    """
    Handle var subcommands.

    Args:
        conn: Database connection
        args: List of arguments for the var subcommand

    Returns:
        tuple: (exit_code, stdout_text, stderr_text)
    """
    if len(args) < 1:
        return 4, "", "var subcommand requires an action (set, get, list)\n"

    action = args[0]
    action_args = args[1:]

    if action == "set":
        return admin_var_set(conn, action_args)
    elif action == "get":
        return admin_var_get(conn, action_args)
    elif action == "list":
        return admin_var_list(conn, action_args)
    else:
        return 4, "", f"unknown var action: {action}\n"


def admin_session_list(conn):
    """List all sessions."""
    sessions = state_db.list_sessions(conn)
    return 0, "\n".join(sessions) + ("\n" if sessions else ""), ""


def admin_session_create(conn, name: str):
    """Create a session."""
    # Check if session already exists by trying to get it
    existing_sessions = state_db.list_sessions(conn)
    if name in existing_sessions:
        return 0, f"session exists {name}\n", ""

    # Create the session
    session_id = state_db.ensure_session(conn, name)
    return 0, f"created session {name}\n", ""


def admin_session_delete(conn, name: str):
    """Delete a session."""
    deleted = state_db.delete_session(conn, name)
    if deleted:
        return 0, f"deleted session {name}\n", ""
    else:
        return 4, f"session not found {name}\n", ""


def admin_var_set(conn, args: list):
    """Set a variable in a session."""
    # Parse arguments manually
    session_name = None
    key = None
    value = None
    var_type = "string"

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--session" and i + 1 < len(args):
            session_name = args[i + 1]
            i += 2
        elif arg == "--key" and i + 1 < len(args):
            key = args[i + 1]
            i += 2
        elif arg == "--value" and i + 1 < len(args):
            value = args[i + 1]
            i += 2
        elif arg == "--type" and i + 1 < len(args):
            var_type = args[i + 1]
            i += 2
        else:
            i += 1

    if not session_name or not key or value is None:
        return 4, "", "var set requires --session, --key, and --value arguments\n"

    state_db.set_var(conn, session_name, key, value, var_type)
    return 0, f"set {session_name}:{key}\n", ""


def admin_var_get(conn, args: list):
    """Get a variable from a session."""
    # Parse arguments manually
    session_name = None
    key = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--session" and i + 1 < len(args):
            session_name = args[i + 1]
            i += 2
        elif arg == "--key" and i + 1 < len(args):
            key = args[i + 1]
            i += 2
        else:
            i += 1

    if not session_name or not key:
        return 4, "", "var get requires --session and --key arguments\n"

    result = state_db.get_var(conn, session_name, key)
    if result:
        value, var_type = result
        return 0, f"{value}\n", f"(type={var_type})\n" if var_type != "string" else ""
    else:
        return 4, "", f"variable not found: {session_name}:{key}\n"


def admin_var_list(conn, args: list):
    """List all variables in a session."""
    # Parse arguments manually
    session_name = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--session" and i + 1 < len(args):
            session_name = args[i + 1]
            i += 2
        else:
            i += 1

    if not session_name:
        return 4, "", "var list requires --session argument\n"

    vars_list = state_db.list_vars(conn, session_name)
    output_lines = []
    for key, value, var_type in vars_list:
        if var_type == "string":
            output_lines.append(f"{key}={value}")
        else:
            output_lines.append(f"{key}={value} (type={var_type})")

    return 0, "\n".join(output_lines) + ("\n" if output_lines else ""), ""


def admin_list_errors(state_dir: str):
    """List error cookies."""
    import glob
    error_dir = os.path.join(state_dir, "errors")
    error_files = glob.glob(os.path.join(error_dir, "*.json"))
    cookies = [os.path.basename(f)[:-5] for f in error_files]  # Remove .json extension
    cookies.sort()  # Sort alphabetically
    return 0, "\n".join(cookies) + ("\n" if cookies else ""), ""


def admin_show_error(state_dir: str, cookie_val: str):
    """Show details of a specific error."""
    # Validate cookie format
    if not cookie.validate_cookie(cookie_val):
        return 4, "", f"invalid cookie format: {cookie_val}\n"

    error_file_path = os.path.join(state_dir, "errors", f"{cookie_val}.json")
    if not os.path.exists(error_file_path):
        return 4, "", f"error cookie not found: {cookie_val}\n"

    try:
        with open(error_file_path, 'r', encoding='utf-8') as f:
            error_data = json.load(f)

        # Pretty-print selected fields
        output = f"COOKIE: {error_data.get('cookie', 'N/A')}\n"
        output += f"TIMESTAMP_UTC: {error_data.get('timestamp_utc', 'N/A')}\n"
        output += f"ARGV: {error_data.get('argv', 'N/A')}\n"
        output += f"CWD: {error_data.get('cwd', 'N/A')}\n"
        stdin_snippet = error_data.get('stdin_text', '')[:100]  # Truncate to 100 chars
        output += f"STDIN_SNIPPET: {stdin_snippet}{'...' if len(error_data.get('stdin_text', '')) > 100 else ''}\n"
        output += f"BLINDFOLD_VERSION: {error_data.get('version', 'N/A')}\n"

        return 0, output, ""
    except (json.JSONDecodeError, KeyError) as e:
        return 4, "", f"error reading error file: {str(e)}\n"


def admin_list_feedback(state_dir: str):
    """List feedback cookies."""
    import glob
    feedback_dir = os.path.join(state_dir, "feedback")
    feedback_files = glob.glob(os.path.join(feedback_dir, "*.yaml"))
    cookies = [os.path.basename(f)[:-5] for f in feedback_files]  # Remove .yaml extension
    cookies.sort()  # Sort alphabetically
    return 0, "\n".join(cookies) + ("\n" if cookies else ""), ""


def admin_show_feedback(state_dir: str, cookie: str):
    """Show details of a specific feedback."""
    feedback_file_path = os.path.join(state_dir, "feedback", f"{cookie}.yaml")
    if not os.path.exists(feedback_file_path):
        return 4, "", f"feedback cookie not found: {cookie}\n"

    try:
        with open(feedback_file_path, 'r', encoding='utf-8') as f:
            feedback_data = yaml.safe_load(f)

        output = f"FEEDBACK {cookie}:\n"
        output += yaml.safe_dump(feedback_data, sort_keys=False)
        return 0, output, ""
    except (yaml.YAMLError, Exception) as e:
        return 4, "", f"error reading feedback file: {str(e)}\n"


def admin_add_mapping(paths: dict, args: list):
    """Add a new mapping."""
    # Parse arguments manually since we're not using argparse for the admin subcommands
    argv_string = None
    interface_filename = None
    mapping_id = None
    notes = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--argv" and i + 1 < len(args):
            argv_string = args[i + 1]
            i += 2
        elif arg == "--interface" and i + 1 < len(args):
            interface_filename = args[i + 1]
            i += 2
        elif arg == "--id" and i + 1 < len(args):
            mapping_id = args[i + 1]
            i += 2
        elif arg == "--notes" and i + 1 < len(args):
            notes = args[i + 1]
            i += 2
        else:
            i += 1

    if not argv_string or not interface_filename:
        return 4, "", "add-mapping requires --argv and --interface arguments\n"

    # Parse argv tokens from string using shlex
    try:
        argv_tokens = shlex.split(argv_string)
    except ValueError as e:
        return 4, "", f"error parsing argv string: {str(e)}\n"

    # Validate interface file exists in <data_dir>/interfaces/<interface_filename>
    interface_path = os.path.join(paths["data_dir"], "interfaces", interface_filename)
    if not os.path.exists(interface_path):
        return 4, "", f"interface file does not exist: {interface_path}\n"

    # Call mapping.add_mapping
    try:
        mappings_file = os.path.join(paths["data_dir"], "mappings", "mappings.yaml")
        new_mapping = mapping.add_mapping(mappings_file, argv_tokens, interface_filename, mapping_id, notes)

        output = f"added mapping {new_mapping['id']}: argv={new_mapping['argv']} -> interface={new_mapping['interface']}\n"
        return 0, output, ""
    except Exception as e:
        return 4, "", f"error adding mapping: {str(e)}\n"


def parse_duration_to_seconds(s: str) -> int:
    """
    Parse duration string to seconds.

    Args:
        s: Duration string in format Nd, Nh, Nm (N days, hours, minutes)

    Returns:
        int: Number of seconds

    Raises:
        ValueError: If the format is invalid
    """
    import re

    # Validate with regex r"^(\d+)([dhm])$"
    match = re.match(r"^(\d+)([dhm])$", s)
    if not match:
        raise ValueError(f"Invalid duration format: {s}. Expected format: Nd (days), Nh (hours), Nm (minutes)")

    value, unit = match.groups()
    value = int(value)

    if unit == 'd':
        return value * 24 * 60 * 60  # days to seconds
    elif unit == 'h':
        return value * 60 * 60       # hours to seconds
    elif unit == 'm':
        return value * 60            # minutes to seconds
    else:
        raise ValueError(f"Invalid unit: {unit}. Expected d, h, or m")


def admin_gc(state_dir: str, duration_str: str):
    """
    Garbage collect old error logs and feedback files.

    Args:
        state_dir: Base state directory
        duration_str: Duration string like '30d', '12h', '90m'

    Returns:
        tuple: (exit_code, stdout_text, stderr_text)
    """
    import os
    import time
    from datetime import datetime

    try:
        seconds = parse_duration_to_seconds(duration_str)
    except ValueError as e:
        return 4, "", f"{str(e)}\n"

    # Calculate cutoff time
    cutoff_time = time.time() - seconds

    # Directories to clean
    errors_dir = os.path.join(state_dir, "errors")
    feedback_dir = os.path.join(state_dir, "feedback")

    # Count deleted files
    deleted_errors = 0
    deleted_feedback = 0

    # Delete old error files
    if os.path.exists(errors_dir):
        for filename in os.listdir(errors_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(errors_dir, filename)
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    deleted_errors += 1

    # Delete old feedback files
    if os.path.exists(feedback_dir):
        for filename in os.listdir(feedback_dir):
            if filename.endswith('.yaml'):
                filepath = os.path.join(feedback_dir, filename)
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    deleted_feedback += 1

    # Print summary
    summary = f"gc: deleted {deleted_errors} error logs, {deleted_feedback} feedback files (older than {duration_str})\n"
    return 0, summary, ""