"""
CLI command handlers for work session management.
"""
import json
import logging
from pathlib import Path
from typing import Optional
import sys
from datetime import datetime

try:
    from ..work_session import (
        WorkSession,
        list_sessions,
        load_session,
        get_session_hierarchy,
        create_session,
        complete_session,
        save_session,
        get_session_cookie,
        is_session_closed,
        get_sessions_base_path,
        find_session_by_id,
        get_open_child_sessions,
    )
    from ..breadcrumb import (
        list_breadcrumbs,
        get_breadcrumb_summary,
        reconstruct_session_timeline,
        create_breadcrumb,
        write_breadcrumb,
    )
    from ..visualization.tree import SessionTreeRenderer
    from ..visualization.table import SessionTableFormatter
    from ..visualization.detail import SessionDetailFormatter
    from ..stats.session_stats import calculate_session_stats, calculate_tree_stats, SessionStats
except ImportError:
    # Fallback for direct execution
    sys.path.append(str(Path(__file__).parent.parent))
    from work_session import (
        WorkSession,
        list_sessions,
        load_session,
        get_session_hierarchy,
        create_session,
        complete_session,
        save_session,
        get_session_cookie,
        is_session_closed,
        get_sessions_base_path,
        find_session_by_id,
        get_open_child_sessions,
    )
    from breadcrumb import (
        list_breadcrumbs,
        get_breadcrumb_summary,
        reconstruct_session_timeline,
        create_breadcrumb,
        write_breadcrumb,
    )
    from visualization.tree import SessionTreeRenderer
    from visualization.table import SessionTableFormatter
    from visualization.detail import SessionDetailFormatter
    from stats.session_stats import calculate_session_stats, calculate_tree_stats, SessionStats


def add_wsession_parser(subparsers):
    wsession_parser = subparsers.add_parser("wsession", aliases=["ws"], help="Work session management")
    wsession_subparsers = wsession_parser.add_subparsers(dest="wsession_subcommand", help="Work session subcommands")

    list_parser = wsession_subparsers.add_parser("list", aliases=["ls", "l"], help="List work sessions")
    list_parser.add_argument("--type", help="Filter by session type")
    list_parser.add_argument("--status", help="Filter by session status")
    list_parser.add_argument("--since", help="Filter by created ISO timestamp (YYYY-MM-DD...)")
    list_parser.add_argument("--entity", help="Filter by related entity value")
    list_parser.add_argument(
        "--sort-by",
        choices=["created", "modified", "status", "type"],
        default="created",
        help="Sort field (default: created)",
    )
    list_parser.add_argument("--reverse", action="store_true", help="Reverse sort order")

    show_parser = wsession_subparsers.add_parser("show", aliases=["sh"], help="Show work session details")
    show_parser.add_argument("session_id", help="Session ID (or prefix)")
    show_parser.add_argument("--all", dest="show_all_breadcrumbs", action="store_true", help="Show all breadcrumbs")
    show_parser.add_argument("--export-json", dest="export_json", help="Export session JSON to file")
    show_parser.add_argument("--export-md", dest="export_md", help="Export session Markdown to file")

    tree_parser = wsession_subparsers.add_parser("tree", aliases=["tr"], help="Show session hierarchy tree")
    tree_parser.add_argument("--depth", type=int, help="Max depth to display")
    tree_parser.add_argument("--status", dest="filter_status", help="Filter by session status")
    tree_parser.add_argument("--show-breadcrumbs", action="store_true", help="Show breadcrumb counts")

    breadcrumbs_parser = wsession_subparsers.add_parser("breadcrumbs", help="Show breadcrumbs for a session")
    breadcrumbs_parser.add_argument("session_id", help="Session ID (or prefix)")
    breadcrumbs_parser.add_argument("--summary", action="store_true", help="Show summary only")
    breadcrumbs_parser.add_argument("--depth", type=int, help="Depth level to include")
    breadcrumbs_parser.add_argument("--limit", type=int, help="Limit number of breadcrumbs displayed")

    breadcrumb_parser = wsession_subparsers.add_parser("breadcrumb", help="Add a breadcrumb to a session")
    breadcrumb_subparsers = breadcrumb_parser.add_subparsers(dest="breadcrumb_subcommand", help="Breadcrumb subcommands")
    breadcrumb_add = breadcrumb_subparsers.add_parser("add", help="Add a breadcrumb to a session")
    breadcrumb_add.add_argument("--cookie", required=True, help="Session cookie (required)")
    breadcrumb_add.add_argument("--prompt", default="", help="Prompt text for breadcrumb")
    breadcrumb_add.add_argument("--response", default="", help="Response text for breadcrumb")
    breadcrumb_add.add_argument("--model", default="manual", help="Model name for breadcrumb")
    breadcrumb_add.add_argument("--depth", type=int, default=0, help="Depth level for breadcrumb")

    close_parser = wsession_subparsers.add_parser("close", help="Close a work session")
    close_parser.add_argument("session_id", help="Session ID (or prefix)")

    timeline_parser = wsession_subparsers.add_parser("timeline", help="Show timeline for a session")
    timeline_parser.add_argument("session_id", help="Session ID (or prefix)")

    stats_parser = wsession_subparsers.add_parser("stats", help="Show work session stats")
    stats_parser.add_argument("session_id", nargs="?", help="Session ID (or prefix)")
    stats_parser.add_argument("--tree", action="store_true", help="Include child sessions")

    return wsession_parser


def _resolve_session_id(session_id: str) -> Optional[str]:
    if session_id != "latest":
        return session_id

    sessions = list_sessions()
    if not sessions:
        return None

    def _parse_time(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.min

    sessions.sort(key=lambda s: _parse_time(s.modified), reverse=True)
    return sessions[0].session_id


def _load_session_by_id(session_id: str) -> Optional[tuple[WorkSession, Path]]:
    result = find_session_by_id(session_id)
    if result:
        return result
    return None


def _load_session_by_cookie(cookie: str) -> Optional[tuple[WorkSession, Path]]:
    base_path = get_sessions_base_path()
    if not base_path.exists():
        return None

    for session_dir in base_path.iterdir():
        if not session_dir.is_dir():
            continue
        for session_file in [session_dir / "session.json"] + list(session_dir.glob("*/session.json")):
            if not session_file.exists():
                continue
            session = load_session(session_file)
            if get_session_cookie(session) == cookie:
                return session, session_file
    return None

def handle_wsession_list(args) -> None:
    """Handle the 'wsession list' command."""
    try:
        # Apply filters
        sessions = list_sessions(
            session_type=getattr(args, 'type', None),
            status=getattr(args, 'status', None)
        )

        # Additional filtering based on args
        if hasattr(args, 'since') and args.since:
            from datetime import datetime
            since_dt = datetime.fromisoformat(args.since)
            sessions = [s for s in sessions if datetime.fromisoformat(s.created) >= since_dt]

        if hasattr(args, 'entity') and args.entity:
            sessions = [s for s in sessions if args.entity in str(s.related_entity)]

        # Apply sorting
        sort_key = getattr(args, 'sort_by', 'created')
        reverse_order = getattr(args, 'reverse', False)

        if sort_key == 'created':
            sessions.sort(key=lambda s: s.created, reverse=reverse_order)
        elif sort_key == 'modified':
            sessions.sort(key=lambda s: s.modified, reverse=reverse_order)
        elif sort_key == 'status':
            sessions.sort(key=lambda s: s.status, reverse=reverse_order)
        elif sort_key == 'type':
            sessions.sort(key=lambda s: s.session_type, reverse=reverse_order)

        if not sessions:
            print("No work sessions found.")
            return

        # Use the new visualization component for table formatting
        formatter = SessionTableFormatter()
        print(formatter.format_table(sessions))

    except Exception as e:
        logging.error(f"Error listing work sessions: {e}")
        print(f"Error listing work sessions: {e}")


def handle_wsession_show(args) -> None:
    """Handle the 'wsession show' command."""
    try:
        session_id = _resolve_session_id(args.session_id)
        if not session_id:
            print("No work sessions found.")
            return

        # First try to find the session in the standard location
        base_path = get_sessions_base_path()
        session_found = False
        session = None

        # Look in top-level directories
        for session_dir in base_path.iterdir():
            if session_dir.is_dir() and session_id.startswith(session_dir.name):
                session_file = session_dir / "session.json"
                if session_file.exists():
                    session = load_session(session_file)
                    session_found = True
                    break

        # If not found in top-level, check nested directories
        if not session_found:
            for session_dir in base_path.iterdir():
                if session_dir.is_dir():
                    for nested_dir in session_dir.iterdir():
                        if nested_dir.is_dir() and session_id.startswith(nested_dir.name):
                            session_file = nested_dir / "session.json"
                            if session_file.exists():
                                session = load_session(session_file)
                                session_found = True
                                break
                if session_found:
                    break

        if not session_found:
            print(f"Session '{session_id}' not found.")
            return

        # Use the new visualization component for detailed display
        formatter = SessionDetailFormatter()
        show_all_breadcrumbs = hasattr(args, 'show_all_breadcrumbs') and args.show_all_breadcrumbs
        print(formatter.format_details(session, show_all_breadcrumbs=show_all_breadcrumbs))

        # Export to JSON if requested
        if hasattr(args, 'export_json') and args.export_json:
            export_session_json(session, args.export_json)
            print(f"\nSession exported to {args.export_json}")

        # Export to Markdown if requested
        if hasattr(args, 'export_md') and args.export_md:
            export_session_markdown(session, args.export_md)
            print(f"\nSession exported to {args.export_md}")

    except FileNotFoundError:
        print(f"Session '{args.session_id}' not found.")
    except Exception as e:
        logging.error(f"Error showing work session {args.session_id}: {e}")
        print(f"Error showing work session: {e}")


def handle_wsession_breadcrumb_add(args) -> None:
    """Handle the 'wsession breadcrumb add' command."""
    if not getattr(args, "cookie", None):
        print("Error: --cookie is required to add a breadcrumb.")
        return

    result = _load_session_by_cookie(args.cookie)
    if not result:
        print("Error: No session found for the provided cookie.")
        return

    session, _session_file = result
    if is_session_closed(session):
        print("Error: Session is closed; open or resume it before adding breadcrumbs.")
        return

    prompt = getattr(args, "prompt", "")
    response = getattr(args, "response", "")
    model_used = getattr(args, "model", "manual")
    depth_level = getattr(args, "depth", 0)

    breadcrumb = create_breadcrumb(
        prompt=prompt,
        response=response,
        tools_called=[],
        files_modified=[],
        parent_session_id=session.session_id,
        depth_level=depth_level,
        model_used=model_used,
        token_count={"input": len(prompt), "output": len(response)},
        cost=None
    )
    write_breadcrumb(breadcrumb, session.session_id)
    print(f"Breadcrumb added to session {session.session_id}.")


def handle_wsession_close(args) -> None:
    """Handle the 'wsession close' command."""
    session_id = _resolve_session_id(args.session_id)
    if not session_id:
        print("No work sessions found.")
        return

    result = _load_session_by_id(session_id)
    if not result:
        print(f"Session '{session_id}' not found.")
        return

    session, session_file = result
    if is_session_closed(session):
        print(f"Session '{session.session_id}' is already closed.")
        return
    if session.state not in {"running", "paused"}:
        print(f"Session '{session.session_id}' is not open (state: {session.state}).")
        return

    open_children = get_open_child_sessions(session.session_id, base_path=get_sessions_base_path())
    if open_children:
        print(f"Cannot close session '{session.session_id}': open child sessions exist.")
        for child in open_children:
            print(f"  - {child.session_id} ({child.status})")
        print("Next: maestro work subwork list <PARENT_WSESSION_ID>")
        return

    session = complete_session(session)
    save_session(session, session_file)
    print(f"Closed session {session.session_id}.")


def _display_session_details(session: WorkSession) -> None:
    """Helper function to display session details."""
    print("=" * 60)
    print(f"Session ID: {session.session_id}")
    print(f"Type: {session.session_type}")
    print(f"Status: {session.status}")
    print(f"Parent Session: {session.parent_session_id or 'None'}")
    print(f"Created: {session.created}")
    print(f"Modified: {session.modified}")
    print(f"Breadcrumbs Directory: {session.breadcrumbs_dir}")
    
    if session.related_entity:
        print("\nRelated Entities:")
        for key, value in session.related_entity.items():
            print(f"  {key}: {value}")
    
    if session.metadata:
        print("\nMetadata:")
        for key, value in session.metadata.items():
            print(f"  {key}: {json.dumps(value, indent=2)}")


def handle_wsession_tree(args) -> None:
    """Handle the 'wsession tree' command."""
    try:
        hierarchy = get_session_hierarchy()

        if not hierarchy.get("root"):
            print("No work sessions found in the hierarchy.")
            return

        # Use the new visualization component for tree rendering
        renderer = SessionTreeRenderer(color=True)
        max_depth = getattr(args, 'depth', None)

        # Apply status filter if specified
        if hasattr(args, 'filter_status') and args.filter_status:
            _filter_hierarchy_by_status(hierarchy, args.filter_status)

        tree_output = renderer.render(hierarchy, max_depth=max_depth)
        print(tree_output)

        # Show breadcrumbs count if requested
        if hasattr(args, 'show_breadcrumbs') and args.show_breadcrumbs:
            print("\nBreadcrumb counts:")
            _print_breadcrumb_counts(hierarchy["root"])

    except Exception as e:
        logging.error(f"Error showing session hierarchy: {e}")
        print(f"Error showing session hierarchy: {e}")


def _filter_hierarchy_by_status(hierarchy: dict, status: str) -> None:
    """Filter hierarchy to only include sessions with the specified status."""
    def filter_recursive(nodes):
        filtered_nodes = []
        for node in nodes:
            # Only keep nodes with matching status
            if node["session"].status == status:
                # Also filter children
                if node.get("children"):
                    node["children"] = filter_recursive(node["children"])
                filtered_nodes.append(node)
        return filtered_nodes

    hierarchy["root"] = filter_recursive(hierarchy["root"])


def _print_breadcrumb_counts(nodes, level=0):
    """Print breadcrumb counts for each session in the hierarchy."""
    for node in nodes:
        session = node["session"]
        breadcrumbs = list_breadcrumbs(session.session_id)
        indent = "  " * (level + 1)
        print(f"{indent}{session.session_id}: {len(breadcrumbs)} breadcrumbs")

        # Process children
        if node.get("children"):
            _print_breadcrumb_counts(node["children"], level + 1)


def handle_wsession_breadcrumbs(args) -> None:
    """Handle the 'wsession breadcrumbs' command."""
    try:
        session_id = _resolve_session_id(args.session_id)
        if not session_id:
            print("No work sessions found.")
            return

        # Find the session directory
        base_path = get_sessions_base_path()
        session_dir = None

        # Look for the session directory
        for item in base_path.iterdir():
            if item.is_dir() and session_id.startswith(item.name):
                session_dir = item
                break

        # Check nested directories as well
        if not session_dir:
            for item in base_path.iterdir():
                if item.is_dir():
                    for nested_item in item.iterdir():
                        if nested_item.is_dir() and session_id.startswith(nested_item.name):
                            session_dir = nested_item
                            break

        if not session_dir:
            print(f"Session '{session_id}' not found.")
            return

        if args.summary:
            # Show summary
            summary = get_breadcrumb_summary(session_id)
            print(f"Breadcrumb Summary for Session: {session_id}")
            print(f"Total Breadcrumbs: {summary['total_breadcrumbs']}")
            print(f"Total Tokens: Input: {summary['total_tokens']['input']}, Output: {summary['total_tokens']['output']}")
            print(f"Total Cost: ${summary['total_cost']:.6f}")
            print(f"Duration: {summary['duration']:.2f} seconds")
        else:
            # List breadcrumbs
            breadcrumbs = list_breadcrumbs(
                session_id,
                depth=args.depth
            )

            # Apply limit if specified
            if args.limit and args.limit > 0:
                breadcrumbs = breadcrumbs[:args.limit]

            print(f"Breadcrumbs for Session: {session_id}")
            if args.depth is not None:
                print(f"Depth Level: {args.depth}")
            print(f"Found {len(breadcrumbs)} breadcrumb(s)")
            print("-" * 80)

            for i, breadcrumb in enumerate(breadcrumbs):
                print(f"{i+1}. [{breadcrumb.timestamp}] - {breadcrumb.model_used}")
                print(f"   Prompt: {breadcrumb.prompt[:50]}...")
                print(f"   Response: {breadcrumb.response[:50]}...")
                print(f"   Tools Called: {len(breadcrumb.tools_called)}")
                print(f"   Files Modified: {len(breadcrumb.files_modified)}")
                print(f"   Depth: {breadcrumb.depth_level}")
                print(f"   Tokens: Input: {breadcrumb.token_count.get('input', 0)}, Output: {breadcrumb.token_count.get('output', 0)}")
                if breadcrumb.cost:
                    print(f"   Cost: ${breadcrumb.cost:.6f}")
                if breadcrumb.error:
                    print(f"   Error: {breadcrumb.error}")
                print()

    except Exception as e:
        logging.error(f"Error showing breadcrumbs for session {args.session_id}: {e}")
        print(f"Error showing breadcrumbs: {e}")


def handle_wsession_timeline(args) -> None:
    """Handle the 'wsession timeline' command."""
    try:
        session_id = _resolve_session_id(args.session_id)
        if not session_id:
            print("No work sessions found.")
            return

        # Find the session directory
        base_path = get_sessions_base_path()
        session_dir = None

        # Look for the session directory
        for item in base_path.iterdir():
            if item.is_dir() and session_id.startswith(item.name):
                session_dir = item
                break

        # Check nested directories as well
        if not session_dir:
            for item in base_path.iterdir():
                if item.is_dir():
                    for nested_item in item.iterdir():
                        if nested_item.is_dir() and session_id.startswith(nested_item.name):
                            session_dir = nested_item
                            break

        if not session_dir:
            print(f"Session '{session_id}' not found.")
            return

        # Reconstruct the full session timeline
        timeline = reconstruct_session_timeline(session_id)
        print(f"Timeline for Session: {session_id}")
        print(f"Total Events: {len(timeline)}")
        print("-" * 80)

        for i, event in enumerate(timeline):
            print(f"{i+1}. [{event.timestamp}] Depth: {event.depth_level}, Model: {event.model_used}")
            print(f"   Prompt: {event.prompt[:100]}...")
            print(f"   Response: {event.response[:100]}...")

            if event.tools_called:
                print(f"   Tools Called: {len(event.tools_called)}")

            if event.files_modified:
                print(f"   Files Modified: {len(event.files_modified)}")

            if event.token_count:
                print(f"   Tokens: Input: {event.token_count.get('input', 0)}, Output: {event.token_count.get('output', 0)}")

            if event.cost:
                print(f"   Cost: ${event.cost:.6f}")

            if event.error:
                print(f"   Error: {event.error}")

            print()

    except Exception as e:
        logging.error(f"Error showing timeline for session {args.session_id}: {e}")
        print(f"Error showing timeline: {e}")


def export_session_json(session: WorkSession, output_path: str):
    """
    Export session to JSON file.

    Includes:
    - Session metadata
    - All breadcrumbs
    - Child sessions
    - Statistics
    """
    import json
    from pathlib import Path

    # Get session data
    session_data = {
        "session_id": session.session_id,
        "session_type": session.session_type,
        "parent_session_id": session.parent_session_id,
        "status": session.status,
        "created": session.created,
        "modified": session.modified,
        "related_entity": session.related_entity,
        "breadcrumbs_dir": session.breadcrumbs_dir,
        "metadata": session.metadata
    }

    # Include breadcrumbs
    from ..breadcrumb import list_breadcrumbs
    breadcrumbs = list_breadcrumbs(session.session_id)
    session_data["breadcrumbs"] = [breadcrumb.__dict__ for breadcrumb in breadcrumbs]

    # Include statistics
    from ..stats.session_stats import calculate_session_stats
    stats = calculate_session_stats(session)
    session_data["statistics"] = stats.__dict__

    # Include child sessions
    from ..work_session import list_sessions
    all_sessions = list_sessions()
    child_sessions = [s for s in all_sessions if s.parent_session_id == session.session_id]
    session_data["child_sessions"] = [child.__dict__ for child in child_sessions]

    # Write to file
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)


def export_session_markdown(session: WorkSession, output_path: str):
    """
    Export session to Markdown file.

    Formatted report suitable for documentation.
    """
    from pathlib import Path
    from datetime import datetime
    from ..breadcrumb import list_breadcrumbs
    from ..stats.session_stats import calculate_session_stats

    # Get session details
    created_dt = datetime.fromisoformat(session.created.replace('Z', '+00:00'))
    modified_dt = datetime.fromisoformat(session.modified.replace('Z', '+00:00'))

    # Calculate stats
    stats = calculate_session_stats(session)
    breadcrumbs = list_breadcrumbs(session.session_id)

    # Build markdown content
    content = f"""# Session Report: {session.session_id}

## Session Information
- **Type**: {session.session_type}
- **Status**: {session.status}
- **Created**: {session.created}
- **Modified**: {session.modified}
- **Duration**: {modified_dt - created_dt}

## Related Entities
"""

    if session.related_entity:
        for key, value in session.related_entity.items():
            content += f"- **{key}**: {value}\n"
    else:
        content += "- None\n"

    content += f"""
## Statistics
- **Total Breadcrumbs**: {stats.total_breadcrumbs}
- **Total Input Tokens**: {stats.total_tokens_input:,}
- **Total Output Tokens**: {stats.total_tokens_output:,}
- **Estimated Cost**: ${stats.estimated_cost:.2f}
- **Files Modified**: {stats.files_modified}
- **Tools Called**: {stats.tools_called}
- **Duration (seconds)**: {int(stats.duration_seconds)}
- **Success Rate**: {stats.success_rate:.1f}%

## Breadcrumbs
"""

    for i, breadcrumb in enumerate(breadcrumbs):
        content += f"### Breadcrumb {i+1}: {breadcrumb.timestamp}\n"
        content += f"- **Model**: {breadcrumb.model_used}\n"
        content += f"- **Tokens**: Input: {breadcrumb.token_count.get('input', 0)}, Output: {breadcrumb.token_count.get('output', 0)}\n"
        if breadcrumb.cost:
            content += f"- **Cost**: ${breadcrumb.cost:.6f}\n"
        if breadcrumb.error:
            content += f"- **Error**: {breadcrumb.error}\n"
        content += f"\n**Prompt Preview**:\n```\n{breadcrumb.prompt[:200]}...\n```\n\n"
        content += f"**Response Preview**:\n```\n{breadcrumb.response[:200]}...\n```\n\n---\n\n"

    # Write to file
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)


def handle_wsession_stats(args) -> None:
    """Handle the 'wsession stats' command."""
    try:
        session_id = None
        if args.session_id:
            session_id = _resolve_session_id(args.session_id)
            if not session_id:
                print("No work sessions found.")
                return

        if session_id:
            # Show stats for specific session
            result = _load_session_by_id(session_id)
            if not result:
                print(f"Session '{session_id}' not found.")
                return
            session, _session_path = result

            # Calculate and display stats
            from ..stats.session_stats import calculate_session_stats, calculate_tree_stats
            if hasattr(args, 'tree') and args.tree:
                stats = calculate_tree_stats(session)
            else:
                stats = calculate_session_stats(session)

            formatter = SessionDetailFormatter()
            print(formatter.format_statistics(session))
        else:
            # Show stats for all sessions
            all_sessions = list_sessions()
            if not all_sessions:
                print("No sessions found.")
                return

            # Aggregate stats across all sessions
            total_breadcrumbs = 0
            total_tokens_input = 0
            total_tokens_output = 0
            total_cost = 0.0
            total_files_modified = 0
            total_tools_called = 0
            total_duration = 0.0
            total_sessions = len(all_sessions)

            for session in all_sessions:
                session_stats = calculate_session_stats(session)
                total_breadcrumbs += session_stats.total_breadcrumbs
                total_tokens_input += session_stats.total_tokens_input
                total_tokens_output += session_stats.total_tokens_output
                total_cost += session_stats.estimated_cost
                total_files_modified += session_stats.files_modified
                total_tools_called += session_stats.tools_called
                total_duration += session_stats.duration_seconds

            avg_success_rate = sum(calculate_session_stats(s).success_rate for s in all_sessions) / len(all_sessions) if all_sessions else 0.0

            print("Aggregate Statistics for All Sessions:")
            print(f"  Total Sessions: {total_sessions}")
            print(f"  Total Breadcrumbs: {total_breadcrumbs}")
            print(f"  Total Tokens (Input): {total_tokens_input:,}")
            print(f"  Total Tokens (Output): {total_tokens_output:,}")
            print(f"  Total Estimated Cost: ${total_cost:.2f}")
            print(f"  Total Files Modified: {total_files_modified}")
            print(f"  Total Tools Called: {total_tools_called}")
            print(f"  Total Duration (seconds): {int(total_duration)}")
            print(f"  Average Success Rate: {avg_success_rate:.1f}%")

    except Exception as e:
        logging.error(f"Error showing session stats: {e}")
        print(f"Error showing session stats: {e}")
