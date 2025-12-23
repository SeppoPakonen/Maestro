"""
Command handlers for the plan feature.
"""
from typing import Optional
import sys
import json
from pathlib import Path
from ..plans import PlanStore
from ..modules.utils import print_error, print_success, print_info, styled_print, Colors, print_header
from ..plan_explore.session import (
    create_explore_session,
    load_explore_session,
    save_explore_session,
    add_iteration_to_session,
    resume_explore_session,
    complete_explore_session,
    interrupt_explore_session,
    ExploreIteration,
    ExploreIterationStatus
)


def handle_plan_add(title: str, session_path: Optional[str] = None, verbose: bool = False):
    """Add a new plan."""
    try:
        store = PlanStore()
        plan = store.add_plan(title)
        print_success(f"Added plan: {title}", 2)
    except ValueError as e:
        print_error(str(e), 2)
        sys.exit(1)


def handle_plan_list(session_path: Optional[str] = None, verbose: bool = False):
    """List all plans as a numbered list."""
    try:
        store = PlanStore()
        plans = store.load()
        
        if not plans:
            print_info("No plans found.", 2)
            return
        
        print_header("PLANS")
        for i, plan in enumerate(plans, 1):
            item_count = len(plan.items)
            status = f" ({item_count} item{'s' if item_count != 1 else ''})"
            styled_print(f"{i:2d}. {plan.title}{status}", Colors.BRIGHT_YELLOW, None, 0)
    except Exception as e:
        print_error(f"Error loading plans: {str(e)}", 2)
        sys.exit(1)


def handle_plan_remove(title_or_number: str, session_path: Optional[str] = None, verbose: bool = False):
    """Remove a plan by title or number."""
    try:
        store = PlanStore()
        # Try to interpret as a number first
        try:
            number = int(title_or_number)
            plans = store.load()
            if 1 <= number <= len(plans):
                title = plans[number - 1].title
            else:
                print_error(f"Invalid plan number: {number}", 2)
                sys.exit(1)
        except ValueError:
            # Not a number, treat as title
            title = title_or_number
        
        success = store.remove_plan(title)
        if success:
            print_success(f"Removed plan: {title}", 2)
        else:
            print_error(f"Plan not found: {title}", 2)
            sys.exit(1)
    except Exception as e:
        print_error(f"Error removing plan: {str(e)}", 2)
        sys.exit(1)


def handle_plan_show(title_or_number: str, session_path: Optional[str] = None, verbose: bool = False):
    """Show a plan and its items as a numbered list."""
    try:
        store = PlanStore()
        plan = store.get_plan(title_or_number)
        
        if plan is None:
            print_error(f"Plan not found: {title_or_number}", 2)
            sys.exit(1)
        
        print_header(f"PLAN: {plan.title}")
        if not plan.items:
            print_info("No items in this plan.", 2)
        else:
            for i, item in enumerate(plan.items, 1):
                styled_print(f"{i:2d}. {item.text}", Colors.BRIGHT_WHITE, None, 0)
    except Exception as e:
        print_error(f"Error showing plan: {str(e)}", 2)
        sys.exit(1)


def handle_plan_add_item(title_or_number: str, item_text: str, session_path: Optional[str] = None, verbose: bool = False):
    """Add an item to a plan."""
    try:
        store = PlanStore()
        success = store.add_item_to_plan(title_or_number, item_text)
        
        if success:
            print_success(f"Added item to plan: {title_or_number}", 2)
        else:
            print_error(f"Plan not found: {title_or_number}", 2)
            sys.exit(1)
    except Exception as e:
        print_error(f"Error adding item to plan: {str(e)}", 2)
        sys.exit(1)


def handle_plan_remove_item(title_or_number: str, item_number: int, session_path: Optional[str] = None, verbose: bool = False):
    """Remove an item from a plan by its number."""
    try:
        store = PlanStore()
        success = store.remove_item_from_plan(title_or_number, item_number)

        if success:
            print_success(f"Removed item {item_number} from plan: {title_or_number}", 2)
        else:
            print_error(f"Plan not found or invalid item number: {item_number}", 2)
            sys.exit(1)
    except Exception as e:
        print_error(f"Error removing item from plan: {str(e)}", 2)
        sys.exit(1)


def handle_plan_discuss(title_or_number: str, session_path: Optional[str] = None, verbose: bool = False):
    """Start an AI discussion to edit a plan, producing a canonical PlanOpsResult JSON."""
    from ..ai.manager import AiEngineManager
    from ..plan_ops.decoder import decode_plan_ops_json, DecodeError
    from ..plan_ops.translator import actions_to_ops
    from ..plan_ops.executor import PlanOpsExecutor

    try:
        # Use session_path if provided, otherwise use default
        store = PlanStore(session_path) if session_path else PlanStore()
        plan = store.get_plan(title_or_number)

        if plan is None:
            print_error(f"Plan not found: {title_or_number}", 2)
            sys.exit(1)

        print_header(f"PLAN DISCUSSION: {plan.title}")
        if not plan.items:
            print_info("No items in this plan.", 2)
        else:
            for i, item in enumerate(plan.items, 1):
                styled_print(f"{i:2d}. {item.text}", Colors.BRIGHT_WHITE, None, 0)

        print("\nStarting AI discussion to edit this plan...")

        # Prepare the plan context for the AI
        plan_context = {
            "title": plan.title,
            "items": [{"number": i, "text": item.text} for i, item in enumerate(plan.items, 1)]
        }

        # Create the prompt for the AI using the prompt contract
        from ..plan_ops.prompt_contract import get_plan_discuss_prompt
        prompt = get_plan_discuss_prompt(plan_context['title'], plan_context['items'])

        # Use the AI manager to get the response
        manager = AiEngineManager()

        # Try to get a response from the AI with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print_info(f"Retrying AI request (attempt {attempt}/{max_retries})...", 2)
                prompt += f"\n\nPrevious response was invalid. Error: {last_error}. Please return only the valid PlanOpsResult JSON."

            try:
                # Get response from AI
                response = manager.run_completion(
                    engine="qwen",  # Using qwen as default, could be configurable
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}  # Request JSON format
                )

                # Extract the JSON from the response
                ai_response = response.choices[0].message.content.strip()

                if verbose:
                    print_info(f"AI Response: {ai_response}", 2)

                # Try to parse the response as PlanOpsResult JSON
                plan_ops_result = decode_plan_ops_json(ai_response)

                # If we get here, the JSON is valid, break out of retry loop
                break

            except DecodeError as e:
                last_error = str(e)
                if attempt == max_retries:
                    print_error(f"AI response failed validation after {max_retries} retries: {last_error}", 2)
                    sys.exit(1)
                continue
            except Exception as e:
                last_error = str(e)
                if attempt == max_retries:
                    print_error(f"Error processing AI response after {max_retries} retries: {last_error}", 2)
                    sys.exit(1)
                continue

        # Translate the PlanOpsResult to operations
        ops = actions_to_ops(plan_ops_result)

        # Create an executor and get preview
        executor = PlanOpsExecutor(store)
        preview_result = executor.preview_ops(ops)

        # Show the preview to the user
        print_header("PREVIEW OF CHANGES")
        if preview_result.changes:
            for i, change in enumerate(preview_result.changes, 1):
                styled_print(f"{i}. {change}", Colors.BRIGHT_YELLOW, None, 0)
        else:
            print_info("No changes would be made", 2)

        # Ask for user confirmation
        response = input("\nApply these changes? [y]es/[n]o: ").lower().strip()
        if response in ['y', 'yes']:
            # Apply the operations
            result = executor.apply_ops(ops, dry_run=False)
            print_success(f"Successfully applied {len([op for op in ops if not hasattr(op, '__class__') or op.__class__.__name__ != 'Commentary'])} operations", 2)
        else:
            print_info("Changes not applied.", 2)

    except Exception as e:
        print_error(f"Error during plan discussion: {str(e)}", 2)
        sys.exit(1)


def handle_plan_explore(title_or_number: str = None, session_path: Optional[str] = None, verbose: bool = False, dry_run: bool = True, apply: bool = False, max_iterations: int = 3, engine: str = "qwen", save_session: bool = False, auto_apply: bool = False, stop_after_apply: bool = False):
    """Explore plans and convert them to project operations using iterative planning."""
    import signal
    import hashlib
    from ..ai.manager import AiEngineManager
    from ..project_ops.decoder import decode_project_ops_json, DecodeError
    from ..project_ops.translator import actions_to_ops
    from ..project_ops.executor import ProjectOpsExecutor
    from ..data.markdown_parser import parse_todo_md

    # Handle Ctrl+C interruption
    def signal_handler(signum, frame):
        if 'current_session' in locals() or 'current_session' in globals():
            try:
                session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
                interrupt_explore_session(current_session, "Interrupted by user (Ctrl+C)")
                save_explore_session(current_session, session_path)
                print_info(f"\nSession {current_session.session_id} has been interrupted and saved.", 2)
                print_info(f"Resume with: maestro plan explore --session {current_session.session_id}", 2)
            except:
                print_error("Error saving interrupted session", 2)
        print_info("\nExiting on user interrupt (Ctrl+C)", 2)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Check if we're resuming an existing session
        # If session_path looks like a UUID (has dashes in the middle), treat as session ID to resume
        # Otherwise, treat as file path for PlanStore
        current_session = None
        is_session_id = session_path and len(session_path) > 10 and '-' in session_path and not session_path.endswith('.md')

        if is_session_id:  # This is the session ID to resume
            try:
                current_session = resume_explore_session(session_path)
                print_info(f"Resuming explore session: {current_session.session_id}", 2)

                # Reload plans based on session's selected plans
                store = PlanStore()  # Use default plan store
                all_plans = store.load()
                selected_plans = []
                for plan_title in current_session.selected_plans:
                    plan = store.get_plan(plan_title)
                    if plan:
                        selected_plans.append(plan)

                # Update parameters from session
                max_iterations = current_session.max_iterations
                engine = current_session.engine
            except FileNotFoundError:
                print_error(f"Explore session {session_path} not found.", 2)
                sys.exit(1)
        else:
            # Use session_path as file path for PlanStore, otherwise use default
            store = PlanStore(session_path) if session_path else PlanStore()

            # Get the specified plan or all plans
            if title_or_number:
                # Try to interpret as a number first
                try:
                    number = int(title_or_number)
                    plans = store.load()
                    if 1 <= number <= len(plans):
                        selected_plans = [plans[number - 1]]
                    else:
                        print_error(f"Invalid plan number: {number}", 2)
                        sys.exit(1)
                except ValueError:
                    # Not a number, treat as title
                    plan = store.get_plan(title_or_number)
                    if plan is None:
                        print_error(f"Plan not found: {title_or_number}", 2)
                        sys.exit(1)
                    selected_plans = [plan]
            else:
                # Explore all plans
                selected_plans = store.load()

            if not selected_plans:
                print_info("No plans found to explore.", 2)
                return

            # Create a new explore session
            plan_titles = [plan.title for plan in selected_plans]
            current_session = create_explore_session(
                selected_plans=plan_titles,
                engine=engine,
                max_iterations=max_iterations
            )

            print_info(f"Created new explore session: {current_session.session_id}", 2)

        # Print header with plan information
        if len(selected_plans) == 1:
            print_header(f"PLAN EXPLORE: {selected_plans[0].title}")
        else:
            print_header(f"PLAN EXPLORE: {len(selected_plans)} plans")

        # Print the plans being explored
        for i, plan in enumerate(selected_plans, 1):
            print(f"\nPlan {i}: {plan.title}")
            if not plan.items:
                print_info("  No items in this plan.", 2)
            else:
                for j, item in enumerate(plan.items, 1):
                    styled_print(f"  {j}. {item.text}", Colors.BRIGHT_WHITE, None, 0)

        # Create the AI manager
        manager = AiEngineManager()

        # Iterative planning loop - start from current iteration
        iteration_count = current_session.current_iteration
        while iteration_count < max_iterations:
            print_header(f"\nITERATION {iteration_count + 1}")

            # Load current project state (tracks/phases/tasks/context)
            # For now, we'll use a basic representation of the project state
            try:
                # This is a simplified way to get project state
                # In a real implementation, we'd have a proper way to get current state
                project_state = parse_todo_md("docs/todo.md") if Path("docs/todo.md").exists() else {}

                # Create a summary of current state
                current_tracks = project_state.get('tracks', [])
                tracks_summary = f"Current tracks ({len(current_tracks)}): {[track.get('title', 'Unknown') for track in current_tracks]}"
            except Exception as e:
                tracks_summary = f"Could not load project state: {str(e)}"

            # Prepare the plan context for the AI
            plans_context = []
            for plan in selected_plans:
                plan_context = {
                    "title": plan.title,
                    "items": [{"number": i, "text": item.text} for i, item in enumerate(plan.items, 1)]
                }
                plans_context.append(plan_context)

            # Create the prompt for the AI using the explore prompt contract
            prompt = create_explore_prompt(plans_context, tracks_summary)

            # Create a hash of the prompt for session tracking
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

            # Try to get a response from the AI with retry logic
            max_retries = 2
            response_valid = False
            last_error = None
            ai_response = None
            project_ops_result = None

            for attempt in range(max_retries + 1):
                if attempt > 0:
                    print_info(f"Retrying AI request (attempt {attempt}/{max_retries})...", 2)
                    if last_error:
                        prompt += f"\n\nPrevious response was invalid. Error: {last_error}. Please return only the valid ProjectOpsResult JSON."

                try:
                    from ..ai.types import PromptRef
                    from ..ai.chat import run_one_shot
                    from ..ai.runner import run_engine_command
                    from ..ai.types import RunOpts

                    # Create run options
                    opts = RunOpts(
                        dangerously_skip_permissions=False,
                        continue_latest=False,
                        resume_id=None,
                        stream_json=False,  # We want the full response
                        quiet=not verbose,   # Show output if verbose is True
                        model=None
                    )

                    # Create prompt reference
                    prompt_ref = PromptRef(source=prompt)

                    # Run the AI engine and get response
                    result = manager.run_once(engine, prompt_ref, opts)

                    # Read the response from the output file
                    if result.stdout_path:
                        with open(result.stdout_path, 'r', encoding='utf-8') as f:
                            ai_response = f.read().strip()
                    else:
                        print_error("No response from AI engine", 2)
                        continue

                    if verbose:
                        print_info(f"AI Response: {ai_response}", 2)

                    # Try to parse the response as ProjectOpsResult JSON
                    project_ops_result = decode_project_ops_json(ai_response)

                    # If we get here, the JSON is valid, break out of retry loop
                    response_valid = True
                    break

                except DecodeError as e:
                    last_error = str(e)
                    if attempt == max_retries:
                        print_error(f"AI response failed validation after {max_retries} retries: {last_error}", 2)
                        break
                    continue
                except Exception as e:
                    last_error = str(e)
                    if attempt == max_retries:
                        print_error(f"Error processing AI response after {max_retries} retries: {str(e)}", 2)
                        break
                    continue

            # Create the iteration object to track this attempt
            iteration = ExploreIteration(
                index=iteration_count,
                prompt_hash=prompt_hash,
                prompt=prompt if save_session else None,  # Only save prompt if save_session is enabled
                ai_response=ai_response,
                project_ops_json=project_ops_result if response_valid else None,
                validation_result={"valid": response_valid, "error": last_error if not response_valid else None},
                preview_summary=[],
                applied=False,
                error=None if response_valid else last_error
            )

            if not response_valid:
                print_error("Failed to get valid response from AI after retries. Stopping exploration.", 2)
                # Add iteration to session with error info
                current_session = add_iteration_to_session(current_session, iteration)
                session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
                save_explore_session(current_session, session_path)
                break

            # Translate the ProjectOpsResult to operations
            ops = actions_to_ops(project_ops_result)

            # Create an executor and get preview
            executor = ProjectOpsExecutor()
            preview_result = executor.preview_ops(ops)

            # Update iteration with preview info
            iteration.preview_summary = preview_result.changes

            # Show the preview to the user
            print_header("PREVIEW OF CHANGES")
            if preview_result.changes:
                for i, change in enumerate(preview_result.changes, 1):
                    styled_print(f"{i}. {change}", Colors.BRIGHT_YELLOW, None, 0)
            else:
                print_info("No changes would be made", 2)

                # If no changes, we can stop early
                print_info("No meaningful changes to apply. Stopping exploration.", 2)
                current_session = add_iteration_to_session(current_session, iteration)
                session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
                save_explore_session(current_session, session_path)
                break

            # Check if user wants to apply changes
            user_apply = False
            if auto_apply or apply:
                # Auto-apply if --auto-apply or --apply flag was given
                user_apply = True
                print_info("Applying changes automatically (--auto-apply flag was given)", 2)
            else:
                # Ask for user confirmation if --dry-run is not explicitly set
                if not dry_run:
                    response = input("\nApply these changes? [y]es/[n]o/[s]top: ").lower().strip()
                    if response in ['y', 'yes']:
                        user_apply = True
                    elif response in ['s', 'stop']:
                        print_info("User chose to stop exploration.", 2)
                        break
                    else:
                        print_info("Changes not applied. Continuing to next iteration.", 2)
                else:
                    print_info("Dry run mode: changes not applied.", 2)

            # Apply the operations if user approved
            if user_apply:
                result = executor.apply_ops(ops, dry_run=False)
                print_success(f"Successfully applied {len(result.changes)} operations", 2)

                # Mark iteration as applied
                iteration.applied = True

                # Reload the plans after applying changes
                if title_or_number:
                    plan = store.get_plan(title_or_number)
                    if plan is not None:
                        selected_plans = [plan]
                else:
                    selected_plans = store.load()

                # If stop_after_apply is enabled, exit after applying this iteration
                if stop_after_apply:
                    print_info("Stopping after applying one iteration (--stop-after-apply flag)", 2)
                    break
            else:
                # If user declined, continue to next iteration
                pass

            # Add iteration to session
            current_session = add_iteration_to_session(current_session, iteration)

            # Save session state after each iteration
            session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
            save_explore_session(current_session, session_path)

            iteration_count += 1

            # Check if AI returned empty actions (meaning no more ops to perform)
            if not project_ops_result.get('actions', []):
                print_info("AI returned no actions. Stopping exploration.", 2)
                break

        # Complete the session if all iterations are done
        if iteration_count >= max_iterations or current_session.status == "completed":
            current_session = complete_explore_session(current_session)
            session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
            save_explore_session(current_session, session_path)
            print_info(f"Exploration completed after {iteration_count} iterations. Session saved: {current_session.session_id}", 2)
        else:
            print_info(f"Exploration completed after {iteration_count} iterations. Session saved: {current_session.session_id}", 2)

    except Exception as e:
        print_error(f"Error during plan exploration: {str(e)}", 2)
        # If we have a session, try to save the interrupted state
        if 'current_session' in locals() and current_session:
            try:
                current_session = interrupt_explore_session(current_session, str(e))
                session_path = Path("docs") / "sessions" / "explore" / current_session.session_id / "explore_session.json"
                save_explore_session(current_session, session_path)
                print_info(f"Session {current_session.session_id} has been interrupted and saved.", 2)
                print_info(f"Resume with: maestro plan explore --session {current_session.session_id}", 2)
            except:
                pass  # If we can't save the session, just exit
        sys.exit(1)


def create_explore_prompt(plans_context, tracks_summary):
    """Create the prompt for the explore command."""
    # Format the selected plans into a string
    plans_text = ""
    for i, plan_context in enumerate(plans_context, 1):
        plans_text += f"\nPlan {i}: {plan_context['title']}\n"
        for item in plan_context['items']:
            plans_text += f"  - {item['text']}\n"

    prompt = f"""
You are a project structure assistant. Based on the following plan(s) and the current project state, propose minimal project operations to advance the project structure.

PLANS TO EXPLORE:
{plans_text}

CURRENT PROJECT STATE:
{tracks_summary}

CONSTRAINTS:
- Respond with ONLY canonical ProjectOpsResult JSON (no other text)
- Actions must be minimal and consistent
- No duplicate titles
- Must respect Track → Phase → Task model
- Must not edit docs directly; propose ops only
- If no meaningful next ops exist, return `actions: []`

Return a JSON object with this structure:
{{
  "kind": "project_ops",
  "version": 1,
  "scope": "project",
  "actions": [
    {{
      "action": "track_create",
      "title": "Track Title"
    }},
    {{
      "action": "phase_create",
      "track": "Track Title",
      "title": "Phase Title"
    }},
    {{
      "action": "task_create",
      "track": "Track Title",
      "phase": "Phase Title",
      "title": "Task Title"
    }},
    {{
      "action": "task_move_to_done",
      "track": "Track Title",
      "phase": "Phase Title",
      "task": "Task Title"
    }},
    {{
      "action": "context_set",
      "current_track": "Track Title",
      "current_phase": "Phase Title",
      "current_task": "Task Title"
    }}
  ]
}}
"""
    return prompt


def add_plan_parser(subparsers):
    """Add plan command subparsers."""
    plan_parser = subparsers.add_parser('plan', aliases=['pl'], help='Plan management')
    try:
        # Python 3.7+ supports required parameter
        plan_subparsers = plan_parser.add_subparsers(dest='plan_subcommand', help='Plan subcommands', metavar='{add,a,list,ls,remove,rm,show,sh,add-item,ai,remove-item,ri}', required=False)
    except TypeError:
        # For older Python versions, required parameter is not available
        plan_subparsers = plan_parser.add_subparsers(dest='plan_subcommand', help='Plan subcommands', metavar='{add,a,list,ls,remove,rm,show,sh,add-item,ai,remove-item,ri}')

    # Add subcommand
    add_parser = plan_subparsers.add_parser('add', aliases=['a'], help='Add a new plan')
    add_parser.add_argument('title', help='Plan title')

    # List subcommand
    list_parser = plan_subparsers.add_parser('list', aliases=['ls'], help='List all plans')

    # Remove subcommand
    remove_parser = plan_subparsers.add_parser('remove', aliases=['rm'], help='Remove a plan')
    remove_parser.add_argument('title_or_number', help='Plan title or number from list')

    # Show subcommand (for displaying a plan)
    show_parser = plan_subparsers.add_parser('show', aliases=['sh'], help='Show a plan and its items')
    show_parser.add_argument('title_or_number', help='Plan title or number from list')

    # Plan-specific subcommands (for working with plan items)
    # Add item to plan
    add_item_parser = plan_subparsers.add_parser('add-item', aliases=['ai'], help='Add an item to a plan')
    add_item_parser.add_argument('title_or_number', help='Plan title or number from list')
    add_item_parser.add_argument('item_text', help='Item text to add')

    # Remove item from plan
    remove_item_parser = plan_subparsers.add_parser('remove-item', aliases=['ri'], help='Remove an item from a plan')
    remove_item_parser.add_argument('title_or_number', help='Plan title or number from list')
    remove_item_parser.add_argument('item_number', type=int, help='Item number to remove (from plan show)')

    # Plan operations subcommand
    try:
        from ..plan_ops.commands import add_plan_ops_parser
        add_plan_ops_parser(plan_subparsers)
    except ImportError:
        # If plan_ops module is not available, skip adding the ops subcommand
        pass

    # Plan discuss subcommand
    discuss_parser = plan_subparsers.add_parser('discuss', aliases=['d'], help='Discuss and edit a plan with AI')
    discuss_parser.add_argument('title_or_number', help='Plan title or number from list')

    # Plan explore subcommand
    explore_parser = plan_subparsers.add_parser('explore', aliases=['e'], help='Explore plans and convert to project operations')
    explore_parser.add_argument('title_or_number', help='Plan title or number from list (optional, if omitted explores all plans)', nargs='?')
    explore_parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only (default true)')
    explore_parser.add_argument('--apply', action='store_true', default=False, help='Actually apply after preview confirmation')
    explore_parser.add_argument('--max-iterations', type=int, default=3, help='Maximum number of iterations (default 3)')
    explore_parser.add_argument('--engine', default='qwen', help='AI engine to use (default qwen)')
    # Work session flags
    explore_parser.add_argument('--session', help='Resume existing explore session by ID')
    explore_parser.add_argument('--save-session', action='store_true', default=False, help='Force session logging')
    explore_parser.add_argument('--auto-apply', action='store_true', default=False, help='Apply without asking each iteration (dangerous but explicit)')
    explore_parser.add_argument('--stop-after-apply', action='store_true', default=False, help='Apply one iteration then stop')

    # Add a positional argument for plan title to show (default behavior when no subcommand is provided)
    # This needs to be added after subparsers to avoid conflicts
    plan_parser.add_argument('plan_title', help='Plan title or number to show', nargs='?', metavar='PLAN_TITLE')

    return plan_parser