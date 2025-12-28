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
    load_breadcrumb_settings,
    complete_session,
    save_session
)
from ..ai.task_sync import (
    build_task_prompt,
    build_task_queue,
    find_task_context,
    task_is_done,
    write_sync_state,
)
from ..breadcrumb import (
    create_breadcrumb,
    write_breadcrumb,
    estimate_tokens,
    calculate_cost,
    capture_tool_call,
    track_file_modification
)
from ..data import parse_phase_md, parse_todo_md
from ..engines import get_engine, EngineError


def add_work_parser(subparsers):
    work_parser = subparsers.add_parser("work", aliases=["wk"], help="AI work sessions")
    work_parser.add_argument("--ignore-gates", action="store_true", help="Bypass all work gates")
    work_subparsers = work_parser.add_subparsers(dest="work_subcommand", help="Work subcommands")

    any_parser = work_subparsers.add_parser("any", help="Let AI select the best work item")
    any_subparsers = any_parser.add_subparsers(dest="any_subcommand", help="Any subcommands")
    any_subparsers.add_parser("pick", help="Show top 3 work items and select one")

    track_parser = work_subparsers.add_parser("track", help="Work on a track")
    track_parser.add_argument("id", nargs="?", help="Track ID")

    phase_parser = work_subparsers.add_parser("phase", help="Work on a phase")
    phase_parser.add_argument("id", nargs="?", help="Phase ID")

    issue_parser = work_subparsers.add_parser("issue", help="Work on an issue")
    issue_parser.add_argument("id", nargs="?", help="Issue ID")

    task_parser = work_subparsers.add_parser("task", help="Work on a task")
    task_parser.add_argument("id", nargs="?", help="Task ID")
    task_parser.add_argument("--simulate", action="store_true", help="Print the prompt without executing work")

    discuss_parser = work_subparsers.add_parser("discuss", help="Start a discussion for a work item")
    discuss_parser.add_argument("entity_type", choices=["track", "phase", "task"], help="Entity type")
    discuss_parser.add_argument("entity_id", help="Entity ID")

    analyze_parser = work_subparsers.add_parser("analyze", help="Analyze a target before work")
    analyze_parser.add_argument("target", nargs="?", help="Target to analyze (file, directory, or ID)")
    analyze_parser.add_argument("--simulate", action="store_true", help="Print the prompt without executing work")

    fix_parser = work_subparsers.add_parser("fix", help="Fix a target or issue")
    fix_parser.add_argument("target", nargs="?", help="Target to fix (file, directory, or ID)")
    fix_parser.add_argument("--issue", help="Issue ID to fix")
    fix_parser.add_argument("--simulate", action="store_true", help="Print the prompt without executing work")

    return work_parser

def _normalize_work_status(value: Optional[str]) -> str:
    if not value:
        return "todo"
    normalized = value.strip().lower()
    if normalized in {"done", "completed", "complete", "closed"}:
        return "done"
    return "todo"


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


def check_work_gates(ignore_gates: bool = False, repo_root: Optional[str] = None) -> bool:
    """
    Check work gates and return whether work can proceed.

    Args:
        ignore_gates: If True, bypass all gates
        repo_root: Repository root (defaults to current directory)

    Returns:
        True if work can proceed, False if blocked by gates
    """
    if ignore_gates:
        return True

    # Load issues from JSON storage
    try:
        from ..issues.json_store import list_issues_json, load_issue_json
        from ..data import parse_phase_md
    except ImportError:
        # If modules aren't available, allow work to proceed
        return True

    if not repo_root:
        repo_root = os.getcwd()

    # Get all open blocker issues
    blocker_issues = list_issues_json(repo_root, severity='blocker', status='open')

    if not blocker_issues:
        # No blocker issues, allow work
        return True

    # Check if any blockers have linked in-progress tasks
    blocking_issues = []
    for issue in blocker_issues:
        has_in_progress_task = False

        # Check if issue has linked tasks in progress
        if issue.linked_tasks:
            phases_dir = Path("docs/phases")
            if phases_dir.exists():
                for phase_file in phases_dir.glob("*.md"):
                    try:
                        phase = parse_phase_md(str(phase_file))
                        for task in phase.get("tasks", []):
                            task_id = task.get("task_id") or task.get("task_number")
                            if task_id in issue.linked_tasks:
                                task_status = task.get("status", "").lower()
                                if task_status in ["in_progress", "in progress", "active"]:
                                    has_in_progress_task = True
                                    break
                        if has_in_progress_task:
                            break
                    except Exception:
                        continue

        if not has_in_progress_task:
            blocking_issues.append(issue)

    if not blocking_issues:
        # All blockers have linked in-progress tasks, allow work
        return True

    # Print gate message
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║ GATE: BLOCKED_BY_ISSUES                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print()
    print("The following blocker issues must be addressed before work can proceed:")
    print()

    for issue in blocking_issues:
        print(f"  {issue.issue_id}: {issue.message[:60]}{'...' if len(issue.message) > 60 else ''}")
        print(f"    Severity: {issue.severity}")
        print(f"    First seen: {issue.first_seen}")
        print(f"    Last seen: {issue.last_seen}")
        print(f"    Occurrences: {len(issue.occurrences)}")
        print()

    print("Recommended actions:")
    print("  1. Triage and link issues to tasks:")
    for issue in blocking_issues[:3]:  # Show first 3 as examples
        print(f"     maestro issues link-task {issue.issue_id} TASK-XXX")
    print()
    print("  2. Or mark as resolved if already fixed:")
    print(f"     maestro issues resolve {blocking_issues[0].issue_id} --reason \"Fixed in commit abc123\"")
    print()
    print("  3. Or bypass gates (use with caution):")
    print("     maestro work --ignore-gates")
    print()
    print("For more details:")
    print(f"  maestro issues list --severity blocker --status open")
    print(f"  maestro issues show {blocking_issues[0].issue_id}")
    print()

    return False


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
    todo_data = parse_todo_md("docs/todo.md")
    # Scan docs/issues/ for open issues
    issues = load_issues()

    tracks: List[Dict[str, Any]] = []
    phases: List[Dict[str, Any]] = []

    for track in todo_data.get("tracks", []):
        track_id = track.get("track_id")
        if not track_id:
            continue
        track_status = _normalize_work_status(track.get("status"))
        track_item = {
            "id": track_id,
            "name": track.get("name", "Unnamed Track"),
            "type": "track",
            "status": track_status,
            "description": "\n".join(track.get("description", [])),
        }
        tracks.append(track_item)

        for phase in track.get("phases", []):
            phase_id = phase.get("phase_id")
            if not phase_id:
                continue
            phase_status = _normalize_work_status(phase.get("status"))
            phases.append({
                "id": phase_id,
                "name": phase.get("name", "Unnamed Phase"),
                "type": "phase",
                "track": track_id,
                "status": phase_status,
                "description": "\n".join(phase.get("description", [])),
            })

    return {
        "tracks": [t for t in tracks if t["status"] == "todo"],
        "phases": [p for p in phases if p["status"] == "todo"],
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
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

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
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

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
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

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
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

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
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

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


def _load_task_entries() -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    phases_dir = Path("docs/phases")
    if not phases_dir.exists():
        return tasks

    for phase_file in phases_dir.glob("*.md"):
        phase = parse_phase_md(str(phase_file))
        for task in phase.get("tasks", []):
            task_id = task.get("task_id") or task.get("task_number")
            if not task_id:
                continue
            if task_is_done(task):
                continue
            tasks.append({
                "id": task_id,
                "name": task.get("name", "Unnamed Task"),
                "phase_id": phase.get("phase_id"),
                "phase_name": phase.get("name"),
                "track_id": phase.get("track_id"),
            })
    return tasks


async def handle_work_task(args):
    """
    Work on a specific task or list tasks for selection.
    """
    # Check work gates
    ignore_gates = getattr(args, 'ignore_gates', False)
    if not check_work_gates(ignore_gates=ignore_gates):
        return 1

    if args.id:
        task_id = args.id
        task_context = find_task_context(task_id)
        if not task_context:
            print(f"Task with ID '{task_id}' not found.")
            return

        phase = task_context["phase"]
        task = task_context["task"]
        phase_id = phase.get("phase_id")
        track_id = phase.get("track_id")
        metadata = {
            "task_queue": build_task_queue(phase),
            "current_task_id": task_id,
        }

        session = create_session(
            session_type="work_task",
            related_entity={"task_id": task_id, "phase_id": phase_id, "track_id": track_id},
            metadata=metadata,
        )
        write_sync_state(session, metadata["task_queue"], task_id)

        prompt = build_task_prompt(task_id, task, phase, session_id=session.session_id, sync_source="work task")
        if getattr(args, "simulate", False):
            print(prompt)
            return

        response = _run_ai_interaction_with_breadcrumb(session, prompt)
        print(f"AI response: {response}")
        return

    tasks = _load_task_entries()
    if not tasks:
        print("No tasks available!")
        return

    print("Available tasks:")
    for i, task in enumerate(tasks, 1):
        phase_info = f" (phase {task.get('phase_id')})" if task.get("phase_id") else ""
        print(f"{i}. {task['id']}: {task['name']}{phase_info}")

    if len(tasks) == 1:
        selected_task = tasks[0]
    else:
        while True:
            try:
                choice = int(input(f"\nSelect task (1-{len(tasks)}): "))
                if 1 <= choice <= len(tasks):
                    selected_task = tasks[choice - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(tasks)}")
            except ValueError:
                print("Please enter a valid number")

    task_id = selected_task["id"]
    task_context = find_task_context(task_id)
    if not task_context:
        print(f"Task with ID '{task_id}' not found.")
        return

    phase = task_context["phase"]
    task = task_context["task"]
    phase_id = phase.get("phase_id")
    track_id = phase.get("track_id")
    metadata = {
        "task_queue": build_task_queue(phase),
        "current_task_id": task_id,
    }

    session = create_session(
        session_type="work_task",
        related_entity={"task_id": task_id, "phase_id": phase_id, "track_id": track_id},
        metadata=metadata,
    )
    write_sync_state(session, metadata["task_queue"], task_id)

    prompt = build_task_prompt(task_id, task, phase, session_id=session.session_id, sync_source="work task")
    if getattr(args, "simulate", False):
        print(prompt)
        return

    response = _run_ai_interaction_with_breadcrumb(session, prompt)
    print(f"AI response: {response}")

def _run_ai_interaction_with_breadcrumb(
    session: WorkSession,
    prompt: str,
    model_used: str = "claude",
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

    response, error = _safe_generate(prompt, model_used)

    if not is_breadcrumb_enabled():
        return response

    input_tokens = estimate_tokens(prompt, model_used)
    output_tokens = estimate_tokens(response, model_used)
    cost = calculate_cost(input_tokens, output_tokens, model_used)

    breadcrumb = create_breadcrumb(
        prompt=prompt,
        response=response,
        tools_called=tools_called,
        files_modified=files_modified,
        parent_session_id=session.parent_session_id,
        depth_level=0,  # This would need to be determined based on session hierarchy
        model_used=model_used,
        token_count={"input": input_tokens, "output": output_tokens},
        cost=cost,
        error=error
    )

    write_breadcrumb(breadcrumb, session.session_id)

    return response


def _safe_generate(prompt: str, model_used: str) -> tuple[str, Optional[str]]:
    try:
        engine = get_engine(model_used)
        return engine.generate(prompt), None
    except (EngineError, KeyError, AttributeError, OSError) as exc:
        return f"[SIMULATED RESPONSE] {prompt[:200]}", str(exc)


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


async def handle_work_analyze(args):
    """
    Analyze the current state or a specific target.

    If target is provided:
      - Analyze the specified target (file, directory, phase, track, or issue)
      - Create a work session with type='analyze'
      - Use AI to analyze the target and provide insights
      - Write breadcrumbs during the analysis
      - Report findings

    If target is not provided:
      - Analyze the current repository state
      - Show overall health, pending tasks, blocking issues
      - Provide actionable recommendations

    Args:
        args: Arguments with optional target and simulate flag
    """
    # Check if simulation mode
    simulate = getattr(args, 'simulate', False)

    if simulate:
        print("=" * 60)
        print("SIMULATION MODE - No actions will be executed")
        print("=" * 60)

    print("Starting analysis..." if not simulate else "Would start analysis...")

    # In simulate mode, don't create actual session
    if not simulate:
        # Create WorkSession for the analysis
        session = create_session(
            session_type="analyze",
            related_entity={"target": getattr(args, 'target', None)}
        )
    else:
        print(f"\n[SIMULATE] Would create analysis session")
        print(f"  - Session type: analyze")
        print(f"  - Target: {getattr(args, 'target', 'current repository')}")

    try:
        if args.target:
            # Analyze specific target
            target = args.target

            # Check if target is a file or directory
            if os.path.exists(target):
                if os.path.isfile(target):
                    print(f"{'Would analyze' if simulate else 'Analyzing'} file: {target}")
                    if simulate:
                        print(f"[SIMULATE] Would read file content (first 4000 chars)")
                        prompt = f"Analyze the file '{target}'"
                    else:
                        # Read file content
                        with open(target, 'r', encoding='utf-8') as f:
                            content = f.read()
                        prompt = f"Analyze the following file content:\n\n{content[:4000]}...\n\nProvide insights about this file."
                elif os.path.isdir(target):
                    print(f"{'Would analyze' if simulate else 'Analyzing'} directory: {target}")
                    # List directory contents
                    contents = os.listdir(target)
                    if simulate:
                        print(f"[SIMULATE] Directory contains {len(contents)} items")
                        print(f"[SIMULATE] First 10: {', '.join(contents[:10])}")
                    prompt = f"Analyze the directory '{target}' containing {len(contents)} items: {', '.join(contents[:20])}.\n\nWhat can you infer about this directory and its purpose?"
                else:
                    # Handle unknown target type
                    if simulate:
                        print(f"[SIMULATE] Would analyze unknown target type: {target}")
                    prompt = f"Analyze the target '{target}'. What can you tell me about this?"
            else:
                # Check if target might be a track, phase, or issue ID
                work_items = load_available_work()

                # Search in tracks
                matching_track = next((t for t in work_items["tracks"] if t["id"] == target), None)
                if matching_track:
                    print(f"{'Would analyze' if simulate else 'Analyzing'} track: {target}")
                    if simulate:
                        print(f"[SIMULATE] Track: {matching_track['name']} (status: {matching_track['status']})")
                    prompt = f"Analyze the track '{target}' with name '{matching_track['name']}' and status '{matching_track['status']}'.\n\nWhat are the characteristics of this track, and what should we consider when working on it?"
                else:
                    # Search in phases
                    matching_phase = next((p for p in work_items["phases"] if p["id"] == target), None)
                    if matching_phase:
                        print(f"{'Would analyze' if simulate else 'Analyzing'} phase: {target}")
                        if simulate:
                            print(f"[SIMULATE] Phase: {matching_phase['name']} (track: {matching_phase['track']}, status: {matching_phase['status']})")
                        prompt = f"Analyze the phase '{target}' with name '{matching_phase['name']}', track '{matching_phase['track']}', and status '{matching_phase['status']}'.\n\nWhat are the characteristics of this phase, and what should we consider when working on it?"
                    else:
                        # Search in issues
                        matching_issue = next((i for i in work_items["issues"] if i["id"] == target), None)
                        if matching_issue:
                            print(f"{'Would analyze' if simulate else 'Analyzing'} issue: {target}")
                            if simulate:
                                print(f"[SIMULATE] Issue: {matching_issue['title']} (status: {matching_issue['status']})")
                            prompt = f"Analyze the issue '{target}' with title '{matching_issue['title']}' and status '{matching_issue['status']}'.\n\nWhat can you tell me about this issue, its complexity, and how to approach resolving it?"
                        else:
                            # Target not found, treat as generic analysis
                            print(f"Target '{target}' not found. {'Would perform' if simulate else 'Performing'} general analysis.")
                            prompt = f"Perform a general analysis of target '{target}'. Provide any insights you can."
        else:
            # Analyze current repository state
            print(f"{'Would analyze' if simulate else 'Analyzing'} current repository state...")

            # Get available work items
            work_items = load_available_work()

            # Count items
            num_tracks = len(work_items["tracks"])
            num_phases = len(work_items["phases"])
            num_issues = len(work_items["issues"])

            if simulate:
                print(f"[SIMULATE] Repository stats:")
                print(f"  - Available tracks: {num_tracks}")
                print(f"  - Available phases: {num_phases}")
                print(f"  - Open issues: {num_issues}")

            # Check for recent changes
            recent_changes = []
            git_exists = os.path.exists('.git')
            if git_exists:
                try:
                    import subprocess
                    # Get recent commits
                    result = subprocess.run(['git', 'log', '--oneline', '-10'], capture_output=True, text=True, cwd='.')
                    if result.returncode == 0:
                        recent_changes = result.stdout.split('\n')[:10]
                except Exception:
                    pass  # Git command failed, skip recent changes

            prompt = f"""
            Perform a comprehensive analysis of the current repository state:

            - Available tracks: {num_tracks}
            - Available phases: {num_phases}
            - Open issues: {num_issues}
            - Git repository: {'Yes' if git_exists else 'No'}
            - Recent changes: {recent_changes[:5]}

            Provide insights about:
            1. Overall repository health
            2. Priority items that should be worked on
            3. Blocking issues or dependencies
            4. Recommendations for next steps
            5. Any potential problems or risks
            """

        # Run AI analysis with breadcrumbs or simulate
        if simulate:
            # In simulation mode, we still call AI but with special instructions
            simulation_prompt = f"""
SIMULATION MODE - DO NOT EXECUTE ANY CHANGES

You are in simulation mode. Your task is to analyze what you would do for this request,
but DO NOT actually execute any changes, write any files, or perform any actions.

Original request:
{prompt}

Respond with:
1. One short line (max 100 chars) summarizing what you would do
2. A brief bullet list (3-5 items) of the main steps you would take

Example response:
"Would analyze repository health and identify top 3 priority items"
- Check git status and recent commits
- Scan docs/todo.md for pending phases
- Evaluate issue complexity and dependencies
- Recommend next actionable item
- Estimate time/effort required

Your response:"""

            # Call AI with simulation prompt (no breadcrumbs in simulation)
            engine = get_engine("claude_planner")
            response = engine.generate(simulation_prompt)

            print("\n[SIMULATION] AI Work Plan:")
            print("="*60)
            print(response)
            print("="*60)
            print("\n[SIMULATE] No session created, no breadcrumbs written")
            print("=" * 60)
            print("SIMULATION COMPLETE - No actual work performed")
            print("=" * 60)
        else:
            response = _run_ai_interaction_with_breadcrumb(session, prompt)

            print("\nAnalysis Results:")
            print("="*50)
            print(response)
            print("="*50)

            # Complete the session
            complete_session(session)
            print(f"\nAnalysis completed. Session ID: {session.session_id}")

    except ImportError as e:
        print(f"Error importing required modules: {e}")
        # Create a simple AI interaction for now
        prompt = f"Analyze the target '{getattr(args, 'target', 'current repository')}'. Provide insights."
        response = _run_ai_interaction_with_breadcrumb(session, prompt)
        print(f"AI response: {response}")
        complete_session(session)
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

        # Update session status in case of error
        session.status = "failed"
        session.metadata["error"] = str(e)
        save_session(session, Path(session.breadcrumbs_dir).parent / "session.json")


async def handle_work_fix(args):
    """
    Fix an issue or resolve a problem with a target.

    If --issue is provided:
      - Follow the 4-phase workflow for issues (analyze → decide → fix → verify)
      - Create sub-sessions for each phase
      - Link sessions in parent-child relationship

    If only target is provided without --issue:
      - Attempt to fix the specified target directly
      - Use AI to understand the problem and generate a fix
      - Write breadcrumbs throughout
      - Report success or failure

    Args:
        args: Arguments with target, optional issue parameter, and simulate flag
    """
    # Check if simulation mode
    simulate = getattr(args, 'simulate', False)

    if simulate:
        print("=" * 60)
        print("SIMULATION MODE - No actions will be executed")
        print("=" * 60)

    print("Starting fix operation..." if not simulate else "Would start fix operation...")

    # In simulate mode, don't create actual session
    if not simulate:
        # Create the main fix session
        session = create_session(
            session_type="fix",
            metadata={"target": args.target, "issue_id": getattr(args, 'issue', None)}
        )
    else:
        print(f"\n[SIMULATE] Would create fix session")
        print(f"  - Session type: fix")
        print(f"  - Target: {args.target}")
        print(f"  - Issue ID: {getattr(args, 'issue', None)}")

    try:
        # Check if an issue ID is provided
        if hasattr(args, 'issue') and args.issue:
            # 4-phase workflow for issue fixing
            issue_id = args.issue
            target = args.target

            print(f"{'Would start' if simulate else 'Starting'} 4-phase workflow to fix issue {issue_id} related to target '{target}'")

            # Phase 1: Analyze Issue
            print(f"\n{'[SIMULATE] ' if simulate else ''}Phase 1: {'Would analyze' if simulate else 'Analyzing'} the issue...")

            if not simulate:
                analyze_session = create_session(
                    session_type="analyze_issue",
                    parent_session_id=session.session_id,
                    related_entity={"issue_id": issue_id, "target": target},
                    metadata={"phase": "analyze"}
                )
            else:
                print(f"  [SIMULATE] Would create analyze_issue sub-session")
                print(f"  [SIMULATE] Parent session: fix session")

            # Load issue details
            work_items = load_available_work()
            issue_details = next((i for i in work_items["issues"] if i["id"] == issue_id), None)

            if issue_details:
                if simulate:
                    print(f"  [SIMULATE] Issue: {issue_details['title']}")
                    print(f"  [SIMULATE] Would analyze issue description and target")
                analyze_prompt = f"""
                Analyze the issue '{issue_id}' with title '{issue_details['title']}'.
                Issue description:
                {issue_details['description'][:2000]}

                The target of the fix is '{target}'.
                What is the root cause of this issue? What needs to be fixed?
                """
            else:
                if simulate:
                    print(f"  [SIMULATE] Issue '{issue_id}' not found in database")
                analyze_prompt = f"Analyze the issue '{issue_id}' related to target '{target}'. What is the root cause and what needs to be fixed?"

            if not simulate:
                analyze_response = _run_ai_interaction_with_breadcrumb(analyze_session, analyze_prompt)
                print(f"Analysis: {analyze_response[:200]}...")
                complete_session(analyze_session)
            else:
                # In simulation, call AI with special instructions
                sim_prompt = f"""
SIMULATION MODE - DO NOT EXECUTE ANY CHANGES

You are analyzing an issue in simulation mode. Provide a brief analysis plan (1 line + 3-5 bullets)
without actually making any changes.

Original analysis request:
{analyze_prompt[:500]}...

Your analysis plan:"""
                engine = get_engine("claude_planner")
                analyze_response = engine.generate(sim_prompt)
                print(f"  [SIMULATE] AI Analysis Plan:")
                print(f"  {analyze_response[:200]}...")
                print(f"  [SIMULATE] (Phase 1 complete - no session created)")

            # Phase 2: Decide on Fix Approach
            print(f"\n{'[SIMULATE] ' if simulate else ''}Phase 2: {'Would decide on' if simulate else 'Deciding on'} fix approach...")

            if not simulate:
                decide_session = create_session(
                    session_type="decide_fix",
                    parent_session_id=session.session_id,
                    related_entity={"issue_id": issue_id, "target": target},
                    metadata={"phase": "decide"}
                )

            decide_prompt = f"""
            Based on the analysis:
            {analyze_response[:2000]}

            What is the best approach to fix the issue '{issue_id}' related to target '{target}'?
            Consider different solutions, their pros and cons, and recommend the best approach.
            """

            if not simulate:
                decide_response = _run_ai_interaction_with_breadcrumb(decide_session, decide_prompt)
                print(f"Approach: {decide_response[:200]}...")
                complete_session(decide_session)
            else:
                sim_prompt = f"SIMULATION MODE - Provide brief decision plan (1 line + 3 bullets) for: {decide_prompt[:300]}..."
                engine = get_engine("claude_planner")
                decide_response = engine.generate(sim_prompt)
                print(f"  [SIMULATE] AI Decision Plan:")
                print(f"  {decide_response[:200]}...")
                print(f"  [SIMULATE] (Phase 2 complete - no session created)")

            # Phase 3: Implement Fix
            print(f"\n{'[SIMULATE] ' if simulate else ''}Phase 3: {'Would implement' if simulate else 'Implementing'} the fix...")

            if not simulate:
                fix_session = create_session(
                    session_type="fix_issue",
                    parent_session_id=session.session_id,
                    related_entity={"issue_id": issue_id, "target": target},
                    metadata={"phase": "implement"}
                )

            fix_prompt = f"""
            Implement the fix for issue '{issue_id}' as decided:
            {decide_response[:2000]}

            The target to fix is '{target}'.
            Generate the specific code/files/changes needed to fix the issue.
            If the target is a file, show the exact changes needed.
            If the target is a directory, explain what needs to be modified.
            """

            if not simulate:
                fix_response = _run_ai_interaction_with_breadcrumb(fix_session, fix_prompt)
                print(f"Fix implemented: {fix_response[:200]}...")
                complete_session(fix_session)
            else:
                sim_prompt = f"SIMULATION MODE - Provide brief implementation plan (1 line + 3 bullets) for: {fix_prompt[:300]}..."
                engine = get_engine("claude_planner")
                fix_response = engine.generate(sim_prompt)
                print(f"  [SIMULATE] AI Implementation Plan:")
                print(f"  {fix_response[:200]}...")
                print(f"  [SIMULATE] (Phase 3 complete - no session created)")

            # Phase 4: Verify Fix
            print(f"\n{'[SIMULATE] ' if simulate else ''}Phase 4: {'Would verify' if simulate else 'Verifying'} the fix...")

            if not simulate:
                verify_session = create_session(
                    session_type="verify_fix",
                    parent_session_id=session.session_id,
                    related_entity={"issue_id": issue_id, "target": target},
                    metadata={"phase": "verify"}
                )

            verify_prompt = f"""
            Verify the fix implemented for issue '{issue_id}':
            {fix_response[:3000]}

            Is the issue properly resolved? What tests should be run to confirm?
            Are there any potential side effects of the changes?
            """

            if not simulate:
                verify_response = _run_ai_interaction_with_breadcrumb(verify_session, verify_prompt)
                print(f"Verification: {verify_response[:200]}...")
                complete_session(verify_session)
            else:
                sim_prompt = f"SIMULATION MODE - Provide brief verification plan (1 line + 3 bullets) for: {verify_prompt[:300]}..."
                engine = get_engine("claude_planner")
                verify_response = engine.generate(sim_prompt)
                print(f"  [SIMULATE] AI Verification Plan:")
                print(f"  {verify_response[:200]}...")
                print(f"  [SIMULATE] (Phase 4 complete - no session created)")

            if simulate:
                print(f"\n[SIMULATE] 4-phase workflow simulation complete")
                print(f"[SIMULATE] In real mode, would have created:")
                print(f"  - 1 main fix session")
                print(f"  - 4 sub-sessions (analyze, decide, fix, verify)")
                print(f"  - All linked in parent-child hierarchy")
                print("\n" + "=" * 60)
                print("SIMULATION COMPLETE - No actual work performed")
                print("=" * 60)
            else:
                print(f"\n4-phase fix workflow completed for issue {issue_id}")
                print(f"Main session: {session.session_id}")
                print(f"Sub-sessions: {analyze_session.session_id}, {decide_session.session_id}, {fix_session.session_id}, {verify_session.session_id}")
        else:
            # Direct fix without issue reference
            target = args.target
            print(f"Attempting to fix target: {target}")

            # Check if target is a file or directory
            if os.path.exists(target):
                if os.path.isfile(target):
                    print(f"Fixing file: {target}")
                    # Read file content
                    with open(target, 'r', encoding='utf-8') as f:
                        content = f.read()

                    fix_prompt = f"""
                    The file '{target}' needs to be fixed. Examine the content below and identify any issues or areas for improvement.

                    File content:
                    {content[:3000]}

                    What should be fixed in this file? Suggest specific changes.
                    """
                elif os.path.isdir(target):
                    print(f"Addressing issues in directory: {target}")
                    # List directory contents
                    contents = os.listdir(target)
                    fix_prompt = f"""
                    The directory '{target}' needs attention. It contains the following items:
                    {', '.join(contents[:20])}

                    What issues might exist in this directory? How should they be addressed?
                    """
                else:
                    # Handle unknown target type
                    fix_prompt = f"The target '{target}' needs to be fixed. What approach should be taken?"
            else:
                # Target not found, treat as general fix request
                print(f"Target '{target}' not found. Attempting general fix.")
                fix_prompt = f"Attempt to address any potential issues with the target '{target}'. What should be fixed?"

            # Run AI fix with breadcrumbs
            fix_response = _run_ai_interaction_with_breadcrumb(session, fix_prompt)

            print("\nFix Results:")
            print("="*50)
            print(fix_response)
            print("="*50)

        # Complete the main session
        complete_session(session)
        print(f"\nFix operation completed. Main session ID: {session.session_id}")

    except ImportError as e:
        print(f"Error importing required modules: {e}")
        # Create a simple AI interaction for now
        prompt = f"Fix the target '{getattr(args, 'target', 'unknown')}'. Issue ID: {getattr(args, 'issue', 'None')}"
        response = _run_ai_interaction_with_breadcrumb(session, prompt)
        print(f"AI response: {response}")
        complete_session(session)
    except Exception as e:
        print(f"Error during fix operation: {e}")
        import traceback
        traceback.print_exc()

        # Update session status in case of error
        session.status = "failed"
        session.metadata["error"] = str(e)
        save_session(session, Path(session.breadcrumbs_dir).parent / "session.json")
