"""
CLI command handlers for work session management.
"""
import json
import logging
from pathlib import Path
from typing import Optional
import sys

try:
    from ..work_session import (
        WorkSession,
        list_sessions,
        load_session,
        get_session_hierarchy,
        create_session
    )
    from ..breadcrumb import (
        list_breadcrumbs,
        get_breadcrumb_summary,
        reconstruct_session_timeline
    )
except ImportError:
    # Fallback for direct execution
    sys.path.append(str(Path(__file__).parent.parent))
    from work_session import (
        WorkSession,
        list_sessions,
        load_session,
        get_session_hierarchy,
        create_session
    )
    from breadcrumb import (
        list_breadcrumbs,
        get_breadcrumb_summary,
        reconstruct_session_timeline
    )


def handle_wsession_list(args) -> None:
    """Handle the 'wsession list' command."""
    try:
        sessions = list_sessions(
            session_type=args.type,
            status=args.status
        )
        
        if not sessions:
            print("No work sessions found.")
            return
        
        print(f"Found {len(sessions)} work session(s):")
        print("-" * 80)
        for session in sessions:
            parent_info = f" (child of {session.parent_session_id})" if session.parent_session_id else ""
            status_icon = {
                "running": "▶",
                "paused": "⏸", 
                "completed": "✅",
                "interrupted": "⚠",
                "failed": "❌"
            }.get(session.status, "?")
            
            print(f"{status_icon} {session.session_id[:8]}... ({session.session_type}) - {session.status}{parent_info}")
            print(f"  Created: {session.created}")
            if session.related_entity:
                entities = ", ".join([f"{k}:{v}" for k, v in session.related_entity.items()])
                print(f"  Related: {entities}")
            print()
    
    except Exception as e:
        logging.error(f"Error listing work sessions: {e}")
        print(f"Error listing work sessions: {e}")


def handle_wsession_show(args) -> None:
    """Handle the 'wsession show' command."""
    try:
        # First try to find the session in the standard location
        base_path = Path("docs") / "sessions"
        session_found = False
        
        # Look in top-level directories
        for session_dir in base_path.iterdir():
            if session_dir.is_dir() and args.session_id.startswith(session_dir.name):
                session_file = session_dir / "session.json"
                if session_file.exists():
                    session = load_session(session_file)
                    _display_session_details(session)
                    session_found = True
                    break
        
        # If not found in top-level, check nested directories
        if not session_found:
            for session_dir in base_path.iterdir():
                if session_dir.is_dir():
                    for nested_dir in session_dir.iterdir():
                        if nested_dir.is_dir() and args.session_id.startswith(nested_dir.name):
                            session_file = nested_dir / "session.json"
                            if session_file.exists():
                                session = load_session(session_file)
                                _display_session_details(session)
                                session_found = True
                                break
                if session_found:
                    break
        
        if not session_found:
            print(f"Session '{args.session_id}' not found.")
            return
    
    except FileNotFoundError:
        print(f"Session '{args.session_id}' not found.")
    except Exception as e:
        logging.error(f"Error showing work session {args.session_id}: {e}")
        print(f"Error showing work session: {e}")


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
        _display_session_tree(hierarchy, level=0)
        
        if not hierarchy.get("root"):
            print("No work sessions found in the hierarchy.")
    
    except Exception as e:
        logging.error(f"Error showing session hierarchy: {e}")
        print(f"Error showing session hierarchy: {e}")


def _display_session_tree(tree_node: dict, level: int = 0) -> None:
    """Helper function to display session hierarchy as a tree."""
    indent = "  " * level
    prefix = "└─ " if level > 0 else ""

    if "session" in tree_node:
        session = tree_node["session"]
        status_icon = {
            "running": "▶",
            "paused": "⏸",
            "completed": "✅",
            "interrupted": "⚠",
            "failed": "❌"
        }.get(session.status, "?")

        print(f"{indent}{prefix}{status_icon} {session.session_id[:8]}... ({session.session_type}) - {session.status}")

        # Print any additional info
        if session.related_entity:
            entities_str = ", ".join([f"{k}:{str(v)[:10]}..." for k, v in session.related_entity.items()])
            print(f"{indent}    └─ Related: {entities_str}")

    # Process children if present
    children = tree_node.get("children", [])
    if isinstance(tree_node.get("session"), WorkSession):
        # This is a node with a session
        for child in children:
            _display_session_tree(child, level + 1)
    else:
        # This is the root level (tree_node directly contains list of root sessions)
        if "root" in tree_node:
            for child in tree_node["root"]:
                _display_session_tree(child, level)
        else:
            # This was processed as a child node previously
            for child in children:
                _display_session_tree(child, level + 1)


def handle_wsession_breadcrumbs(args) -> None:
    """Handle the 'wsession breadcrumbs' command."""
    try:
        # Find the session directory
        base_path = Path("docs") / "sessions"
        session_dir = None

        # Look for the session directory
        for item in base_path.iterdir():
            if item.is_dir() and args.session_id.startswith(item.name):
                session_dir = item
                break

        # Check nested directories as well
        if not session_dir:
            for item in base_path.iterdir():
                if item.is_dir():
                    for nested_item in item.iterdir():
                        if nested_item.is_dir() and args.session_id.startswith(nested_item.name):
                            session_dir = nested_item
                            break

        if not session_dir:
            print(f"Session '{args.session_id}' not found.")
            return

        if args.summary:
            # Show summary
            summary = get_breadcrumb_summary(args.session_id)
            print(f"Breadcrumb Summary for Session: {args.session_id}")
            print(f"Total Breadcrumbs: {summary['total_breadcrumbs']}")
            print(f"Total Tokens: Input: {summary['total_tokens']['input']}, Output: {summary['total_tokens']['output']}")
            print(f"Total Cost: ${summary['total_cost']:.6f}")
            print(f"Duration: {summary['duration']:.2f} seconds")
        else:
            # List breadcrumbs
            breadcrumbs = list_breadcrumbs(
                args.session_id,
                depth=args.depth
            )

            # Apply limit if specified
            if args.limit and args.limit > 0:
                breadcrumbs = breadcrumbs[:args.limit]

            print(f"Breadcrumbs for Session: {args.session_id}")
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
        # Find the session directory
        base_path = Path("docs") / "sessions"
        session_dir = None

        # Look for the session directory
        for item in base_path.iterdir():
            if item.is_dir() and args.session_id.startswith(item.name):
                session_dir = item
                break

        # Check nested directories as well
        if not session_dir:
            for item in base_path.iterdir():
                if item.is_dir():
                    for nested_item in item.iterdir():
                        if nested_item.is_dir() and args.session_id.startswith(nested_item.name):
                            session_dir = nested_item
                            break

        if not session_dir:
            print(f"Session '{args.session_id}' not found.")
            return

        # Reconstruct the full session timeline
        timeline = reconstruct_session_timeline(args.session_id)
        print(f"Timeline for Session: {args.session_id}")
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