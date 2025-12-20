"""Work command handlers with automatic breadcrumb creation for AI interactions."""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import yaml

from ..work_session import (
    WorkSession,
    create_session,
    is_breadcrumb_enabled,
    load_breadcrumb_settings
)
from ..breadcrumb import (
    create_breadcrumb,
    write_breadcrumb,
    estimate_tokens,
    calculate_cost,
    capture_tool_call,
    track_file_modification
)
from ..engines import get_engine, EngineError


def parse_todo_md() -> Dict[str, Any]:
    """
    Parse docs/todo.md for tracks and phases.

    Returns:
        {
          "tracks": [...],
          "phases": [...]
        }
    """
    todo_path = Path("docs/todo.md")
    if not todo_path.exists():
        return {"tracks": [], "phases": []}

    content = todo_path.read_text()
    lines = content.splitlines()

    result = {"tracks": [], "phases": []}
    current_track = None

    for line in lines:
        # Match track headers (## <id>_<name>)
        track_match = re.match(r'^##\s+([a-zA-Z0-9]+)_([^\n]+)$', line)
        if track_match:
            track_id = track_match.group(1)
            track_name = track_match.group(2).strip()
            current_track = {
                "id": track_id,
                "name": track_name,
                "type": "track",
                "status": "todo",
                "description": ""
            }
            result["tracks"].append(current_track)
            continue

        # Match phase headers (### <id>_<name>)
        phase_match = re.match(r'^###\s+([a-zA-Z0-9]+)_([^\n]+)$', line)
        if phase_match and current_track:
            phase_id = phase_match.group(1)
            phase_name = phase_match.group(2).strip()

            # Check if phase is completed (has checklist with all items checked)
            is_completed = False
            for i, next_line in enumerate(lines[lines.index(line)+1:], lines.index(line)+1):
                if next_line.startswith("## ") or next_line.startswith("# "):
                    break
                if next_line.startswith("- [x]") or next_line.startswith("- [X]"):
                    is_completed = True
                    break
                if next_line.startswith("- [ ]"):
                    is_completed = False
                    break

            phase = {
                "id": phase_id,
                "name": phase_name,
                "type": "phase",
                "track": current_track["id"],
                "status": "done" if is_completed else "todo",
                "description": ""
            }
            result["phases"].append(phase)

    return result


def load_issues() -> List[Dict[str, Any]]:
    """Load all issues from docs/issues/."""
    issues_dir = Path("docs/issues")
    if not issues_dir.exists():
        return []

    issues = []
    for issue_file in issues_dir.glob("*.md"):
        content = issue_file.read_text()
        # Extract issue ID from filename
        issue_id = issue_file.stem
        title_match = re.match(r'^# (.+)', content)
        title = title_match.group(1) if title_match else issue_id

        # Basic issue metadata extraction
        issue = {
            "id": issue_id,
            "title": title,
            "type": "issue",
            "status": "open",  # Default to open
            "description": content
        }

        # Check if issue is completed by looking for resolution markers
        if "**Status: Resolved**" in content or "**Status: Closed**" in content:
            issue["status"] = "closed"

        issues.append(issue)

    return issues


def load_available_work() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all available work items from various sources.

    Returns:
        {
          "tracks": [...],
          "phases": [...],
          "issues": [...]
        }
    """
    # Parse docs/todo.md for tracks and phases
    todo_data = parse_todo_md()
    # Scan docs/issues/ for open issues
    issues = load_issues()

    return {
        "tracks": [t for t in todo_data["tracks"] if t["status"] == "todo"],
        "phases": [p for p in todo_data["phases"] if p["status"] == "todo"],
        "issues": [i for i in issues if i["status"] == "open"]
    }


def ai_select_work_items(
    items: List[Dict[str, Any]],
    context: Optional[str] = None,
    mode: str = "best"  # "best" or "top_n"
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Use AI to evaluate and rank work items (tracks/phases/issues).

    Args:
        items: List of work items with metadata
        context: Additional context for selection (user preferences, etc.)
        mode: "best" returns single best item, "top_n" returns top 3

    Returns:
        Selected item(s) with reasoning
    """
    if not items:
        return [] if mode == "top_n" else {}

    # Prepare the AI prompt
    prompt = f"""
    Select the best work item(s) from the following:

    {json.dumps(items, indent=2)}

    Consider these factors:
    - Priority level
    - Dependencies (blocked by other items?)
    - Complexity (can AI handle it?)
    - User preferences
    - Recent activity
    - Estimated impact

    Context: {context or 'No additional context provided'}

    Return JSON with selected item(s) and reasoning, in this format:
    {{
      "selected": [
        {{
          "id": "ws1",
          "type": "phase",
          "name": "Session Infrastructure",
          "track": "work-session",
          "reason": "Foundational work needed before other phases can proceed",
          "confidence": 0.9,
          "estimated_difficulty": "medium"
        }},
        ...
      ],
      "reasoning": "Full explanation of selection logic"
    }}

    {f"Return only the top 3 items in the 'selected' array for mode 'top_n'." if mode == "top_n" else "Return the single best item in the 'selected' array for mode 'best'."}
    """

    try:
        # Call the AI with the prepared prompt
        engine = get_engine("claude_planner")  # Using appropriate engine
        response = engine.generate(prompt)

        # Parse the response
        try:
            result = json.loads(response)
            selected_items = result.get("selected", [])

            if mode == "best" and selected_items:
                return selected_items[0] if selected_items else {}
            else:
                return selected_items
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logging.warning("Failed to parse AI response as JSON, using fallback selection")
            return simple_priority_sort(items, mode)
    except (EngineError, KeyError, Exception) as e:
        logging.error(f"AI engine error during work selection: {e}")
        # Fallback to simple heuristic if AI fails
        return simple_priority_sort(items, mode)


def simple_priority_sort(items: List[Dict[str, Any]], mode: str = "best") -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Simple fallback heuristic for work item selection when AI fails.

    Args:
        items: List of work items to sort
        mode: "best" returns single best item, "top_n" returns top 3

    Returns:
        Selected item(s) based on simple heuristics
    """
    if not items:
        return [] if mode == "top_n" else {}

    # Sort by a simple heuristic (prioritizing phases over tracks, open issues)
    sorted_items = sorted(items, key=lambda x: (
        # Prioritize by type (phases first, then tracks, then issues)
        {"phase": 0, "track": 1, "issue": 2}.get(x.get("type", "track"), 3),
        # Then by ID to have consistent ordering
        x.get("id", "")
    ))

    if mode == "best":
        return sorted_items[0] if sorted_items else {}
    else:
        return sorted_items[:3]


async def handle_work_any(args):
    """
    AI picks best work item and starts working on it automatically.

    Steps:
    1. Load all available work items (tracks, phases, issues)
    2. Use AI to select best item
    3. Create work session for selected item
    4. Execute work (call appropriate worker)
    5. Write breadcrumbs throughout
    6. Report progress
    7. Complete or pause with status update
    """
    print("Loading available work items...")

    # Step 1: Load all available work items
    work_items = load_available_work()
    all_items = (
        work_items["tracks"] +
        work_items["phases"] +
        work_items["issues"]
    )

    if not all_items:
        print("No work items available!")
        return

    print(f"Found {len(all_items)} work items. Asking AI to select the best one...")

    # Step 2: Use AI to select best item
    selected_item = ai_select_work_items(all_items, mode="best")

    if not selected_item:
        print("AI couldn't select a work item. No items available or selection failed.")
        return

    print(f"AI selected: {selected_item.get('name', selected_item.get('id', 'Unknown'))} ({selected_item.get('type', 'item')})")
    print(f"Reason: {selected_item.get('reason', 'No specific reason provided')}")

    # Step 3: Create WorkSession with type based on selected item
    session_type = f"work_{selected_item['type']}"
    session = create_session(
        session_type=session_type,
        related_entity={f"{selected_item['type']}_id": selected_item['id']}
    )

    # Step 4: Execute appropriate worker based on item type
    try:
        if selected_item['type'] == 'track':
            from ..workers.track_worker import execute_track_work
            result = await execute_track_work(selected_item['id'], session)
        elif selected_item['type'] == 'phase':
            from ..workers.phase_worker import execute_phase_work
            result = await execute_phase_work(selected_item['id'], session)
        elif selected_item['type'] == 'issue':
            from ..workers.issue_worker import execute_issue_work
            result = await execute_issue_work(selected_item['id'], session)
        else:
            print(f"Unknown work item type: {selected_item['type']}")
            return

        # Step 7: Print summary
        print(f"\nWork completed for {selected_item['type']} {selected_item['id']}")
        print(f"Result: {result}")
    except ImportError as e:
        print(f"Error importing worker module: {e}")
        print("Creating a basic work session without executing actual work...")

        # Create a simple AI interaction for now
        prompt = f"Work on the selected {selected_item['type']} '{selected_item['id']}' - {selected_item.get('name', '')}"
        response = _run_ai_interaction_with_breadcrumb(session, prompt)
        print(f"AI response: {response}")
    except Exception as e:
        print(f"Error executing work: {e}")
        import traceback
        traceback.print_exc()


async def handle_work_any_pick(args):
    """
    AI shows top 3 work options, user selects one.

    Steps:
    1. Load all available work items
    2. Use AI to select top 3 options
    3. Display formatted list to user
    4. Prompt user to select (1, 2, or 3)
    5. Create session for selected item
    6. Execute work
    """
    print("Loading available work items...")

    # Step 1: Load all available work items
    work_items = load_available_work()
    all_items = (
        work_items["tracks"] +
        work_items["phases"] +
        work_items["issues"]
    )

    if not all_items:
        print("No work items available!")
        return

    print(f"Found {len(all_items)} work items. Asking AI to select top 3 options...")

    # Step 2: Use AI to select top 3 options
    top_items = ai_select_work_items(all_items, mode="top_n")

    if not top_items:
        print("AI couldn't select any work items.")
        return

    # Step 3: Display formatted list to user
    print("\nTop 3 recommended work items:\n")
    for i, item in enumerate(top_items, 1):
        item_type = item.get('type', 'item').upper()
        name = item.get('name', item.get('id', 'Unknown'))
        track = item.get('track', 'N/A')
        reason = item.get('reason', 'No reason provided')
        difficulty = item.get('estimated_difficulty', 'Unknown')
        priority = item.get('priority', 'Medium')

        track_info = f" ({track} track)" if item.get('track') else ""
        print(f"{i}. [{item_type}] {name}{track_info}")
        print(f"   Reason: {reason}")
        print(f"   Difficulty: {difficulty.title()} | Priority: {priority.title()}\n")

    # Step 4: Prompt user to select (1, 2, or 3) or quit
    while True:
        choice = input("Select option (1-3) or 'q' to quit: ").strip().lower()

        if choice == 'q':
            print("Cancelled by user.")
            return
        elif choice in ['1', '2', '3']:
            selected_item = top_items[int(choice) - 1]
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 'q'.")

    print(f"\nWorking on selected item: {selected_item.get('name', selected_item.get('id', 'Unknown'))}")

    # Step 5: Create session for selected item
    session_type = f"work_{selected_item['type']}"
    session = create_session(
        session_type=session_type,
        related_entity={f"{selected_item['type']}_id": selected_item['id']}
    )

    # Step 6: Execute work
    try:
        if selected_item['type'] == 'track':
            from ..workers.track_worker import execute_track_work
            result = await execute_track_work(selected_item['id'], session)
        elif selected_item['type'] == 'phase':
            from ..workers.phase_worker import execute_phase_work
            result = await execute_phase_work(selected_item['id'], session)
        elif selected_item['type'] == 'issue':
            from ..workers.issue_worker import execute_issue_work
            result = await execute_issue_work(selected_item['id'], session)
        else:
            print(f"Unknown work item type: {selected_item['type']}")
            return

        print(f"\nWork completed for {selected_item['type']} {selected_item['id']}")
        print(f"Result: {result}")
    except ImportError as e:
        print(f"Error importing worker module: {e}")
        print("Creating a basic work session without executing actual work...")

        # Create a simple AI interaction for now
        prompt = f"Work on the selected {selected_item['type']} '{selected_item['id']}' - {selected_item.get('name', '')}"
        response = _run_ai_interaction_with_breadcrumb(session, prompt)
        print(f"AI response: {response}")
    except Exception as e:
        print(f"Error executing work: {e}")
        import traceback
        traceback.print_exc()


async def handle_work_track(args):
    """
    Work on a specific track or list tracks for selection.

    If <id> provided:
      - Load track from docs/todo.md
      - Create WorkSession with type='work_track'
      - Execute track worker

    If no <id>:
      - List all tracks
      - Use AI to sort by recommendation
      - User selects from list
      - Execute selected track
    """
    # If track ID is provided, work on that specific track
    if args.id:
        track_id = args.id
        work_items = load_available_work()
        matching_track = None

        for track in work_items["tracks"]:
            if track["id"] == track_id:
                matching_track = track
                break

        if not matching_track:
            print(f"Track with ID '{track_id}' not found or already completed.")
            return

        # Create WorkSession and execute track worker
        session = create_session(
            session_type="work_track",
            related_entity={"track_id": track_id}
        )

        try:
            from ..workers.track_worker import execute_track_work
            result = await execute_track_work(track_id, session)
            print(f"Work completed for track {track_id}")
            print(f"Result: {result}")
        except ImportError:
            print("Track worker not available. Creating a basic work session...")

            prompt = f"Work on track '{track_id}'"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing track work: {e}")
            import traceback
            traceback.print_exc()
    else:
        # List all tracks and let user select
        work_items = load_available_work()
        tracks = work_items["tracks"]

        if not tracks:
            print("No tracks available!")
            return

        print("Available tracks:")
        for i, track in enumerate(tracks, 1):
            print(f"{i}. {track['id']}: {track['name']}")

        if len(tracks) == 1:
            selected_track = tracks[0]
        else:
            # Use AI to sort by recommendation
            recommended = ai_select_work_items(tracks, mode="top_n")
            print("\nAI recommended order:")
            for i, track in enumerate(recommended, 1):
                reason = track.get('reason', 'No specific reason')
                print(f"{i}. {track['id']}: {track['name']} - {reason}")

            # Let user select
            while True:
                try:
                    choice = int(input(f"\nSelect track (1-{len(tracks)}): "))
                    if 1 <= choice <= len(tracks):
                        selected_track = tracks[choice - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(tracks)}")
                except ValueError:
                    print("Please enter a valid number")

        # Create WorkSession and execute track worker
        session = create_session(
            session_type="work_track",
            related_entity={"track_id": selected_track['id']}
        )

        try:
            from ..workers.track_worker import execute_track_work
            result = await execute_track_work(selected_track['id'], session)
            print(f"Work completed for track {selected_track['id']}")
            print(f"Result: {result}")
        except ImportError:
            print("Track worker not available. Creating a basic work session...")

            prompt = f"Work on track '{selected_track['id']}' - {selected_track['name']}"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing track work: {e}")
            import traceback
            traceback.print_exc()


async def handle_work_phase(args):
    """
    Work on a specific phase or list phases for selection.

    If <id> provided:
      - Load phase from docs/todo.md
      - Create WorkSession with type='work_phase'
      - Execute phase worker

    If no <id>:
      - List all phases
      - Use AI to sort by recommendation
      - User selects from list
      - Execute selected phase
    """
    # If phase ID is provided, work on that specific phase
    if args.id:
        phase_id = args.id
        work_items = load_available_work()
        matching_phase = None

        for phase in work_items["phases"]:
            if phase["id"] == phase_id:
                matching_phase = phase
                break

        if not matching_phase:
            print(f"Phase with ID '{phase_id}' not found or already completed.")
            return

        # Create WorkSession and execute phase worker
        session = create_session(
            session_type="work_phase",
            related_entity={"phase_id": phase_id}
        )

        try:
            from ..workers.phase_worker import execute_phase_work
            result = await execute_phase_work(phase_id, session)
            print(f"Work completed for phase {phase_id}")
            print(f"Result: {result}")
        except ImportError:
            print("Phase worker not available. Creating a basic work session...")

            prompt = f"Work on phase '{phase_id}'"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing phase work: {e}")
            import traceback
            traceback.print_exc()
    else:
        # List all phases and let user select
        work_items = load_available_work()
        phases = work_items["phases"]

        if not phases:
            print("No phases available!")
            return

        print("Available phases:")
        for i, phase in enumerate(phases, 1):
            track_info = f" (in {phase.get('track', 'unknown')} track)" if phase.get('track') else ""
            print(f"{i}. {phase['id']}: {phase['name']}{track_info}")

        if len(phases) == 1:
            selected_phase = phases[0]
        else:
            # Use AI to sort by recommendation
            recommended = ai_select_work_items(phases, mode="top_n")
            print("\nAI recommended order:")
            for i, phase in enumerate(recommended, 1):
                reason = phase.get('reason', 'No specific reason')
                track_info = f" (in {phase.get('track', 'unknown')} track)" if phase.get('track') else ""
                print(f"{i}. {phase['id']}: {phase['name']}{track_info} - {reason}")

            # Let user select
            while True:
                try:
                    choice = int(input(f"\nSelect phase (1-{len(phases)}): "))
                    if 1 <= choice <= len(phases):
                        selected_phase = phases[choice - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(phases)}")
                except ValueError:
                    print("Please enter a valid number")

        # Create WorkSession and execute phase worker
        session = create_session(
            session_type="work_phase",
            related_entity={"phase_id": selected_phase['id']}
        )

        try:
            from ..workers.phase_worker import execute_phase_work
            result = await execute_phase_work(selected_phase['id'], session)
            print(f"Work completed for phase {selected_phase['id']}")
            print(f"Result: {result}")
        except ImportError:
            print("Phase worker not available. Creating a basic work session...")

            prompt = f"Work on phase '{selected_phase['id']}' - {selected_phase['name']}"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing phase work: {e}")
            import traceback
            traceback.print_exc()


async def handle_work_issue(args):
    """
    Work on a specific issue or list issues for selection.

    If <id> provided:
      - Load issue from docs/issues/
      - Create WorkSession with type='work_issue'
      - Execute issue worker

    If no <id>:
      - List all issues
      - Use AI to sort by recommendation
      - User selects from list
      - Execute selected issue
    """
    # If issue ID is provided, work on that specific issue
    if args.id:
        issue_id = args.id
        work_items = load_available_work()
        matching_issue = None

        for issue in work_items["issues"]:
            if issue["id"] == issue_id:
                matching_issue = issue
                break

        if not matching_issue:
            print(f"Issue with ID '{issue_id}' not found or already closed.")
            return

        # Create WorkSession and execute issue worker
        session = create_session(
            session_type="work_issue",
            related_entity={"issue_id": issue_id}
        )

        try:
            from ..workers.issue_worker import execute_issue_work
            result = await execute_issue_work(issue_id, session)
            print(f"Work completed for issue {issue_id}")
            print(f"Result: {result}")
        except ImportError:
            print("Issue worker not available. Creating a basic work session...")

            prompt = f"Work on issue '{issue_id}'"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing issue work: {e}")
            import traceback
            traceback.print_exc()
    else:
        # List all issues and let user select
        work_items = load_available_work()
        issues = work_items["issues"]

        if not issues:
            print("No issues available!")
            return

        print("Available issues:")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue['id']}: {issue['title']}")

        if len(issues) == 1:
            selected_issue = issues[0]
        else:
            # Use AI to sort by recommendation
            recommended = ai_select_work_items(issues, mode="top_n")
            print("\nAI recommended order:")
            for i, issue in enumerate(recommended, 1):
                reason = issue.get('reason', 'No specific reason')
                print(f"{i}. {issue['id']}: {issue['title']} - {reason}")

            # Let user select
            while True:
                try:
                    choice = int(input(f"\nSelect issue (1-{len(issues)}): "))
                    if 1 <= choice <= len(issues):
                        selected_issue = issues[choice - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(issues)}")
                except ValueError:
                    print("Please enter a valid number")

        # Create WorkSession and execute issue worker
        session = create_session(
            session_type="work_issue",
            related_entity={"issue_id": selected_issue['id']}
        )

        try:
            from ..workers.issue_worker import execute_issue_work
            result = await execute_issue_work(selected_issue['id'], session)
            print(f"Work completed for issue {selected_issue['id']}")
            print(f"Result: {result}")
        except ImportError:
            print("Issue worker not available. Creating a basic work session...")

            prompt = f"Work on issue '{selected_issue['id']}' - {selected_issue['title']}"
            response = _run_ai_interaction_with_breadcrumb(session, prompt)
            print(f"AI response: {response}")
        except Exception as e:
            print(f"Error executing issue work: {e}")
            import traceback
            traceback.print_exc()


def _run_ai_interaction_with_breadcrumb(
    session: WorkSession,
    prompt: str,
    model_used: str = "claude-3-5-sonnet",
    tools_called: Optional[list] = None,
    files_modified: Optional[list] = None
) -> str:
    """
    Run AI interaction with automatic breadcrumb creation.

    Args:
        session: The work session
        prompt: The prompt to send to the AI
        model_used: The AI model to use
        tools_called: List of tools that were called during the interaction
        files_modified: List of files that were modified during the interaction

    Returns:
        The AI's response
    """
    if tools_called is None:
        tools_called = []
    if files_modified is None:
        files_modified = []

    # Check if breadcrumbs are enabled
    if not is_breadcrumb_enabled():
        # If not enabled, just run the interaction without breadcrumbs
        engine = get_engine(model_used)
        response = engine.run(prompt)
        return response

    # Run the AI interaction
    try:
        engine = get_engine(model_used)
        response = engine.run(prompt)

        # Calculate tokens and cost
        input_tokens = estimate_tokens(prompt, model_used)
        output_tokens = estimate_tokens(response, model_used)
        cost = calculate_cost(input_tokens, output_tokens, model_used)

        # Create breadcrumb
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=tools_called,
            files_modified=files_modified,
            parent_session_id=session.parent_session_id,
            depth_level=0,  # This would need to be determined based on session hierarchy
            model_used=model_used,
            token_count={"input": input_tokens, "output": output_tokens},
            cost=cost
        )

        # Write breadcrumb to disk
        write_breadcrumb(breadcrumb, session.session_id)

        return response
    except Exception as e:
        # Create breadcrumb with error info
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response="",
            tools_called=tools_called,
            files_modified=files_modified,
            parent_session_id=session.parent_session_id,
            depth_level=0,
            model_used=model_used,
            token_count={"input": estimate_tokens(prompt, model_used), "output": 0},
            cost=0.0,
            error=str(e)
        )

        write_breadcrumb(breadcrumb, session.session_id)
        raise e


def handle_work_discuss(args):
    """
    Start a discussion session for a work item (track, phase, or issue).

    Args:
        args: Arguments with entity_type and entity_id
    """
    from .discuss import handle_track_discuss, handle_phase_discuss, handle_task_discuss

    # Map entity_type to the appropriate handler
    if args.entity_type == "track":
        return handle_track_discuss(args.entity_id, args)
    elif args.entity_type == "phase":
        return handle_phase_discuss(args.entity_id, args)
    elif args.entity_type == "task":
        return handle_task_discuss(args.entity_id, args)
    else:
        print(f"Unsupported entity type: {args.entity_type}")
        return 1