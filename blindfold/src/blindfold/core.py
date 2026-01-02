"""Blindfold core module."""

import yaml
from . import persistence
from . import cookie
from . import error_log
from . import feedback
from . import mapping
from . import interface_loader
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

        # Write feedback
        feedback.write_feedback(paths["state_dir"], cookie_str, feedback_data)

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
                version="0.0.0"
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