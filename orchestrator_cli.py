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
from session_model import Session, Subtask, PlanNode, load_session, save_session
from engines import EngineError


class PlannerError(Exception):
    """Custom exception for planner errors."""
    pass


# Legacy hard-coded subtask titles for safety checking
LEGACY_TITLES = {
    "Analysis and Research",
    "Implementation",
    "Testing and Integration",
}


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


def run_planner(session: Session, session_path: str, rules_text: str, summaries_text: str, planner_preference: list[str], verbose: bool = False, clean_task: bool = True) -> dict:
    """
    Build the planner prompt, call the planner engine, and parse JSON.
    IMPORTANT: All planning must use the JSON-based planner. Hard-coded plans are FORBIDDEN.
    Legacy planning approaches are not allowed - only JSON-based planning is permitted.

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

    # Use the clean root task for the planner prompt if available, otherwise fall back to raw
    root_task_to_use = session.root_task_clean or session.root_task_raw or session.root_task
    categories_str = ", ".join(session.root_task_categories) if session.root_task_categories else "No specific categories"

    prompt = f"[ROOT TASK]\n{root_task_to_use}\n\n"
    prompt += f"[ROOT TASK SUMMARY]\n{session.root_task_summary or '(no summary available)'}\n\n"
    prompt += f"[ROOT TASK CATEGORIES]\n{categories_str}\n\n"
    prompt += f"[RULES]\n{rules_text}\n\n"
    prompt += f"[SUMMARIES]\n{summaries_text}\n\n"
    prompt += f"[CURRENT_PLAN]\n{current_plan}\n\n"
    prompt += f"[INSTRUCTIONS]\n"
    prompt += f"You are a planning AI. Propose an updated subtask plan in JSON format.\n"
    prompt += f"- Return a JSON object with a 'subtasks' field containing an array of subtask objects.\n"
    prompt += f"- Include 'root' field with 'raw_summary', 'clean_text', and 'categories'.\n"
    prompt += f"- Each subtask object should have 'title', 'description', 'categories', and 'root_excerpt' fields.\n"
    prompt += f"- Use the cleaned root task and categories to guide subtask creation.\n"
    prompt += f"- Consider previous subtask summaries when planning new tasks.\n"
    prompt += f"- The root.clean_text should be a cleaned-up, well-structured description.\n"
    prompt += f"- The root.raw_summary should be 1-3 sentences summarizing the intent.\n"
    prompt += f"- The root.categories should be high-level categories from the root task.\n"
    prompt += f"- For each subtask, select which categories apply and provide an optional root_excerpt.\n"
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

        # Call engine.generate(prompt) with interruption handling
        try:
            stdout = engine.generate(prompt)
        except KeyboardInterrupt:
            # For planner interruptions, don't modify the session
            print(f"\n[orchestrator] Planner interrupted by user", file=sys.stderr)
            # Save partial output for debugging, but don't modify session
            partial_dir = os.path.join(session_dir, "partials")
            os.makedirs(partial_dir, exist_ok=True)
            partial_filename = os.path.join(partial_dir, f"planner_{engine_name}_{int(time.time())}.partial.txt")
            with open(partial_filename, 'w', encoding='utf-8') as f:
                f.write(stdout if stdout else "")
            if verbose:
                print(f"[VERBOSE] Partial planner output saved to: {partial_filename}")

            # Re-raise to allow main thread to handle properly
            raise KeyboardInterrupt
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
    parser = argparse.ArgumentParser(
        description="AI Task Orchestrator - Manage AI task sessions",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-s', '--session', required=True,
                       help='Path to session JSON file')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed debug, engine commands, and file paths')

    # Mutually exclusive group for commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--new', action='store_true',
                      help='Create a new session and read root task from stdin')
    group.add_argument('-r', '--resume', action='store_true',
                      help='Resume processing subtasks')
    group.add_argument('-R', '--rules', action='store_true',
                      help='Edit the session\'s rules file in $EDITOR')
    group.add_argument('-p', '--plan', action='store_true',
                      help='Run planner and update subtask plan')

    # Add new modes for planning
    group.add_argument('--one-shot-plan', action='store_true',
                      help='Run single planner call that rewrites root task and returns finalized JSON plan')
    group.add_argument('--discuss-plan', action='store_true',
                      help='Enter interactive planning mode for back-and-forth discussion')

    # Add --refine-root flag for cleaning up and categorizing the root task (as part of the group)
    group.add_argument('--refine-root', action='store_true',
                      help='Clean up and categorize the root task before planning')

    # Add flags for plan tree management
    parser.add_argument('--show-plan-tree', action='store_true',
                       help='Print the entire plan tree with ASCII art')
    parser.add_argument('--focus-plan', type=str,
                       help='Set active plan ID to switch focus')

    # Add --dry-run flag, but only for --resume command
    parser.add_argument('-d', '--dry-run', action='store_true',
                       help='Simulate execution without modifying files')

    # Add new streaming and prompt printing flags
    parser.add_argument('-o', '--stream-ai-output', action='store_true',
                       help='Stream model stdout live to the terminal')
    parser.add_argument('-P', '--print-ai-prompts', action='store_true',
                       help='Print constructed prompts before running them')

    # Add --root-task argument for loading from file
    parser.add_argument('-t', '--root-task',
                       help='Inline root task instead of reading stdin')

    # Add --planner-order argument for specifying planner preference order
    parser.add_argument('-O', '--planner-order',
                       help='Comma-separated order: codex,claude',
                       default="codex,claude")

    # Add --force-replan flag for clearing existing subtasks and running JSON planner from scratch
    parser.add_argument('-f', '--force-replan', action='store_true',
                       help='Ignore existing subtasks and force new planning')

    # Add --retry-interrupted flag for resuming interrupted subtasks
    parser.add_argument('--retry-interrupted', action='store_true',
                       help='Automatically resume interrupted subtasks using partial output')

    args = parser.parse_args()

    # Determine which action to take based on flags
    if args.new:
        handle_new_session(args.session, args.verbose, root_task_file=args.root_task)
    elif args.resume:
        handle_resume_session(args.session, args.verbose, args.dry_run, args.stream_ai_output, args.print_ai_prompts, retry_interrupted=args.retry_interrupted)
    elif args.rules:
        handle_rules_file(args.session, args.verbose)
    elif args.plan or args.one_shot_plan or args.discuss_plan:
        # Handle different planning modes
        if args.discuss_plan:
            handle_interactive_plan_session(args.session, args.verbose, args.stream_ai_output, args.print_ai_prompts, args.planner_order, force_replan=args.force_replan)
        else:
            # If --one-shot-plan is set, or --plan with no explicit mode, use one-shot planning
            # For --plan case, ask user which mode to use
            if args.plan and not args.one_shot_plan:
                response = input("Do you want to discuss the plan with the planner AI first? [Y/n]: ").strip().lower()
                if response in ['', 'y', 'yes']:
                    handle_interactive_plan_session(args.session, args.verbose, args.stream_ai_output, args.print_ai_prompts, args.planner_order, force_replan=args.force_replan)
                else:
                    # Ask whether to rewrite/clean the root task
                    response = input("Do you want the planner to rewrite/clean the root task before planning? [Y/n]: ").strip().lower()
                    clean_task = response in ['', 'y', 'yes']
                    handle_plan_session(args.session, args.verbose, args.stream_ai_output, args.print_ai_prompts, args.planner_order, force_replan=args.force_replan, clean_task=clean_task)
            else:
                # Use one-shot planning
                clean_task = True if args.one_shot_plan else False
                handle_plan_session(args.session, args.verbose, args.stream_ai_output, args.print_ai_prompts, args.planner_order, force_replan=args.force_replan, clean_task=clean_task)
    elif args.show_plan_tree:
        handle_show_plan_tree(args.session, args.verbose)
    elif args.focus_plan:
        handle_focus_plan(args.session, args.focus_plan, args.verbose)
    elif args.refine_root:
        handle_refine_root(args.session, args.verbose, args.planner_order)
    else:
        print("No valid command specified", file=sys.stderr)
        sys.exit(1)


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


def handle_resume_session(session_path, verbose=False, dry_run=False, stream_ai_output=False, print_ai_prompts=False, retry_interrupted=False):
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
    session_dir = os.path.dirname(os.path.abspath(session_path))
    inputs_dir = os.path.join(session_dir, "inputs")
    outputs_dir = os.path.join(session_dir, "outputs")
    os.makedirs(inputs_dir, exist_ok=True)
    if not dry_run:
        os.makedirs(outputs_dir, exist_ok=True)

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
            partial_dir = os.path.join(session_dir, "partials")
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

            prompt = f"[ROOT TASK (CLEANED)]\n{root_task_to_use}\n\n"
            prompt += f"[RELEVANT CATEGORIES]\n{categories_str}\n\n"
            prompt += f"[RELEVANT ROOT EXCERPT]\n{root_excerpt}\n\n"

            # Include partial result if available
            if partial_output:
                prompt += f"[PARTIAL RESULT FROM PREVIOUS ATTEMPT]\n{partial_output}\n\n"
                prompt += f"[CURRENT INSTRUCTIONS]\n"
                prompt += f"You must continue the work from the partial output above.\n"
                prompt += f"Do not repeat already completed steps.\n\n"
            else:
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

                # Save partial output if available
                partial_dir = os.path.join(session_dir, "partials")
                os.makedirs(partial_dir, exist_ok=True)
                partial_filename = os.path.join(partial_dir, f"worker_{subtask.id}.partial.txt")

                with open(partial_filename, 'w', encoding='utf-8') as f:
                    f.write(output if output else "")

                if verbose:
                    print(f"[VERBOSE] Partial stdout saved to: {partial_filename}")
                    print(f"[VERBOSE] Subtask {subtask.id} marked as interrupted")

                # Exit with clean code for interruption
                sys.exit(130)
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

    # MIGRATION CHECK: For --plan, if there are only legacy tasks, warn and recommend re-planning
    if has_legacy_plan(session.subtasks) and len(session.subtasks) == 3:
        print(f"Warning: Session contains legacy hard-coded plan with tasks: {list(LEGACY_TITLES)}", file=sys.stderr)
        print("The legacy plan will be replaced with a new JSON-based plan.", file=sys.stderr)
        if verbose:
            print("[VERBOSE] Legacy plan detected during planning; will replace with new JSON plan")

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    # FORCE REPLAN: If --force-replan is specified, clear all existing subtasks
    if force_replan:
        if verbose:
            print(f"[VERBOSE] Force re-plan flag detected: clearing {len(session.subtasks)} existing subtasks")
        session.subtasks.clear()  # Clear all existing subtasks
        print("Cleared existing subtasks. Running fresh planning from scratch.", file=sys.stderr)

    # Ensure root_task is set
    if not session.root_task or session.root_task.strip() == "":
        print("Error: Session root_task is not set.", file=sys.stderr)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Load rules
    rules = load_rules(session)
    if verbose:
        print(f"[VERBOSE] Loaded rules (length: {len(rules)} chars)")

    # Initialize conversation
    planner_conversation = [
        {"role": "system", "content": f"You are a planning AI. The user will discuss the plan with you and then finalize it. The main goal is: {session.root_task}"},
        {"role": "user", "content": f"Root task: {session.root_task}\n\nRules: {rules}\n\nCurrent plan: {len(session.subtasks)} existing subtasks"}
    ]

    print("[planner] Ready to discuss the plan for this session.")
    print("Type your message and press Enter. Use /done when you want to generate the plan.")

    # Create conversations directory
    session_dir = os.path.dirname(os.path.abspath(session_path))
    conversations_dir = os.path.join(session_dir, "conversations")
    os.makedirs(conversations_dir, exist_ok=True)

    while True:
        user_input = input("> ").strip()

        if user_input == "/done" or user_input == "/plan":
            break

        if user_input == "/quit" or user_input == "/exit":
            print("Exiting without generating plan.")
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

            json_plan = run_planner_with_prompt(conversation_prompt, planner_preference, session_path, verbose)
            assistant_response = json.dumps(json_plan) if isinstance(json_plan, dict) else str(json_plan)

            print(f"[planner]: {assistant_response}")

            # Append assistant's response to conversation
            planner_conversation.append({"role": "assistant", "content": assistant_response})

        except KeyboardInterrupt:
            print("\n[orchestrator] Conversation interrupted by user", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            print(f"Error in conversation: {e}", file=sys.stderr)
            continue

    # Final: Generate the actual plan
    final_conversation_prompt = "The planning conversation is complete. Please generate the final JSON plan based on the discussion:\n\n"
    for msg in planner_conversation:
        final_conversation_prompt += f"{msg['role'].upper()}: {msg['content']}\n\n"

    final_conversation_prompt += "Return ONLY the JSON plan with 'subtasks' array and 'root' object with 'clean_text', 'raw_summary', and 'categories', and no other text."

    planner_preference = planner_order.split(",") if planner_order else ["codex", "claude"]
    planner_preference = [item.strip() for item in planner_preference if item.strip()]

    try:
        final_json_plan = run_planner_with_prompt(final_conversation_prompt, planner_preference, session_path, verbose)

        # Show the plan to the user
        print("Final plan generated:")
        if "subtasks" in final_json_plan:
            for i, subtask_data in enumerate(final_json_plan["subtasks"], 1):
                title = subtask_data.get("title", "Untitled")
                description = subtask_data.get("description", "")
                print(f"{i}. {title}")
                print(f"   {description}")

        # Save the conversation transcript
        plan_id = str(uuid.uuid4())
        conversation_filename = os.path.join(conversations_dir, f"planner_conversation_{plan_id}.txt")
        with open(conversation_filename, "w", encoding="utf-8") as f:
            f.write(f"Planning conversation for plan {plan_id}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n\n")
            for msg in planner_conversation:
                f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")

        print(f"Conversation saved to: {conversation_filename}")

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

        print("Plan accepted and saved to session.")

    except Exception as e:
        print(f"Error generating final plan: {e}", file=sys.stderr)
        sys.exit(1)


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
            root_task_snapshot=session.root_task_raw,
            root_clean_snapshot=session.root_task_clean,
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
        root_task_snapshot=session.root_task_raw if hasattr(session, 'root_task_raw') else session.root_task,
        root_clean_snapshot=session.root_task_clean,
        categories_snapshot=session.root_task_categories,
        subtask_ids=[]  # Will be populated when subtasks are created
    )
    session.plans.append(new_plan)
    session.active_plan_id = new_plan_id
    return new_plan


def handle_show_plan_tree(session_path, verbose=False):
    """
    Print the entire plan tree with ASCII art representation.
    """
    try:
        session = load_session(session_path)
    except FileNotFoundError:
        print(f"Error: Session file '{session_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not load session from '{session_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    if not session.plans:
        print("No plans in session yet.")
        return

    # Build a tree structure from the plan nodes
    plan_tree = {}
    root_plans = []

    for plan in session.plans:
        if plan.parent_plan_id is None:
            root_plans.append(plan)
        else:
            if plan.parent_plan_id not in plan_tree:
                plan_tree[plan.parent_plan_id] = []
            plan_tree[plan.parent_plan_id].append(plan)

    def print_tree_node(plan, level=0, prefix=""):
        """Recursively print the plan tree."""
        # Determine if this plan is active
        is_active = (session.active_plan_id == plan.plan_id)
        is_dead = (plan.status == "dead")

        # Count subtasks that belong to this plan
        subtasks_for_plan = [st for st in session.subtasks if st.plan_id == plan.plan_id]
        done_count = len([st for st in subtasks_for_plan if st.status == "done"])
        total_count = len(subtasks_for_plan)

        status_str = f" ({done_count}/{total_count} subtasks done)" if subtasks_for_plan else ""

        # Print the plan with appropriate indicators
        indent = "  " * level
        marker = "[*]" if is_active else ("[x]" if is_dead else "[ ]")
        status_symbol = "(dead)" if is_dead else ""
        print(f"{indent}{prefix}{marker} Plan {plan.plan_id} ({plan.label}) {status_symbol}{status_str}")

        # Print children
        children = plan_tree.get(plan.plan_id, [])
        for i, child_plan in enumerate(children):
            new_prefix = "├─ " if i < len(children) - 1 else "└─ "
            print_tree_node(child_plan, level + 1, new_prefix)

    # Print the tree starting from root plans
    for i, plan in enumerate(root_plans):
        prefix = "├─ " if i < len(root_plans) - 1 else "└─ "
        print_tree_node(plan, 0, prefix if len(root_plans) > 1 else "")


def handle_focus_plan(session_path, plan_id, verbose=False):
    """
    Set the active plan ID to switch focus.
    """
    try:
        session = load_session(session_path)
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
        print(f"This plan branch has {len(new_plan_subtasks)} subtasks that may need to be re-run or ignored.")
        response = input(f"Are you sure you want to switch focus to PLAN_ID={plan_id}? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Plan focus switch cancelled.")
            return

    # Set the new active plan
    session.active_plan_id = plan_id
    save_session(session, session_path)
    print(f"Plan focus switched to: {plan_id}")



def handle_plan_session(session_path, verbose=False, stream_ai_output=False, print_ai_prompts=False, planner_order="codex,claude", force_replan=False, clean_task=True):
    """
    Handle planning subtasks for the session.
    LEGACY PLANNER BANNED: This function must only use JSON-based planning.
    Hard-coded plans are forbidden - only JSON-based planning is allowed.
    """
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

    # MIGRATION CHECK: For --plan, if there are only legacy tasks, warn and recommend re-planning
    if has_legacy_plan(session.subtasks) and len(session.subtasks) == 3:
        print(f"Warning: Session contains legacy hard-coded plan with tasks: {list(LEGACY_TITLES)}", file=sys.stderr)
        print("The legacy plan will be replaced with a new JSON-based plan.", file=sys.stderr)
        if verbose:
            print("[VERBOSE] Legacy plan detected during planning; will replace with new JSON plan")

    # MIGRATION: Ensure plan tree structure exists for backward compatibility
    migrate_session_if_needed(session)

    # FORCE REPLAN: If --force-replan is specified, clear all existing subtasks
    if force_replan:
        if verbose:
            print(f"[VERBOSE] Force re-plan flag detected: clearing {len(session.subtasks)} existing subtasks")
        session.subtasks.clear()  # Clear all existing subtasks
        print("Cleared existing subtasks. Running fresh planning from scratch.", file=sys.stderr)

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

            # Safety check: ensure legacy hard-coded subtasks are not present
            assert_no_legacy_subtasks(planned_subtasks)
        except KeyboardInterrupt:
            # For planner interruptions, don't modify the session at all
            print("\n[orchestrator] Planner interrupted by user - session unchanged", file=sys.stderr)
            if verbose:
                print("[VERBOSE] Planner interrupted, exiting cleanly")
            sys.exit(130)  # Standard exit code for Ctrl+C
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
            print(f"[VERBOSE] Collected summaries (length: {len(summaries)} chars)")

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
            print("\n[orchestrator] Planner interrupted by user - session unchanged", file=sys.stderr)
            if verbose:
                print("[VERBOSE] Planner interrupted, exiting cleanly")
            sys.exit(130)  # Standard exit code for Ctrl+C
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

        # If this is the first plan for the session, create an initial PlanNode
        if not session.plans:
            create_initial_plan_node(session)
        # Otherwise, for plan branches, we'd normally create a new branch, but for the default case
        # we update the existing active plan's subtask IDs
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


def handle_refine_root(session_path, verbose=False, planner_order="codex,claude"):
    """
    Handle root task refinement: clean up, summarize, and categorize the raw root task.
    Updates the session with root_task_raw, root_task_clean, root_task_summary, and root_task_categories.
    """
    if verbose:
        print(f"[VERBOSE] Loading session from: {session_path}")

    # Load the session
    try:
        session = load_session(session_path)
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
        print("Error: Session root_task is not set.", file=sys.stderr)
        session.status = "failed"
        session.updated_at = datetime.now().isoformat()
        save_session(session, session_path)
        sys.exit(1)

    # Prepare the planner prompt for root refinement
    root_task_raw = session.root_task
    prompt = create_root_refinement_prompt(root_task_raw)

    # Create inputs directory if it doesn't exist
    session_dir = os.path.dirname(os.path.abspath(session_path))
    inputs_dir = os.path.join(session_dir, "inputs")
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
    return f"""You are an expert editor and project architect.
Your task is ONLY to rewrite, summarize, and categorize the user's original project description.

<ROOT_TASK_RAW>
{root_task_raw}
</ROOT_TASK_RAW>

Please produce:
1. "clean_text" — a clear, structured, well-written restatement.
2. "raw_summary" — 1–3 sentences summarizing the intent.
3. "categories" — a list of high-level conceptual categories, such as:
   architecture, backend, frontend, api, deployment, research, ui/ux, testing, refactoring, docs, etc.

Respond ONLY with valid JSON in the following format:

{{
  "version": 1,
  "clean_text": "...",
  "raw_summary": "...",
  "categories": []
}}"""


if __name__ == "__main__":
    main()