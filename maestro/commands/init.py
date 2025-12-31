"""
Init command for Maestro CLI - Initialize a Maestro project.
"""
import os
import sys
from pathlib import Path
import argparse
from typing import Any


def add_init_parser(subparsers: Any) -> None:
    """Add init command parser."""
    init_parser = subparsers.add_parser(
        'init',
        aliases=[],
        help='Initialize Maestro in a repository',
        description='Initialize a Maestro project with required directories and configuration files.'
    )
    init_parser.add_argument(
        '--dir',
        help='Target directory to initialize (default: current directory)'
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Force initialization even if Maestro files already exist'
    )
    init_parser.set_defaults(func=handle_init_command)


def handle_init_command(args: argparse.Namespace) -> None:
    """Handle the init command."""
    print("Initializing Maestro project...")

    base_dir = Path(args.dir).resolve() if getattr(args, "dir", None) else Path.cwd()
    base_dir.mkdir(parents=True, exist_ok=True)

    # Define the directories to create
    required_dirs = [
        ".maestro",
        "docs",
        "docs/maestro",
        "docs/tracks",
        "docs/phases", 
        "docs/tasks",
        "docs/sessions",
        "docs/RepoRules.md"
    ]

    # Create required directories
    for dir_path in required_dirs:
        path = base_dir / dir_path
        if path.suffix == '.md':
            # This is a file, create parent directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # This is a directory
            path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {dir_path}")

    # Create Settings.md file if it doesn't exist or --force is used
    settings_path = base_dir / "docs/Settings.md"
    if not settings_path.exists() or args.force:
        settings_content = """# Maestro Settings

## Project Configuration
- Project name: [Your project name]
- Description: [Your project description]
- Root task: [Your root task]

## Default Settings
- Default track: 
- Default phase: 
- Default task status: active
- Default priority: medium

## AI Configuration
- Default model: [gpt-4, claude-3, etc.]
- Temperature: 0.7
- Max tokens: 2048

## Workflow Configuration
- Auto-commit breadcrumbs: true
- Auto-push: false
- Auto-backup: true

## Cost Tracking
- Track costs: true
- Cost limit: [set limit if needed]

## Extensions
- Enabled extensions: []
"""
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(settings_content)
        print(f"  Created: {settings_path}")
    else:
        print(f"  {settings_path} already exists. Use --force to overwrite.")

    # Create basic RepoRules.md if it doesn't exist or --force is used
    reporules_path = base_dir / "docs/RepoRules.md"
    if not reporules_path.exists() or args.force:
        reporules_content = """# Repository Rules

## General Rules
- All code must be documented
- Follow the established coding standards
- All tests must pass before committing

## Commit Rules
- Use conventional commits
- Keep commits small and focused
- Write meaningful commit messages

## Code Quality
- All code must pass linting
- Unit tests coverage > 80%
- All functions must have docstrings

## Branch Rules
- Use feature branches
- Branch names: feature/issue-number-description
- Main branch is protected

## Review Rules
- All PRs require at least one approval
- Changes to core logic require two approvals
- PRs must be linked to issues
"""
        with open(reporules_path, 'w', encoding='utf-8') as f:
            f.write(reporules_content)
        print(f"  Created: {reporules_path}")
    else:
        print(f"  {reporules_path} already exists. Use --force to overwrite.")

    print("\nMaestro project initialized successfully!")
    print("\nNext steps:")
    print("1. Customize docs/Settings.md with your project details")
    print("2. Customize docs/RepoRules.md with your repository rules")
    print("3. Start tracking work with 'maestro track add \"Your Track Name\"'")
