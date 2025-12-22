"""
Command handlers for Maestro.
"""
import os
import sys
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path

from ..session_model import Session, Subtask, PlanNode, load_session, save_session
from .dataclasses import *
from .utils import *


def handle_session_new(session_name: str, verbose: bool = False, root_task_file: str = None):
    """Handle creating a new session in the .maestro/sessions directory."""
    if verbose:
        print_debug(f"Creating new session: {session_name}", 2)

    if not session_name:
        # Prompt for session name if not provided
        session_name = input("Enter session name: ").strip()
        if not session_name:
            print_error("Session name is required", 2)
            sys.exit(1)

    # Check if session already exists and prompt for overwrite confirmation
    session_path = get_session_path_by_name(session_name)
    if os.path.exists(session_path):
        print_warning(f"Session '{session_name}' already exists", 2)
        confirm = input(f"Do you want to overwrite the existing session '{session_name}'? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print_info("Session creation cancelled", 2)
            return

    # Get root task based on provided file or interactive editor
    if root_task_file:
        # Load from file
        try:
            with open(root_task_file, 'r', encoding='utf-8') as f:
                root_task = f.read().strip()
        except FileNotFoundError:
            print_error(f"Root task file '{root_task_file}' not found.", 2)
            sys.exit(1)
        except Exception as e:
            print_error(f"Could not read root task file '{root_task_file}': {e}", 2)
            sys.exit(1)
    else:
        # Open editor for the root task
        root_task = edit_root_task_in_editor()

    try:
        # Create session with overwrite=True since we already confirmed with user
        session_path = create_session(session_name, root_task, overwrite=True)
        print_success(f"Created new session: {session_name}", 2)
        print_info(f"Session stored at: {session_path}", 2)

        if verbose:
            # Load the session to show details
            session = load_session(session_path)
            print_debug(f"Session ID: {session.id}", 4)
            print_debug(f"Session created at: {session.created_at}", 4)

        # Set this session as the active session
        if set_active_session_name(session_name):
            print_info(f"Session '{session_name}' is now the active session", 2)
        else:
            print_warning(f"Could not set '{session_name}' as active session", 2)

    except Exception as e:
        print_error(f"Error creating session: {str(e)}", 2)
        sys.exit(1)


def handle_session_list(verbose: bool = False):
    """Handle listing all sessions in the .maestro/sessions directory."""
    sessions = list_sessions()
    active_session = get_active_session_name()

    if not sessions:
        print_info("No sessions found.", 2)
        return

    print_header("SESSIONS")

    for i, session_name in enumerate(sessions, 1):
        session_path = get_session_path_by_name(session_name)
        marker = "[*]" if session_name == active_session else "[ ]"
        status_color = Colors.BRIGHT_GREEN if session_name == active_session else Colors.BRIGHT_WHITE

        # Get last modified time
        last_modified = ""
        if os.path.exists(session_path):
            try:
                import time
                mod_time = os.path.getmtime(session_path)
                last_modified = f" (last modified: {time.strftime('%Y-%m-%d %H:%M', time.localtime(mod_time))})"
            except:
                pass  # If we can't get modification time, just continue without it

        styled_print(f"{i:2d}. {marker} {session_name}{last_modified}", status_color, None, 0)

        if verbose:
            # Show details for each session
            details = get_session_details(session_name)
            if details:
                styled_print(f"    ID: {details['id']}", Colors.BRIGHT_CYAN, None, 0)
                styled_print(f"    Status: {details['status']}", Colors.BRIGHT_YELLOW, None, 0)
                styled_print(f"    Subtasks: {details['subtasks_count']}", Colors.BRIGHT_MAGENTA, None, 0)
                styled_print(f"    Created: {details['created_at']}", Colors.BRIGHT_GREEN, None, 0)
                if details.get('updated_at'):
                    styled_print(f"    Updated: {details['updated_at']}", Colors.BRIGHT_GREEN, None, 0)
                if details.get('active_plan_id'):
                    styled_print(f"    Active Plan: {details['active_plan_id']}", Colors.BRIGHT_WHITE, None, 0)


def handle_session_set(session_name: str, list_number: int = None, verbose: bool = False):
    """Handle setting the active session."""
    if verbose:
        print_debug(f"Setting active session: {session_name} (list number: {list_number})", 2)

    # If no session_name provided, list sessions and prompt for selection
    if not session_name and list_number is None:
        sessions = list_sessions()
        if not sessions:
            print_error("No sessions available", 2)
            return

        print_info("Available sessions:", 2)
        for i, name in enumerate(sessions, 1):
            active_marker = " (ACTIVE)" if name == get_active_session_name() else ""
            print_info(f"{i}. {name}{active_marker}", 2)

        try:
            selection = input("Enter session number or name: ").strip()
            if selection.isdigit():
                idx = int(selection) - 1
                sessions = list_sessions()  # Get again in case it changed since last call
                if 0 <= idx < len(sessions):
                    session_name = sessions[idx]
                else:
                    print_error(f"Invalid session number: {selection}", 2)
                    sys.exit(1)
            else:
                session_name = selection
        except ValueError:
            print_error("Invalid input", 2)
            sys.exit(1)
    elif list_number is not None:
        # Use list number to get session name
        sessions = list_sessions()
        if 1 <= list_number <= len(sessions):
            session_name = sessions[list_number - 1]
        else:
            print_error(f"Invalid session number: {list_number}", 2)
            sys.exit(1)
    else:
        # Handle the case where session_name is a number (user typed "1" instead of passing as list_number)
        if session_name.isdigit():
            sessions = list_sessions()
            list_num = int(session_name)
            if 1 <= list_num <= len(sessions):
                session_name = sessions[list_num - 1]
            else:
                print_error(f"Invalid session number: {session_name}", 2)
                sys.exit(1)

    if not session_name:
        print_error("Session name is required", 2)
        sys.exit(1)

    # Verify session exists
    session_path = get_session_path_by_name(session_name)
    if not os.path.exists(session_path):
        print_error(f"Session '{session_name}' does not exist", 2)
        sys.exit(1)

    # Set as active session
    if set_active_session_name(session_name):
        print_success(f"Session '{session_name}' is now active", 2)
        if verbose:
            print_debug(f"Active session configuration updated", 2)
    else:
        print_error(f"Failed to set '{session_name}' as active session", 2)
        sys.exit(1)


def handle_session_get(verbose: bool = False):
    """Handle getting the active session."""
    active_session = get_active_session_name()

    if active_session:
        active_session_path = get_session_path_by_name(active_session)

        if os.path.exists(active_session_path):
            print(active_session)
            if verbose:
                details = get_session_details(active_session)
                if details:
                    print_info(f"Active session details:", 2)
                    print_info(f"  Name: {details['name']}", 2)
                    print_info(f"  Path: {details['path']}", 2)
                    print_info(f"  ID: {details['id']}", 2)
                    print_info(f"  Status: {details['status']}", 2)
                    print_info(f"  Subtasks: {details['subtasks_count']}", 2)
                    if details.get('active_plan_id'):
                        print_info(f"  Active Plan: {details['active_plan_id']}", 2)
                    print_info(f"  Last updated: {details['updated_at']}", 2)
        else:
            print_error(f"Active session '{active_session}' points to missing file: {active_session_path}", 2)
            print_info("Please set a valid active session using 'maestro session set'", 2)
    else:
        print_info("No active session set", 2)
        if verbose:
            print_info("Use 'maestro session list' to see available sessions", 2)
            print_info("Use 'maestro session set <name>' to set an active session", 2)


def handle_session_remove(session_name: str, skip_confirmation: bool = False, verbose: bool = False):
    """Handle removing a session."""
    if verbose:
        print_debug(f"Removing session: {session_name}", 2)

    if not session_name:
        print_error("Session name is required", 2)
        sys.exit(1)

    # Verify session exists
    session_path = get_session_path_by_name(session_name)
    if not os.path.exists(session_path):
        print_error(f"Session '{session_name}' does not exist", 2)
        sys.exit(1)

    # Confirm removal unless skip_confirmation is True
    if not skip_confirmation:
        active_session = get_active_session_name()
        is_active = active_session == session_name

        if is_active:
            print_warning(f"Warning: '{session_name}' is the active session", 2)

        confirm = input(f"Are you sure you want to remove session '{session_name}'? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print_info("Session removal cancelled", 2)
            return

    # Remove the session file
    removed = remove_session(session_name)

    if removed:
        print_success(f"Removed session: {session_name}", 2)

        # If this was the active session, clear the active session and optionally set another
        active_session = get_active_session_name()
        if active_session == session_name:
            # Update user config to clear active session
            project_id = get_project_id()
            config_file = get_user_session_config_file()

            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                if project_id in config:
                    del config[project_id]['active_session']

                    # Check if there are other sessions available and ask if user wants to set one as active
                    remaining_sessions = [s for s in list_sessions() if s != session_name]
                    if remaining_sessions:
                        print_info(f"Session '{session_name}' was the active session.", 2)
                        choice = input(f"Do you want to set another session as active? Options: {', '.join(remaining_sessions)} or 'none': ").strip()
                        if choice and choice.lower() != 'none':
                            if choice in remaining_sessions:
                                if set_active_session_name(choice):
                                    print_success(f"Session '{choice}' is now active", 2)
                                else:
                                    print_warning(f"Could not set '{choice}' as active session", 2)
                            else:
                                # Treat as a number in case user entered a list number
                                try:
                                    idx = int(choice) - 1
                                    if 0 <= idx < len(remaining_sessions):
                                        new_active = remaining_sessions[idx]
                                        if set_active_session_name(new_active):
                                            print_success(f"Session '{new_active}' is now active", 2)
                                        else:
                                            print_warning(f"Could not set '{new_active}' as active session", 2)
                                    else:
                                        print_warning("Invalid session number, active session remains cleared", 2)
                                except ValueError:
                                    print_warning("Invalid session name, active session remains cleared", 2)

                    if not config[project_id]:  # Remove project entry if empty
                        del config[project_id]

                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)

                if choice.lower() != 'none' if 'choice' in locals() else True:
                    print_info("Active session cleared", 2)
    else:
        print_error(f"Failed to remove session: {session_name}", 2)
        sys.exit(1)


def handle_session_details(session_name: str, list_number: int = None, verbose: bool = False):
    """Handle showing details of a specific session."""
    if list_number is not None:
        # Use list number to get session name
        sessions = list_sessions()
        if 1 <= list_number <= len(sessions):
            session_name = sessions[list_number - 1]
        else:
            print_error(f"Invalid session number: {list_number}", 2)
            sys.exit(1)
    elif session_name and session_name.isdigit():
        # Handle the case where session_name is a number (user typed "1" instead of passing as list_number)
        sessions = list_sessions()
        list_num = int(session_name)
        if 1 <= list_num <= len(sessions):
            session_name = sessions[list_num - 1]
        else:
            print_error(f"Invalid session number: {session_name}", 2)
            sys.exit(1)

    if not session_name:
        # List available sessions and prompt for selection
        sessions = list_sessions()
        if not sessions:
            print_error("No sessions available", 2)
            return

        print_info("Available sessions:", 2)
        for i, name in enumerate(sessions, 1):
            print_info(f"{i}. {name}", 2)

        try:
            selection = input("Enter session number or name: ").strip()
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(sessions):
                    session_name = sessions[idx]
                else:
                    print_error(f"Invalid session number: {selection}", 2)
                    sys.exit(1)
            else:
                session_name = selection
        except ValueError:
            print_error("Invalid input", 2)
            sys.exit(1)

    if not session_name:
        print_error("Session name is required", 2)
        sys.exit(1)

    details = get_session_details(session_name)

    if details is None:
        print_error(f"Session '{session_name}' does not exist", 2)
        sys.exit(1)

    print_header(f"SESSION DETAILS: {session_name}")
    styled_print(f"ID: {details['id']}", Colors.BRIGHT_YELLOW, Colors.BOLD, 2)
    styled_print(f"Path: {details['path']}", Colors.BRIGHT_CYAN, None, 2)
    styled_print(f"Status: {details['status']}", Colors.BRIGHT_GREEN if details['status'] == 'done' else Colors.BRIGHT_YELLOW, None, 2)
    styled_print(f"Created: {details['created_at']}", Colors.BRIGHT_WHITE, None, 2)
    styled_print(f"Updated: {details['updated_at']}", Colors.BRIGHT_WHITE, None, 2)
    styled_print(f"Subtasks: {details['subtasks_count']}", Colors.BRIGHT_MAGENTA, None, 2)

    # Try to load the session to get more detailed information
    try:
        session = load_session(details['path'])

        # Count build targets if session file exists
        build_targets_count = 0
        try:
            build_targets = list_build_targets(details['path'])
            build_targets_count = len(build_targets) if build_targets else 0
        except:
            build_targets_count = 0  # If we can't list build targets, just show 0

        styled_print(f"Build Targets: {build_targets_count}", Colors.BRIGHT_MAGENTA, None, 2)

        # Show active plan details if available
        if details['active_plan_id']:
            styled_print(f"Active Plan: {details['active_plan_id']}", Colors.BRIGHT_WHITE, None, 2)

        # Show plan count
        plan_count = len(session.plans) if hasattr(session, 'plans') and session.plans else 0
        styled_print(f"Total Plans: {plan_count}", Colors.BRIGHT_MAGENTA, None, 2)

        # Show categories if available
        if hasattr(session, 'root_task_categories') and session.root_task_categories:
            categories_str = ', '.join(session.root_task_categories)
            styled_print(f"Categories: {categories_str}", Colors.BRIGHT_GREEN, None, 2)

    except Exception as e:
        print_warning(f"Could not load additional session details: {e}", 2)

    styled_print(f"Root Task Preview: {details['root_task']}", Colors.BRIGHT_WHITE, None, 2)


def handle_rules_file(session_path, verbose=False):
    """Handle opening the rules file in an editor."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session first
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
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
        if verbose:
            print(f"[VERBOSE] Updated session.rules_path to: {rules_filename}")
        print(f"Updated session.rules_path to: {rules_filename}")
    elif session and session.rules_path:
        rules_filename = session.rules_path
    else:
        # If no session but still need rules, use default location
        rules_filename = os.path.join(session_dir, "rules.txt")

    # Ensure the rules file exists
    if not os.path.exists(rules_filename):
        if verbose:
            print(f"[VERBOSE] Rules file does not exist. Creating: {rules_filename}")
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

    if verbose:
        print(f"[VERBOSE] Opening rules file in editor: {editor}")

    # Open the editor with the rules file
    try:
        subprocess.run([editor, rules_filename])
    except FileNotFoundError:
        print(f"Error: Editor '{editor}' not found.", file=sys.stderr)
        # Try to set the session status to failed if we can load it
        try:
            if session:
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not open editor: {str(e)}", file=sys.stderr)
        # Try to set the session status to failed if we can load it
        try:
            if session:
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
        except:
            pass
        sys.exit(1)


def handle_plan_session(session_path, verbose=False, stream_ai_output=False, print_ai_prompts=False, planner_order="codex,claude", force_replan=False, clean_task=True):
    """
    Handle planning subtasks for the session.
    LEGACY PLANNER BANNED: This function must only use JSON-based planning.
    Hard-coded plans are forbidden - only JSON-based planning is allowed.
    """
    if verbose:
        print_debug(f"Loading session from: {session_path}", 2)

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print_error(f"Session file '{session_path}' does not exist.", 2)
        # Create a failed session
        error_session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="Unknown",
            subtasks=[],
            rules_path=None,
            status="failed"
        )
        save_session(error_session, session_path)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not load session from '{session_path}': {str(e)}", 2)
        # Try to update the session status to failed if possible
        try:
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass
        sys.exit(1)

    # MIGRATION CHECK: For --plan, if there are only legacy tasks, warn and recommend re-planning
    if has_legacy_plan(session.subtasks) and len(session.subtasks) == 3:
        print_warning(f"Session contains legacy hard-coded plan with tasks: {list(LEGACY_TITLES)}", 2)
        print_warning("The legacy plan will be replaced with a new JSON-based plan.", 2)
        if verbose:
            print_debug("Legacy plan detected during planning; will replace with new JSON plan", 4)

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    # Check if we have an existing active plan and ask if user wants to branch
    if session.active_plan_id and not force_replan and session.subtasks:
        print_info(f"Active plan exists: {session.active_plan_id}", 2)
        response = input("Create a new branch from active plan? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            # Create a new plan branch from the active plan
            parent_plan_id = session.active_plan_id
            # Get the label from the active plan to use as a basis
            parent_plan_label = ""
            for plan in session.plans:
                if plan.plan_id == parent_plan_id:
                    parent_plan_label = plan.label
                    break
            new_plan_label = f"Branch from {parent_plan_label}" if parent_plan_label else f"Branch from {parent_plan_id[:8]}"
            new_plan = create_plan_branch(session, parent_plan_id, new_plan_label)
            print_info(f"Created new plan branch: {new_plan.plan_id} as active plan", 2)
            # Clear subtasks for the new plan so it can be replanned
            session.subtasks.clear()

    # FORCE REPLAN: If --force-replan is specified, clear all existing subtasks
    if force_replan:
        if verbose:
            print_debug(f"Force re-plan flag detected: clearing {len(session.subtasks)} existing subtasks", 4)
        session.subtasks.clear()  # Clear all existing subtasks
        print_warning("Cleared existing subtasks. Running fresh planning from scratch.", 2)

    # Ensure root_task is set
    if not session.root_task or session.root_task.strip() == "":
        print_error("Session root_task is not set.", 2)
        # Update session status to failed
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Check if we have refined root task data, warn if only raw task exists
    if not session.root_task_clean and session.root_task_raw:
        print_warning("Root task has not been refined yet. Planner may perform better with refined data.", 2)
        response = input("Would you like to refine the root task now? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            handle_root_refine(session_path, verbose, planner_order)
        else:
            response2 = input("Continue with raw root task? [Y/n]: ").strip().lower()
            if response2 not in ['', 'y', 'yes']:
                print_info("Aborting planning session.", 2)
                return

    # Load rules
    rules = load_rules(session)
    if verbose:
        print_debug(f"Loaded rules (length: {len(rules)} chars)", 4)

    # LEGACY PLANNER BANNED: Runtime guard to ensure no legacy planning is used
    # Ensure that we are using the JSON-based planner and not any legacy approach
    import inspect
    # Check that the plan_subtasks function does not exist (was removed in Task A)
    if hasattr(inspect.getmodule(handle_plan_session), 'plan_subtasks'):
        raise RuntimeError(
            "Legacy planner function 'plan_subtasks' detected; this is forbidden. "
            "All planning must use the JSON-based planner."
        )

    # Check if there are existing subtasks to determine the planning phase
    if not session.subtasks:
        # Initial planning phase: no existing subtasks
        if verbose:
            print_debug("Starting initial planning phase...", 2)
        print_info("Starting initial planning phase...", 2)

        # Use the new run_planner function with planner preference from CLI
        summaries = "(no summaries yet)"
        planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
        # Clean up whitespace from split
        planner_preference = [item.strip() for item in planner_preference if item.strip()]
        try:
            json_plan = run_planner(session, session_path, rules, summaries, planner_preference, verbose)
            planned_subtasks = json_to_planned_subtasks(json_plan)

            # Safety check: ensure legacy hard-coded subtasks are not present
            assert_no_legacy_subtasks(planned_subtasks)
        except KeyboardInterrupt:
            # For planner interruptions, don't modify the session at all
            print_warning("\nPlanner interrupted by user - session unchanged", 2)
            if verbose:
                print_debug("Planner interrupted, exiting cleanly", 4)
            sys.exit(130)  # Standard exit code for Ctrl+C
        except PlannerError as e:
            print_error(f"Planner failed: {e}", 2)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)
    else:
        # Refinement phase: process existing subtasks and plan new ones based on summaries
        if verbose:
            print_debug("Starting refinement planning phase using worker summaries...", 2)
        print_info("Starting refinement planning phase using worker summaries...", 2)

        # LEGACY PLANNER BANNED: Runtime guard to ensure no legacy planning is used
        # Ensure that we are using the JSON-based planner and not any legacy approach
        import inspect
        # Check that the plan_subtasks function does not exist (was removed in Task A)
        if hasattr(inspect.getmodule(handle_plan_session), 'plan_subtasks'):
            raise RuntimeError(
                "Legacy planner function 'plan_subtasks' detected; this is forbidden. "
                "All planning must use the JSON-based planner."
            )

        # Collect existing subtask summaries
        summaries = collect_worker_summaries(session, session_path)
        if verbose:
            print_debug(f"Collected summaries (length: {len(summaries)} chars)", 4)

        # Use the new run_planner function with planner preference from CLI
        planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
        # Clean up whitespace from split
        planner_preference = [item.strip() for item in planner_preference if item.strip()]
        try:
            json_plan = run_planner(session, session_path, rules, summaries, planner_preference, verbose)
            planned_subtasks = json_to_planned_subtasks(json_plan)

            # Safety check: ensure legacy hard-coded subtasks are not present
            assert_no_legacy_subtasks(planned_subtasks)
        except KeyboardInterrupt:
            # For planner interruptions, don't modify the session at all
            print_warning("\nPlanner interrupted by user - session unchanged", 2)
            if verbose:
                print_debug("Planner interrupted, exiting cleanly", 4)
            sys.exit(130)  # Standard exit code for Ctrl+C
        except PlannerError as e:
            print_error(f"Planner failed: {e}", 2)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

    # Show the plan to the user
    print_subheader("PROPOSED SUBTASK BREAKDOWN")
    for i, subtask_data in enumerate(json_plan.get("subtasks", []), 1):
        title = subtask_data.get("title", "Untitled")
        description = subtask_data.get("description", "")
        styled_print(f"{i}. {title}", Colors.BRIGHT_YELLOW, Colors.BOLD, 2)
        styled_print(f"   {description}", Colors.BRIGHT_CYAN, None, 4)

    # Ask for confirmation
    print_info("Is this subtask breakdown OK? [Y/n]: ", 2)
    response = input().strip().lower()

    if response in ['', 'y', 'yes']:
        # User accepted the plan
        if verbose:
            print("[VERBOSE] User accepted the plan")

        # Apply the JSON plan directly to the session
        apply_json_plan_to_session(session, json_plan)

        # Create a new plan branch when force-replan is used or if no plans exist yet
        if force_replan:
            parent_plan_id = session.active_plan_id
            new_plan = create_plan_branch(session, parent_plan_id, "New plan after force-replan")
            # The new plan is already set as active in create_plan_branch
        elif not session.plans:
            create_initial_plan_node(session)
        # Otherwise, update the currently active plan's subtask IDs
        else:
            # Update the active plan's subtask IDs to reflect the new subtasks
            if session.active_plan_id:
                for plan in session.plans:
                    if plan.plan_id == session.active_plan_id:
                        plan.subtask_ids = [subtask.id for subtask in session.subtasks]
                        break

        # Save the updated session
        save_session(session, session_path)
        if verbose:
            print_debug(f"Session saved with status: {session.status}")
        print_success("Plan accepted and saved to session.", 2)
    else:
        # User rejected the plan
        if verbose:
            print_debug("User rejected the plan")
        print_warning("Please explain how to improve the plan (press Enter on an empty line to finish):", 2)
        # Read multi-line feedback until user presses Enter on an empty line
        feedback_lines = []
        line = input()
        while line != "":
            feedback_lines.append(line)
            line = input()

        feedback = "\n".join(feedback_lines)

        # For now, just print that the plan was rejected
        # In a real implementation, we would store this feedback in the session
        print_warning("Plan rejected; please re-run --plan when ready", 2)


def handle_interactive_plan_session(session_path, verbose=False, stream_ai_output=False, print_ai_prompts=False, planner_order="codex,claude", force_replan=False):
    """
    Handle interactive planning mode where user and planner AI chat back-and-forth
    before finalizing the plan.
    """
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print_error(f"Session file '{session_path}' does not exist.", 2)
        error_session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="Unknown",
            subtasks=[],
            rules_path=None,
            status="failed"
        )
        save_session(error_session, session_path)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not load session from '{session_path}': {str(e)}", 2)
        try:
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass
        sys.exit(1)

    # MIGRATION CHECK: For --plan, if there are only legacy tasks, warn and recommend re-planning
    if has_legacy_plan(session.subtasks) and len(session.subtasks) == 3:
        print_warning(f"Session contains legacy hard-coded plan with tasks: {list(LEGACY_TITLES)}", 2)
        print_warning("The legacy plan will be replaced with a new JSON-based plan.", 2)
        if verbose:
            print_debug("Legacy plan detected during planning; will replace with new JSON plan", 4)

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    # Check if we have an existing active plan and ask if user wants to branch
    if session.active_plan_id and not force_replan and session.subtasks:
        print_info(f"Active plan exists: {session.active_plan_id}", 2)
        response = input("Create a new branch from active plan? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            # Create a new plan branch from the active plan
            parent_plan_id = session.active_plan_id
            # Get the label from the active plan to use as a basis
            parent_plan_label = ""
            for plan in session.plans:
                if plan.plan_id == parent_plan_id:
                    parent_plan_label = plan.label
                    break
            new_plan_label = f"Branch from {parent_plan_label}" if parent_plan_label else f"Branch from {parent_plan_id[:8]}"
            new_plan = create_plan_branch(session, parent_plan_id, new_plan_label)
            print_info(f"Created new plan branch: {new_plan.plan_id} as active plan", 2)
            # Clear subtasks for the new plan so it can be replanned
            session.subtasks.clear()

    # FORCE REPLAN: If --force-replan is specified, clear all existing subtasks
    if force_replan:
        if verbose:
            print_debug(f"Force re-plan flag detected: clearing {len(session.subtasks)} existing subtasks", 4)
        session.subtasks.clear()  # Clear all existing subtasks
        print_warning("Cleared existing subtasks. Running fresh planning from scratch.", 2)

    # Ensure root_task is set
    if not session.root_task or session.root_task.strip() == "":
        print_error("Session root_task is not set.", 2)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Check if we have refined root task data, warn if only raw task exists
    if not session.root_task_clean and session.root_task_raw:
        print_warning("Root task has not been refined yet. Planner may perform better with refined data.", 2)
        response = input("Would you like to refine the root task now? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            handle_root_refine(session_path, verbose, planner_order)
        else:
            response2 = input("Continue with raw root task? [Y/n]: ").strip().lower()
            if response2 not in ['', 'y', 'yes']:
                print_info("Aborting planning session.", 2)
                return

    # Load rules
    rules = load_rules(session)
    if verbose:
        print(f"[VERBOSE] Loaded rules (length: {len(rules)} chars)")

    # Initialize conversation
    planner_conversation = [
        {"role": "system", "content": f"You are a planning AI. The user will discuss the plan with you and then finalize it. The main goal is: {session.root_task}"},
        {"role": "user", "content": f"Root task: {session.root_task}\n\nRules: {rules}\n\nCurrent plan: {len(session.subtasks)} existing subtasks"}
    ]

    print_header("PLANNING DISCUSSION MODE")
    print_info("Ready to discuss the plan for this session.", 4)
    print_info("Type your message and press Enter. Use /done when you want to generate the plan.", 4)

    # Create conversations directory
    maestro_dir = get_maestro_dir(session_path)
    conversations_dir = os.path.join(maestro_dir, "conversations")
    os.makedirs(conversations_dir, exist_ok=True)

    while True:
        # Get user input with support for multi-line (for later enhancement)
        user_input = get_multiline_input("> ")

        if user_input == "/done" or user_input == "/plan":
            break

        if user_input == "/quit" or user_input == "/exit":
            print_warning("Exiting without generating plan.", 2)
            return

        # Append user message to conversation
        planner_conversation.append({"role": "user", "content": user_input})

        # Call the planner engine with the conversation
        planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
        planner_preference = [item.strip() for item in planner_preference if item.strip()]

        try:
            # Build a prompt from the conversation
            conversation_prompt = "You are in a planning conversation. Here's the conversation so far:\n\n"
            for msg in planner_conversation:
                conversation_prompt += f"{msg['role'].upper()}: {msg['content']}\n\n"

            conversation_prompt += "\nPlease respond to continue the planning discussion."

            # During discussion mode, we expect natural language responses, not JSON
            # Use engine.generate directly instead of run_planner_with_prompt to avoid JSON parsing
            from .engines import get_engine

            # Try each planner in preference order
            assistant_response = None
            last_error = None
            for engine_name in planner_preference:
                try:
                    engine = get_engine(engine_name + "_planner")
                    assistant_response = engine.generate(conversation_prompt)

                    # If we get a response, break out of the loop
                    if assistant_response:
                        break
                except Exception as e:
                    last_error = e
                    print(f"Warning: Engine {engine_name} failed: {e}", file=sys.stderr)
                    continue

            if assistant_response is None:
                raise Exception(f"All planners failed: {last_error}")

            # Print the natural language response from the AI
            print_ai_response(assistant_response)

            # Append assistant's response to conversation
            planner_conversation.append({"role": "assistant", "content": assistant_response})

        except KeyboardInterrupt:
            print("\n[orchestrator] Conversation interrupted by user", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            print(f"Error in conversation: {e}", file=sys.stderr)
            continue

    # Final: Generate the actual plan with forced JSON output
    final_conversation_prompt = "The planning conversation is complete. Please generate the final JSON plan based on the discussion:\n\n"
    for msg in planner_conversation:
        final_conversation_prompt += f"{msg['role'].upper()}: {msg['content']}\n\n"

    final_conversation_prompt += """Return ONLY the JSON plan with 'subtasks' array and 'root' object with 'clean_text', 'raw_summary', and 'categories', and no other text.

Expected format:
{
  "subtasks": [
    {
      "title": "Descriptive title for the subtask",
      "description": "Detailed description of what needs to be done",
      "categories": ["category1", "category2"],
      "root_excerpt": "Relevant excerpt from root task"
    }
  ],
  "root": {
    "version": 1,
    "clean_text": "...",
    "raw_summary": "...",
    "categories": ["..."]
  }
}

Make sure each subtask has a 'title' and 'description' field."""

    planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
    planner_preference = [item.strip() for item in planner_preference if item.strip()]

    try:
        final_json_plan = run_planner_with_prompt(final_conversation_prompt, planner_preference, session_path, verbose=True)

        # Verify that final_json_plan is a dictionary
        if not isinstance(final_json_plan, dict):
            raise PlannerError(f"Planner returned invalid data type: {type(final_json_plan)}")

        # Show the plan to the user
        print_header("FINAL PLAN GENERATED")
        if "subtasks" in final_json_plan:
            subtasks = final_json_plan["subtasks"]
            # Ensure subtasks is a list
            if not isinstance(subtasks, list):
                raise PlannerError(f"Planner returned invalid subtasks format: expected list, got {type(subtasks)}")

            for i, subtask_data in enumerate(subtasks, 1):
                # Ensure each subtask is a dictionary
                if not isinstance(subtask_data, dict):
                    raise PlannerError(f"Planner returned invalid subtask format: expected dict, got {type(subtask_data)}")

                title = subtask_data.get("title", "Untitled")
                description = subtask_data.get("description", "")

                # If title is still "Untitled", try other common fields
                if title == "Untitled":
                    # Check for other common field names that might contain the title
                    for field_name in ["name", "task", "subtask", "id", "identifier"]:
                        if field_name in subtask_data:
                            title = str(subtask_data[field_name])
                            break
                    else:
                        # If no title found, show the raw subtask data for debugging
                        print_warning(f"Subtask {i} missing 'title' field. Raw data: {str(subtask_data)[:200]}...", 2)
                        title = f"Untitled Subtask {i}"

                styled_print(f"{i}. {title}", Colors.BRIGHT_YELLOW, Colors.BOLD, 2)
                styled_print(f"   {description}", Colors.BRIGHT_CYAN, None, 4)
        else:
            print_warning("No 'subtasks' field found in final plan. Raw plan: ", 2)
            styled_print(str(final_json_plan)[:500], Colors.RED, None, 4)

        # Save the conversation transcript
        plan_id = str(uuid.uuid4())
        conversation_filename = os.path.join(conversations_dir, f"planner_conversation_{plan_id}.txt")
        with open(conversation_filename, "w", encoding="utf-8") as f:
            f.write(f"Planning conversation for plan {plan_id}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n\n")
            for msg in planner_conversation:
                f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")

        print_success(f"Conversation saved to: {conversation_filename}", 2)

        # Create a new plan branch for this interactive planning session
        parent_plan_id = session.active_plan_id
        new_plan = create_plan_branch(session, parent_plan_id, "Interactive planning session")

        # Apply the plan to the session (this will set the plan_id for subtasks)
        # Since we just created the new plan and set it as active, the subtasks will be assigned to it
        apply_json_plan_to_session(session, final_json_plan)

        # Update the new plan's subtask IDs
        for plan in session.plans:
            if plan.plan_id == new_plan.plan_id:
                plan.subtask_ids = [subtask.id for subtask in session.subtasks]
                break

        # The new plan is already the active plan from create_plan_branch, so we're done

        save_session(session, session_path)

        print_success("Plan accepted and saved to session.", 2)

    except Exception as e:
        print_error(f"Error generating final plan: {e}", 2)
        sys.exit(1)


def handle_root_refine(session_path, verbose=False, planner_order="codex,claude"):
    """Refine the root task using the planner engine."""
    handle_refine_root(session_path, verbose, planner_order)


def handle_root_discuss(session_path, verbose=False, stream_ai_output=False, print_ai_prompts=False, planner_order="codex,claude"):
    """Interactive conversation about the root task."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print_error(f"Session file '{session_path}' does not exist.", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not load session from '{session_path}': {str(e)}", 2)
        sys.exit(1)

    # Initialize conversation with the current root task
    maestro_dir = get_maestro_dir(session_path)
    conversations_dir = os.path.join(maestro_dir, "conversations")
    os.makedirs(conversations_dir, exist_ok=True)

    # Create initial conversation
    root_task_text = session.root_task_raw if session.root_task_raw else session.root_task
    conversation = [
        {"role": "system", "content": f"You are helping refine and discuss the root task: {root_task_text}"},
        {"role": "assistant", "content": f"Let's discuss your root task: {root_task_text}. How can I help you refine or improve it?"}
    ]

    print_header("ROOT TASK DISCUSSION MODE")
    print_info("Ready to discuss the root task. Type '/done' to finalize, '/abort' to discard changes.", 4)

    # Print initial message from AI
    print(f"\n[AI]: {conversation[-1]['content']}")

    try:
        while True:
            # Get user input
            user_input = input("\n[USER]: ").strip()

            # Check for exit conditions
            if user_input.lower() == '/done':
                print_info("Finalizing root task discussion...", 2)
                break
            elif user_input.lower() == '/abort':
                print_info("Aborting conversation, changes will be discarded.", 2)
                return

            # Add user message to conversation
            conversation.append({"role": "user", "content": user_input})

            # Build a prompt from the conversation
            conversation_prompt = "You are in a discussion about the root task. Here's the conversation so far:\n\n"
            for msg in conversation:
                conversation_prompt += f"{msg['role'].upper()}: {msg['content']}\n\n"
            conversation_prompt += "\nPlease respond to continue the discussion."

            # Print prompt if requested
            if print_ai_prompts:
                print_debug(f"Prompt to AI:\n{conversation_prompt}", 2)

            # Call the engine to get AI response
            planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
            planner_preference = [item.strip() for item in planner_preference if item.strip()]

            # Find the first available engine
            engine = None
            for model_name in planner_preference:
                try:
                    from .engines import get_engine
                    engine = get_engine(model_name + "_planner", debug=verbose, stream_output=stream_ai_output)
                    break
                except Exception as e:
                    if verbose:
                        print_debug(f"Failed to get engine {model_name}_planner: {e}", 2)
                    continue

            if not engine:
                print_error("No available AI engine found", 2)
                sys.exit(1)

            # Get AI response
            assistant_response = engine.generate(conversation_prompt)

            # Print AI response if streaming
            if stream_ai_output:
                print(f"\n[AI]: {assistant_response}")
            else:
                print(f"\n[AI]: {assistant_response}")

            # Add AI response to conversation
            conversation.append({"role": "assistant", "content": assistant_response})

    except KeyboardInterrupt:
        print("\n[orchestrator] Conversation interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error in conversation: {e}", file=sys.stderr)
        sys.exit(1)

    # At this point, the conversation is complete
    # Ask the AI to generate final JSON with refined root, summary, and categories
    final_prompt = f"Based on our conversation about the root task, please return ONLY valid JSON with the following fields:\n"
    final_prompt += f"{{\n"
    final_prompt += f'  "version": 1,\n'
    final_prompt += f'  "clean_text": "refined version of the root task",\n'
    final_prompt += f'  "raw_summary": "1-3 sentences summarizing the intent",\n'
    final_prompt += f'  "categories": ["list", "of", "relevant", "categories"]\n'
    final_prompt += f"}}\n\n"
    final_prompt += f"Conversation transcript:\n"
    for msg in conversation:
        final_prompt += f"{msg['role'].upper()}: {msg['content']}\n"

    # Get AI to format the final result as JSON
    try:
        # Find the first available engine
        engine = None
        for model_name in planner_preference:
            try:
                from .engines import get_engine
                engine = get_engine(model_name + "_planner", debug=verbose, stream_output=False)
                break
            except Exception as e:
                if verbose:
                    print_debug(f"Failed to get engine {model_name}_planner: {e}", 2)
                continue

        if not engine:
            print_error("No available AI engine found for finalizing", 2)
            sys.exit(1)

        final_json_response = engine.generate(final_prompt)

        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', final_json_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            import json as json_module
            try:
                final_result = json_module.loads(json_str)

                # Update session with the refined fields
                session.root_task_clean = final_result.get("clean_text", session.root_task_clean)
                session.root_task_summary = final_result.get("raw_summary", session.root_task_summary)
                session.root_task_categories = final_result.get("categories", session.root_task_categories)

                # Update the session with conversation history
                timestamp = datetime.now().isoformat()
                history_entry = {
                    "type": "discussion",
                    "timestamp": timestamp,
                    "initial_raw": session.root_task_raw if session.root_task_raw else session.root_task,
                    "final_clean": session.root_task_clean,
                    "final_summary": session.root_task_summary,
                    "final_categories": session.root_task_categories,
                    "conversation": conversation
                }
                session.root_history.append(history_entry)

                # Save the updated session
                save_session(session, session_path)

                print_success("Root task discussion finalized successfully", 2)
                print_info(f"Cleaned text: {session.root_task_clean[:100]}..." if session.root_task_clean and len(session.root_task_clean) > 100 else f"Cleaned text: {session.root_task_clean}", 2)
                print_info(f"Categories: {session.root_task_categories}", 2)

            except json_module.JSONDecodeError:
                print_error("Could not parse JSON from AI response", 2)
                print_info(f"Raw AI response: {final_json_response}", 2)
        else:
            print_error("Could not extract JSON from AI response", 2)
            print_info(f"Raw AI response: {final_json_response}", 2)

    except Exception as e:
        print_error(f"Error finalizing root task discussion: {e}", 2)
        # Still save the conversation even if finalization fails
        print_info("Conversation was saved but root task was not updated", 2)

    # Save the conversation as a separate file
    conversation_filename = os.path.join(conversations_dir, f"root_discussion_{int(time.time())}.txt")
    with open(conversation_filename, "w", encoding="utf-8") as f:
        f.write(f"Root task discussion conversation\n\n")
        for i, msg in enumerate(conversation):
            f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")

    print_success(f"Conversation saved to: {conversation_filename}", 2)


def handle_root_show(session_path, verbose=False):
    """Show all root fields (raw, clean, categories, summary)."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print_error(f"Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    print_header("ROOT TASK DETAILS")
    print(f"Raw: {session.root_task_raw if session.root_task_raw else (session.root_task if session.root_task else '(empty)')}")
    print(f"Clean: {session.root_task_clean if session.root_task_clean else '(not refined yet)'}")
    print(f"Summary: {session.root_task_summary if session.root_task_summary else '(not refined yet)'}")
    print(f"Categories: {session.root_task_categories if session.root_task_categories else ['(not refined yet)']}")
    print(f"History entries: {len(session.root_history) if hasattr(session, 'root_history') else 0}")


def handle_root_set(session_path, text=None, verbose=False):
    """Set the raw root task in the session."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        error_session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="",
            subtasks=[],
            rules_path=None,
            status="failed"
        )
        save_session(error_session, session_path)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        try:
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass
        sys.exit(1)

    # Get the root task text
    if text is not None:
        root_task_text = text
    else:
        # Read from stdin
        print_info("Enter the root task (press Ctrl+D or Ctrl+Z on a new line when done):", 2)
        root_task_text = sys.stdin.read()

    # Set the root task in the session
    session.root_task = root_task_text.strip()
    session.root_task_raw = root_task_text.strip()  # Also set raw for consistency
    # Clear the refined fields since we now have a new raw input
    session.root_task_clean = None
    session.root_task_summary = None
    session.root_task_categories = []
    session.updated_at = datetime.now().isoformat()

    # Save the updated session
    save_session(session, session_path)

    print_success(f"Root task set successfully (length: {len(root_task_text)} characters), refined fields cleared")


def handle_root_get(session_path, clean=False, verbose=False):
    """Print the raw root task or clean version if --clean is specified."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Print the requested field
    if clean and session.root_task_clean:
        print(session.root_task_clean)
    else:
        print(session.root_task_raw if session.root_task_raw else session.root_task)


def handle_resume_session(session_path, verbose=False, dry_run=False, stream_ai_output=False, print_ai_prompts=False, retry_interrupted=False):
    """Handle resuming an existing session."""
    if verbose and dry_run:
        print(f"[VERBOSE] DRY RUN MODE: Loading session from: {session_path}")
    elif verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Attempt to load the session, which will handle file not found and JSON errors
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        # Set status to failed if the session file doesn't exist but we tried to resume
        error_session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="Unknown",
            subtasks=[],
            rules_path=None,
            status="failed"
        )
        save_session(error_session, session_path)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        # Update session status to failed if we can load it
        try:
            session = load_session(session_path)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass  # If we can't even load to set failed status, we just exit
        sys.exit(1)

    # MIGRATION CHECK: Detect legacy hard-coded 3-task plan and handle appropriately
    if has_legacy_plan(session.subtasks):
        print(f"Warning: Session contains legacy hard-coded plan with tasks: {list(LEGACY_TITLES)}", file=sys.stderr)
        print("This legacy plan is no longer supported.", file=sys.stderr)
        print("Please re-plan the session using '--plan' before resuming.", file=sys.stderr)
        if verbose:
            print("[VERBOSE] Legacy plan migration: refusing to resume with legacy tasks")
        sys.exit(1)

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    if verbose:
        print(f"[VERBOSE] Loaded session with status: {session.status}")

    # Load rules
    rules = load_rules(session)
    if verbose:
        print(f"[VERBOSE] Loaded rules (length: {len(rules)} chars)")

    # Process pending subtasks (and interrupted subtasks if retry_interrupted is True)
    # Only include subtasks that belong to the active plan (if plan tree exists)
    active_plan_id = session.active_plan_id

    # Check if active plan is dead before proceeding
    if active_plan_id:
        active_plan = None
        for plan in session.plans:
            if plan.plan_id == active_plan_id:
                active_plan = plan
                break

        if active_plan and active_plan.status == "dead":
            print_error(f"Cannot resume: Active plan '{active_plan_id}' is marked as dead.", 2)
            print_info("Use 'maestro plan list' to see available plans, or 'maestro plan set <plan_id>' to switch to an active plan.", 2)
            sys.exit(1)

    if retry_interrupted:
        target_subtasks = [
            subtask for subtask in session.subtasks
            if subtask.status in ["pending", "interrupted"]
            and (not active_plan_id or subtask.plan_id == active_plan_id)
        ]
        if verbose and target_subtasks:
            interrupt_count = len([s for s in target_subtasks if s.status == "interrupted"])
            pending_count = len([s for s in target_subtasks if s.status == "pending"])
            print(f"[VERBOSE] Processing {len(target_subtasks)} subtasks: {pending_count} pending, {interrupt_count} interrupted")
    else:
        target_subtasks = [
            subtask for subtask in session.subtasks
            if subtask.status == "pending"
            and (not active_plan_id or subtask.plan_id == active_plan_id)
        ]

    if not target_subtasks:
        # No subtasks to process, just print current status
        if verbose:
            print("[VERBOSE] No subtasks to process")
        print(f"Status: {session.status}")
        print(f"Number of subtasks: {len(session.subtasks)}")
        all_done = all(subtask.status == "done" for subtask in session.subtasks)
        if all_done and session.subtasks:
            session.status = "done"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            print("Session status updated to 'done'")
        return

    # Create inputs and outputs directories for the session
    maestro_dir = get_maestro_dir(session_path)
    inputs_dir = os.path.join(maestro_dir, "inputs")
    outputs_dir = os.path.join(maestro_dir, "outputs")
    os.makedirs(inputs_dir, exist_ok=True)
    if not dry_run:
        os.makedirs(outputs_dir, exist_ok=True)
        # Also create partials directory in the maestro directory
        partials_dir = os.path.join(maestro_dir, "partials")
        os.makedirs(partials_dir, exist_ok=True)

    # Process each target subtask in order
    for subtask in target_subtasks:
        # Check if this subtask should be processed (status is pending or interrupted)
        if subtask.status in ["pending", "interrupted"]:
            if verbose:
                print(f"[VERBOSE] Processing subtask: '{subtask.title}' (ID: {subtask.id})")

            # Set the summary file path if not already set
            if not subtask.summary_file:
                subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

            # Check if there's partial output from a previous interrupted run
            partial_dir = os.path.join(maestro_dir, "partials")
            partial_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.txt")
            partial_output = None
            if os.path.exists(partial_filename):
                try:
                    with open(partial_filename, 'r', encoding='utf-8') as f:
                        partial_output = f.read()
                except:
                    partial_output = None

            # Build the full worker prompt with structured format using flexible root task handling
            # Use the clean root task and relevant categories/excerpt for this subtask
            root_task_to_use = session.root_task_clean or session.root_task_raw or session.root_task
            categories_str = ", ".join(subtask.categories) if subtask.categories else "No specific categories"
            root_excerpt = subtask.root_excerpt if subtask.root_excerpt else "No specific excerpt, see categories."

            # Build structured prompt
            goal_parts = [f"Complete the subtask: {subtask.title}", f"Description: {subtask.description}"]
            if partial_output:
                goal_parts.append("Continue work from a previous partial attempt")
            goal = "\n".join(goal_parts)

            # Prepare context for the worker prompt
            context_parts = [f"ROOT TASK (CLEANED):\n{root_task_to_use}"]
            context_parts.append(f"RELEVANT CATEGORIES:\n{categories_str}")
            context_parts.append(f"RELEVANT ROOT EXCERPT:\n{root_excerpt}")
            if partial_output:
                context_parts.append(f"PARTIAL RESULT FROM PREVIOUS ATTEMPT:\n{partial_output}")
            context = "\n\n".join(context_parts)

            requirements_parts = [f"SUBTASK DETAILS:\nid: {subtask.id}\ntitle: {subtask.title}\ndescription:\n{subtask.description}"]
            requirements_parts.append(f"CURRENT RULES:\n{rules}")
            if partial_output:
                requirements_parts.append(f"You must continue the work from the partial output above.\nDo not repeat already completed steps.")
            requirements_parts.append(f"You are an autonomous coding agent working in this repository.")
            requirements_parts.append(f"Perform ONLY the work needed for this subtask.")
            requirements_parts.append(f"Use your normal tools and workflows.")
            requirements = "\n\n".join(requirements_parts)

            acceptance_criteria = "The work should be completed according to the subtask requirements. The work should be properly integrated with existing codebase. If continuing from partial work, build upon what was already done without repeating completed steps. When done, write a short summary to the specified file."

            deliverables = f"Completed work for subtask '{subtask.title}'\nWrite a summary to file: {subtask.summary_file}"

            # Build the structured prompt using the new centralized function
            prompt = build_prompt(goal, context, requirements, acceptance_criteria, deliverables)

            # Add engine role declaration
            prompt += f"[ENGINE ROLE]\nWorker engine: {subtask.worker_model}_worker\nPurpose: Execute the specified subtask and generate appropriate work output\n\n"

            if verbose:
                print(f"[VERBOSE] Using worker model: {subtask.worker_model}")

            # Look up the worker engine
            from .engines import get_engine
            try:
                engine = get_engine(subtask.worker_model + "_worker", debug=verbose, stream_output=stream_ai_output)
            except ValueError:
                # If we don't have the specific model with "_worker" suffix, try directly
                try:
                    engine = get_engine(subtask.worker_model, debug=verbose, stream_output=stream_ai_output)
                except ValueError:
                    print(f"Error: Unknown worker model '{subtask.worker_model}'", file=sys.stderr)
                    session.status = "failed"
                    session.updated_at = datetime.now().isoformat()
                    save_session(session, session_path)
                    sys.exit(1)

            if verbose:
                print(f"[VERBOSE] Generated prompt for engine (length: {len(prompt)} chars)")

            # Save the worker prompt for traceability
            prompt_file_path = save_prompt_for_traceability(prompt, session_path, "worker", f"{subtask.worker_model}_worker")
            if verbose:
                print(f"[VERBOSE] Worker prompt saved to: {prompt_file_path}")

            # Print AI prompt if requested
            if print_ai_prompts:
                print("===== AI PROMPT BEGIN =====")
                print(prompt)
                print("===== AI PROMPT END =====")

            # Log verbose information
            log_verbose(verbose, f"Engine={subtask.worker_model} subtask={subtask.id}")
            log_verbose(verbose, f"Prompt file: {prompt_file_path}")
            log_verbose(verbose, f"Output file: {os.path.join(outputs_dir, f'{subtask.id}.txt')}")

            # Call engine.generate(prompt) with interruption handling
            try:
                output = engine.generate(prompt)
            except KeyboardInterrupt:
                # Handle user interruption
                print(f"\n[orchestrator] Interrupt received — stopping after current AI step...", file=sys.stderr)
                subtask.status = "interrupted"
                session.status = "interrupted"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)

                # Save AI output and partial result for traceability
                output_file_path = save_ai_output(output if output else "", session_path, "worker", f"{subtask.worker_model}_worker")
                if verbose:
                    print(f"[VERBOSE] Partial worker output saved to: {output_file_path}")

                # Save partial output if available
                partial_dir = os.path.join(maestro_dir, "partials")
                os.makedirs(partial_dir, exist_ok=True)
                partial_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.txt")

                with open(partial_filename, 'w', encoding='utf-8') as f:
                    f.write(output if output else "")

                # Also create an empty summary file to prevent error on resume
                # This ensures that when the task is resumed, the expected summary file exists
                if subtask.summary_file and not os.path.exists(subtask.summary_file):
                    os.makedirs(os.path.dirname(subtask.summary_file), exist_ok=True)
                    with open(subtask.summary_file, 'w', encoding='utf-8') as f:
                        f.write("")  # Create empty summary file

                if verbose:
                    print(f"[VERBOSE] Partial stdout saved to: {partial_filename}")
                    print(f"[VERBOSE] Subtask {subtask.id} marked as interrupted")

                # Exit with clean code for interruption
                sys.exit(130)
            except EngineError as e:
                # Log stderr for engine errors
                print(f"Engine error stderr: {e.stderr}", file=sys.stderr)

                # Save the engine error output for traceability
                output_file_path = save_ai_output(f"Engine error: {e.stderr}", session_path, "worker_error", f"{subtask.worker_model}_worker")
                if verbose:
                    print(f"[VERBOSE] Worker error output saved to: {output_file_path}")

                print(f"Error: Engine failed with exit code {e.exit_code}: {e.name}", file=sys.stderr)
                subtask.status = "error"
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
                sys.exit(1)
            except Exception as e:
                # Save any exception output for traceability
                output_file_path = save_ai_output(f"Exception: {str(e)}", session_path, "worker_exception", f"{subtask.worker_model}_worker")
                if verbose:
                    print(f"[VERBOSE] Worker exception output saved to: {output_file_path}")

                print(f"Error: Failed to generate output from engine: {str(e)}", file=sys.stderr)
                subtask.status = "error"
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
                sys.exit(1)

            if verbose:
                print(f"[VERBOSE] Generated output from engine (length: {len(output)} chars)")

            # Save the raw stdout to a file
            stdout_filename = os.path.join(outputs_dir, f"worker_{subtask.id}.stdout.txt")
            if not dry_run:
                with open(stdout_filename, 'w', encoding='utf-8') as f:
                    f.write(output)

                if verbose:
                    print(f"[VERBOSE] Saved raw stdout to: {stdout_filename}")

            # Verify summary file exists and is non-empty
            if not dry_run:
                if not os.path.exists(subtask.summary_file):
                    print(f"Error: Summary file missing for subtask {subtask.id}: {subtask.summary_file}", file=sys.stderr)
                    subtask.status = "error"
                    session.status = "failed"
                    session.updated_at = datetime.now().isoformat()
                    save_session(session, session_path)
                    sys.exit(1)

                size = os.path.getsize(subtask.summary_file)
                if size == 0:
                    print(f"Error: Summary file empty for subtask {subtask.id}: {subtask.summary_file}", file=sys.stderr)
                    subtask.status = "error"
                    session.status = "failed"
                    session.updated_at = datetime.now().isoformat()
                    save_session(session, session_path)
                    sys.exit(1)

            if not dry_run:
                output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(output)

                if verbose:
                    print(f"[VERBOSE] Saved output to: {output_file_path}")
            else:
                output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
                if verbose:
                    print(f"[VERBOSE] DRY RUN: Would save output to: {output_file_path}")

            # Mark subtask.status as "done" and update updated_at
            if not dry_run:
                subtask.status = "done"
                session.updated_at = datetime.now().isoformat()

                if verbose:
                    print(f"[VERBOSE] Updated subtask status to 'done'")
            else:
                if verbose:
                    print(f"[VERBOSE] DRY RUN: Would update subtask status to 'done'")

    # Update session status based on subtask completion
    if not dry_run:
        all_done = all(subtask.status == "done" for subtask in session.subtasks)
        if all_done and session.subtasks:
            session.status = "done"
        else:
            session.status = "in_progress"

        # Save the updated session
        save_session(session, session_path)

        if verbose:
            print(f"[VERBOSE] Saved session with new status: {session.status}")

    # Count how many subtasks are done or would be done
    if dry_run:
        done_count = len([s for s in session.subtasks if s.status == "done"])  # Already done
        pending_count = len([s for s in session.subtasks if s.status == "pending"])  # Would be processed
        print(f"Processed {done_count} subtasks (DRY RUN: would process {pending_count} more)")
    else:
        print(f"Processed {len([s for s in session.subtasks if s.status == 'done'])} subtasks")

    if not dry_run:
        print(f"New session status: {session.status}")
    else:
        # In dry-run, we calculate what status would be if all pending tasks were completed
        all_would_be_done = all(subtask.status == "done" or subtask.status == "pending" for subtask in session.subtasks)
        would_status = "done" if all_would_be_done else "in_progress"
        print(f"DRY RUN: Would update session status to: {would_status}")


def handle_task_list(session_path, verbose=False):
    """List tasks in the current session."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Get the active plan or use the first plan if no active plan is set
    if session.active_plan_id:
        active_plan = next((p for p in session.plans if p.plan_id == session.active_plan_id), None)
    else:
        # If no active plan, use the first plan or show all tasks
        active_plan = session.plans[0] if session.plans else None

    print_header("TASKS")

    # Determine which subtasks to show
    subtasks_to_show = []

    if active_plan:
        # Show tasks from the active plan
        for subtask_id in active_plan.subtask_ids:
            subtask = next((st for st in session.subtasks if st.id == subtask_id), None)
            if subtask:
                subtasks_to_show.append(subtask)
    else:
        # If no plan is active, show all subtasks
        subtasks_to_show = session.subtasks

    if not subtasks_to_show:
        print("No tasks in current plan.")
        return

    # Show tasks with status indicators (enhanced visibility)
    for i, subtask in enumerate(subtasks_to_show, 1):
        # Show more comprehensive status
        status_symbol = "✓" if subtask.status == "done" else "○" if subtask.status == "pending" else "⚠" if subtask.status == "interrupted" else "✗"
        status_color = Colors.BRIGHT_GREEN if subtask.status == "done" else Colors.BRIGHT_YELLOW if subtask.status == "pending" else Colors.BRIGHT_MAGENTA if subtask.status == "interrupted" else Colors.BRIGHT_RED

        # Format the display with task id, title, status, and engine
        task_info = f"{i:2d}. {status_symbol} {subtask.id}: {subtask.title} [{subtask.status}]"
        if subtask.worker_model:  # Show engine if available
            task_info += f" | Engine: {subtask.worker_model}"

        styled_print(task_info, status_color, None, 0)

        # Show last summary indicator if available
        if subtask.summary_file and os.path.exists(subtask.summary_file):
            try:
                with open(subtask.summary_file, 'r', encoding='utf-8') as f:
                    summary_content = f.read().strip()
                    if summary_content:
                        # Show first line or first 60 characters of summary
                        first_line = summary_content.split('\n')[0]
                        short_summary = first_line[:60] + "..." if len(first_line) > 60 else first_line
                        styled_print(f"    Summary: {short_summary}", Colors.BRIGHT_WHITE, None, 0)
            except:
                pass  # If summary file can't be read, just continue

        if verbose or subtask.status != "done":
            # In verbose mode or for non-completed tasks, also show additional information
            styled_print(f"    Description: {subtask.description[:120]}{'...' if len(subtask.description) > 120 else ''}", Colors.BRIGHT_WHITE, None, 0)
            if subtask.categories:
                styled_print(f"    Categories: {', '.join(subtask.categories)}", Colors.BRIGHT_CYAN, None, 0)
            if subtask.root_excerpt:
                styled_print(f"    Excerpt: {subtask.root_excerpt[:100]}{'...' if len(subtask.root_excerpt) > 100 else ''}", Colors.BRIGHT_MAGENTA, None, 0)

            # Show plan ID as well
            if subtask.plan_id:
                styled_print(f"    Plan: {subtask.plan_id}", Colors.BRIGHT_BLUE, None, 0)

    # If in verbose mode, also show rule-based information
    if verbose:
        # Load rules to identify recurring tasks
        rules = load_rules(session)
        if rules:
            print_subheader("RULES-GENERATED TASKS")
            # Parse rules to identify potential recurring tasks
            # This would typically be handled by the AI, but we can show common patterns
            import json
            try:
                # Try to parse rules as JSON if it's structured that way
                rules_json = json.loads(rules)
                if isinstance(rules_json, dict) and "rules" in rules_json:
                    for i, rule in enumerate(rules_json.get("rules", []), 1):
                        if isinstance(rule, dict) and rule.get("enabled", True):
                            styled_print(f"  {i}. {rule.get('content', 'N/A')} [Rule-based task]", Colors.BRIGHT_CYAN, None, 0)
            except json.JSONDecodeError:
                # If not JSON, parse as text rules
                rule_lines = [line.strip() for line in rules.split('\n') if line.strip() and not line.strip().startswith('#')]
                for i, rule_line in enumerate(rule_lines, 1):
                    styled_print(f"  {i}. {rule_line} [Rule-based task]", Colors.BRIGHT_CYAN, None, 0)


def handle_task_run(session_path, num_tasks=None, verbose=False, quiet=False, retry_interrupted=False,
                   stream_ai_output=False, print_ai_prompts=False):
    """Run tasks (similar to resume, but with optional limit on number of tasks)."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Load rules
    rules = load_rules(session)
    if verbose:
        print_info(f"Loaded rules (length: {len(rules)} chars)", 2)

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    # Determine active plan and get tasks to run
    active_plan_id = session.active_plan_id
    active_plan = None
    if active_plan_id:
        for plan in session.plans:
            if plan.plan_id == active_plan_id:
                active_plan = plan
                break

    # If no active plan exists, abort with guidance
    if not active_plan:
        print_error("Cannot execute tasks: No active plan exists.", 2)
        print_info("Use 'maestro plan discuss' to create or select an active plan.", 2)
        sys.exit(1)

    # Validate that the active plan is not dead
    if active_plan and active_plan.status == "dead":
        print_error(f"Cannot execute tasks: Active plan '{active_plan_id}' is marked as dead.", 2)
        print_info("Use 'maestro plan list' to see available plans, or 'maestro plan set <plan_id>' to switch to an active plan.", 2)
        sys.exit(1)

    # Determine eligible subtasks from the active plan only
    pending_subtasks = [
        subtask for subtask in session.subtasks
        if subtask.status == "pending" and subtask.plan_id == active_plan_id
    ]

    interrupted_subtasks = []
    if retry_interrupted:
        interrupted_subtasks = [
            subtask for subtask in session.subtasks
            if subtask.status == "interrupted" and subtask.plan_id == active_plan_id
        ]

    # Combine eligible subtasks: first pending, then interrupted (if retrying)
    eligible_subtasks = pending_subtasks + interrupted_subtasks

    # Count total eligible tasks for verbose output
    total_pending = len(pending_subtasks)
    total_interrupted = len(interrupted_subtasks)
    total_eligible = len(eligible_subtasks)

    if verbose:
        print_info(f"Eligible subtasks: {total_eligible} (pending={total_pending}, interrupted={total_interrupted})", 2)

    # Apply execution limit if specified
    if num_tasks is not None and num_tasks > 0:
        target_subtasks = eligible_subtasks[:num_tasks]
        if verbose:
            print_info(f"Limiting execution to first {num_tasks} subtasks.", 2)
    else:
        target_subtasks = eligible_subtasks

    # If no tasks to process, just print current status
    if not target_subtasks:
        if verbose:
            print_info("No tasks to process", 2)
        print(f"Status: {session.status}")
        print(f"Number of pending tasks in active plan: {total_pending}")
        print(f"Number of interrupted tasks in active plan: {total_interrupted}")
        return

    # Create inputs and outputs directories for the session
    maestro_dir = get_maestro_dir(session_path)
    inputs_dir = os.path.join(maestro_dir, "inputs")
    outputs_dir = os.path.join(maestro_dir, "outputs")
    os.makedirs(inputs_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    # Also create partials directory in the maestro directory
    partials_dir = os.path.join(maestro_dir, "partials")
    os.makedirs(partials_dir, exist_ok=True)

    # Process each target subtask in order
    tasks_processed = 0
    for i, subtask in enumerate(target_subtasks, 1):
        # Print "now playing" line unless quiet
        if not quiet:
            print_info(f"Running subtask {i}/{len(target_subtasks)}: \"{subtask.title}\"", 2)
            if verbose:
                print_info(f"Engine: {subtask.worker_model} | Stream: {'on' if stream_ai_output or (not quiet) else 'off'} | Prompt: saved to ...", 2)

        if subtask.status == "pending":
            if verbose:
                print_info(f"Processing pending subtask: '{subtask.title}' (ID: {subtask.id})", 2)

            # Set the summary file path if not already set
            if not subtask.summary_file:
                subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

            # Build structured prompt
            goal = f"Complete the subtask: {subtask.title}\nDescription: {subtask.description}"

            requirements_parts = [f"ROOT TASK (CLEANED):\n{root_task_to_use}"]
            requirements_parts.append(f"RELEVANT CATEGORIES:\n{categories_str}")
            requirements_parts.append(f"RELEVANT ROOT EXCERPT:\n{root_excerpt}")
            requirements_parts.append(f"SUBTASK DETAILS:\nid: {subtask.id}\ntitle: {subtask.title}\ndescription:\n{subtask.description}")
            requirements_parts.append(f"CURRENT RULES:\n{rules}")
            requirements = "\n\n".join(requirements_parts)

            acceptance_criteria = "The work should be completed according to the subtask requirements. The work should be properly integrated with existing codebase."

            deliverables_parts = [f"Completed work for subtask '{subtask.title}'"]
            deliverables_parts.append(f"Write a summary to file: {subtask.summary_file}")
            deliverables = "\n".join(deliverables_parts)

            prompt = build_structured_prompt(goal, requirements, acceptance_criteria, deliverables)

            # Add additional instructions that were in the original prompt
            prompt += f"[ADDITIONAL INSTRUCTIONS]\n"
            prompt += f"[SUBTASK]\n"
            prompt += f"id: {subtask.id}\n"
            prompt += f"title: {subtask.title}\n"
            prompt += f"description:\n{subtask.description}\n\n"
            prompt += f"You are an autonomous coding agent working in this repository.\n"
            prompt += f"- Perform ONLY the work needed for this subtask.\n"
            prompt += f"- Use your normal tools and workflows.\n"
            prompt += f"- When you are done, write a short plain-text summary of what you did\n"
            prompt += f"  into the file: {subtask.summary_file}\n\n"
            prompt += f"The summary MUST be written to that file before you consider the task complete."

        elif subtask.status == "interrupted" and retry_interrupted:
            if verbose:
                print_info(f"Processing interrupted subtask: '{subtask.title}' (ID: {subtask.id})", 2)

            # Load partial output to inject into the next prompt
            partial_dir = os.path.join(maestro_dir, "partials")
            partial_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.txt")

            partial_output_content = ""
            if os.path.exists(partial_filename):
                with open(partial_filename, 'r', encoding='utf-8') as f:
                    partial_output_content = f.read().strip()

            # Set the summary file path if not already set
            if not subtask.summary_file:
                subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

            # Build structured prompt - but inject partial result
            goal = f"Resume the subtask: {subtask.title}\nDescription: {subtask.description}"

            requirements_parts = [f"ROOT TASK (CLEANED):\n{root_task_to_use}"]
            requirements_parts.append(f"RELEVANT CATEGORIES:\n{categories_str}")
            requirements_parts.append(f"RELEVANT ROOT EXCERPT:\n{root_excerpt}")
            requirements_parts.append(f"SUBTASK DETAILS:\nid: {subtask.id}\ntitle: {subtask.title}\ndescription:\n{subtask.description}")
            requirements_parts.append(f"CURRENT RULES:\n{rules}")
            requirements_parts.append(f"[PARTIAL RESULT FROM PREVIOUS ATTEMPT]\n{partial_output_content}")
            requirements = "\n\n".join(requirements_parts)

            acceptance_criteria = "The work should be completed according to the subtask requirements. The work should be properly integrated with existing codebase. Build upon the partial result provided."

            deliverables_parts = [f"Continue and complete work for subtask '{subtask.title}', based on the partial result"]
            deliverables_parts.append(f"Write a summary to file: {subtask.summary_file}")
            deliverables = "\n".join(deliverables_parts)

            prompt = build_structured_prompt(goal, requirements, acceptance_criteria, deliverables)

            # Add additional instructions that were in the original prompt
            prompt += f"[ADDITIONAL INSTRUCTIONS]\n"
            prompt += f"[SUBTASK]\n"
            prompt += f"id: {subtask.id}\n"
            prompt += f"title: {subtask.title}\n"
            prompt += f"description:\n{subtask.description}\n\n"
            prompt += f"You are resuming an autonomous coding agent task that was previously interrupted.\n"
            prompt += f"- Continue the work needed for this subtask based on the partial result.\n"
            prompt += f"- Use your normal tools and workflows.\n"
            prompt += f"- When you are done, write a short plain-text summary of what you did\n"
            prompt += f"  into the file: {subtask.summary_file}\n\n"
            prompt += f"The summary MUST be written to that file before you consider the task complete."

        else:
            # This shouldn't happen if the logic is working correctly
            if verbose:
                print_info(f"Skipping subtask with status: '{subtask.status}' (ID: {subtask.id})", 2)
            continue

        if verbose:
            print_info(f"Using worker model: {subtask.worker_model}", 2)

        # Print prompt if requested
        if print_ai_prompts and not quiet:
            print_info("PROMPT:", 2)
            print(prompt)
            print_info("END PROMPT", 2)

        # Look up the worker engine
        from .engines import get_engine
        try:
            # Use stream_ai_output parameter when retry_interrupted is True, otherwise use (not quiet)
            effective_stream = stream_ai_output
            if not retry_interrupted:  # Only use quiet for non-interrupted tasks
                effective_stream = not quiet

            engine = get_engine(subtask.worker_model + "_worker", debug=verbose, stream_output=effective_stream)
        except ValueError:
            # If we don't have the specific model with "_worker" suffix, try directly
            try:
                engine = get_engine(subtask.worker_model, debug=verbose, stream_output=effective_stream)
            except ValueError:
                print(f"Error: Unknown worker model '{subtask.worker_model}'", file=sys.stderr)
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
                sys.exit(1)

        if verbose:
            print_info(f"Generated prompt for engine (length: {len(prompt)} chars)", 2)

        # Save the worker prompt to the inputs directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        worker_prompt_filename = os.path.join(inputs_dir, f"worker_{subtask.id}_{timestamp}.txt")
        with open(worker_prompt_filename, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Log verbose information
        if verbose:
            print_info(f"Engine={subtask.worker_model} subtask={subtask.id}", 2)
            print_info(f"Prompt file: {worker_prompt_filename}", 2)
            print_info(f"Output file: {os.path.join(outputs_dir, f'{subtask.id}.txt')}", 2)

        # Call engine.generate(prompt) with interruption handling
        try:
            output = engine.generate(prompt)
        except KeyboardInterrupt:
            # Handle user interruption
            print(f"\n[maestro] Interrupt received — stopping current AI step…", file=sys.stderr)
            subtask.status = "interrupted"
            session.status = "interrupted"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)

            # Save partial output if available
            partial_dir = os.path.join(maestro_dir, "partials")
            os.makedirs(partial_dir, exist_ok=True)
            partial_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.txt")

            with open(partial_filename, 'w', encoding='utf-8') as f:
                f.write(output if output else "")

            # Also save stderr if available (not currently implemented in engines)
            partial_stderr_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.err.txt")
            # This will be saved if we track stderr in engine results (not currently done)

            # Also create an empty summary file to prevent error on resume
            # This ensures that when the task is resumed, the expected summary file exists
            if subtask.summary_file and not os.path.exists(subtask.summary_file):
                os.makedirs(os.path.dirname(subtask.summary_file), exist_ok=True)
                with open(subtask.summary_file, 'w', encoding='utf-8') as f:
                    f.write("")  # Create empty summary file

            if verbose:
                print_info(f"Partial stdout saved to: {partial_filename}", 2)
                print_info(f"Subtask {subtask.id} marked as interrupted", 2)

            # Exit with clean code for interruption
            sys.exit(130)
        except Exception as e:
            print(f"Error: Failed to generate output from engine: {str(e)}", file=sys.stderr)
            subtask.status = "error"
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

        if verbose:
            print_info(f"Generated output from engine (length: {len(output)} chars)", 2)

        # Save the raw stdout to a file with engine name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        stdout_filename = os.path.join(outputs_dir, f"worker_{subtask.id}_{subtask.worker_model}_{timestamp}.txt")
        with open(stdout_filename, 'w', encoding='utf-8') as f:
            f.write(output)

        if verbose:
            print_info(f"Saved raw stdout to: {stdout_filename}", 2)

        output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(output)

        if verbose:
            print_info(f"Saved output to: {output_file_path}", 2)

        # Verify summary file exists and is non-empty
        if not os.path.exists(subtask.summary_file):
            print(f"Error: Summary file missing for subtask {subtask.id}: {subtask.summary_file}", file=sys.stderr)
            subtask.status = "error"
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

        size = os.path.getsize(subtask.summary_file)
        if size == 0:
            print(f"Error: Summary file empty for subtask {subtask.id}: {subtask.summary_file}", file=sys.stderr)
            subtask.status = "error"
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

        # Mark subtask.status as "done" and update updated_at
        subtask.status = "done"
        session.updated_at = datetime.now().isoformat()

        if verbose:
            print_info(f"Updated subtask status to 'done'", 2)

        tasks_processed += 1

        # Process rule-based post-tasks if any
        if verbose:
            print_info("Processing rule-based post-tasks...", 2)

        # Process rule-based post-tasks if they exist in the rules
        # When running with limited tasks, we still process rules for each completed task
        process_rule_based_post_tasks(session, subtask, rules, session_dir, verbose)

    # Update session status based on subtask completion
    all_done = all(subtask.status == "done" for subtask in session.subtasks)
    if all_done and session.subtasks:
        session.status = "done"
    else:
        session.status = "in_progress"

    # Save the updated session
    save_session(session, session_path)

    if verbose:
        print_info(f"Saved session with new status: {session.status}", 2)

    print_info(f"Processed {tasks_processed} subtasks", 2)
    print_info(f"New session status: {session.status}", 2)


def handle_show_plan_tree(session_path, verbose=False):
    """Print the entire plan tree with ASCII art representation."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    if not session.plans:
        print("No plans in session yet.")
        return

    # Use the new render_plan_tree function
    tree_str = render_plan_tree(session.plans, session.active_plan_id)
    print(tree_str)


def handle_focus_plan(session_path, plan_id, verbose=False):
    """Set the active plan ID to switch focus."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Check if the plan exists
    target_plan = None
    for plan in session.plans:
        if plan.plan_id == plan_id:
            target_plan = plan
            break

    if target_plan is None:
        print(f"Error: Plan with ID '{plan_id}' not found.", file=sys.stderr)
        sys.exit(1)

    # Check if the plan is dead - refuse to switch to dead plans
    if target_plan.status == "dead":
        print(f"Error: Cannot switch to plan '{plan_id}' because it is marked as dead.", file=sys.stderr)
        print(f"Plan '{plan_id}' status is: {target_plan.status}")
        # List dead plans for the user
        dead_plans = [p for p in session.plans if p.status == "dead"]
        if dead_plans:
            print(f"Dead plans: {[p.plan_id for p in dead_plans]}")
        sys.exit(1)

    # Check if switching focus would affect subtasks
    current_active_plan = None
    if session.active_plan_id:
        for plan in session.plans:
            if plan.plan_id == session.active_plan_id:
                current_active_plan = plan
                break

    # Count subtasks for the new and current plans
    new_plan_subtasks = [st for st in session.subtasks if st.plan_id == plan_id]
    current_plan_subtasks = [st for st in session.subtasks if st.plan_id == session.active_plan_id] if session.active_plan_id else []

    if new_plan_subtasks and current_plan_subtasks and new_plan_subtasks != current_plan_subtasks:
        print_warning(f"This plan branch has {len(new_plan_subtasks)} subtasks that may need to be re-run or ignored.", 2)
        response = input(f"Are you sure you want to switch focus to PLAN_ID={plan_id}? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print_info("Plan focus switch cancelled.", 2)
            return

    # Check if there's an active plan that is dead and warn user
    if session.active_plan_id:
        current_plan = next((p for p in session.plans if p.plan_id == session.active_plan_id), None)
        if current_plan and current_plan.status == "dead":
            print_warning(f"Warning: Current active plan '{session.active_plan_id}' is dead. Switching to '{plan_id}' is recommended.", 2)

    # Set the new active plan
    session.active_plan_id = plan_id
    save_session(session, session_path)
    print_success(f"Plan focus switched to: {plan_id} ({target_plan.label})", 2)


def handle_kill_plan(session_path, plan_id, verbose=False):
    """Mark a plan branch as dead by setting its status to 'dead'."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Check if the plan exists
    target_plan = None
    for plan in session.plans:
        if plan.plan_id == plan_id:
            target_plan = plan
            break

    if target_plan is None:
        print(f"Error: Plan with ID '{plan_id}' not found.", file=sys.stderr)
        sys.exit(1)

    # Check if this is the active plan and warn user
    if plan_id == session.active_plan_id:
        print_warning(f"WARNING: You are about to kill the active plan '{plan_id}'.", 2)
        print_info("After killing this plan, you must choose a new active plan from the remaining plans.", 2)

        # List all available non-dead plans for the user to choose from
        alive_plans = [p for p in session.plans if p.plan_id != plan_id and p.status != "dead"]
        if not alive_plans:
            print_error("ERROR: This is the last active plan. Killing it would leave no active plan.", 2)
            print_info("You cannot kill the last active plan without another plan to switch to.", 2)
            sys.exit(1)
        else:
            print_info(f"Available plans to switch to: {[p.plan_id for p in alive_plans]}", 2)
            response = input("Do you still want to kill this active plan? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print_info("Kill plan operation cancelled.", 2)
                return

    # Ask for confirmation before marking as dead
    subtasks_for_plan = [st for st in session.subtasks if st.plan_id == plan_id]
    subtask_count = len(subtasks_for_plan)

    print_info(f"Marking plan '{plan_id}' as dead will affect {subtask_count} subtasks.", 2)
    if subtask_count > 0:
        print_info(f"Affected subtasks: {[st.title for st in subtasks_for_plan][:5]}{'...' if subtask_count > 5 else ''}", 2)

    response = input(f"Are you sure you want to mark PLAN_ID={plan_id} as dead? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print_info("Kill plan operation cancelled.", 2)
        return

    # Mark the plan as dead
    target_plan.status = "dead"

    # If this was the active plan, force the user to select a new active plan
    if plan_id == session.active_plan_id:
        alive_plans = [p for p in session.plans if p.status != "dead"]

        if alive_plans:
            print_header("SELECT NEW ACTIVE PLAN")
            for i, p in enumerate(alive_plans, 1):
                marker = "[*]" if p.plan_id == session.active_plan_id else "[ ]"
                print(f"  {i}. {marker} {p.plan_id} - {p.label} ({p.status})")

            while True:
                try:
                    choice_input = input(f"Enter the number of the plan to make active (1-{len(alive_plans)}): ").strip()
                    choice_idx = int(choice_input) - 1
                    if 0 <= choice_idx < len(alive_plans):
                        new_active_plan_id = alive_plans[choice_idx].plan_id
                        session.active_plan_id = new_active_plan_id
                        print_info(f"Switched active plan to: {new_active_plan_id}", 2)
                        break
                    else:
                        print_error(f"Invalid choice. Please enter a number between 1 and {len(alive_plans)}.", 2)
                except ValueError:
                    print_error("Invalid input. Please enter a number.", 2)

        else:
            print_warning("No active plans remain after killing this plan.", 2)

    # Optionally, we could also mark subtasks as cancelled, but for now just update the plan status
    save_session(session, session_path)
    print_success(f"Plan {plan_id} has been marked as dead.", 2)


def handle_plan_list(session_path, verbose=False):
    """List all plans in the session as a numbered list."""
    import shutil

    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    if not session.plans:
        print("No plans in session yet.")
        return

    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    term_width = max(term_width, 80)
    print()
    print("=" * term_width)
    print("PLANS LIST")
    print("=" * term_width)

    for i, plan in enumerate(session.plans, 1):
        marker = "[*]" if plan.plan_id == session.active_plan_id else "[ ]"
        status_symbol = "✓" if plan.status == "active" else "✗" if plan.status == "dead" else "○"
        prefix = f"{i:2d}. {marker} {status_symbol} {plan.plan_id}  "
        suffix = f" ({plan.status})"
        available = term_width - len(prefix) - len(suffix)
        if available < 1:
            available = 1
        label = plan.label
        if len(label) > available:
            if available >= 4:
                label = label[:available - 3] + "..."
            else:
                label = label[:available]
        print(f"{prefix}{label}{suffix}")


def handle_plan_show(session_path, plan_id, verbose=False):
    """Show details of a specific plan by ID, number, or name."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    if not session.plans:
        print("No plans in session yet.")
        return

    # If no plan_id is provided, show the active plan
    if plan_id is None:
        if session.active_plan_id:
            # Find the active plan
            for plan in session.plans:
                if plan.plan_id == session.active_plan_id:
                    target_plan = plan
                    break
            else:
                print(f"Error: Active plan ID '{session.active_plan_id}' not found in session plans.", file=sys.stderr)
                sys.exit(1)
        else:
            print("No active plan set.", file=sys.stderr)
            sys.exit(1)
    else:
        # Try to find plan by ID, or by index number
        target_plan = None

        # First, try to match by exact plan_id
        for plan in session.plans:
            if plan.plan_id == plan_id:
                target_plan = plan
                break

        # If not found and plan_id is a number, try to match by index
        if target_plan is None:
            try:
                plan_index = int(plan_id) - 1  # Convert to 0-based index
                if 0 <= plan_index < len(session.plans):
                    target_plan = session.plans[plan_index]
            except ValueError:
                # Not a number, continue without error
                pass

        if target_plan is None:
            print(f"Error: Plan with ID or number '{plan_id}' not found.", file=sys.stderr)
            sys.exit(1)

    # Print plan details
    print_header(f"PLAN DETAILS: {target_plan.plan_id}")
    styled_print(f"Label: {target_plan.label}", Colors.BRIGHT_YELLOW, Colors.BOLD, 2)
    styled_print(f"Status: {target_plan.status}", Colors.BRIGHT_CYAN, None, 2)
    styled_print(f"Created: {target_plan.created_at}", Colors.BRIGHT_GREEN, None, 2)
    styled_print(f"Active: {'Yes' if target_plan.plan_id == session.active_plan_id else 'No'}", Colors.BRIGHT_MAGENTA, None, 2)
    styled_print(f"Notes: {target_plan.notes if target_plan.notes else '(no notes)'}", Colors.BRIGHT_WHITE, None, 2)
    styled_print(f"Root snapshot: {target_plan.root_snapshot[:100] if target_plan.root_snapshot else '(no root snapshot)'}", Colors.BRIGHT_WHITE, None, 2)
    styled_print(f"Categories: {target_plan.categories_snapshot if target_plan.categories_snapshot else '[]'}", Colors.BRIGHT_WHITE, None, 2)

    if target_plan.subtask_ids:
        print_subheader("SUBTASKS IN THIS PLAN")
        for subtask_id in target_plan.subtask_ids:
            subtask = next((st for st in session.subtasks if st.id == subtask_id), None)
            if subtask:
                status_symbol = "✓" if subtask.status == "done" else "○" if subtask.status == "pending" else "✗"
                styled_print(f"  {status_symbol} {subtask.title} [{subtask.status}]", Colors.BRIGHT_WHITE, None, 2)
            else:
                styled_print(f"  ? Subtask ID: {subtask_id}", Colors.BRIGHT_RED, None, 2)
    else:
        styled_print("No subtasks in this plan", Colors.BRIGHT_RED, None, 2)


def handle_plan_get(session_path, verbose=False):
    """Print the active plan ID."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    if session.active_plan_id:
        print(session.active_plan_id)
    else:
        print("No active plan set")


def handle_log_list(session_path, verbose=False):
    """List all past modifications."""
    print_warning("Log functionality not fully implemented in this version.", 2)


def handle_log_list_work(session_path, verbose=False):
    """List all working sessions of tasks."""
    print_warning("Work log functionality not fully implemented in this version.", 2)


def handle_log_list_plan(session_path, verbose=False):
    """List all plan changes."""
    print_warning("Plan log functionality not fully implemented in this version.", 2)


def handle_rules_list(session_path, verbose=False):
    """Parse and list all rules from the rules file in JSON format."""
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Load rules text
    rules_text = load_rules(session)

    if not rules_text.strip():
        print("No rules found in rules file.")
        return

    # Try to parse as JSON first
    import json
    try:
        parsed_rules = json.loads(rules_text)
        print(json.dumps(parsed_rules, indent=2))
        return
    except json.JSONDecodeError:
        # If not JSON, parse as text
        # Split into lines and remove empty lines
        lines = [line.strip() for line in rules_text.split('\n') if line.strip()]

        # Create a JSON object representing the rules
        rules_json = {
            "rules": []
        }

        for i, line in enumerate(lines):
            # Skip comment lines (starting with #)
            if line.startswith('#'):
                continue
            rules_json["rules"].append({
                "id": f"rule_{i+1}",
                "content": line,
                "enabled": True  # Assume all rules are enabled by default
            })

        print(json.dumps(rules_json, indent=2))


def handle_rules_enable(session_path, rule_id, verbose=False):
    """Enable a specific rule by ID or number."""
    print_warning(f"Rule enabling not implemented in this version. Rule '{rule_id}' is now considered enabled.", 2)


def handle_rules_disable(session_path, rule_id, verbose=False):
    """Disable a specific rule by ID or number."""
    print_warning(f"Rule disabling not implemented in this version. Rule '{rule_id}' is now considered disabled.", 2)


def get_session_path_by_name(session_name: str) -> str:
    """
    Get the full path to a session file by its name.

    Args:
        session_name: Name of the session

    Returns:
        Full path to the session file
    """
    sessions_dir = get_maestro_sessions_dir()
    session_filename = f"{session_name}.json"
    return os.path.join(sessions_dir, session_filename)


def get_session_name_from_path(session_path: str) -> str:
    """
    Extract the session name from a session file path.

    Args:
        session_path: Full path to the session file

    Returns:
        Session name (without path and extension)
    """
    return os.path.splitext(os.path.basename(session_path))[0]


def list_sessions() -> List[str]:
    """
    List all session files in the .maestro/sessions directory.

    Returns:
        List of session names
    """
    sessions_dir = get_maestro_sessions_dir()
    sessions = []

    if os.path.exists(sessions_dir):
        for filename in os.listdir(sessions_dir):
            if filename.endswith('.json'):
                session_name = os.path.splitext(filename)[0]
                sessions.append(session_name)

    return sorted(sessions)


def create_session(session_name: str, root_task: str = "", overwrite: bool = False) -> str:
    """
    Create a new session file in the .maestro/sessions directory.

    Args:
        session_name: Name of the session to create
        root_task: Optional root task for the session
        overwrite: Whether to overwrite if session already exists

    Returns:
        Path to the created session file
    """
    session_path = get_session_path_by_name(session_name)

    if os.path.exists(session_path) and not overwrite:
        raise FileExistsError(f"Session '{session_name}' already exists at {session_path}")

    # Create a new session with status="new" and empty subtasks
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        root_task=root_task,
        subtasks=[],
        rules_path=None,  # Point to rules file if it exists
        status="new"
    )

    # Save the session
    save_session(session, session_path)
    return session_path


def remove_session(session_name: str) -> bool:
    """
    Remove a session file from the .maestro/sessions directory.

    Args:
        session_name: Name of the session to remove

    Returns:
        True if successful, False otherwise
    """
    session_path = get_session_path_by_name(session_name)

    if not os.path.exists(session_path):
        return False

    try:
        os.remove(session_path)
        return True
    except Exception:
        return False


def get_session_details(session_name: str) -> Optional[dict]:
    """
    Get details about a specific session.

    Args:
        session_name: Name of the session

    Returns:
        Dictionary with session details, or None if session doesn't exist
    """
    session_path = get_session_path_by_name(session_name)

    if not os.path.exists(session_path):
        return None

    try:
        session = load_session(session_path)
        return {
            'name': session_name,
            'path': session_path,
            'id': session.id,
            'created_at': session.created_at,
            'updated_at': session.updated_at,
            'status': session.status,
            'root_task': session.root_task[:100] + "..." if len(session.root_task) > 100 else session.root_task,
            'subtasks_count': len(session.subtasks),
            'active_plan_id': session.active_plan_id
        }
    except Exception:
        return None


def get_multiline_input(prompt: str) -> str:
    """
    Get input from user supporting commands and multiline functionality.
    Enter sends the message; to add newlines, enter \\n in the text or use multiple inputs.
    For true shift+enter or ctrl+j support, we'd need prompt_toolkit library.
    For now, the function returns immediately on Enter (satisfies main requirement).
    """
    import sys

    try:
        line = input(prompt)
        return line.rstrip()
    except EOFError:
        # Handle case where input is not available (e.g., if stdin is redirected)
        return "/quit"


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


def process_rule_based_post_tasks(session, completed_subtask, rules, session_dir, verbose=False):
    """
    Process rule-based post-tasks that should be executed after each completed task.
    """
    # This function would handle recurring tasks defined in rules that should be executed
    # after each completed task. Since the AI converts rules to JSON with task info,
    # we would parse those rules and execute associated tasks.

    # For now, we'll implement basic rule parsing to identify recurring tasks
    import json

    try:
        # Try to parse rules as JSON with structured rule information
        rules_json = json.loads(rules)
        if isinstance(rules_json, dict) and "rules" in rules_json:
            for rule in rules_json.get("rules", []):
                if isinstance(rule, dict):
                    rule_content = rule.get("content", "")
                    # Example: look for recurring tasks like "commit to git" or "run tests"
                    # In a real implementation, this would create and execute new tasks
                    if verbose and rule_content:
                        print_info(f"Rule-based post-task identified: {rule_content}", 4)
    except json.JSONDecodeError:
        # If not JSON, process as text rules
        rule_lines = [line.strip() for line in rules.split('\n') if line.strip() and not line.strip().startswith('#')]
        for rule_line in rule_lines:
            if verbose:
                print_info(f"Rule-based post-task: {rule_line}", 4)


def migrate_session_if_needed(session: Session):
    """
    Migrate an old session to use the new plan tree structure if needed.
    This ensures backward compatibility for sessions created before plan trees existed.
    """
    # If the session has no plans, create a default plan structure
    if not session.plans:
        # For backward compatibility, assume the original root_task was the raw task
        session.root_task_raw = session.root_task_raw or session.root_task
        session.root_task_clean = session.root_task_clean or session.root_task
        session.root_task_categories = session.root_task_categories or []

        # Create the initial plan node
        plan_id = "P1"  # Default first plan ID
        initial_plan = PlanNode(
            plan_id=plan_id,
            parent_plan_id=None,
            created_at=datetime.now().isoformat(),
            label="Initial plan",
            status="active",
            notes="Generated from initial planning",
            root_snapshot=session.root_task_clean or session.root_task_raw or session.root_task,
            categories_snapshot=session.root_task_categories,
            subtask_ids=[subtask.id for subtask in session.subtasks]
        )
        session.plans.append(initial_plan)
        session.active_plan_id = plan_id

        # Assign plan_id to all existing subtasks if they don't have one
        for subtask in session.subtasks:
            if not subtask.plan_id:
                subtask.plan_id = plan_id


def create_initial_plan_node(session: Session):
    """
    Create an initial PlanNode for the session if it doesn't have any plans yet.
    """
    if not session.plans:
        migrate_session_if_needed(session)
        for plan in session.plans:
            if plan.plan_id == session.active_plan_id:
                return plan
    return session.plans[0] if session.plans else None  # Return the first plan if one exists


def create_plan_branch(session: Session, parent_plan_id: str | None, label: str):
    """
    Create a new plan branch as a child of the parent plan.
    """
    new_plan_id = str(uuid.uuid4())
    new_plan = PlanNode(
        plan_id=new_plan_id,
        parent_plan_id=parent_plan_id,
        created_at=datetime.now().isoformat(),
        label=label,
        status="active",
        notes=None,
        root_snapshot=session.root_task_clean or session.root_task_raw or session.root_task,
        categories_snapshot=session.root_task_categories,
        subtask_ids=[]  # Will be populated when subtasks are created
    )
    session.plans.append(new_plan)
    session.active_plan_id = new_plan_id
    return new_plan


def render_plan_tree(plans, active_plan_id):
    """
    Render the plan tree using ASCII art with proper indentation and markers.

    Args:
        plans: List of PlanNode objects
        active_plan_id: ID of the currently active plan

    Returns:
        String representation of the plan tree
    """
    if not plans:
        return "No plans available."

    # 1. Build parent→children mapping
    children = {}
    root_plans = []

    for plan in plans:
        if plan.parent_plan_id is None:
            root_plans.append(plan)
        else:
            if plan.parent_plan_id not in children:
                children[plan.parent_plan_id] = []
            children[plan.parent_plan_id].append(plan)

    # Add empty lists for plans that have no children
    for plan in plans:
        if plan.plan_id not in children:
            children[plan.plan_id] = []

    # Determine terminal colors if supported
    try:
        import os
        # Check if we're in a terminal that supports colors
        supports_color = (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()) or os.getenv('TERM')

        if supports_color:
            # ANSI color codes
            GREEN = '\033[32m'   # Active plans
            YELLOW = '\033[33m'  # Inactive plans
            RED = '\033[31m'     # Dead plans
            BRIGHT_GREEN = '\033[92m'  # Active plans (bright)
            BRIGHT_RED = '\033[91m'    # Dead plans (bright)
            BRIGHT_YELLOW = '\033[93m' # Inactive plans (bright)
            RESET = '\033[0m'    # Reset color
        else:
            # No colors for terminals that don't support them
            GREEN = YELLOW = RED = BRIGHT_GREEN = BRIGHT_RED = BRIGHT_YELLOW = RESET = ''
    except:
        # Default to no colors if there's any error
        GREEN = YELLOW = RED = BRIGHT_GREEN = BRIGHT_RED = BRIGHT_YELLOW = RESET = ''

    def get_status_marker(plan):
        """Get the status marker for a plan."""
        if plan.plan_id == active_plan_id:
            return "[*]"
        elif plan.status == "dead":
            return "[x]"
        else:  # inactive
            return "[ ]"

    def get_status_color(plan):
        """Get the color code for a plan based on its status."""
        if plan.plan_id == active_plan_id:
            return BRIGHT_GREEN if plan.status == "active" else GREEN
        elif plan.status == "dead":
            return BRIGHT_RED if plan.status == "dead" else RED
        else:  # inactive
            return BRIGHT_YELLOW if plan.status == "active" else YELLOW

    result_lines = []  # Define result_lines before inner function

    # Add header
    result_lines.append("Plan Tree Visualization")
    result_lines.append("=======================")

    # Use a helper that tracks which columns have vertical bars
    def draw_recursive(plan, level=0, is_last_child_list=None, prefix=""):
        """
        Draw the plan tree recursively with proper vertical bars.
        - level: depth in the tree
        - is_last_child_list: list indicating for each level if the node is the last child
        """
        nonlocal result_lines  # Add nonlocal to access the outer scope variable
        if is_last_child_list is None:
            is_last_child_list = []

        marker = get_status_marker(plan)
        color = get_status_color(plan)

        # Format plan info with additional details like creation time and short label
        from datetime import datetime
        try:
            # Parse the datetime string to make it more readable
            created_time = datetime.fromisoformat(plan.created_at.replace('Z', '+00:00'))
            formatted_time = created_time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = plan.created_at  # Fallback if parsing fails

        plan_info = f"{color}{marker}{RESET} {plan.plan_id}  {plan.label} [{plan.status}] (created {formatted_time})"

        result_lines.append(f"{prefix}{plan_info}")

        # Get children of this plan
        plan_children = children.get(plan.plan_id, [])

        # Process each child
        for i, child_plan in enumerate(plan_children):
            is_last = (i == len(plan_children) - 1)

            # Build prefix for the child
            child_prefix = ""
            for j in range(level):
                if is_last_child_list[j]:
                    # If the ancestor at level j was the last child, use spaces
                    child_prefix += "    "
                else:
                    # If the ancestor at level j had more siblings, use vertical bar
                    child_prefix += " │   "

            # Add the connection character for this level
            if is_last:
                child_prefix += " └─ "
            else:
                child_prefix += " ├─ "

            # Create a new list for this child's recursive call
            new_is_last_list = is_last_child_list + [is_last]

            draw_recursive(child_plan, level + 1, new_is_last_list, child_prefix)

    # Start from root plans
    for i, plan in enumerate(root_plans):
        is_last = (i == len(root_plans) - 1)
        if len(root_plans) > 1:
            # Multiple root plans - connect them with ├─ or └─
            prefix = " ├─ " if not is_last else " └─ "
            draw_recursive(plan, 0, [is_last], prefix)
        else:
            # Single root plan - start directly
            draw_recursive(plan, 0, [True], "")

    return "\n".join(result_lines)


def apply_json_plan_to_session(session: Session, plan: dict) -> None:
    """
    Clear or update session.subtasks based on the JSON plan.
    Sets planner_model and worker_model for each subtask.
    Also handles root task cleaning and categories from the plan.
    """
    # Validate plan["subtasks"] is a list; if empty, raise error
    if "subtasks" not in plan or not isinstance(plan["subtasks"], list):
        raise ValueError("Plan must contain a 'subtasks' list")

    if len(plan["subtasks"]) == 0:
        raise ValueError("Plan 'subtasks' list cannot be empty")

    # Handle root task information from the plan if present
    if "root" in plan:
        root_info = plan["root"]
        session.root_task_raw = session.root_task  # Set raw from current root_task
        session.root_task_clean = root_info.get("clean_text", session.root_task)
        session.root_task_summary = root_info.get("raw_summary")  # Add raw_summary
        session.root_task_categories = root_info.get("categories", [])

        # Update the main root_task to the clean version
        session.root_task = session.root_task_clean

    # Create new subtasks from the JSON plan
    new_subtasks = []

    # Use the active plan ID for the current plan if available
    current_plan_id = session.active_plan_id if session.active_plan_id else str(uuid.uuid4())

    for item in plan["subtasks"]:
        if not isinstance(item, dict):
            continue  # Skip non-dict items

        # Extract fields from the JSON item
        subtask_id = item.get("id", str(uuid.uuid4()))  # Generate if not provided
        title = item.get("title", "Untitled")
        description = item.get("description", "")
        kind = item.get("kind", "code")  # default to "code"
        complexity = item.get("complexity", "normal")  # default to "normal"
        planner_model = plan.get("planner_model", "unknown")
        depends_on = item.get("depends_on", [])  # default to no dependencies

        # Extract new fields for flexible root task handling
        categories = item.get("categories", [])
        root_excerpt = item.get("root_excerpt")

        # Determine worker model using the helper function
        preferred_worker = item.get("preferred_worker", None)
        worker_model = select_worker_model(kind, complexity, preferred_worker)

        # Create the Subtask with all required fields
        subtask = Subtask(
            id=subtask_id,
            title=title,
            description=description,
            planner_model=planner_model,
            worker_model=worker_model,
            status="pending",  # Default to pending
            summary_file="",  # Will be set later when worker processes the task
            categories=categories,
            root_excerpt=root_excerpt,
            plan_id=current_plan_id  # Assign the plan_id to the subtask
        )

        new_subtasks.append(subtask)

    # Replace session.subtasks entirely
    session.subtasks = new_subtasks

    # Update session status and timestamp
    session.status = "planned"
    session.updated_at = datetime.now().isoformat()


def select_worker_model(kind: str, complexity: str, preferred_worker: str | None = None) -> str:
    """
    Decide which worker model to use ("qwen" or "gemini") based on task kind,
    complexity, and planner's hint.
    """
    # If preferred_worker is "qwen" or "gemini", and it's allowed, use it.
    if preferred_worker in ["qwen", "gemini"]:
        return preferred_worker

    # Else, heuristics:
    # If kind in {"code", "bugfix"}:
    if kind in {"code", "bugfix"}:
        # Use "qwen" for "trivial" or "normal".
        if complexity in {"trivial", "normal"}:
            return "qwen"
        # For "hard" bugfixes, you *may* still route to qwen but flag them in planner_notes for possible manual rerouting to claude/codex later.
        elif complexity == "hard" and kind == "bugfix":
            return "qwen"  # For hard bugfixes, default to qwen but they may need manual attention
        else:  # "complex" or "hard" code tasks
            return "qwen"

    # If kind in {"research", "text", "docs"}:
    elif kind in {"research", "text", "docs"}:
        # Use "gemini" by default.
        return "gemini"

    # Default fallback: "qwen".
    return "qwen"


def json_to_planned_subtasks(json_plan: dict) -> list:
    """
    Convert the JSON plan with subtasks to PlannedSubtask objects.

    Args:
        json_plan: The parsed JSON object from the planner

    Returns:
        List of PlannedSubtask objects
    """
    planned_subtasks = []

    if "subtasks" in json_plan and isinstance(json_plan["subtasks"], list):
        for subtask_data in json_plan["subtasks"]:
            if isinstance(subtask_data, dict) and "title" in subtask_data:
                title = subtask_data["title"]
                description = subtask_data.get("description", "")
                planned_subtasks.append(PlannedSubtask(title=title, description=description))

    return planned_subtasks


def collect_worker_summaries(session: Session, session_path: str) -> str:
    """
    Collect all existing subtask summary files and concatenate their contents.

    Args:
        session: The session object containing subtasks
        session_path: Path to the session file to locate outputs directory

    Returns:
        A string containing all summaries with clear separators
    """
    summaries = []

    # Get the directory containing the session file
    maestro_dir = get_maestro_dir(session_path)
    outputs_dir = os.path.join(maestro_dir, "outputs")

    for subtask in session.subtasks:
        # Only collect summaries for subtasks that are marked as done
        if subtask.status == "done":
            # First check if the explicit summary_file exists
            summary_file_path = subtask.summary_file
            if not summary_file_path:
                # If summary_file is not set, try the default location
                summary_file_path = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

            if summary_file_path and os.path.exists(summary_file_path):
                try:
                    with open(summary_file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            summaries.append(f"### Subtask {subtask.id} ({subtask.title})\n")
                            summaries.append(content)
                            summaries.append("\n\n")
                except Exception:
                    # If there's an error reading a summary file, continue with other files
                    pass

    summaries_text = "".join(summaries) if summaries else "(no summaries yet)"
    return summaries_text


def edit_root_task_in_editor():
    """Open an editor to input the root task text."""
    import tempfile

    # Create a temporary file with default content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("# Enter the root task here\n# This is the main task for your AI session\n\n")
        temp_file_path = tmp_file.name

    try:
        # Use the EDITOR environment variable or default to 'nano'
        editor = os.environ.get('EDITOR', 'nano')

        # Open the editor
        result = subprocess.run([editor, temp_file_path])

        if result.returncode != 0:
            print_warning(f"Editor exited with code {result.returncode}. Using empty root task.", 2)
            return ""

        # Read the content from the temporary file
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove comments and empty lines, and return the first non-empty line or all content
        lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
        content = '\n'.join(lines).strip()

        return content
    except FileNotFoundError:
        # If the editor is not found, fall back to stdin
        print_error(f"Editor '{editor}' not found. Falling back to stdin input.", 2)
        print_info("Enter the root task:", 2)
        return sys.stdin.readline().strip()
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def handle_refine_root(session_path, verbose=False, planner_order="codex,claude"):
    """Handle root task refinement: clean up, summarize, and categorize the raw root task."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        error_session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            root_task="Unknown",
            subtasks=[],
            rules_path=None,
            status="failed"
        )
        save_session(error_session, session_path)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        try:
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass
        sys.exit(1)

    # Ensure root_task is set
    if not session.root_task or session.root_task.strip() == "":
        print_error("Session root_task is not set.", 2)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Prepare the planner prompt for root refinement
    root_task_raw = session.root_task
    prompt = create_root_refinement_prompt(root_task_raw)

    # Create inputs directory if it doesn't exist
    maestro_dir = get_maestro_dir(session_path)
    inputs_dir = os.path.join(maestro_dir, "inputs")
    os.makedirs(inputs_dir, exist_ok=True)

    # Save the planner prompt to the inputs directory
    timestamp = int(time.time())
    planner_prompt_filename = os.path.join(inputs_dir, f"root_refinement_{timestamp}.txt")
    with open(planner_prompt_filename, "w", encoding="utf-8") as f:
        f.write(prompt)

    if verbose:
        print(f"[VERBOSE] Root refinement prompt saved to: {planner_prompt_filename}")

    # Parse planner preference from CLI argument
    planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
    planner_preference = [item.strip() for item in planner_preference if item.strip()]

    # Call the planner with the prompt
    try:
        json_result = run_planner_with_prompt(prompt, planner_preference, session_path, verbose)
    except KeyboardInterrupt:
        print("\n[orchestrator] Root refinement interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: Root refinement failed: {e}", file=sys.stderr)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Validate the JSON result has the required fields
    if not isinstance(json_result, dict):
        print(f"Error: Root refinement did not return a JSON object", file=sys.stderr)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    required_fields = ["version", "clean_text", "raw_summary", "categories"]
    for field in required_fields:
        if field not in json_result:
            print(f"Error: Root refinement missing required field: {field}", file=sys.stderr)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

    # Update the session with the refinement results
    session.root_task_raw = root_task_raw
    session.root_task_clean = json_result["clean_text"]
    session.root_task_summary = json_result["raw_summary"]
    session.root_task_categories = json_result["categories"]

    # Update session status and timestamp
    session.status = "refined"
    session.updated_at = datetime.now().isoformat()

    # Save the updated session
    save_session(session, session_path)

    # Print the results
    print("Root task refinement completed:")
    print(f"  Version: {json_result['version']}")
    print(f"  Clean text: {json_result['clean_text'][:100]}{'...' if len(json_result['clean_text']) > 100 else ''}")
    print(f"  Summary: {json_result['raw_summary']}")
    print(f"  Categories: {json_result['categories']}")

    if verbose:
        print(f"[VERBOSE] Session saved with status: {session.status}")


def create_root_refinement_prompt(root_task_raw):
    """
    Create the prompt for root task refinement.
    """
    goal = "Rewrite, summarize, and categorize the user's original project description."
    context = f"ORIGINAL PROJECT DESCRIPTION:\n{root_task_raw}"
    requirements = (
        "Return valid JSON with fields: version, clean_text (clear, structured, well-written restatement), "
        "raw_summary (1-3 sentences summarizing the intent), and categories (list of high-level conceptual categories). "
        "Respond ONLY with valid JSON in the following format:\n"
        "{\n"
        '  "version": 1,\n'
        '  "clean_text": "...",\n'
        '  "raw_summary": "...",\n'
        '  "categories": []\n'
        "}"
    )
    acceptance_criteria = "Return valid JSON with fields: version, clean_text (clear, structured, well-written restatement), raw_summary (1-3 sentences summarizing the intent), and categories (list of high-level conceptual categories)."
    deliverables = "JSON object with fields: version=1, clean_text, raw_summary, and categories (list of high-level conceptual categories like: architecture, backend, frontend, api, deployment, research, ui/ux, testing, refactoring, docs, etc.)"

    prompt = build_prompt(goal, context, requirements, acceptance_criteria, deliverables)

    # Add specific format requirements
    prompt += f"[ADDITIONAL INSTRUCTIONS]\n"
    prompt += f"Respond ONLY with valid JSON in the following format:\n\n"
    prompt += f"{{\n"
    prompt += f'  "version": 1,\n'
    prompt += f'  "clean_text": "...",\n'
    prompt += f'  "raw_summary": "...",\n'
    prompt += f'  "categories": []\n'
    prompt += f"}}"

    return prompt