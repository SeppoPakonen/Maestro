"""
Workflow command for Maestro CLI - UML-like programming and statemachine management.

This command provides tools for creating and managing workflow diagrams and state machines
for the maestro instance.
"""
import argparse
from pathlib import Path
from typing import Any

from maestro.archive.workflow_archive import (
    ArchiveError,
    RestoreError,
    archive_workflow,
    find_archive_entry,
    list_active_workflows,
    list_archived_workflows,
    restore_workflow,
)


def add_workflow_parser(subparsers: Any) -> None:
    """Add workflow command parser."""
    workflow_parser = subparsers.add_parser(
        'workflow',
        aliases=[],
        help='UML-like programming and statemachine management',
        description='Manage workflow diagrams and state machines for the maestro instance.'
    )

    # Add subparsers for workflow command
    workflow_subparsers = workflow_parser.add_subparsers(dest='workflow_subcommand', help='Workflow subcommands')

    # Add workflow list command
    list_parser = workflow_subparsers.add_parser('list', aliases=['ls'], help='List all workflows')
    list_parser.add_argument('--archived', action='store_true', help='List archived workflows instead of active')

    # Add workflow show command
    show_parser = workflow_subparsers.add_parser('show', aliases=['sh'], help='Show a specific workflow')
    show_parser.add_argument('path', help='Path to the workflow file')
    show_parser.add_argument('--archived', action='store_true', help='Show archived workflow')
    
    # Add workflow create command
    workflow_create_parser = workflow_subparsers.add_parser('create', aliases=['new'], help='Create a new workflow')
    workflow_create_parser.add_argument('name', help='Name of the workflow to create')
    
    # Add workflow edit command
    workflow_edit_parser = workflow_subparsers.add_parser('edit', aliases=['e'], help='Edit a workflow')
    workflow_edit_parser.add_argument('name', help='Name of the workflow to edit')
    
    # Add workflow delete command
    workflow_delete_parser = workflow_subparsers.add_parser('delete', aliases=['rm'], help='Delete a workflow')
    workflow_delete_parser.add_argument('name', help='Name of the workflow to delete')
    
    # Add workflow visualize command
    workflow_visualize_parser = workflow_subparsers.add_parser('visualize', aliases=['viz'], help='Visualize a workflow as UML diagram')
    workflow_visualize_parser.add_argument('name', help='Name of the workflow to visualize')
    workflow_visualize_parser.add_argument('--format', choices=['plantuml', 'mermaid', 'graphviz'], default='plantuml',
                                         help='Output format for visualization (default: plantuml)')

    # Add workflow archive command
    archive_parser = workflow_subparsers.add_parser('archive', help='Archive a workflow file')
    archive_parser.add_argument('path', help='Path to the workflow file')
    archive_parser.add_argument('--reason', help='Reason for archiving')

    # Add workflow restore command
    restore_parser = workflow_subparsers.add_parser('restore', help='Restore an archived workflow')
    restore_parser.add_argument('archive_id', help='Archive ID to restore')

    workflow_parser.set_defaults(func=handle_workflow_command)


def handle_workflow_command(args: argparse.Namespace) -> None:
    """Handle the workflow command."""
    if args.workflow_subcommand in ['list', 'ls']:
        handle_workflow_list(args)
    elif args.workflow_subcommand in ['show', 'sh']:
        handle_workflow_show(args)
    elif args.workflow_subcommand in ['create', 'new']:
        handle_workflow_create(args)
    elif args.workflow_subcommand in ['edit', 'e']:
        handle_workflow_edit(args)
    elif args.workflow_subcommand in ['delete', 'rm']:
        handle_workflow_delete(args)
    elif args.workflow_subcommand in ['visualize', 'viz']:
        handle_workflow_visualize(args)
    elif args.workflow_subcommand == 'archive':
        handle_workflow_archive(args)
    elif args.workflow_subcommand == 'restore':
        handle_workflow_restore(args)
    else:
        # If no subcommand is provided, show help
        print("Usage: maestro workflow [list|show|create|edit|delete|visualize|archive|restore] [options]")
        print("\nUML-like programming and statemachine management for maestro instance.")


def handle_workflow_list(args: argparse.Namespace) -> None:
    """Handle the workflow list command."""
    if args.archived:
        # List archived workflows
        archived = list_archived_workflows()
        if not archived:
            print("No archived workflows found.")
            return

        print(f"Archived workflows ({len(archived)}):")
        for entry in archived:
            print(f"  [{entry.archive_id}] {entry.original_path}")
            if entry.reason:
                print(f"      Reason: {entry.reason}")
            print(f"      Archived: {entry.archived_at}")
    else:
        # List active workflows
        active = list_active_workflows()
        if not active:
            print("No active workflows found.")
            return

        print(f"Active workflows ({len(active)}):")
        for path in active:
            print(f"  {path}")


def handle_workflow_show(args: argparse.Namespace) -> None:
    """Handle the workflow show command."""
    if args.archived:
        # Show archived workflow - treat path as archive ID or original path
        entry = find_archive_entry(args.path)
        if not entry:
            print(f"Error: Archived workflow not found: {args.path}")
            return

        archived_path = Path(entry.archived_path)
        if not archived_path.exists():
            print(f"Error: Archived file missing: {archived_path}")
            return

        print(f"Workflow: {entry.original_path} (archived)")
        print(f"Archive ID: {entry.archive_id}")
        print(f"Archived at: {entry.archived_at}")
        if entry.reason:
            print(f"Reason: {entry.reason}")
        print("\nContent:")
        print(archived_path.read_text())
    else:
        # Show active workflow
        workflow_path = Path(args.path)
        if not workflow_path.exists():
            print(f"Error: Workflow file not found: {workflow_path}")
            return

        print(f"Workflow: {workflow_path}")
        print("\nContent:")
        print(workflow_path.read_text())


def handle_workflow_create(args: argparse.Namespace) -> None:
    """Handle the workflow create command."""
    print(f"Creating workflow: {args.name} (This is a stub implementation)")
    # In the future, this would create a new workflow file


def handle_workflow_edit(args: argparse.Namespace) -> None:
    """Handle the workflow edit command."""
    print(f"Editing workflow: {args.name} (This is a stub implementation)")
    # In the future, this would open an editor to edit the workflow


def handle_workflow_delete(args: argparse.Namespace) -> None:
    """Handle the workflow delete command."""
    print(f"Deleting workflow: {args.name} (This is a stub implementation)")
    # In the future, this would delete a workflow file


def handle_workflow_visualize(args: argparse.Namespace) -> None:
    """Handle the workflow visualize command."""
    print(f"Visualizing workflow: {args.name} in {args.format} format (This is a stub implementation)")
    # In the future, this would generate a UML diagram of the workflow


def handle_workflow_archive(args: argparse.Namespace) -> None:
    """Handle the workflow archive command."""
    try:
        workflow_path = Path(args.path)
        reason = args.reason if hasattr(args, 'reason') else None

        entry = archive_workflow(workflow_path, reason=reason)

        print(f"Successfully archived workflow: {workflow_path}")
        print(f"Archive ID: {entry.archive_id}")
        if entry.reason:
            print(f"Reason: {entry.reason}")
        print(f"\nUse 'maestro workflow restore {entry.archive_id}' to restore.")

    except ArchiveError as e:
        print(f"Error archiving workflow: {e}")


def handle_workflow_restore(args: argparse.Namespace) -> None:
    """Handle the workflow restore command."""
    try:
        restored_path = restore_workflow(args.archive_id)

        print(f"Successfully restored workflow to: {restored_path}")

    except RestoreError as e:
        print(f"Error restoring workflow: {e}")