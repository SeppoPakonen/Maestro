#!/usr/bin/env python3
"""
Orchestrator CLI - A command-line interface for managing AI task sessions.
"""
import argparse
import sys
import os
import subprocess
import uuid
from datetime import datetime

# Import the session model from the same directory
from session_model import Session, Subtask, load_session, save_session


def main():
    parser = argparse.ArgumentParser(description="AI Task Orchestrator")
    parser.add_argument('--session', required=True, help='Path to the session JSON file')

    # Mutually exclusive group for commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', action='store_true', help='Create a new session')
    group.add_argument('--resume', action='store_true', help='Resume an existing session')
    group.add_argument('--rules', action='store_true', help='Edit the rules file')

    args = parser.parse_args()

    # Determine which action to take based on flags
    if args.new:
        handle_new_session(args.session)
    elif args.resume:
        handle_resume_session(args.session)
    elif args.rules:
        handle_rules_file(args.session)


def handle_new_session(session_path):
    """Handle creating a new session."""
    # Check if session file already exists
    if os.path.exists(session_path):
        print(f"Error: Session file '{session_path}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Determine the directory of the session file
    session_dir = os.path.dirname(os.path.abspath(session_path)) or '.'

    # Determine if there's a corresponding rules file in the same directory
    rules_filename = os.path.join(session_dir, "rules.txt")
    rules_path = rules_filename if os.path.exists(rules_filename) else None

    # Prompt user for the root task
    print("Enter the root task:", end=" ", flush=True)
    root_task = sys.stdin.readline().strip()

    # Create a new session with status="new" and empty subtasks
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task=root_task,
        subtasks=[],
        rules_path=rules_path,  # Point to rules file if it exists
        status="new"
    )

    # Save the session
    save_session(session, session_path)
    print(f"Created new session: {session_path}")


def handle_resume_session(session_path):
    """Handle resuming an existing session."""
    # Attempt to load the session, which will handle file not found and JSON errors
    try:
        session = load_session(session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Print the current status and number of subtasks
    print(f"Status: {session.status}")
    print(f"Number of subtasks: {len(session.subtasks)}")


def handle_rules_file(session_path):
    """Handle opening the rules file in an editor."""
    # Load the session first
    try:
        session = load_session(session_path)
    except FileNotFoundError:
        # If session doesn't exist, we can't update its rules_path, but we'll still create a rules file
        session = None
        print(f"Session file '{session_path}' does not exist. Creating rules file anyway.")

    # Determine the directory of the session file
    session_dir = os.path.dirname(os.path.abspath(session_path))

    # If session.rules_path is empty or None, set it to the default
    if session and session.rules_path is None:
        rules_filename = os.path.join(session_dir, "rules.txt")
        session.rules_path = rules_filename
        # Update the session with the new rules path
        save_session(session, session_path)
        print(f"Updated session.rules_path to: {rules_filename}")
    elif session and session.rules_path:
        rules_filename = session.rules_path
    else:
        # If no session but still need rules, use default location
        rules_filename = os.path.join(session_dir, "rules.txt")

    # Ensure the rules file exists
    if not os.path.exists(rules_filename):
        print(f"Rules file does not exist. Creating: {rules_filename}")
        # Create the file with some default content
        with open(rules_filename, 'w') as f:
            f.write("# Rules for AI task orchestration\n")
            f.write("# Add your rules here\n")
            f.write("# Examples of instructions that can be included:\n")
            f.write("# - Commit to git at the end.\n")
            f.write("# - Compile the program and run tests.\n")
            f.write("# - Generate build.sh and run.sh scripts.\n")

    # Use vi as fallback if EDITOR is not set
    editor = os.environ.get('EDITOR', 'vi')

    # Open the editor with the rules file
    try:
        subprocess.run([editor, rules_filename])
    except FileNotFoundError:
        print(f"Error: Editor '{editor}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not open editor: {str(e)}", file=sys.stderr)
        sys.exit(1)


def load_rules(session: Session) -> str:
    """
    Load the rules text from the rules file specified in the session.

    Args:
        session: The session object containing the rules path

    Returns:
        The rules text as a string (empty if no rules file exists or path is None)
    """
    if not session.rules_path:
        return ""

    try:
        with open(session.rules_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # If the rules file doesn't exist, return empty string
        return ""
    except Exception:
        # If there's any other error reading the file, return empty string
        print(f"Warning: Could not read rules file '{session.rules_path}'", file=sys.stderr)
        return ""


if __name__ == "__main__":
    main()