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


class PlannedSubtask:
    """
    Represents a planned subtask before being converted to the session format.
    """
    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description


def main():
    parser = argparse.ArgumentParser(description="AI Task Orchestrator")
    parser.add_argument('--session', required=True, help='Path to the session JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed steps and information')

    # Mutually exclusive group for commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', action='store_true', help='Create a new session')
    group.add_argument('--resume', action='store_true', help='Resume an existing session')
    group.add_argument('--rules', action='store_true', help='Edit the rules file')
    group.add_argument('--plan', action='store_true', help='Plan subtasks for the session')

    # Add --dry-run flag, but only for --resume command
    parser.add_argument('--dry-run', action='store_true', help='Simulate running subtasks without writing files or changing statuses (for --resume only)')

    args = parser.parse_args()

    # Determine which action to take based on flags
    if args.new:
        handle_new_session(args.session, args.verbose)
    elif args.resume:
        handle_resume_session(args.session, args.verbose, args.dry_run)
    elif args.rules:
        handle_rules_file(args.session, args.verbose)
    elif args.plan:
        handle_plan_session(args.session, args.verbose)


def handle_new_session(session_path, verbose=False):
    """Handle creating a new session."""
    if verbose:
        print(f"[VERBOSE] Creating new session at: {session_path}")

    # Check if session file already exists
    if os.path.exists(session_path):
        print(f"Error: Session file '{session_path}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Determine the directory of the session file
    session_dir = os.path.dirname(os.path.abspath(session_path)) or '.'

    # Determine if there's a corresponding rules file in the same directory
    rules_filename = os.path.join(session_dir, "rules.txt")
    rules_path = rules_filename if os.path.exists(rules_filename) else None

    if verbose and rules_path:
        print(f"[VERBOSE] Found rules file: {rules_path}")
    elif verbose:
        print(f"[VERBOSE] No rules file found in directory: {session_dir}")

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
    if verbose:
        print(f"[VERBOSE] Session created with ID: {session.id}")


def handle_resume_session(session_path, verbose=False, dry_run=False):
    """Handle resuming an existing session."""
    if verbose and dry_run:
        print(f"[VERBOSE] DRY RUN MODE: Loading session from: {session_path}")
    elif verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Attempt to load the session, which will handle file not found and JSON errors
    try:
        session = load_session(session_path)
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

    if verbose:
        print(f"[VERBOSE] Loaded session with status: {session.status}")

    # Load rules
    rules = load_rules(session)
    if verbose:
        print(f"[VERBOSE] Loaded rules (length: {len(rules)} chars)")

    # Process pending subtasks
    pending_subtasks = [subtask for subtask in session.subtasks if subtask.status == "pending"]

    if not pending_subtasks:
        # No pending subtasks, just print current status
        if verbose:
            print("[VERBOSE] No pending subtasks to process")
        print(f"Status: {session.status}")
        print(f"Number of subtasks: {len(session.subtasks)}")
        all_done = all(subtask.status == "done" for subtask in session.subtasks)
        if all_done and session.subtasks:
            session.status = "done"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            print("Session status updated to 'done'")
        return

    # Process each pending subtask in order
    for subtask in session.subtasks:
        if subtask.status == "pending":
            if verbose:
                print(f"[VERBOSE] Processing subtask: '{subtask.title}' (ID: {subtask.id})")

            # Build the full worker prompt
            prompt = f"[ROOT TASK]\n{session.root_task}\n\n"
            prompt += f"[SUBTASK]\n{subtask.description}\n\n"
            prompt += f"[RULES]\n{rules}\n\n"
            prompt += f"[INSTRUCTIONS]\n- Perform the work for this subtask.\n"
            prompt += f"- Write a short summary of what you did to the summary file: {subtask.summary_file}."

            if verbose:
                print(f"[VERBOSE] Using worker model: {subtask.worker_model}")

            # Look up the worker engine
            from engines import get_engine
            try:
                engine = get_engine(subtask.worker_model + "_worker")
            except ValueError:
                # If we don't have the specific model with "_worker" suffix, try directly
                try:
                    engine = get_engine(subtask.worker_model)
                except ValueError:
                    print(f"Error: Unknown worker model '{subtask.worker_model}'", file=sys.stderr)
                    session.status = "failed"
                    session.updated_at = datetime.now().isoformat()
                    save_session(session, session_path)
                    sys.exit(1)

            if verbose:
                print(f"[VERBOSE] Generated prompt for engine (length: {len(prompt)} chars)")

            # Call engine.generate(prompt) - this is still simulated
            try:
                output = engine.generate(prompt)
            except Exception as e:
                print(f"Error: Failed to generate output from engine: {str(e)}", file=sys.stderr)
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
                sys.exit(1)

            if verbose:
                print(f"[VERBOSE] Generated output from engine (length: {len(output)} chars)")

            # Create output directory based on session file location
            session_dir = os.path.dirname(os.path.abspath(session_path))
            outputs_dir = os.path.join(session_dir, "outputs")

            if not dry_run:
                os.makedirs(outputs_dir, exist_ok=True)

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


def handle_rules_file(session_path, verbose=False):
    """Handle opening the rules file in an editor."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

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


def plan_subtasks(root_task: str, rules: str) -> list:
    """
    Plan subtasks based on the root task and rules.
    For now, this is a fake planner that creates 3 hard-coded subtasks.

    Args:
        root_task: The main task to be broken down
        rules: Rules to consider when planning

    Returns:
        List of PlannedSubtask objects
    """
    # Simple heuristics to generate subtasks
    subtasks = [
        PlannedSubtask(
            title="Analysis and Research",
            description=f"Analyze the requirements of the task: '{root_task}'. Research best practices and gather necessary information."
        ),
        PlannedSubtask(
            title="Implementation",
            description=f"Implement the solution for: '{root_task}' following the architecture and requirements identified in the analysis phase."
        ),
        PlannedSubtask(
            title="Testing and Integration",
            description=f"Test the implemented solution for '{root_task}', ensure it meets all requirements and integrate it properly."
        )
    ]

    return subtasks


def handle_plan_session(session_path, verbose=False):
    """Handle planning subtasks for the session."""
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
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
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        # Try to update the session status to failed if possible
        try:
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
        except:
            pass
        sys.exit(1)

    # Ensure root_task is set
    if not session.root_task or session.root_task.strip() == "":
        print("Error: Session root_task is not set.", file=sys.stderr)
        # Update session status to failed
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Load rules
    rules = load_rules(session)
    if verbose:
        print(f"[VERBOSE] Loaded rules (length: {len(rules)} chars)")

    # Check if there are existing subtasks to determine the planning phase
    if not session.subtasks:
        # Initial planning phase: no existing subtasks
        if verbose:
            print("[VERBOSE] Starting initial planning phase...")
        print("Starting initial planning phase...")
        planned_subtasks = plan_subtasks(session.root_task, rules)
    else:
        # Refinement phase: process existing subtasks and plan new ones based on summaries
        if verbose:
            print("[VERBOSE] Starting refinement planning phase using worker summaries...")
        print("Starting refinement planning phase using worker summaries...")

        # Collect existing subtask summaries
        summaries = collect_worker_summaries(session, session_path)
        if verbose:
            print(f"[VERBOSE] Collected summaries (length: {len(summaries)} chars)")

        # Build the planner prompt with summaries, rules, and current plan
        planner_prompt = build_planner_prompt(session.root_task, summaries, rules, session.subtasks)
        if verbose:
            print(f"[VERBOSE] Built planner prompt (length: {len(planner_prompt)} chars)")

        # Get the planner engine (use codex_planner for now)
        from engines import get_engine
        try:
            planner_engine = get_engine("codex_planner")  # or "claude_planner"
            if verbose:
                print(f"[VERBOSE] Using planner engine: {planner_engine.name}")
        except ValueError:
            print(f"Error: Unknown planner model 'codex_planner'", file=sys.stderr)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

        # Call the planner engine to get updated plan
        try:
            planner_output = planner_engine.generate(planner_prompt)
        except Exception as e:
            print(f"Error: Failed to generate plan from planner engine: {str(e)}", file=sys.stderr)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

        if verbose:
            print(f"[VERBOSE] Received planner output (length: {len(planner_output)} chars)")

        print(f"Planner output:\n{planner_output}\n")

        # For now, parse the planner output in a trivial way (re-use existing plan)
        # This will be enhanced in future implementation
        planned_subtasks = plan_subtasks(session.root_task, rules)

    # Show the plan to the user
    if verbose:
        print("[VERBOSE] Showing proposed subtask breakdown to user")
    print("Proposed subtask breakdown:")
    for i, subtask in enumerate(planned_subtasks, 1):
        print(f"{i}. {subtask.title}")
        print(f"   {subtask.description}")

    # Ask for confirmation
    response = input("Is this subtask breakdown OK? [Y/n]: ").strip().lower()

    if response in ['', 'y', 'yes']:
        # User accepted the plan
        if verbose:
            print("[VERBOSE] User accepted the plan")
        # Convert PlannedSubtask objects to Subtask objects
        new_subtasks = []
        worker_models = ["qwen", "gemini"]  # Alternate between these models
        for i, planned_task in enumerate(planned_subtasks):
            subtask = Subtask(
                id=str(uuid.uuid4()),
                title=planned_task.title,
                description=planned_task.description,
                planner_model="codex",  # Hard-coded for now
                worker_model=worker_models[i % len(worker_models)],  # Alternate between models
                status="pending",  # New subtasks start as pending
                summary_file=""  # Will be set later when worker processes the task
            )
            new_subtasks.append(subtask)

        # Update the session with the new subtasks
        session.subtasks = new_subtasks

        # Update status based on the phase
        if not session.status or session.status == "new":
            session.status = "planned"
        elif session.status in ["done", "in_progress"]:
            session.status = "planned"  # Replanning updates back to planned

        session.updated_at = datetime.now().isoformat()  # Update timestamp

        # Save the updated session
        save_session(session, session_path)
        if verbose:
            print(f"[VERBOSE] Session saved with status: {session.status}")
        print("Plan accepted and saved to session.")
    else:
        # User rejected the plan
        if verbose:
            print("[VERBOSE] User rejected the plan")
        print("Please explain how to improve the plan (press Enter on an empty line to finish):")
        # Read multi-line feedback until user presses Enter on an empty line
        feedback_lines = []
        line = input()
        while line != "":
            feedback_lines.append(line)
            line = input()

        feedback = "\n".join(feedback_lines)

        # For now, just print that the plan was rejected
        # In a real implementation, we would store this feedback in the session
        print("Plan rejected; please re-run --plan when ready")


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
    session_dir = os.path.dirname(os.path.abspath(session_path))
    outputs_dir = os.path.join(session_dir, "outputs")

    for subtask in session.subtasks:
        # First check if the explicit summary_file exists
        if subtask.summary_file and os.path.exists(subtask.summary_file):
            try:
                with open(subtask.summary_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        summaries.append(f"--- Summary for '{subtask.title}' (Status: {subtask.status}) ---\n{content}")
            except Exception:
                # If there's an error reading a summary file, continue with other files
                pass
        # If not, check for the output file generated by the worker in the outputs directory
        else:
            output_file_path = os.path.join(outputs_dir, f"{subtask.id}.txt")
            if os.path.exists(output_file_path):
                try:
                    with open(output_file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # Extract the actual output from the simulation format
                            # The content looks like "[MODEL SIMULATION]\n[ROOT TASK]..."
                            # We want to get just the part after the simulation header
                            lines = content.split('\n')
                            if len(lines) > 1:
                                # Skip the first line which is the simulation header
                                actual_content = '\n'.join(lines[1:]).strip()
                                summaries.append(f"--- Summary for '{subtask.title}' (Status: {subtask.status}) ---\n{actual_content}")
                except Exception:
                    # If there's an error reading an output file, continue with other files
                    pass

    return "\n\n".join(summaries)


def build_planner_prompt(root_task: str, summaries: str, rules: str, subtasks: list) -> str:
    """
    Build the planner prompt with all required sections.

    Args:
        root_task: The main task
        summaries: Concatenated worker summaries
        rules: Current rules
        subtasks: Current list of subtasks

    Returns:
        The complete planner prompt string
    """
    # Build current plan string with subtasks and statuses
    current_plan_parts = []
    for i, subtask in enumerate(subtasks, 1):
        current_plan_parts.append(f"{i}. {subtask.title} [{subtask.status}]")
        current_plan_parts.append(f"   {subtask.description}")
    current_plan = "\n".join(current_plan_parts)

    prompt = f"[ROOT TASK]\n{root_task}\n\n"
    prompt += f"[CURRENT SUMMARIES FROM WORKERS]\n{summaries}\n\n" if summaries else "[CURRENT SUMMARIES FROM WORKERS]\nNo summaries available.\n\n"
    prompt += f"[CURRENT RULES]\n{rules}\n\n"
    prompt += f"[CURRENT PLAN]\n{current_plan}\n\n"
    prompt += f"[INSTRUCTIONS]\n- Propose an updated plan.\n- You may add new subtasks if necessary.\n- Keep the number of subtasks manageable."

    return prompt


if __name__ == "__main__":
    main()