"""
Command handler for the understand dump feature.
"""
import os
import sys
from pathlib import Path
from typing import Optional
from ..modules.utils import print_error, print_success, print_info, print_header
from .introspector import ProjectIntrospector
from .renderer import MarkdownRenderer


def handle_understand_dump(output_path: Optional[str] = None, check: bool = False) -> int:
    """Handle the understand dump command."""
    # Set default output path if not provided
    if output_path is None:
        output_path = "docs/UNDERSTANDING_SNAPSHOT.md"
    
    output_file = Path(output_path)
    
    # Create introspector and renderer
    introspector = ProjectIntrospector()
    renderer = MarkdownRenderer(introspector)
    
    # Generate the new snapshot
    new_content = renderer.render()
    
    # If --check is specified, compare with existing file
    if check:
        if output_file.exists():
            existing_content = output_file.read_text(encoding='utf-8')
            if new_content.strip() != existing_content.strip():
                print_error(f"Snapshot would change: {output_path}", 2)
                return 1  # Exit with non-zero status to indicate change
            else:
                print_success("Snapshot is up to date", 2)
                return 0
        else:
            print_error(f"Snapshot file does not exist: {output_path}", 2)
            return 1
    
    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the snapshot to the file
    output_file.write_text(new_content, encoding='utf-8')
    
    print_success(f"Project understanding snapshot written to: {output_path}", 2)
    return 0