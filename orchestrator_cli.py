#!/usr/bin/env python3
"""
Orchestrator CLI - A command-line interface for managing AI task sessions.
"""
import argparse
import sys
import os
import subprocess
import uuid
import json
import time
from datetime import datetime

# Import the session model and engines from the same directory
from session_model import Session, Subtask, load_session, save_session
from engines import EngineError


class PlannerError(Exception):
    """Custom exception for planner errors."""
    pass


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
            print(f"Editor exited with code {result.returncode}. Using empty root task.", file=sys.stderr)
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
        print(f"Editor '{editor}' not found. Falling back to stdin input.", file=sys.stderr)
        print("Enter the root task:", end=" ", flush=True)
        return sys.stdin.readline().strip()
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def log_verbose(verbose, message: str):
    """Simple logging helper for verbose mode."""
    if verbose:
        print(f"[orchestrator] {message}")


def run_planner(session: Session, session_path: str, rules_text: str, summaries_text: str, planner_preference: list[str], verbose: bool = False) -> dict:
    """
    Build the planner prompt, call the planner engine, and parse JSON.

    planner_preference is a list like ["codex", "claude"].
    Returns the parsed JSON object.
    Raises on failure.
    """
    # Build the planner prompt using the template
    # <ROOT_TASK> = session.root_task
    # <RULES> = rules_text
    # <SUMMARIES> = concatenation of worker summaries (or a note "no summaries yet")
    # <CURRENT_PLAN> = human-readable list of subtasks and statuses from session.subtasks

    # Build current plan string with subtasks and statuses
    current_plan_parts = []
    for i, subtask in enumerate(session.subtasks, 1):
        current_plan_parts.append(f"{i}. {subtask.title} [{subtask.status}]")
        current_plan_parts.append(f"   {subtask.description}")
    current_plan = "\n".join(current_plan_parts) if session.subtasks else "(no current plan)"

    prompt = f"[ROOT TASK]\n{session.root_task}\n\n"
    prompt += f"[RULES]\n{rules_text}\n\n"
    prompt += f"[SUMMARIES]\n{summaries_text}\n\n"
    prompt += f"[CURRENT_PLAN]\n{current_plan}\n\n"
    prompt += f"[INSTRUCTIONS]\n"
    prompt += f"You are a planning AI. Propose an updated subtask plan in JSON format.\n"
    prompt += f"- Return a JSON object with a 'subtasks' field containing an array of subtask objects.\n"
    prompt += f"- Each subtask object should have 'title' and 'description' fields.\n"
    prompt += f"- You may add new subtasks if strictly necessary.\n"
    prompt += f"- Keep the number of subtasks manageable.\n"
    prompt += f"- Only return valid JSON with no additional text or explanations outside the JSON."

    # Create inputs directory if it doesn't exist
    session_dir = os.path.dirname(os.path.abspath(session_path))
    inputs_dir = os.path.join(session_dir, "inputs")
    os.makedirs(inputs_dir, exist_ok=True)

    # Save the planner prompt to the inputs directory
    timestamp = int(time.time())
    planner_prompt_filename = os.path.join(inputs_dir, f"planner_{timestamp}.txt")
    with open(planner_prompt_filename, "w", encoding="utf-8") as f:
        f.write(prompt)

    return run_planner_with_prompt(prompt, planner_preference, session_path, verbose)


def run_planner_with_prompt(prompt: str, planner_preference: list[str], session_path: str, verbose: bool = False) -> dict:
    """
    Execute the planner with the given prompt against preferred engines.

    Args:
        prompt: The planner prompt to use
        planner_preference: List of planner engine names to try
        session_path: Path to the session file

    Returns:
        Parsed JSON object containing the plan

    Raises:
        PlannerError: If all planners fail
    """
    # Loop over planner_preference (e.g. ["codex", "claude"])
    for engine_name in planner_preference:
        # Resolve engine via get_engine()
        from engines import get_engine
        try:
            engine = get_engine(engine_name + "_planner")
        except ValueError as e:
            print(f"Warning: Engine {engine_name}_planner not found, skipping: {e}", file=sys.stderr)
            continue

        # Call engine.generate(prompt)
        try:
            stdout = engine.generate(prompt)
        except Exception as e:
            print(f"Warning: Engine {engine_name} failed: {e}", file=sys.stderr)
            continue

        # Create outputs directory if it doesn't exist
        session_dir = os.path.dirname(os.path.abspath(session_path))
        outputs_dir = os.path.join(session_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)

        # Save the raw planner stdout to outputs directory
        timestamp = int(time.time())
        output_filename = os.path.join(outputs_dir, f"planner_{engine_name}_{timestamp}.txt")
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(stdout)

        # Try json.loads(stdout)
        try:
            result = json.loads(stdout)
            # If parsing succeeds and the result contains "subtasks" list, return it
            if isinstance(result, dict) and "subtasks" in result and isinstance(result["subtasks"], list):
                return result
        except json.JSONDecodeError as e:
            # If parsing fails, log the error with first ~200 chars of output
            output_preview = stdout[:200] if len(stdout) > 200 else stdout
            print(f"Warning: Failed to parse JSON from {engine_name} planner: {e}", file=sys.stderr)
            if verbose:  # Only in verbose mode
                print(f"[VERBOSE] Planner output (first 200 chars): {output_preview}", file=sys.stderr)

            # Write the error details to a file
            error_filename = os.path.join(outputs_dir, f"planner_{engine_name}_parse_error.txt")
            with open(error_filename, "w", encoding="utf-8") as f:
                f.write(f"Engine: {engine_name}\n")
                f.write(f"Error: {e}\n")
                f.write(f"Output that failed to parse:\n")
                f.write(stdout)

            continue

    # If all planners fail, raise a custom PlannerError
    raise PlannerError("All planners failed or returned invalid JSON")


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

    # Add new streaming and prompt printing flags
    parser.add_argument('--stream-ai-output', action='store_true', help='Stream engine stdout line-by-line to orchestrator stdout')
    parser.add_argument('--print-ai-prompts', action='store_true', help='Print the prompt text before calling the engine')

    # Add --root-task argument for loading from file
    parser.add_argument('--root-task', help='Path to file containing root task text')

    # Add --planner-order argument for specifying planner preference order
    parser.add_argument('--planner-order', help='Comma-separated list of planners in preference order (e.g., "claude,codex")', default="codex,claude")

    args = parser.parse_args()

    # Determine which action to take based on flags
    if args.new:
        handle_new_session(args.session, args.verbose, root_task_file=args.root_task)
    elif args.resume:
        handle_resume_session(args.session, args.verbose, args.dry_run, args.stream_ai_output, args.print_ai_prompts)
    elif args.rules:
        handle_rules_file(args.session, args.verbose)
    elif args.plan:
        handle_plan_session(args.session, args.verbose, args.stream_ai_output, args.print_ai_prompts, args.planner_order)


def handle_new_session(session_path, verbose=False, root_task_file=None):
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

    # Get root task based on provided file or interactive editor
    if root_task_file:
        # Load from file
        try:
            with open(root_task_file, 'r', encoding='utf-8') as f:
                root_task = f.read().strip()
        except FileNotFoundError:
            print(f"Error: Root task file '{root_task_file}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Could not read root task file '{root_task_file}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Open editor for the root task
        root_task = edit_root_task_in_editor()

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


def handle_resume_session(session_path, verbose=False, dry_run=False, stream_ai_output=False, print_ai_prompts=False):
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

    # Create inputs and outputs directories for the session
    session_dir = os.path.dirname(os.path.abspath(session_path))
    inputs_dir = os.path.join(session_dir, "inputs")
    outputs_dir = os.path.join(session_dir, "outputs")
    os.makedirs(inputs_dir, exist_ok=True)
    if not dry_run:
        os.makedirs(outputs_dir, exist_ok=True)

    # Process each pending subtask in order
    for subtask in session.subtasks:
        if subtask.status == "pending":
            if verbose:
                print(f"[VERBOSE] Processing subtask: '{subtask.title}' (ID: {subtask.id})")

            # Set the summary file path if not already set
            if not subtask.summary_file:
                subtask.summary_file = os.path.join(outputs_dir, f"{subtask.id}.summary.txt")

            # Build the full worker prompt with structured format
            prompt = f"[ROOT TASK]\n{session.root_task}\n\n"
            prompt += f"[SUBTASK]\n"
            prompt += f"id: {subtask.id}\n"
            prompt += f"title: {subtask.title}\n"
            prompt += f"description:\n{subtask.description}\n\n"
            prompt += f"[RULES]\n{rules}\n\n"
            prompt += f"[INSTRUCTIONS]\n"
            prompt += f"You are an autonomous coding agent working in this repository.\n"
            prompt += f"- Perform ONLY the work needed for this subtask.\n"
            prompt += f"- Use your normal tools and workflows.\n"
            prompt += f"- When you are done, write a short plain-text summary of what you did\n"
            prompt += f"  into the file: {subtask.summary_file}\n\n"
            prompt += f"The summary MUST be written to that file before you consider the task complete."

            if verbose:
                print(f"[VERBOSE] Using worker model: {subtask.worker_model}")

            # Look up the worker engine
            from engines import get_engine
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

            # Save the worker prompt to the inputs directory
            worker_prompt_filename = os.path.join(inputs_dir, f"worker_{subtask.id}_{subtask.worker_model}.txt")
            with open(worker_prompt_filename, "w", encoding="utf-8") as f:
                f.write(prompt)

            # Print AI prompt if requested
            if print_ai_prompts:
                print("===== AI PROMPT BEGIN =====")
                print(prompt)
                print("===== AI PROMPT END =====")

            # Log verbose information
            log_verbose(verbose, f"Engine={subtask.worker_model} subtask={subtask.id}")
            log_verbose(verbose, f"Prompt file: {worker_prompt_filename}")
            log_verbose(verbose, f"Output file: {os.path.join(outputs_dir, f'{subtask.id}.txt')}")

            # Call engine.generate(prompt) - this is still simulated
            try:
                output = engine.generate(prompt)
            except EngineError as e:
                # Log stderr for engine errors
                print(f"Engine error stderr: {e.stderr}", file=sys.stderr)

                print(f"Error: Engine failed with exit code {e.exit_code}: {e.name}", file=sys.stderr)
                subtask.status = "error"
                session.status = "failed"
                session.updated_at = datetime.now().isoformat()
                save_session(session, session_path)
                sys.exit(1)
            except Exception as e:
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


def handle_plan_session(session_path, verbose=False, stream_ai_output=False, print_ai_prompts=False, planner_order="codex,claude"):
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

        # Use the new run_planner function with planner preference from CLI
        summaries = "(no summaries yet)"
        planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
        # Clean up whitespace from split
        planner_preference = [item.strip() for item in planner_preference if item.strip()]
        try:
            json_plan = run_planner(session, session_path, rules, summaries, planner_preference, verbose)
            planned_subtasks = json_to_planned_subtasks(json_plan)
        except PlannerError as e:
            print(f"Error: Planner failed: {e}", file=sys.stderr)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)
    else:
        # Refinement phase: process existing subtasks and plan new ones based on summaries
        if verbose:
            print("[VERBOSE] Starting refinement planning phase using worker summaries...")
        print("Starting refinement planning phase using worker summaries...")

        # Collect existing subtask summaries
        summaries = collect_worker_summaries(session, session_path)
        if verbose:
            print(f"[VERBOSE] Collected summaries (length: {len(summaries)} chars)")

        # Use the new run_planner function with planner preference from CLI
        planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
        # Clean up whitespace from split
        planner_preference = [item.strip() for item in planner_preference if item.strip()]
        try:
            json_plan = run_planner(session, session_path, rules, summaries, planner_preference, verbose)
            planned_subtasks = json_to_planned_subtasks(json_plan)
        except PlannerError as e:
            print(f"Error: Planner failed: {e}", file=sys.stderr)
            session.status = "failed"
            session.updated_at = datetime.now().isoformat()
            save_session(session, session_path)
            sys.exit(1)

    # Show the plan to the user
    if verbose:
        print("[VERBOSE] Showing proposed subtask breakdown to user")
    print("Proposed subtask breakdown:")
    for i, subtask_data in enumerate(json_plan.get("subtasks", []), 1):
        title = subtask_data.get("title", "Untitled")
        description = subtask_data.get("description", "")
        print(f"{i}. {title}")
        print(f"   {description}")

    # Ask for confirmation
    response = input("Is this subtask breakdown OK? [Y/n]: ").strip().lower()

    if response in ['', 'y', 'yes']:
        # User accepted the plan
        if verbose:
            print("[VERBOSE] User accepted the plan")

        # Apply the JSON plan directly to the session
        apply_json_plan_to_session(session, json_plan)

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


def apply_json_plan_to_session(session: Session, plan: dict) -> None:
    """
    Clear or update session.subtasks based on the JSON plan.
    Sets planner_model and worker_model for each subtask.
    """
    # Validate plan["subtasks"] is a list; if empty, raise error
    if "subtasks" not in plan or not isinstance(plan["subtasks"], list):
        raise ValueError("Plan must contain a 'subtasks' list")

    if len(plan["subtasks"]) == 0:
        raise ValueError("Plan 'subtasks' list cannot be empty")

    # Create new subtasks from the JSON plan
    new_subtasks = []

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
            summary_file=""  # Will be set later when worker processes the task
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
    session_dir = os.path.dirname(os.path.abspath(session_path))
    outputs_dir = os.path.join(session_dir, "outputs")

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
    prompt += f"[CURRENT RULES]\n{rules}\n\n"
    prompt += f"[CURRENT SUMMARIES FROM WORKERS]\n{summaries}\n\n"
    prompt += f"[CURRENT PLAN]\n{current_plan}\n\n"
    prompt += f"[INSTRUCTIONS]\n"
    prompt += f"You are a planning AI. Propose an updated subtask plan.\n"
    prompt += f"- You may add new subtasks if strictly necessary.\n"
    prompt += f"- Keep the number of subtasks manageable.\n"
    prompt += f"- Clearly mark each subtask with an id, title and description."

    return prompt


if __name__ == "__main__":
    main()