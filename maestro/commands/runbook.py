"""
Runbook command for Maestro CLI - runbook-first bootstrap before workflow.

This command provides tools for managing runbook entries as first-class project assets
stored in repo truth (JSON). Runbooks are a lower-friction, narrative-first modeling layer
that can later feed Workflow graphs.
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def add_runbook_parser(subparsers: Any) -> None:
    """Add runbook command parser."""
    runbook_parser = subparsers.add_parser(
        'runbook',
        aliases=['runba', 'rb'],
        help='Runbook-first bootstrap before workflow',
        description='Manage runbook entries as first-class project assets. '
                    'Runbooks provide a narrative-first modeling layer before formalization.'
    )

    # Add subparsers for runbook command
    runbook_subparsers = runbook_parser.add_subparsers(dest='runbook_subcommand', help='Runbook subcommands')

    # List command
    list_parser = runbook_subparsers.add_parser('list', aliases=['ls'], help='List all runbooks')
    list_parser.add_argument('--status', choices=['proposed', 'approved', 'deprecated'], help='Filter by status')
    list_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'], help='Filter by scope')
    list_parser.add_argument('--tag', help='Filter by tag')

    # Show command
    show_parser = runbook_subparsers.add_parser('show', aliases=['sh'], help='Show a specific runbook')
    show_parser.add_argument('id', help='ID of the runbook to show')

    # Add command
    add_parser = runbook_subparsers.add_parser('add', aliases=['new'], help='Create a new runbook')
    add_parser.add_argument('--title', required=True, help='Title of the runbook')
    add_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'],
                           default='product', help='Scope of the runbook (default: product)')
    add_parser.add_argument('--tag', action='append', help='Add tags (can be specified multiple times)')
    add_parser.add_argument('--source-program', help='Source program name/version (for reverse engineering)')
    add_parser.add_argument('--target-project', help='Target project name')

    # Edit command
    edit_parser = runbook_subparsers.add_parser('edit', aliases=['e'], help='Edit a runbook')
    edit_parser.add_argument('id', help='ID of the runbook to edit')
    edit_parser.add_argument('--title', help='New title')
    edit_parser.add_argument('--status', choices=['proposed', 'approved', 'deprecated'], help='New status')
    edit_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'], help='New scope')
    edit_parser.add_argument('--tag', action='append', help='Add tags (can be specified multiple times)')

    # Remove command
    rm_parser = runbook_subparsers.add_parser('rm', aliases=['remove', 'delete'], help='Delete a runbook')
    rm_parser.add_argument('id', help='ID of the runbook to delete')
    rm_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    # Step add command
    step_add_parser = runbook_subparsers.add_parser('step-add', aliases=['sa'], help='Add a step to a runbook')
    step_add_parser.add_argument('id', help='ID of the runbook')
    step_add_parser.add_argument('--actor', required=True, help='Actor performing the step (e.g., user, manager, system, ai)')
    step_add_parser.add_argument('--action', required=True, help='Short action description')
    step_add_parser.add_argument('--expected', required=True, help='Expected outcome')
    step_add_parser.add_argument('--details', help='Multi-line detailed description')
    step_add_parser.add_argument('--variants', action='append', help='Variant descriptions (can be specified multiple times)')

    # Step edit command
    step_edit_parser = runbook_subparsers.add_parser('step-edit', aliases=['se'], help='Edit a step in a runbook')
    step_edit_parser.add_argument('id', help='ID of the runbook')
    step_edit_parser.add_argument('n', type=int, help='Step number to edit')
    step_edit_parser.add_argument('--actor', help='New actor')
    step_edit_parser.add_argument('--action', help='New action')
    step_edit_parser.add_argument('--expected', help='New expected outcome')
    step_edit_parser.add_argument('--details', help='New details')

    # Step rm command
    step_rm_parser = runbook_subparsers.add_parser('step-rm', aliases=['sr'], help='Remove a step from a runbook')
    step_rm_parser.add_argument('id', help='ID of the runbook')
    step_rm_parser.add_argument('n', type=int, help='Step number to remove')

    # Step renumber command
    step_renumber_parser = runbook_subparsers.add_parser('step-renumber', aliases=['srn'], help='Renumber steps in a runbook')
    step_renumber_parser.add_argument('id', help='ID of the runbook')

    # Export command
    export_parser = runbook_subparsers.add_parser('export', aliases=['exp'], help='Export a runbook')
    export_parser.add_argument('id', help='ID of the runbook to export')
    export_parser.add_argument('--format', choices=['md', 'puml'], default='md', help='Export format (default: md)')
    export_parser.add_argument('--out', help='Output file path (default: docs/maestro/runbooks/exports/<id>.<format>)')

    # Render command (optional PUML to SVG)
    render_parser = runbook_subparsers.add_parser('render', aliases=['rnd'], help='Render a runbook PUML to SVG')
    render_parser.add_argument('id', help='ID of the runbook to render')
    render_parser.add_argument('--out', help='Output SVG file path')

    # Discuss command
    discuss_parser = runbook_subparsers.add_parser('discuss', aliases=['d'], help='Discuss runbook with AI (placeholder)')
    discuss_parser.add_argument('id', help='ID of the runbook to discuss')

    runbook_parser.set_defaults(func=handle_runbook_command)


def handle_runbook_command(args: argparse.Namespace) -> None:
    """Handle the runbook command."""
    if not hasattr(args, 'runbook_subcommand') or args.runbook_subcommand is None:
        print("Usage: maestro runbook [list|show|add|edit|rm|step-add|step-edit|step-rm|step-renumber|export|render|discuss] [options]")
        print("\nRunbook-first bootstrap - manage narrative-style procedural descriptions before workflow formalization.")
        return

    if args.runbook_subcommand in ['list', 'ls']:
        handle_runbook_list(args)
    elif args.runbook_subcommand in ['show', 'sh']:
        handle_runbook_show(args)
    elif args.runbook_subcommand in ['add', 'new']:
        handle_runbook_add(args)
    elif args.runbook_subcommand in ['edit', 'e']:
        handle_runbook_edit(args)
    elif args.runbook_subcommand in ['rm', 'remove', 'delete']:
        handle_runbook_rm(args)
    elif args.runbook_subcommand in ['step-add', 'sa']:
        handle_step_add(args)
    elif args.runbook_subcommand in ['step-edit', 'se']:
        handle_step_edit(args)
    elif args.runbook_subcommand in ['step-rm', 'sr']:
        handle_step_rm(args)
    elif args.runbook_subcommand in ['step-renumber', 'srn']:
        handle_step_renumber(args)
    elif args.runbook_subcommand in ['export', 'exp']:
        handle_runbook_export(args)
    elif args.runbook_subcommand in ['render', 'rnd']:
        handle_runbook_render(args)
    elif args.runbook_subcommand in ['discuss', 'd']:
        handle_runbook_discuss(args)
    else:
        print(f"Unknown runbook subcommand: {args.runbook_subcommand}")


def _get_runbook_storage_path() -> Path:
    """Get the base path for runbook storage."""
    return Path.cwd() / "docs" / "maestro" / "runbooks"


def _ensure_runbook_storage() -> None:
    """Ensure runbook storage directories exist."""
    storage_path = _get_runbook_storage_path()
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "items").mkdir(exist_ok=True)
    (storage_path / "exports").mkdir(exist_ok=True)


def _load_index() -> List[Dict[str, Any]]:
    """Load the runbook index."""
    index_path = _get_runbook_storage_path() / "index.json"
    if not index_path.exists():
        return []
    with open(index_path, 'r') as f:
        return json.load(f)


def _save_index(index: List[Dict[str, Any]]) -> None:
    """Save the runbook index."""
    _ensure_runbook_storage()
    index_path = _get_runbook_storage_path() / "index.json"
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)


def _load_runbook(runbook_id: str) -> Optional[Dict[str, Any]]:
    """Load a runbook by ID."""
    runbook_path = _get_runbook_storage_path() / "items" / f"{runbook_id}.json"
    if not runbook_path.exists():
        return None
    with open(runbook_path, 'r') as f:
        return json.load(f)


def _save_runbook(runbook: Dict[str, Any]) -> None:
    """Save a runbook."""
    _ensure_runbook_storage()
    runbook_id = runbook['id']
    runbook_path = _get_runbook_storage_path() / "items" / f"{runbook_id}.json"
    with open(runbook_path, 'w') as f:
        json.dump(runbook, f, indent=2)


def _generate_runbook_id(title: str) -> str:
    """Generate a runbook ID from title."""
    # Simple ID generation: lowercase, replace spaces with dashes, limit length
    base_id = title.lower().replace(' ', '-')[:30]
    # Remove special characters
    base_id = ''.join(c for c in base_id if c.isalnum() or c == '-')

    # Check for conflicts and add suffix if needed
    index = _load_index()
    existing_ids = {item['id'] for item in index}

    if base_id not in existing_ids:
        return base_id

    # Add numeric suffix
    counter = 1
    while f"{base_id}-{counter}" in existing_ids:
        counter += 1
    return f"{base_id}-{counter}"


def handle_runbook_list(args: argparse.Namespace) -> None:
    """Handle the runbook list command."""
    index = _load_index()

    # Apply filters
    if hasattr(args, 'status') and args.status:
        index = [item for item in index if item.get('status') == args.status]
    if hasattr(args, 'scope') and args.scope:
        index = [item for item in index if item.get('scope') == args.scope]
    if hasattr(args, 'tag') and args.tag:
        index = [item for item in index if args.tag in item.get('tags', [])]

    if not index:
        print("No runbooks found.")
        return

    print(f"Found {len(index)} runbook(s):\n")
    for item in index:
        # Load full runbook to get scope (index doesn't store it)
        runbook = _load_runbook(item['id'])
        tags_str = ', '.join(item.get('tags', [])) if item.get('tags') else 'none'
        print(f"  {item['id']:<30} [{item.get('status', 'proposed'):>10}] {item['title']}")
        scope = runbook.get('scope', 'product') if runbook else 'product'
        print(f"  {'':30} scope: {scope:<20} tags: {tags_str}")
        print(f"  {'':30} updated: {item.get('updated_at', 'N/A')}")
        print()


def handle_runbook_show(args: argparse.Namespace) -> None:
    """Handle the runbook show command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    print(f"Runbook: {runbook['title']}")
    print(f"ID: {runbook['id']}")
    print(f"Status: {runbook.get('status', 'proposed')}")
    print(f"Scope: {runbook.get('scope', 'product')}")
    if runbook.get('tags'):
        print(f"Tags: {', '.join(runbook['tags'])}")
    print(f"Created: {runbook.get('created_at', 'N/A')}")
    print(f"Updated: {runbook.get('updated_at', 'N/A')}")

    context = runbook.get('context', {})
    if context.get('source_program'):
        print(f"Source Program: {context['source_program']}")
    if context.get('target_project'):
        print(f"Target Project: {context['target_project']}")

    steps = runbook.get('steps', [])
    if steps:
        print(f"\nSteps ({len(steps)}):")
        for step in steps:
            print(f"  {step['n']}. [{step['actor']}] {step['action']}")
            print(f"     Expected: {step['expected']}")
            if step.get('details'):
                print(f"     Details: {step['details']}")
            if step.get('variants'):
                print(f"     Variants: {', '.join(step['variants'])}")
    else:
        print("\nSteps: none")

    links = runbook.get('links', {})
    if links:
        if links.get('workflows'):
            print(f"\nLinked Workflows: {', '.join(links['workflows'])}")
        if links.get('issues'):
            print(f"Linked Issues: {', '.join(links['issues'])}")
        if links.get('tasks'):
            print(f"Linked Tasks: {', '.join(links['tasks'])}")


def handle_runbook_add(args: argparse.Namespace) -> None:
    """Handle the runbook add command."""
    runbook_id = _generate_runbook_id(args.title)
    now = datetime.now().isoformat()

    runbook = {
        'id': runbook_id,
        'title': args.title,
        'status': 'proposed',
        'scope': args.scope if hasattr(args, 'scope') and args.scope else 'product',
        'tags': args.tag if hasattr(args, 'tag') and args.tag else [],
        'context': {},
        'steps': [],
        'links': {
            'workflows': [],
            'issues': [],
            'tasks': []
        },
        'created_at': now,
        'updated_at': now
    }

    if hasattr(args, 'source_program') and args.source_program:
        runbook['context']['source_program'] = args.source_program
    if hasattr(args, 'target_project') and args.target_project:
        runbook['context']['target_project'] = args.target_project

    # Save runbook
    _save_runbook(runbook)

    # Update index
    index = _load_index()
    index.append({
        'id': runbook_id,
        'title': args.title,
        'tags': runbook['tags'],
        'status': 'proposed',
        'updated_at': now
    })
    _save_index(index)

    print(f"Created runbook: {runbook_id}")
    print(f"  Title: {args.title}")
    print(f"  Scope: {runbook['scope']}")


def handle_runbook_edit(args: argparse.Namespace) -> None:
    """Handle the runbook edit command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Update fields
    changed = False
    if hasattr(args, 'title') and args.title:
        runbook['title'] = args.title
        changed = True
    if hasattr(args, 'status') and args.status:
        runbook['status'] = args.status
        changed = True
    if hasattr(args, 'scope') and args.scope:
        runbook['scope'] = args.scope
        changed = True
    if hasattr(args, 'tag') and args.tag:
        runbook['tags'] = list(set(runbook.get('tags', []) + args.tag))
        changed = True

    if not changed:
        print("No changes specified.")
        return

    # Update timestamp
    runbook['updated_at'] = datetime.now().isoformat()

    # Save runbook
    _save_runbook(runbook)

    # Update index
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['title'] = runbook['title']
            item['status'] = runbook.get('status', 'proposed')
            item['tags'] = runbook.get('tags', [])
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Updated runbook: {args.id}")


def handle_runbook_rm(args: argparse.Namespace) -> None:
    """Handle the runbook rm command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Confirm unless --force
    if not (hasattr(args, 'force') and args.force):
        response = input(f"Delete runbook '{args.id}' ({runbook['title']})? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    # Delete file
    runbook_path = _get_runbook_storage_path() / "items" / f"{args.id}.json"
    runbook_path.unlink()

    # Update index
    index = _load_index()
    index = [item for item in index if item['id'] != args.id]
    _save_index(index)

    print(f"Deleted runbook: {args.id}")


def handle_step_add(args: argparse.Namespace) -> None:
    """Handle the step add command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    next_n = len(steps) + 1

    step = {
        'n': next_n,
        'actor': args.actor,
        'action': args.action,
        'expected': args.expected
    }

    if hasattr(args, 'details') and args.details:
        step['details'] = args.details
    if hasattr(args, 'variants') and args.variants:
        step['variants'] = args.variants

    steps.append(step)
    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()

    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Added step {next_n} to runbook {args.id}")


def handle_step_edit(args: argparse.Namespace) -> None:
    """Handle the step edit command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    step = next((s for s in steps if s['n'] == args.n), None)
    if not step:
        print(f"Error: Step {args.n} not found in runbook {args.id}.")
        return

    # Update fields
    changed = False
    if hasattr(args, 'actor') and args.actor:
        step['actor'] = args.actor
        changed = True
    if hasattr(args, 'action') and args.action:
        step['action'] = args.action
        changed = True
    if hasattr(args, 'expected') and args.expected:
        step['expected'] = args.expected
        changed = True
    if hasattr(args, 'details') and args.details:
        step['details'] = args.details
        changed = True

    if not changed:
        print("No changes specified.")
        return

    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Updated step {args.n} in runbook {args.id}")


def handle_step_rm(args: argparse.Namespace) -> None:
    """Handle the step rm command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    step = next((s for s in steps if s['n'] == args.n), None)
    if not step:
        print(f"Error: Step {args.n} not found in runbook {args.id}.")
        return

    # Remove step
    steps = [s for s in steps if s['n'] != args.n]

    # Renumber remaining steps
    for i, s in enumerate(sorted(steps, key=lambda x: x['n']), start=1):
        s['n'] = i

    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Removed step {args.n} from runbook {args.id} (steps renumbered)")


def handle_step_renumber(args: argparse.Namespace) -> None:
    """Handle the step renumber command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])

    # Renumber steps sequentially
    for i, step in enumerate(sorted(steps, key=lambda x: x['n']), start=1):
        step['n'] = i

    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Renumbered {len(steps)} steps in runbook {args.id}")


def handle_runbook_export(args: argparse.Namespace) -> None:
    """Handle the runbook export command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Determine output path
    if hasattr(args, 'out') and args.out:
        out_path = Path(args.out)
    else:
        _ensure_runbook_storage()
        out_path = _get_runbook_storage_path() / "exports" / f"{args.id}.{args.format}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == 'md':
        content = _export_runbook_md(runbook)
    elif args.format == 'puml':
        content = _export_runbook_puml(runbook)
    else:
        print(f"Error: Unknown format '{args.format}'")
        return

    with open(out_path, 'w') as f:
        f.write(content)

    print(f"Exported runbook {args.id} to {out_path}")


def _export_runbook_md(runbook: Dict[str, Any]) -> str:
    """Export runbook to Markdown format."""
    lines = []
    lines.append(f"# Runbook: {runbook['title']}\n")
    lines.append(f"**ID:** {runbook['id']}  ")
    lines.append(f"**Status:** {runbook.get('status', 'proposed')}  ")
    lines.append(f"**Scope:** {runbook.get('scope', 'product')}  ")
    if runbook.get('tags'):
        lines.append(f"**Tags:** {', '.join(runbook['tags'])}  ")
    lines.append(f"**Created:** {runbook.get('created_at', 'N/A')}  ")
    lines.append(f"**Updated:** {runbook.get('updated_at', 'N/A')}  ")
    lines.append("")

    context = runbook.get('context', {})
    if context:
        lines.append("## Context\n")
        if context.get('source_program'):
            lines.append(f"- **Source Program:** {context['source_program']}")
        if context.get('target_project'):
            lines.append(f"- **Target Project:** {context['target_project']}")
        lines.append("")

    steps = runbook.get('steps', [])
    if steps:
        lines.append("## Steps\n")
        for step in steps:
            lines.append(f"### Step {step['n']}: {step['action']}\n")
            lines.append(f"**Actor:** {step['actor']}  ")
            lines.append(f"**Expected:** {step['expected']}  ")
            if step.get('details'):
                lines.append(f"\n{step['details']}\n")
            if step.get('variants'):
                lines.append("\n**Variants:**")
                for variant in step['variants']:
                    lines.append(f"- {variant}")
                lines.append("")

    links = runbook.get('links', {})
    if any(links.get(k) for k in ['workflows', 'issues', 'tasks']):
        lines.append("## Links\n")
        if links.get('workflows'):
            lines.append(f"**Workflows:** {', '.join(links['workflows'])}  ")
        if links.get('issues'):
            lines.append(f"**Issues:** {', '.join(links['issues'])}  ")
        if links.get('tasks'):
            lines.append(f"**Tasks:** {', '.join(links['tasks'])}  ")

    return '\n'.join(lines)


def _export_runbook_puml(runbook: Dict[str, Any]) -> str:
    """Export runbook to PlantUML format (simple activity diagram)."""
    lines = []
    lines.append("@startuml")
    lines.append(f"title Runbook: {runbook['title']}")
    lines.append("")
    lines.append("start")

    steps = runbook.get('steps', [])
    for step in steps:
        lines.append(f":{step['action']}|{step['actor']};")
        lines.append(f"note right: {step['expected']}")
        if step.get('variants'):
            lines.append("if (variant?) then (yes)")
            for variant in step['variants']:
                lines.append(f"  :{variant};")
            lines.append("endif")

    lines.append("stop")
    lines.append("@enduml")

    return '\n'.join(lines)


def handle_runbook_render(args: argparse.Namespace) -> None:
    """Handle the runbook render command."""
    import subprocess

    # First export to PUML
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    _ensure_runbook_storage()
    puml_path = _get_runbook_storage_path() / "exports" / f"{args.id}.puml"
    puml_content = _export_runbook_puml(runbook)

    puml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(puml_path, 'w') as f:
        f.write(puml_content)

    # Determine SVG output path
    if hasattr(args, 'out') and args.out:
        svg_path = Path(args.out)
    else:
        svg_path = _get_runbook_storage_path() / "exports" / f"{args.id}.svg"

    # Render with PlantUML
    try:
        result = subprocess.run(
            ['/usr/bin/plantuml', '-tsvg', str(puml_path)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Rendered runbook {args.id} to {svg_path}")
        print(f"PUML source: {puml_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error rendering PlantUML: {e}")
        print(f"PUML source saved at: {puml_path}")
    except FileNotFoundError:
        print("Error: /usr/bin/plantuml not found. Install PlantUML to use this feature.")
        print(f"PUML source saved at: {puml_path}")


def handle_runbook_discuss(args: argparse.Namespace) -> None:
    """Handle the runbook discuss command (placeholder)."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    print(f"AI Discuss for runbook: {runbook['title']}")
    print("\n[PLACEHOLDER: AI Discussion Integration]")
    print("\nThis command will integrate with the existing discuss mechanism.")
    print("It will analyze the runbook and suggest CLI commands for:")
    print("  - Adding/refining steps")
    print("  - Converting to workflow graphs")
    print("  - Linking to issues/tasks")
    print("\nSuggested CLI commands:")
    print(f"  maestro runbook step-add {args.id} --actor user --action \"...\" --expected \"...\"")
    print(f"  maestro runbook export {args.id} --format puml")
    print(f"  maestro workflow create --from-runbook {args.id}")
