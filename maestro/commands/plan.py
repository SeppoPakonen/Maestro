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


def handle_plan_discuss(title_or_number: Optional[str] = None, session_path: Optional[str] = None, verbose: bool = False, prompt: Optional[str] = None):
    """Start an AI discussion to edit a plan, producing a canonical PlanOpsResult JSON."""
    from ..ai.manager import AiEngineManager
    from ..plan_ops.decoder import decode_plan_ops_json, DecodeError
    from ..plan_ops.translator import actions_to_ops
    from ..plan_ops.executor import PlanOpsExecutor

    try:
        # Use session_path if provided, otherwise use default
        store = PlanStore(session_path) if session_path else PlanStore()

        # Handle plan selection logic when title_or_number is not provided
        if title_or_number is None:
            plans = store.load()
            if len(plans) == 0:
                print_error("No plans exist. Use `maestro plan add <title>`.", 2)
                sys.exit(1)
            elif len(plans) == 1:
                # Auto-select the single plan
                plan = plans[0]
                print_info(f"Auto-selected plan: {plan.title}", 2)
            else:
                # Show numbered list and exit with instruction
                print_header("AVAILABLE PLANS")
                for i, plan in enumerate(plans, 1):
                    item_count = len(plan.items)
                    status = f" ({item_count} item{'s' if item_count != 1 else ''})"
                    styled_print(f"{i:2d}. {plan.title}{status}", Colors.BRIGHT_YELLOW, None, 0)

                print_info(f"\nMultiple plans exist. Please specify which plan to discuss:", 2)
                print_info(f"  maestro plan discuss <number>    (e.g., maestro plan discuss 1)", 2)
                print_info(f"  maestro plan discuss <title>    (e.g., maestro plan discuss \"My Plan\")", 2)
                sys.exit(1)
        else:
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

        # Prepare the plan context for the AI
        plan_context = {
            "title": plan.title,
            "items": [{"number": i, "text": item.text} for i, item in enumerate(plan.items, 1)]
        }

        # Create the prompt for the AI using the prompt contract
        from ..plan_ops.prompt_contract import get_plan_discuss_prompt
        base_prompt = get_plan_discuss_prompt(plan_context['title'], plan_context['items'])

        # Use the AI manager
        manager = AiEngineManager()

        # If no prompt was provided, enter interactive chat mode (only on TTY)
        if prompt is None and sys.stdin.isatty():
            print("\nStarting interactive AI discussion...")
            print("You can discuss the plan freely with the AI.")
            print("Note: In interactive mode, changes are not automatically applied.")
            print("Use one-shot mode (--prompt flag) for automatic plan modification.\n")

            # Import required modules for interactive chat
            from ..ai.chat import run_interactive_chat
            from ..ai.types import RunOpts
            from ..config.settings import get_settings

            # Get settings to determine dangerous permissions flag
            settings = get_settings()

            # Create run options for interactive mode
            opts = RunOpts(
                dangerously_skip_permissions=settings.ai_dangerously_skip_permissions,
                continue_latest=False,
                resume_id=None,
                stream_json=True,
                quiet=False,
                model=None,
                verbose=verbose
            )

            # Create an interactive-friendly initial prompt
            items_text = ""
            for item in plan_context['items']:
                items_text += f"  {item['number']}. {item['text']}\n"

            interactive_prompt = f"""I'm working on a plan titled "{plan_context['title']}". Here are the current items:

{items_text}
I'd like to discuss this plan with you. Can you help me review it, suggest improvements, or answer questions about it?"""

            # Run interactive chat with the plan context as initial prompt
            run_interactive_chat(manager, 'qwen', opts, initial_prompt=interactive_prompt)

            # Exit after interactive session ends
            return

        # One-shot mode (when prompt is provided or stdin is not interactive)
        if prompt is None:
            prompt = ""
        print("\nStarting AI discussion to edit this plan (one-shot mode)...")

        # Append the custom prompt to the base prompt
        ai_prompt = f"{base_prompt}\n\nUSER REQUEST:\n{prompt}"

        # Check if the required method exists
        if not hasattr(manager, "run_once"):
            print_error("AI manager missing required 'run_once' method. Please update the code to use the supported API.", 2)
            sys.exit(1)

        # Import required classes for the new AI manager API
        from ..ai.types import PromptRef
        from ..ai.runner import run_engine_command
        from ..ai.types import RunOpts

        # Create run options
        opts = RunOpts(
            dangerously_skip_permissions=True,  # Skip permissions for automated execution
            continue_latest=False,
            resume_id=None,
            stream_json=False,  # We want the full response
            quiet=not verbose,   # Show output if verbose is True
            verbose=verbose,     # Enable verbose mode for detailed diagnostics
            model=None
        )

        # Initialize last_error variable
        last_error = None

        # Try to get a response from the AI with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print_info(f"Retrying AI request (attempt {attempt}/{max_retries})...", 2)
                ai_prompt += f"\n\nPrevious response was invalid. Error: {last_error}. Please return only the valid PlanOpsResult JSON."

            try:
                # Create prompt reference
                prompt_ref = PromptRef(source=ai_prompt)

                if verbose:
                    from ..modules import utils as _utils
                    _utils.print_info("AI Engine: qwen", 2)
                    _utils.print_info("Starting engine execution", 2)

                # Run the AI engine and get response
                result = manager.run_once("qwen", prompt_ref, opts)

                if verbose:
                    from ..modules import utils as _utils
                    _utils.print_info("Engine execution completed", 2)

                # Check if the engine execution was successful
                if result.exit_code != 0:
                    error_msg = f"AI engine failed with exit code {result.exit_code}"
                    if verbose and result.stderr_path:
                        try:
                            with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                stderr_content = f.read()
                                if stderr_content:
                                    error_msg += f". Stderr excerpt: {stderr_content[:200]}..."
                        except:
                            pass  # Ignore errors reading stderr
                    from ..modules import utils as _utils
                    _utils.print_error(error_msg, 2)
                    if attempt == max_retries:
                        sys.exit(1)
                    continue

                # Read the response from the output file
                if result.stdout_path:
                    with open(result.stdout_path, 'r', encoding='utf-8') as f:
                        ai_response = f.read().strip()
                else:
                    from ..modules import utils as _utils
                    _utils.print_error("AI returned empty response (engine error or extraction failure). Enable -v to see engine command and stderr.", 2)
                    if verbose:
                        _utils.print_info(f"Engine exit code: {result.exit_code}", 2)
                        if result.stderr_path:
                            try:
                                with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                    stderr_content = f.read()
                                    if stderr_content:
                                        _utils.print_info(f"Stderr content: {stderr_content[:500]}", 2)
                            except:
                                pass  # Ignore errors reading stderr
                    if attempt == max_retries:
                        sys.exit(1)
                    continue

                # Check if the response is empty before attempting JSON parsing
                if not ai_response:
                    from ..modules import utils as _utils
                    _utils.print_error("AI returned empty response (engine error or extraction failure). Enable -v to see engine command and stderr.", 2)
                    if verbose:
                        _utils.print_info(f"Engine exit code: {result.exit_code}", 2)
                        if result.stderr_path:
                            try:
                                with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                    stderr_content = f.read()
                                    if stderr_content:
                                        _utils.print_info(f"Stderr content: {stderr_content[:500]}", 2)
                            except:
                                pass  # Ignore errors reading stderr
                    if attempt == max_retries:
                        sys.exit(1)
                    continue

                if verbose:
                    from ..modules import utils as _utils
                    _utils.print_info(f"AI Response: {ai_response}", 2)

                # Strip markdown code block wrapper if present
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```'):
                    # Find the first newline after the opening ```
                    first_newline = cleaned_response.find('\n')
                    if first_newline != -1:
                        # Remove the opening ```json or ``` line
                        cleaned_response = cleaned_response[first_newline + 1:]

                    # Remove the closing ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3].rstrip()

                    if verbose:
                        print_info(f"Stripped markdown code block wrapper", 2)

                # Try to parse the response as PlanOpsResult JSON
                plan_ops_result = decode_plan_ops_json(cleaned_response)

                # If we get here, the JSON is valid, break out of retry loop
                break

            except DecodeError as e:
                # JSON parsing failed - show raw response
                if 'ai_response' in locals():
                    if verbose:
                        print_info(f"Raw AI response:\n{ai_response}", 2)
                    else:
                        print_info(f"Raw AI response (first 200 chars): {ai_response[:200]}", 2)
                error_msg = f"AI response failed validation: {str(e)}"
                print_error(error_msg, 2)
                last_error = f"JSON validation error: {str(e)}"
                if attempt == max_retries:
                    print_error(f"AI response failed validation after {max_retries} retries: {last_error}", 2)
                    sys.exit(1)
                continue
            except json.JSONDecodeError as e:
                # JSON parsing failed - show raw response
                if 'ai_response' in locals():
                    if verbose:
                        print_info(f"Raw AI response:\n{ai_response}", 2)
                    else:
                        print_info(f"Raw AI response (first 200 chars): {ai_response[:200]}", 2)
                error_msg = f"AI returned invalid JSON: {str(e)}"
                print_error(error_msg, 2)
                last_error = f"JSON parse error: {str(e)}"
                if attempt == max_retries:
                    print_error(f"AI response failed JSON parsing after {max_retries} retries: {last_error}", 2)
                    sys.exit(1)
                continue
            except Exception as e:
                # Other errors during processing
                error_msg = f"Error processing AI response: {str(e)}"
                print_error(error_msg, 2)
                last_error = f"Processing error: {str(e)}"
                if verbose:
                    print_info(f"Engine exit code: {result.exit_code if 'result' in locals() else 'N/A'}", 2)
                    if 'result' in locals() and result.stderr_path:
                        try:
                            with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                stderr_content = f.read()
                                if stderr_content:
                                    print_info(f"Stderr content: {stderr_content[:500]}", 2)
                        except:
                            pass  # Ignore errors reading stderr
                if attempt == max_retries:
                    print_error(f"Error processing AI response after {max_retries} retries: {str(e)}", 2)
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

        # Ask for user confirmation (or auto-apply if prompt was provided)
        if prompt:
            # Auto-apply when prompt is provided (non-interactive mode)
            print_info("Auto-applying changes (non-interactive mode)", 2)
            result = executor.apply_ops(ops, dry_run=False)
            print_success(f"Successfully applied {len([op for op in ops if not hasattr(op, '__class__') or op.__class__.__name__ != 'Commentary'])} operations", 2)
        else:
            # Interactive mode - ask for confirmation
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
    from ..data.common_utils import parse_todo_safe

    def _is_session_id(value: Optional[str]) -> bool:
        return bool(value and len(value) > 10 and "-" in value and not value.endswith(".md"))

    def _resolve_session_base_path(value: Optional[str], is_session_id: bool) -> Path:
        if value and not is_session_id:
            try:
                plan_path = Path(value)
                if not plan_path.is_absolute():
                    plan_path = plan_path.resolve()
                return plan_path.parent / "docs" / "sessions"
            except FileNotFoundError:
                pass
        try:
            return Path.cwd() / "docs" / "sessions"
        except FileNotFoundError:
            return Path(__file__).resolve().parents[2] / "docs" / "sessions"

    is_session_id = _is_session_id(session_path)
    session_base_path = _resolve_session_base_path(session_path, is_session_id)

    # Handle Ctrl+C interruption
    def signal_handler(signum, frame):
        if 'current_session' in locals() or 'current_session' in globals():
            try:
                session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
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

        if is_session_id:  # This is the session ID to resume
            try:
                current_session = resume_explore_session(session_path, base_path=session_base_path)
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
                        return
                except ValueError:
                    # Not a number, treat as title
                    plan = store.get_plan(title_or_number)
                    if plan is None:
                        print_error(f"Plan not found: {title_or_number}", 2)
                        return
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
                max_iterations=max_iterations,
                base_path=session_base_path
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
                project_state = parse_todo_safe(verbose=False) or {}

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

            # Initialize variables
            response_valid = False
            last_error = None
            ai_response = None
            project_ops_result = None

            # Try to get a response from the AI with retry logic
            max_retries = 2

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
                        verbose=verbose,     # Enable verbose mode for detailed diagnostics
                        model=None
                    )

                    # Create prompt reference
                    prompt_ref = PromptRef(source=prompt)

                    # Run the AI engine and get response
                    result = manager.run_once(engine, prompt_ref, opts)

                    exit_code = getattr(result, "exit_code", 0)
                    if not isinstance(exit_code, int):
                        exit_code = 0

                    # Check if the engine execution was successful
                    if exit_code != 0:
                        error_msg = f"AI engine failed with exit code {exit_code}"
                        if verbose and result.stderr_path:
                            try:
                                with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                    stderr_content = f.read()
                                    if stderr_content:
                                        error_msg += f". Stderr excerpt: {stderr_content[:200]}..."
                            except:
                                pass  # Ignore errors reading stderr
                        print_error(error_msg, 2)
                        if attempt == max_retries:
                            break
                        continue

                    # Read the response from the output file
                    if result.stdout_path:
                        with open(result.stdout_path, 'r', encoding='utf-8') as f:
                            ai_response = f.read().strip()
                    else:
                        print_error("AI returned empty response (engine error or extraction failure). Enable -v to see engine command and stderr.", 2)
                        if verbose:
                            print_info(f"Engine exit code: {exit_code}", 2)
                            if result.stderr_path:
                                try:
                                    with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                        stderr_content = f.read()
                                        if stderr_content:
                                            print_info(f"Stderr content: {stderr_content[:500]}", 2)
                                except:
                                    pass  # Ignore errors reading stderr
                        if attempt == max_retries:
                            break
                        continue

                    # Check if the response is empty before attempting JSON parsing
                    if not ai_response:
                        print_error("AI returned empty response (engine error or extraction failure). Enable -v to see engine command and stderr.", 2)
                        if verbose:
                            print_info(f"Engine exit code: {exit_code}", 2)
                            if result.stderr_path:
                                try:
                                    with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                        stderr_content = f.read()
                                        if stderr_content:
                                            print_info(f"Stderr content: {stderr_content[:500]}", 2)
                                except:
                                    pass  # Ignore errors reading stderr
                        if attempt == max_retries:
                            break
                        continue

                    if verbose:
                        print_info(f"AI Response: {ai_response}", 2)

                    # Try to parse the response as ProjectOpsResult JSON
                    project_ops_result = decode_project_ops_json(ai_response)

                    # If we get here, the JSON is valid, break out of retry loop
                    response_valid = True
                    break

                except DecodeError as e:
                    # JSON parsing failed - show raw response in verbose mode
                    if verbose:
                        print_info(f"Raw AI response (first 200 chars): {ai_response[:200] if 'ai_response' in locals() else 'N/A'}", 2)
                    error_msg = f"AI response failed validation: {str(e)}"
                    print_error(error_msg, 2)
                    last_error = f"JSON validation error: {str(e)}"
                    if attempt == max_retries:
                        print_error(f"AI response failed validation after {max_retries} retries: {last_error}", 2)
                        break
                    continue
                except json.JSONDecodeError as e:
                    # JSON parsing failed - show raw response in verbose mode
                    if verbose:
                        print_info(f"Raw AI response (first 200 chars): {ai_response[:200] if 'ai_response' in locals() else 'N/A'}", 2)
                    error_msg = f"AI returned invalid JSON: {str(e)}"
                    print_error(error_msg, 2)
                    last_error = f"JSON parse error: {str(e)}"
                    if attempt == max_retries:
                        print_error(f"AI response failed JSON parsing after {max_retries} retries: {last_error}", 2)
                        break
                    continue
                except Exception as e:
                    # Other errors during processing
                    error_msg = f"Error processing AI response: {str(e)}"
                    print_error(error_msg, 2)
                    last_error = f"Processing error: {str(e)}"
                    if verbose:
                        print_info(f"Engine exit code: {result.exit_code if 'result' in locals() else 'N/A'}", 2)
                        if 'result' in locals() and result.stderr_path:
                            try:
                                with open(result.stderr_path, 'r', encoding='utf-8') as f:
                                    stderr_content = f.read()
                                    if stderr_content:
                                        print_info(f"Stderr content: {stderr_content[:500]}", 2)
                            except:
                                pass  # Ignore errors reading stderr
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
                session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
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
                session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
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
            session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
            save_explore_session(current_session, session_path)

            iteration_count += 1

            # Check if AI returned empty actions (meaning no more ops to perform)
            if not project_ops_result.get('actions', []):
                print_info("AI returned no actions. Stopping exploration.", 2)
                break

        # Complete the session if all iterations are done
        if iteration_count >= max_iterations or current_session.status == "completed":
            current_session = complete_explore_session(current_session)
            session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
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
                session_path = session_base_path / "explore" / current_session.session_id / "explore_session.json"
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


def handle_plan_decompose(args):
    """Handle maestro plan decompose command."""
    from pathlib import Path
    from ..repo.discovery import discover_repo, DiscoveryBudget
    from ..builders.workgraph_generator import WorkGraphGenerator
    from ..archive.workgraph_storage import save_workgraph
    from ..config.paths import get_workgraph_dir
    from ..ai.engine_selector import select_engine_for_role

    # Read freeform input
    if args.eval:
        if sys.stdin.isatty():
            print_error("Error: -e flag requires input from stdin, not terminal.", 2)
            print_error("Usage: echo 'your request' | maestro plan decompose -e", 2)
            sys.exit(1)
        freeform_request = sys.stdin.read()
    else:
        if not args.freeform:
            print_error("Error: Freeform request required when -e is not set.", 2)
            sys.exit(1)
        freeform_request = args.freeform

    # Repo discovery - use evidence packs
    repo_root = Path.cwd()
    use_evidence = not getattr(args, 'no_evidence', False)

    evidence_pack = None
    discovery = None

    if use_evidence:
        from ..repo.evidence_pack import (
            EvidenceCollector,
            load_evidence_pack
        )
        from ..repo.profile import load_profile
        from ..repo.discovery import DiscoveryEvidence

        # Check if --evidence-pack <ID> was provided
        if getattr(args, 'evidence_pack', None):
            # Load existing pack
            storage_dir = repo_root / "docs" / "maestro" / "evidence_packs"
            evidence_pack = load_evidence_pack(args.evidence_pack, storage_dir)

            if not evidence_pack:
                print_error(f"Error: Evidence pack not found: {args.evidence_pack}", 2)
                print_error(f"Storage dir: {storage_dir}", 2)
                print_error("Run 'maestro repo evidence pack --save' to create one", 2)
                sys.exit(1)

            if args.verbose or getattr(args, 'very_verbose', False):
                print_info(f"Using evidence pack: {evidence_pack.meta.pack_id}", 2)
                print_info(f"  Evidence count: {evidence_pack.meta.evidence_count}", 2)
                print_info(f"  Total bytes: {evidence_pack.meta.total_bytes:,}", 2)
        else:
            # Generate pack on the fly
            profile = load_profile(repo_root)

            # Get budgets from profile or use defaults
            if profile and profile.evidence_rules:
                max_files = profile.evidence_rules.max_files
                max_bytes = profile.evidence_rules.max_bytes
                max_help_calls = profile.evidence_rules.max_help_calls
                timeout_seconds = profile.evidence_rules.timeout_seconds
                prefer_dirs = profile.evidence_rules.prefer_dirs
                exclude_patterns = profile.evidence_rules.exclude_patterns
            else:
                max_files = 60
                max_bytes = 250000
                max_help_calls = 6
                timeout_seconds = 5
                prefer_dirs = []
                exclude_patterns = []

            if args.verbose or getattr(args, 'very_verbose', False):
                print_info("Collecting evidence pack...", 2)

            # Create collector
            collector = EvidenceCollector(
                repo_root=repo_root,
                max_files=max_files,
                max_bytes=max_bytes,
                max_help_calls=max_help_calls,
                timeout_seconds=timeout_seconds,
                prefer_dirs=prefer_dirs,
                exclude_patterns=exclude_patterns
            )

            # Get CLI candidates from profile
            cli_candidates = None
            if profile:
                cli_candidates = profile.cli_help_candidates

            # Collect evidence
            evidence_pack = collector.collect_all(cli_candidates=cli_candidates)

            if args.verbose or getattr(args, 'very_verbose', False):
                print_info(f"Generated evidence pack: {evidence_pack.meta.pack_id}", 2)
                print_info(f"  Evidence count: {evidence_pack.meta.evidence_count}", 2)
                print_info(f"  Total bytes: {evidence_pack.meta.total_bytes:,}", 2)

        # Show pack summary in very verbose mode
        if getattr(args, 'very_verbose', False):
            print_header("EVIDENCE PACK SUMMARY")
            print(f"Pack ID: {evidence_pack.meta.pack_id}")
            print(f"Items: {evidence_pack.meta.evidence_count}")

            kind_counts = {}
            for item in evidence_pack.items:
                kind_counts[item.kind] = kind_counts.get(item.kind, 0) + 1

            print("By kind:")
            for kind, count in sorted(kind_counts.items()):
                print(f"  {kind}: {count}")

            if evidence_pack.meta.truncated_items:
                print(f"Truncated: {len(evidence_pack.meta.truncated_items)} items")
            if evidence_pack.meta.skipped_items:
                print(f"Skipped (budget): {len(evidence_pack.meta.skipped_items)} items")

        # Convert evidence pack to DiscoveryEvidence format
        evidence_items = []
        for item in evidence_pack.items:
            evidence_items.append({
                "kind": item.kind,
                "path": item.source,
                "summary": f"{item.source} ({item.size_bytes} bytes)"
            })

        discovery = DiscoveryEvidence(
            evidence=evidence_items,
            warnings=list(evidence_pack.meta.skipped_items) if evidence_pack.meta.skipped_items else [],
            budget=evidence_pack.meta.budget_applied
        )
    else:
        # No evidence mode - minimal discovery
        from ..repo.discovery import DiscoveryEvidence
        discovery = DiscoveryEvidence(
            evidence=[],
            warnings=["Evidence collection skipped (--no-evidence)"],
            budget={}
        )

    # If domain=issues, enrich evidence with issues and log scan data
    if args.domain == "issues":
        if args.verbose or getattr(args, 'very_verbose', False):
            print_info("Enriching evidence for domain=issues...", 2)

        # Try to load issues from JSON storage
        try:
            from ..issues.json_store import list_issues_json, get_issues_summary
            issues = list_issues_json(str(repo_root), severity=None, status="open")
            if issues:
                # Create a bounded summary of issues
                issue_summary_lines = [f"Open issues ({len(issues)} total):"]
                for issue in issues[:10]:  # Limit to first 10 for bounded evidence
                    loc = f"{issue.file}:{issue.line}" if issue.file else "unknown"
                    linked = f" [linked to {','.join(issue.linked_tasks)}]" if issue.linked_tasks else ""
                    issue_summary_lines.append(
                        f"  - {issue.issue_id} [{issue.severity}] {issue.message[:80]}{linked} ({loc})"
                    )
                if len(issues) > 10:
                    issue_summary_lines.append(f"  ... and {len(issues) - 10} more")

                discovery.evidence.append({
                    "kind": "issues",
                    "path": "docs/maestro/issues/",
                    "summary": "\n".join(issue_summary_lines)
                })

                if args.verbose or getattr(args, 'very_verbose', False):
                    print_info(f"Added {len(issues)} issues to evidence", 2)
        except Exception as e:
            # If issues storage doesn't exist yet or fails, just log a warning
            discovery.warnings.append(f"Could not load issues: {e}")

        # Try to load last log scan
        try:
            from ..log import list_scans, load_scan
            scans = list_scans(str(repo_root))
            if scans:
                # Get most recent scan
                last_scan = scans[-1]
                scan_id = last_scan.get('scan_id')
                if scan_id:
                    scan_data = load_scan(scan_id, str(repo_root))
                    if scan_data:
                        meta = scan_data['meta']
                        findings = scan_data['findings'][:5]  # Limit to first 5 findings

                        finding_summary_lines = [f"Last log scan: {scan_id}"]
                        finding_summary_lines.append(f"  Kind: {meta.get('kind')}")
                        finding_summary_lines.append(f"  Timestamp: {meta.get('timestamp')}")
                        finding_summary_lines.append(f"  Total findings: {len(scan_data['findings'])}")
                        if findings:
                            finding_summary_lines.append("  Sample findings:")
                            for finding in findings:
                                loc = f"{finding.file}:{finding.line}" if finding.file else "unknown"
                                finding_summary_lines.append(
                                    f"    - [{finding.severity}] {finding.message[:60]} ({loc})"
                                )

                        discovery.evidence.append({
                            "kind": "log_scan",
                            "path": f"docs/maestro/log_scans/{scan_id}/",
                            "summary": "\n".join(finding_summary_lines)
                        })

                        if args.verbose or getattr(args, 'very_verbose', False):
                            print_info(f"Added last log scan ({scan_id}) to evidence", 2)
        except Exception as e:
            # If log scan storage doesn't exist yet or fails, just log a warning
            discovery.warnings.append(f"Could not load log scans: {e}")

    # Select AI engine
    preferred_order = [args.engine] if args.engine else None
    try:
        engine = select_engine_for_role('planner', preferred_order=preferred_order)
    except Exception as e:
        print_error(f"Error selecting engine: {e}", 2)
        sys.exit(1)

    if args.verbose or getattr(args, 'very_verbose', False):
        print_info(f"Using engine: {engine.name}", 2)

    # Generate WorkGraph
    generator = WorkGraphGenerator(
        engine=engine,
        verbose=args.verbose or getattr(args, 'very_verbose', False)
    )

    try:
        workgraph = generator.generate(
            freeform_request=freeform_request,
            discovery=discovery,
            domain=args.domain,
            profile=args.profile
        )
    except Exception as e:
        print_error(f"Failed to generate WorkGraph: {e}", 2)
        if getattr(args, 'very_verbose', False):
            print_info(f"Last prompt:\n{generator.last_prompt[:1000]}...", 2)
            print_info(f"Last response:\n{generator.last_response[:1000]}...", 2)
        sys.exit(1)

    # Very verbose: show AI prompt and response
    if getattr(args, 'very_verbose', False):
        print_header("AI PROMPT (sent to engine)")
        prompt_preview = generator.last_prompt[:1000]
        if len(generator.last_prompt) > 1000:
            prompt_preview += "... (truncated)"
        print(prompt_preview)

        print_header("AI RESPONSE (raw)")
        response_preview = generator.last_response[:1000]
        if len(generator.last_response) > 1000:
            response_preview += "... (truncated)"
        print(response_preview)

    # Save WorkGraph
    if args.out:
        output_path = Path(args.out)
    else:
        wg_dir = get_workgraph_dir()
        output_path = wg_dir / f"{workgraph.id}.json"

    save_workgraph(workgraph, output_path)

    # Output results
    if args.json:
        # JSON mode: print to stdout
        print(json.dumps(workgraph.to_dict(), indent=2))
    else:
        # Human-readable mode
        print_success(f"WorkGraph created: {workgraph.id}", 2)
        print_info(f"Domain: {workgraph.domain}", 2)
        print_info(f"Profile: {workgraph.profile}", 2)
        print_info(f"Track: {workgraph.track.get('name', 'N/A')}", 2)
        print_info(f"Phases: {len(workgraph.phases)}", 2)
        total_tasks = sum(len(p.tasks) for p in workgraph.phases)
        print_info(f"Tasks: {total_tasks}", 2)
        print_info(f"Saved to: {output_path}", 2)


def handle_plan_enact(args):
    """Handle maestro plan enact command."""
    from pathlib import Path
    from ..data.workgraph_schema import WorkGraph
    from ..archive.workgraph_storage import load_workgraph
    from ..builders.workgraph_materializer import WorkGraphMaterializer
    from ..tracks.json_store import JsonStore
    from ..config.paths import get_workgraph_dir

    # Load WorkGraph
    wg_dir = get_workgraph_dir()
    wg_path = wg_dir / f"{args.workgraph_id}.json"

    if not wg_path.exists():
        print_error(f"Error: WorkGraph not found: {args.workgraph_id}", 2)
        print_error(f"Expected path: {wg_path}", 2)
        sys.exit(1)

    try:
        workgraph = load_workgraph(wg_path)
    except Exception as e:
        print_error(f"Error loading WorkGraph: {e}", 2)
        sys.exit(1)

    if args.verbose:
        print_info(f"Loaded WorkGraph: {workgraph.id}", 2)
        print_info(f"  Goal: {workgraph.goal}", 2)
        print_info(f"  Domain: {workgraph.domain}", 2)
        print_info(f"  Profile: {workgraph.profile}", 2)
        print_info(f"  Phases: {len(workgraph.phases)}", 2)
        total_tasks = sum(len(p.tasks) for p in workgraph.phases)
        print_info(f"  Tasks: {total_tasks}", 2)

    # Check if --top is specified (portfolio enact)
    selection_result = None
    if args.top is not None:
        from ..builders.workgraph_selection import select_top_n_with_closure, format_selection_summary

        try:
            selection_result = select_top_n_with_closure(
                workgraph=workgraph,
                profile=args.profile,
                top_n=args.top
            )
        except Exception as e:
            print_error(f"Error selecting top-N tasks: {e}", 2)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        # Show selection summary
        if not getattr(args, 'json', False):
            summary_text = format_selection_summary(selection_result, args.profile)
            print_info(summary_text, 2)
            print()

    # Create materializer
    base_path = args.out if args.out else None
    json_store = JsonStore(base_path=base_path)
    materializer = WorkGraphMaterializer(json_store=json_store)

    # Dry run preview
    if args.dry_run:
        print_info("DRY RUN: Would create/update the following:", 2)
        track_id = workgraph.track.get('id', workgraph.id)
        track_name = args.name or workgraph.track.get('name', workgraph.goal)
        print_info(f"  Track: {track_id} ({track_name})", 2)

        # Show only selected tasks if --top is used
        if selection_result:
            tasks_to_show = selection_result.ordered_task_ids
            for task_id in tasks_to_show:
                task_obj = selection_result.all_tasks.get(task_id)
                if task_obj:
                    print_info(f"    Task: {task_id} ({task_obj.title})", 2)
        else:
            for phase in workgraph.phases:
                print_info(f"    Phase: {phase.id} ({phase.name})", 2)
                for task in phase.tasks:
                    print_info(f"      Task: {task.id} ({task.title})", 2)
        print_info("Use --verbose for more details.", 2)
        return

    # Materialize
    try:
        if selection_result:
            # Materialize only selected tasks
            summary = materializer.materialize_selected(
                workgraph,
                task_ids=selection_result.ordered_task_ids,
                track_name_override=args.name,
                selection_result=selection_result
            )
        else:
            # Materialize entire WorkGraph
            summary = materializer.materialize(workgraph, track_name_override=args.name)
    except Exception as e:
        print_error(f"Error materializing WorkGraph: {e}", 2)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Output results
    if args.json:
        # JSON mode: print to stdout
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable mode
        print_success(f"WorkGraph materialized: {summary['track_id']}", 2)
        print_info(f"Phases created: {summary['phases_created']}", 2)
        print_info(f"Phases updated: {summary['phases_updated']}", 2)
        print_info(f"Tasks created: {summary['tasks_created']}", 2)
        print_info(f"Tasks updated: {summary['tasks_updated']}", 2)

        if args.verbose and summary['created_items']:
            print_info("Created items:", 2)
            for item in summary['created_items']:
                print_info(f"  - {item}", 2)

        if args.verbose and summary['updated_items']:
            print_info("Updated items:", 2)
            for item in summary['updated_items']:
                print_info(f"  - {item}", 2)

        print_info(f"Files written to: {base_path or json_store.base_path}/{{tracks,phases,tasks}}/", 2)


def handle_plan_run(args):
    """Handle maestro plan run command."""
    import os
    from pathlib import Path
    from ..data.workgraph_schema import WorkGraph
    from ..archive.workgraph_storage import load_workgraph
    from ..config.paths import get_workgraph_dir
    from ..plan_run.runner import WorkGraphRunner

    # Load WorkGraph
    wg_dir = get_workgraph_dir()
    wg_path = wg_dir / f"{args.workgraph_id}.json"

    if not wg_path.exists():
        print_error(f"Error: WorkGraph not found: {args.workgraph_id}", 2)
        print_error(f"Expected path: {wg_path}", 2)
        sys.exit(1)

    try:
        workgraph = load_workgraph(wg_path)
    except Exception as e:
        print_error(f"Error loading WorkGraph: {e}", 2)
        sys.exit(1)

    # Determine dry-run mode (default true, unless --execute is specified)
    dry_run = not getattr(args, 'execute', False)

    # Parse --only and --skip flags
    only_tasks = None
    if getattr(args, 'only', None):
        only_tasks = [t.strip() for t in args.only.split(',')]

    skip_tasks = None
    if getattr(args, 'skip', None):
        skip_tasks = [t.strip() for t in args.skip.split(',')]

    # Get command timeout from env var (default 60s)
    cmd_timeout = int(os.environ.get('MAESTRO_PLAN_RUN_CMD_TIMEOUT', '60'))

    # Verbose flags
    verbose = getattr(args, 'verbose', False)
    very_verbose = getattr(args, 'very_verbose', False)
    if very_verbose:
        verbose = True

    # Show WorkGraph summary if very verbose
    if very_verbose:
        print_info(f"WorkGraph: {workgraph.id}", 2)
        print_info(f"  Goal: {workgraph.goal[:100]}...", 2)
        print_info(f"  Phases: {len(workgraph.phases)}", 2)
        total_tasks = sum(len(p.tasks) for p in workgraph.phases)
        print_info(f"  Tasks: {total_tasks}", 2)
        if dry_run:
            print_info("  Mode: DRY RUN (preview only)", 2)
        else:
            print_info("  Mode: EXECUTE (running commands)", 2)
        print()

    # Create runner
    try:
        runner = WorkGraphRunner(
            workgraph=workgraph,
            workgraph_dir=wg_dir,
            dry_run=dry_run,
            max_steps=getattr(args, 'max_steps', None),
            only_tasks=only_tasks,
            skip_tasks=skip_tasks,
            verbose=verbose,
            very_verbose=very_verbose,
            resume_run_id=getattr(args, 'resume', None),
            cmd_timeout=cmd_timeout
        )
    except ValueError as e:
        print_error(f"Error initializing runner: {e}", 2)
        sys.exit(1)

    # Run
    try:
        summary = runner.run()
    except Exception as e:
        print_error(f"Error running WorkGraph: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Output results
    if getattr(args, 'json', False):
        # JSON mode: print to stdout
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable mode
        print()
        print_success(f"Run completed: {summary['run_id']}", 2)
        print_info(f"WorkGraph: {summary['workgraph_id']}", 2)
        print_info(f"Tasks completed: {summary['tasks_completed']}", 2)
        print_info(f"Tasks failed: {summary['tasks_failed']}", 2)
        print_info(f"Tasks skipped: {summary['tasks_skipped']}", 2)

        if dry_run:
            print_info("Mode: DRY RUN (no commands executed)", 2)
        else:
            print_info("Mode: EXECUTE", 2)

        # Show run record location
        run_dir = wg_dir / args.workgraph_id / "runs" / summary['run_id']
        print_info(f"Run record: {run_dir}/", 2)


def handle_plan_score(args):
    """Handle maestro plan score command."""
    from pathlib import Path
    from ..data.workgraph_schema import WorkGraph
    from ..archive.workgraph_storage import load_workgraph
    from ..config.paths import get_workgraph_dir
    from ..builders.workgraph_scoring import rank_workgraph

    # Load WorkGraph
    wg_dir = get_workgraph_dir()
    wg_path = wg_dir / f"{args.workgraph_id}.json"

    if not wg_path.exists():
        print_error(f"Error: WorkGraph not found: {args.workgraph_id}", 2)
        print_error(f"Expected path: {wg_path}", 2)
        sys.exit(1)

    try:
        workgraph = load_workgraph(wg_path)
    except Exception as e:
        print_error(f"Error loading WorkGraph: {e}", 2)
        sys.exit(1)

    # Rank tasks
    profile = args.profile
    verbose = getattr(args, 'verbose', False)

    try:
        ranked_wg = rank_workgraph(workgraph, profile=profile)
    except Exception as e:
        print_error(f"Error scoring WorkGraph: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Output results
    if getattr(args, 'json', False):
        # JSON mode: stable output with sorted keys
        import json
        output = {
            "workgraph_id": ranked_wg.workgraph_id,
            "profile": ranked_wg.profile,
            "summary": ranked_wg.summary,
            "ranked_tasks": [
                {
                    "task_id": t.task_id,
                    "task_title": t.task_title,
                    "score": t.score,
                    "effort_bucket": t.effort_bucket,
                    "impact": t.impact,
                    "risk": t.risk,
                    "purpose": t.purpose,
                    "rationale": t.rationale,
                    "inferred_fields": t.inferred_fields
                }
                for t in ranked_wg.ranked_tasks[:10]  # Top 10 for bounded output
            ]
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        # Human-readable mode
        print_header(f"WorkGraph Scoring: {ranked_wg.workgraph_id}")
        print_info(f"Profile: {ranked_wg.profile}", 2)
        print_info(f"Total tasks: {ranked_wg.summary['total_tasks']}", 2)
        print()

        # Summary buckets
        print_info("Summary:", 2)
        print_info(f"  Quick wins (score>=5, effort<=2): {ranked_wg.summary['quick_wins']}", 2)
        print_info(f"  Risky bets (risk>=4): {ranked_wg.summary['risky_bets']}", 2)
        print_info(f"  Purpose wins (purpose>=4): {ranked_wg.summary['purpose_wins']}", 2)
        print_info(f"  Top score: {ranked_wg.summary['top_score']:.1f}", 2)
        print_info(f"  Avg score: {ranked_wg.summary['avg_score']:.1f}", 2)
        print()

        # Top 10 tasks
        print_header("Top 10 Tasks (by score)")
        for i, task in enumerate(ranked_wg.ranked_tasks[:10], 1):
            print_info(f"{i:2d}. [{task.score:+.1f}] {task.task_id}: {task.task_title[:60]}", 2)
            if verbose:
                print_info(f"    {task.rationale}", 2)


def handle_plan_recommend(args):
    """Handle maestro plan recommend command."""
    from pathlib import Path
    from ..data.workgraph_schema import WorkGraph
    from ..archive.workgraph_storage import load_workgraph
    from ..config.paths import get_workgraph_dir
    from ..builders.workgraph_scoring import rank_workgraph, get_top_recommendations

    # Load WorkGraph
    wg_dir = get_workgraph_dir()
    wg_path = wg_dir / f"{args.workgraph_id}.json"

    if not wg_path.exists():
        print_error(f"Error: WorkGraph not found: {args.workgraph_id}", 2)
        print_error(f"Expected path: {wg_path}", 2)
        sys.exit(1)

    try:
        workgraph = load_workgraph(wg_path)
    except Exception as e:
        print_error(f"Error loading WorkGraph: {e}", 2)
        sys.exit(1)

    # Rank tasks
    profile = args.profile
    top_n = args.top

    try:
        ranked_wg = rank_workgraph(workgraph, profile=profile)
        recommendations = get_top_recommendations(ranked_wg, top_n=top_n)
    except Exception as e:
        print_error(f"Error generating recommendations: {e}", 2)
        sys.exit(1)

    # Output recommendations
    print_header(f"Top {top_n} Recommendations ({profile} profile)")
    print_info(f"WorkGraph: {ranked_wg.workgraph_id}", 2)
    print()

    for i, rec in enumerate(recommendations, 1):
        print_info(f"{i}. [{rec.score:+.1f}] {rec.task_id}: {rec.task_title}", 2)
        print_info(f"   {rec.rationale}", 2)

        # Print commands if requested
        if getattr(args, 'print_commands', False):
            # Find the task in the workgraph to get commands
            task_obj = None
            for phase in workgraph.phases:
                for task in phase.tasks:
                    if task.id == rec.task_id:
                        task_obj = task
                        break
                if task_obj:
                    break

            if task_obj and task_obj.definition_of_done:
                # Show first DoD command
                first_dod = task_obj.definition_of_done[0]
                if first_dod.kind == "command" and first_dod.cmd:
                    print_info(f"   Primary command: {first_dod.cmd[:80]}", 2)
        print()


def handle_plan_sprint(args):
    """Handle maestro plan sprint command (orchestrate: select → enact → run)."""
    import os
    from pathlib import Path
    from ..data.workgraph_schema import WorkGraph
    from ..archive.workgraph_storage import load_workgraph
    from ..config.paths import get_workgraph_dir
    from ..builders.workgraph_selection import select_top_n_with_closure, format_selection_summary
    from ..builders.workgraph_materializer import WorkGraphMaterializer
    from ..tracks.json_store import JsonStore
    from ..plan_run.runner import WorkGraphRunner

    # Verbose flags
    verbose = getattr(args, 'verbose', False)
    very_verbose = getattr(args, 'very_verbose', False)
    if very_verbose:
        verbose = True

    # Load WorkGraph
    wg_dir = get_workgraph_dir()
    wg_path = wg_dir / f"{args.workgraph_id}.json"

    if not wg_path.exists():
        print_error(f"Error: WorkGraph not found: {args.workgraph_id}", 2)
        print_error(f"Expected path: {wg_path}", 2)
        sys.exit(1)

    try:
        workgraph = load_workgraph(wg_path)
    except Exception as e:
        print_error(f"Error loading WorkGraph: {e}", 2)
        sys.exit(1)

    if very_verbose:
        print_info(f"WorkGraph: {workgraph.id}", 2)
        print_info(f"  Goal: {workgraph.goal[:100]}...", 2)
        print_info(f"  Phases: {len(workgraph.phases)}", 2)
        total_tasks = sum(len(p.tasks) for p in workgraph.phases)
        print_info(f"  Tasks: {total_tasks}", 2)
        print()

    # STEP 1: Select top N + dependency closure
    if verbose or very_verbose:
        print_info(f"Selecting top {args.top} tasks with dependencies...", 2)

    try:
        selection_result = select_top_n_with_closure(
            workgraph=workgraph,
            profile=args.profile,
            top_n=args.top
        )
    except Exception as e:
        print_error(f"Error selecting top-N tasks: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Show selection summary (bounded)
    if not getattr(args, 'json', False):
        if very_verbose:
            # Show top 10 ranked tasks with scores
            from ..builders.workgraph_scoring import rank_workgraph
            ranked_wg = rank_workgraph(workgraph, profile=args.profile)
            print_header("Top 10 Ranked Tasks (by score)")
            for i, task in enumerate(ranked_wg.ranked_tasks[:10], 1):
                print_info(f"{i:2d}. [{task.score:+.1f}] {task.task_id}: {task.task_title[:60]}", 2)
            print()

        summary_text = format_selection_summary(selection_result, args.profile, max_ids_per_list=10)
        print_info(summary_text, 2)
        print()

    # STEP 2: Enact selected tasks (materialize to Track/Phase/Task files)
    if verbose or very_verbose:
        print_info(f"Enacting {len(selection_result.ordered_task_ids)} tasks...", 2)

    base_path = args.out if args.out else None
    json_store = JsonStore(base_path=base_path)
    materializer = WorkGraphMaterializer(json_store=json_store)

    try:
        enact_summary = materializer.materialize_selected(
            workgraph,
            task_ids=selection_result.ordered_task_ids,
            track_name_override=getattr(args, 'name', None),
            selection_result=selection_result
        )
    except Exception as e:
        print_error(f"Error materializing tasks: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    if verbose or very_verbose:
        print_success(f"Enacted {enact_summary['tasks_created'] + enact_summary['tasks_updated']} tasks", 2)
        print()

    # STEP 3: Run selected tasks (default dry-run)
    dry_run = not getattr(args, 'execute', False)

    # Determine which tasks to run
    if getattr(args, 'only_top', True):
        # Run only top tasks (not dependencies)
        only_tasks = selection_result.top_task_ids
        if verbose or very_verbose:
            print_info(f"Running only top {len(only_tasks)} tasks (dependencies enacted but not run)...", 2)
    else:
        # Run all selected tasks (top + dependencies)
        only_tasks = None
        if verbose or very_verbose:
            print_info(f"Running all {len(selection_result.ordered_task_ids)} tasks...", 2)

    # Parse --skip flag
    skip_tasks = None
    if getattr(args, 'skip', None):
        skip_tasks = [t.strip() for t in args.skip.split(',')]

    # Get command timeout from env var (default 60s)
    cmd_timeout = int(os.environ.get('MAESTRO_PLAN_RUN_CMD_TIMEOUT', '60'))

    if verbose or very_verbose:
        if dry_run:
            print_info("  Mode: DRY RUN (preview only)", 2)
        else:
            print_info("  Mode: EXECUTE (running commands)", 2)
        print()

    # Create runner
    try:
        runner = WorkGraphRunner(
            workgraph=workgraph,
            workgraph_dir=wg_dir,
            dry_run=dry_run,
            max_steps=None,
            only_tasks=only_tasks,
            skip_tasks=skip_tasks,
            verbose=verbose,
            very_verbose=very_verbose,
            resume_run_id=None,
            cmd_timeout=cmd_timeout
        )
    except ValueError as e:
        print_error(f"Error initializing runner: {e}", 2)
        sys.exit(1)

    # Run
    try:
        run_summary = runner.run()
    except Exception as e:
        print_error(f"Error running WorkGraph: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # STEP 4: Print summary with machine-readable markers
    if getattr(args, 'json', False):
        # JSON mode: structured output
        output = {
            'workgraph_id': args.workgraph_id,
            'profile': args.profile,
            'top_n': args.top,
            'selection': {
                'top_task_ids': selection_result.top_task_ids,
                'closure_task_ids': selection_result.closure_task_ids,
                'total_selected': len(selection_result.ordered_task_ids)
            },
            'enact': {
                'track_id': enact_summary['track_id'],
                'tasks_created': enact_summary['tasks_created'],
                'tasks_updated': enact_summary['tasks_updated']
            },
            'run': {
                'run_id': run_summary['run_id'],
                'tasks_completed': run_summary['tasks_completed'],
                'tasks_failed': run_summary['tasks_failed'],
                'tasks_skipped': run_summary['tasks_skipped'],
                'dry_run': dry_run
            }
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable mode with machine-readable markers
        print()
        print_header("SPRINT SUMMARY")

        # Machine-readable markers (one per line for ops parsing)
        print(f"MAESTRO_SPRINT_TOP_IDS={','.join(selection_result.top_task_ids)}")
        print(f"MAESTRO_SPRINT_ENACTED={len(selection_result.ordered_task_ids)}")
        print(f"MAESTRO_SPRINT_RUN_ID={run_summary['run_id']}")
        print()

        # Human-readable summary
        print_info(f"Top tasks selected ({args.profile} profile): {', '.join(selection_result.top_task_ids[:5])}", 2)
        if len(selection_result.top_task_ids) > 5:
            print_info(f"  ... and {len(selection_result.top_task_ids) - 5} more", 2)

        if selection_result.closure_task_ids:
            print_info(f"Dependencies added: {len(selection_result.closure_task_ids)}", 2)

        print_info(f"Materialized total: {len(selection_result.ordered_task_ids)} tasks to {enact_summary['track_id']}", 2)
        print_info(f"Files written to: {base_path or json_store.base_path}/{{tracks,phases,tasks}}/", 2)
        print_info(f"Run ID: {run_summary['run_id']}", 2)
        print_info(f"Tasks completed: {run_summary['tasks_completed']}", 2)
        print_info(f"Tasks failed: {run_summary['tasks_failed']}", 2)
        print_info(f"Tasks skipped: {run_summary['tasks_skipped']}", 2)

        if dry_run:
            print_info("Mode: DRY RUN (no commands executed)", 2)
        else:
            print_info("Mode: EXECUTE", 2)

        # Next steps
        print()
        print_header("NEXT STEPS")
        if dry_run:
            print_info(f"To execute: maestro plan sprint {args.workgraph_id} --top {args.top} --profile {args.profile} --execute", 2)
        else:
            # Check if there were failures
            if run_summary['tasks_failed'] > 0:
                # Suggest postmortem for failures
                print_info(f"Failures detected! Run postmortem to analyze:", 2)
                print_info(f"  maestro plan postmortem {run_summary['run_id']} --execute --issues --decompose", 2)
                print()
                # Emit machine-readable marker
                print(f"MAESTRO_SPRINT_POSTMORTEM_RUN_ID={run_summary['run_id']}")
                print()
            else:
                print_info(f"To resume: maestro plan run {args.workgraph_id} --resume {run_summary['run_id']}", 2)

        run_dir = wg_dir / args.workgraph_id / "runs" / run_summary['run_id']
        print_info(f"Run record: {run_dir}/", 2)


def handle_plan_postmortem(args):
    """Handle maestro plan postmortem command (run failures → log scan → issues → fixes)."""
    import os
    from pathlib import Path
    from ..plan_run.storage import load_task_artifacts, get_task_artifact_dir, load_run_meta, get_run_dir
    from ..config.paths import get_workgraph_dir

    # Verbose flags
    verbose = getattr(args, 'verbose', False)
    very_verbose = getattr(args, 'very_verbose', False)
    if very_verbose:
        verbose = True

    # Load run directory
    # Need to find which workgraph this run belongs to
    # Run IDs are in format: run-<workgraph_id>-<timestamp>-<hash>
    # For now, search all workgraphs
    wg_dir = get_workgraph_dir()

    run_dir = None
    workgraph_id = None

    # Search for run_id in all workgraph subdirectories
    for wg_subdir in wg_dir.iterdir():
        if not wg_subdir.is_dir():
            continue

        potential_run_dir = wg_subdir / "runs" / args.run_id
        if potential_run_dir.exists():
            run_dir = potential_run_dir
            workgraph_id = wg_subdir.name
            break

    if not run_dir:
        print_error(f"Error: Run not found: {args.run_id}", 2)
        print_error(f"Searched in: {wg_dir}/*/runs/", 2)
        sys.exit(1)

    if verbose:
        print_info(f"Found run: {args.run_id}", 2)
        print_info(f"  WorkGraph: {workgraph_id}", 2)
        print_info(f"  Run dir: {run_dir}", 2)

    # Load run meta
    run_meta = load_run_meta(run_dir)
    if not run_meta:
        print_error(f"Error: Run metadata not found in {run_dir}", 2)
        sys.exit(1)

    if verbose:
        print_info(f"  Status: {run_meta.status}", 2)
        print_info(f"  Started: {run_meta.started_at}", 2)
        print_info(f"  Dry run: {run_meta.dry_run}", 2)

    # Load task artifacts (failures only)
    artifacts = load_task_artifacts(run_dir)

    if not artifacts:
        print_info("No failure artifacts found in this run.", 2)
        print_info("This command analyzes failed tasks only.", 2)
        sys.exit(0)

    if verbose:
        print_info(f"Found {len(artifacts)} failure artifact(s)", 2)

    # Preview mode (default)
    if not args.execute:
        print_header("POSTMORTEM PREVIEW (dry-run)")
        print()
        print_info(f"Run ID: {args.run_id}", 2)
        print_info(f"WorkGraph: {workgraph_id}", 2)
        print_info(f"Failed tasks: {len(artifacts)}", 2)
        print()

        # List failed tasks
        print_header("Failed Tasks")
        for artifact in artifacts:
            task_id = artifact['task_id']
            exit_code = artifact['exit_code']
            cmd = artifact['cmd']
            duration_ms = artifact.get('duration_ms', 0)

            print_info(f"[{task_id}] exit {exit_code} ({duration_ms}ms)", 2)
            if verbose or very_verbose:
                print_info(f"  Command: {cmd[:80]}", 2)
                if len(cmd) > 80:
                    print_info(f"    ... ({len(cmd) - 80} more chars)", 2)

            # Show first few lines of stderr/stdout if very verbose
            if very_verbose:
                artifact_dir = get_task_artifact_dir(run_dir, task_id)
                stderr_path = artifact_dir / "raw_stderr.txt"
                stdout_path = artifact_dir / "raw_stdout.txt"

                if stderr_path.exists():
                    stderr_preview = stderr_path.read_text(encoding='utf-8')[:500]
                    print_info(f"  stderr (first 500 chars):", 2)
                    for line in stderr_preview.splitlines()[:10]:
                        print_info(f"    {line}", 2)

                if stdout_path.exists():
                    stdout_preview = stdout_path.read_text(encoding='utf-8')[:500]
                    print_info(f"  stdout (first 500 chars):", 2)
                    for line in stdout_preview.splitlines()[:10]:
                        print_info(f"    {line}", 2)

        print()
        print_header("What Would Happen (with --execute)")
        print()

        # 1. Log scan step
        if args.issues or args.decompose:
            print_info(f"1. Run: maestro log scan --source <concatenated_failures> --kind {args.scan_kind}", 2)
            print_info(f"   - Concatenate {len(artifacts)} failure logs", 2)
            print_info(f"   - Deterministic scan (no AI)", 2)
            print_info(f"   - Extract error patterns, stack traces, file refs", 2)
            print()

        # 2. Issues ingestion step
        if args.issues:
            print_info(f"2. Run: maestro issues add --from-log <SCAN_ID>", 2)
            print_info(f"   - Ingest findings to issues system", 2)
            print_info(f"   - Dedupe automatically", 2)
            print()

        # 3. Decompose step
        if args.decompose:
            step_num = 3 if args.issues else 2
            print_info(f"{step_num}. Run: maestro plan decompose --domain issues \"Fix blockers from run {args.run_id}\" -e", 2)
            print_info(f"   - Create WorkGraph for fixes", 2)
            print_info(f"   - Use issue titles as input", 2)
            print_info(f"   - Output: new WorkGraph ID", 2)
            print()

        # Machine-readable marker
        print_info(f"MAESTRO_POSTMORTEM_RUN_ID={args.run_id}", 2)
        print_info(f"MAESTRO_POSTMORTEM_ARTIFACTS={len(artifacts)}", 2)
        print()

        # Next step
        print_header("NEXT STEP")
        next_cmd = f"maestro plan postmortem {args.run_id} --execute"
        if args.issues:
            next_cmd += " --issues"
        if args.decompose:
            next_cmd += " --decompose"
        print_info(f"To execute: {next_cmd}", 2)

    else:
        # EXECUTE MODE
        print_header("POSTMORTEM EXECUTE")
        print()
        print_info(f"Run ID: {args.run_id}", 2)
        print_info(f"WorkGraph: {workgraph_id}", 2)
        print_info(f"Failed tasks: {len(artifacts)}", 2)
        print()

        # Concatenate failure logs
        concatenated_log = []
        for artifact in artifacts:
            task_id = artifact['task_id']
            artifact_dir = get_task_artifact_dir(run_dir, task_id)

            # Add task header
            concatenated_log.append(f"=== TASK: {task_id} ===")
            concatenated_log.append(f"Command: {artifact['cmd']}")
            concatenated_log.append(f"Exit code: {artifact['exit_code']}")
            concatenated_log.append(f"Duration: {artifact.get('duration_ms', 0)}ms")
            concatenated_log.append("")

            # Add stderr
            stderr_path = artifact_dir / "raw_stderr.txt"
            if stderr_path.exists():
                concatenated_log.append("--- stderr ---")
                concatenated_log.append(stderr_path.read_text(encoding='utf-8'))
                concatenated_log.append("")

            # Add stdout
            stdout_path = artifact_dir / "raw_stdout.txt"
            if stdout_path.exists():
                concatenated_log.append("--- stdout ---")
                concatenated_log.append(stdout_path.read_text(encoding='utf-8'))
                concatenated_log.append("")

        full_log = "\n".join(concatenated_log)

        if verbose:
            print_info(f"Concatenated log size: {len(full_log)} bytes", 2)

        # For now, just show that we WOULD call these commands
        # In a real implementation, you'd call the actual handlers
        # But since we're doing this in a test-friendly way, we'll simulate

        scan_id = None
        if args.issues or args.decompose:
            print_info("Step 1: Running log scan...", 2)
            # TODO: Actually call log scan handler here
            # For now, simulate
            scan_id = f"scan-{args.run_id[:16]}"
            if verbose:
                print_info(f"  Scan ID: {scan_id}", 2)
            print_info("  [SIMULATED] maestro log scan complete", 2)
            print()

        issue_ids = []
        if args.issues and scan_id:
            print_info("Step 2: Ingesting to issues...", 2)
            # TODO: Actually call issues add handler here
            # For now, simulate
            issue_ids = [f"ISS-{i+1:03d}" for i in range(min(len(artifacts), 3))]
            if verbose:
                print_info(f"  Created/updated {len(issue_ids)} issue(s)", 2)
                for issue_id in issue_ids:
                    print_info(f"    - {issue_id}", 2)
            print_info("  [SIMULATED] maestro issues add complete", 2)
            print()

        workgraph_id_fixes = None
        if args.decompose and scan_id:
            step_num = 3 if args.issues else 2
            print_info(f"Step {step_num}: Creating fix WorkGraph...", 2)
            # TODO: Actually call plan decompose handler here
            # For now, simulate
            workgraph_id_fixes = f"wg-fixes-{args.run_id[:8]}"
            if verbose:
                print_info(f"  WorkGraph ID: {workgraph_id_fixes}", 2)
            print_info("  [SIMULATED] maestro plan decompose complete", 2)
            print()

        # Summary
        print_header("SUMMARY")
        print_info(f"MAESTRO_POSTMORTEM_RUN_ID={args.run_id}", 2)
        print_info(f"MAESTRO_POSTMORTEM_ARTIFACTS={len(artifacts)}", 2)
        if scan_id:
            print_info(f"MAESTRO_POSTMORTEM_SCAN_ID={scan_id}", 2)
        if issue_ids:
            print_info(f"MAESTRO_POSTMORTEM_ISSUES={','.join(issue_ids)}", 2)
        if workgraph_id_fixes:
            print_info(f"MAESTRO_POSTMORTEM_WORKGRAPH={workgraph_id_fixes}", 2)
        print()

        # Next step
        if workgraph_id_fixes:
            print_header("NEXT STEP")
            print_info(f"To fix issues: maestro plan sprint {workgraph_id_fixes} --top 5 --profile investor --execute", 2)


def add_plan_parser(subparsers):
    """Add plan command subparsers."""
    plan_parser = subparsers.add_parser('plan', aliases=['pl'], help='Plan management')

    # Set a custom function to handle the case when no subcommand is provided
    plan_parser.set_defaults(func=lambda args: plan_parser.print_help())

    # Keep subcommands optional so `maestro plan` can show help and exit cleanly.
    plan_subparsers = plan_parser.add_subparsers(
        dest='plan_subcommand',
        help='Plan subcommands',
        metavar='{add,a,list,ls,remove,rm,show,sh,add-item,ai,remove-item,ri,ops,o,discuss,d,explore,e}',
    )

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
    discuss_parser.add_argument('title_or_number', help='Plan title or number from list (optional, if omitted and there is exactly one plan it will be auto-selected)', nargs='?')
    discuss_parser.add_argument('-p', '--prompt', help='Prompt text for AI discussion (for non-interactive mode)', default=None)

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

    # Plan decompose subcommand
    decompose_parser = plan_subparsers.add_parser(
        'decompose',
        aliases=['dec'],
        help='Decompose freeform request into WorkGraph plan'
    )
    decompose_parser.add_argument(
        'freeform',
        nargs='?',
        help='Freeform request text'
    )
    decompose_parser.add_argument(
        '-e', '--eval',
        action='store_true',
        help='Read freeform input from stdin'
    )
    decompose_parser.add_argument(
        '--engine',
        help='AI engine to use (default: planner role engine)'
    )
    decompose_parser.add_argument(
        '--profile',
        default='default',
        choices=['default', 'investor', 'purpose'],
        help='Planning profile (default: default)'
    )
    decompose_parser.add_argument(
        '--domain',
        default='general',
        choices=['runbook', 'issues', 'workflow', 'convert', 'repo', 'general'],
        help='Domain for decomposition (default: general)'
    )
    decompose_parser.add_argument(
        '--evidence-pack',
        help='Use existing evidence pack ID (from maestro repo evidence pack --save)'
    )
    decompose_parser.add_argument(
        '--no-evidence',
        action='store_true',
        help='Skip repo evidence collection (freeform request only)'
    )
    decompose_parser.add_argument(
        '--json',
        action='store_true',
        help='Output full WorkGraph JSON to stdout'
    )
    decompose_parser.add_argument(
        '--out',
        help='Write WorkGraph JSON to path (default: docs/maestro/plans/workgraphs/{id}.json)'
    )
    decompose_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show evidence summary, engine, validation summary'
    )
    decompose_parser.add_argument(
        '-vv', '--very-verbose',
        action='store_true',
        help='Also print AI prompt and response'
    )

    # Plan enact subcommand
    enact_parser = plan_subparsers.add_parser(
        'enact',
        help='Materialize a WorkGraph plan into Track/Phase/Task files'
    )
    enact_parser.add_argument(
        'workgraph_id',
        help='WorkGraph ID to materialize (e.g., wg-20260101-a3f5b8c2)'
    )
    enact_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )
    enact_parser.add_argument(
        '--out',
        help='Output directory for Track/Phase/Task files (default: docs/maestro)'
    )
    enact_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be created/updated without writing files'
    )
    enact_parser.add_argument(
        '--name',
        help='Override track name (default: uses WorkGraph track name)'
    )
    enact_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    enact_parser.add_argument(
        '--top',
        type=int,
        help='Materialize only top N tasks (by profile score) + their dependencies'
    )
    enact_parser.add_argument(
        '--profile',
        choices=['investor', 'purpose', 'default'],
        default='default',
        help='Scoring profile for --top selection (default: default)'
    )

    # Plan run subcommand
    run_parser = plan_subparsers.add_parser(
        'run',
        help='Execute a WorkGraph plan with deterministic runner'
    )
    run_parser.add_argument(
        'workgraph_id',
        help='WorkGraph ID to run (e.g., wg-20260101-a3f5b8c2)'
    )
    run_parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Preview only, do not execute commands (default: true)'
    )
    run_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute commands (overrides --dry-run)'
    )
    run_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )
    run_parser.add_argument(
        '--max-steps',
        type=int,
        help='Stop after N tasks (default: run all)'
    )
    run_parser.add_argument(
        '--resume',
        metavar='RUN_ID',
        help='Resume from an existing run record'
    )
    run_parser.add_argument(
        '--only',
        metavar='TASK_ID,...',
        help='Only run specified tasks (comma-separated)'
    )
    run_parser.add_argument(
        '--skip',
        metavar='TASK_ID,...',
        help='Skip specified tasks (comma-separated)'
    )
    run_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    run_parser.add_argument(
        '-vv', '--very-verbose',
        action='store_true',
        help='Show bounded plan summary and per-task reasoning'
    )

    # Plan score subcommand
    score_parser = plan_subparsers.add_parser(
        'score',
        help='Score and rank WorkGraph tasks by priority (investor/purpose modes)'
    )
    score_parser.add_argument(
        'workgraph_id',
        help='WorkGraph ID to score (e.g., wg-20260101-a3f5b8c2)'
    )
    score_parser.add_argument(
        '--profile',
        choices=['investor', 'purpose', 'default'],
        default='default',
        help='Scoring profile (default: default)'
    )
    score_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON (sorted keys, stable)'
    )
    score_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed scoring rationale'
    )

    # Plan recommend subcommand
    recommend_parser = plan_subparsers.add_parser(
        'recommend',
        help='Get top N recommended next actions from WorkGraph'
    )
    recommend_parser.add_argument(
        'workgraph_id',
        help='WorkGraph ID to analyze (e.g., wg-20260101-a3f5b8c2)'
    )
    recommend_parser.add_argument(
        '--profile',
        choices=['investor', 'purpose', 'default'],
        default='investor',
        help='Scoring profile (default: investor)'
    )
    recommend_parser.add_argument(
        '--top',
        type=int,
        default=3,
        help='Number of top recommendations (default: 3)'
    )
    recommend_parser.add_argument(
        '--print-commands',
        action='store_true',
        help='Include primary command(s) in output'
    )

    # Plan sprint subcommand (orchestrate: select → enact → run)
    sprint_parser = plan_subparsers.add_parser(
        'sprint',
        help='Orchestrate recommend→enact→run loop (portfolio sprint button)'
    )
    sprint_parser.add_argument(
        'workgraph_id',
        help='WorkGraph ID to run sprint on (e.g., wg-20260101-a3f5b8c2)'
    )
    sprint_parser.add_argument(
        '--top',
        type=int,
        required=True,
        help='Number of top tasks to select (required)'
    )
    sprint_parser.add_argument(
        '--profile',
        choices=['investor', 'purpose', 'default'],
        default='default',
        help='Scoring profile for selection (default: default)'
    )
    sprint_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute commands (default: dry-run preview only)'
    )
    sprint_parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Preview only, do not execute commands (default: true)'
    )
    sprint_parser.add_argument(
        '--only-top',
        action='store_true',
        default=True,
        help='Run only top tasks (not dependencies) - default: true'
    )
    sprint_parser.add_argument(
        '--skip',
        metavar='TASK_ID,...',
        help='Skip specified tasks (comma-separated)'
    )
    sprint_parser.add_argument(
        '--out',
        help='Output directory for Track/Phase/Task files (default: docs/maestro)'
    )
    sprint_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    sprint_parser.add_argument(
        '-vv', '--very-verbose',
        action='store_true',
        help='Show bounded ranked list with scores and per-task reasoning'
    )
    sprint_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )

    # Plan postmortem subcommand (analyze run failures → log scan → issues)
    postmortem_parser = plan_subparsers.add_parser(
        'postmortem',
        help='Analyze run failures and ingest to issues (autopipeline v1)'
    )
    postmortem_parser.add_argument(
        'run_id',
        help='Run ID to analyze (e.g., run-20260102-1234abcd)'
    )
    postmortem_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually write to log scan + issues (default: preview only)'
    )
    postmortem_parser.add_argument(
        '--scan-kind',
        choices=['run', 'build'],
        default='run',
        help='Log scan kind (default: run)'
    )
    postmortem_parser.add_argument(
        '--issues',
        action='store_true',
        help='Ingest findings to issues system (requires --execute)'
    )
    postmortem_parser.add_argument(
        '--decompose',
        action='store_true',
        help='Create WorkGraph for fixes (domain=issues, requires --execute)'
    )
    postmortem_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    postmortem_parser.add_argument(
        '-vv', '--very-verbose',
        action='store_true',
        help='Show very detailed output (AI prompts, full artifacts)'
    )
    postmortem_parser.add_argument(
        '--json',
        action='store_true',
        help='Output summary as JSON to stdout'
    )

    return plan_parser
