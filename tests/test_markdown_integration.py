#!/usr/bin/env python3
"""
Test script to verify the markdown data backend integration.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_markdown_integration():
    """Test the markdown integration."""
    print("Testing markdown data backend integration...")
    
    # Test importing the new phases module
    try:
        from maestro.ui_facade.phases import (
            get_phase_tree, list_phases, get_phase_details,
            get_active_phase, set_active_phase, kill_phase
        )
        print("✓ Successfully imported phases module")
    except ImportError as e:
        print(f"✗ Failed to import phases module: {e}")
        return False

    # Test creating sample markdown files if they don't exist
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    # Create sample todo.md if it doesn't exist
    todo_file = docs_dir / "todo.md"
    if not todo_file.exists():
        sample_todo = '''## Track: CLI Development

"created_at": "2024-01-01T00:00:00Z"

### Phase CLI1: Markdown Data Backend
"phase_id": "CLI1"
"created_at": "2024-01-01T00:00:00Z"
"status_emoji": "📋"

- [ ] **Task 1.1: Parser Module**
- [ ] **Task 1.2: Writer Module** 

### Phase CLI2: TUI Integration
"phase_id": "CLI2"
"created_at": "2024-01-02T00:00:00Z"
"status_emoji": "💡"

- [ ] **Task 2.1: Update TUI modules**
- [ ] **Task 2.2: Test integration**

## Track: Builder System

### Phase BLD1: Core Builder
"phase_id": "BLD1"
"created_at": "2024-01-03T00:00:00Z"
"status_emoji": "🚧"

- [x] **Task 3.1: Basic architecture**
- [ ] **Task 3.2: Add builder rules**
'''
        todo_file.write_text(sample_todo)
        print("✓ Created sample todo.md")
    else:
        print("✓ Found existing todo.md")

    # Create sample config.md if it doesn't exist
    config_file = docs_dir / "config.md"
    if not config_file.exists():
        sample_config = '''## Configuration

"active_phase_id": "CLI1"
"project_name": "Maestro"
"version": "1.0.0"
'''
        config_file.write_text(sample_config)
        print("✓ Created sample config.md")
    else:
        print("✓ Found existing config.md")

    # Test the functions
    try:
        # Test getting active phase first
        active_phase = get_active_phase("test_session")
        if active_phase:
            print(f"✓ Successfully retrieved active phase: {active_phase.label}")
        else:
            print("✓ Active phase retrieval attempted (may be None if not set)")

        # Test parsing the todo file directly to see if it works
        from maestro.data import parse_todo_md
        try:
            tracks_data = parse_todo_md("docs/todo.md")
            print(f"✓ Successfully parsed todo.md, found {len(tracks_data.get('tracks', []))} tracks")

            # List all phases found in the parsed data
            total_phases = 0
            for track in tracks_data.get('tracks', []):
                phases_in_track = track.get('phases', [])
                total_phases += len(phases_in_track)

            print(f"✓ Found {total_phases} phases in parsed tracks")

            # Test getting phase tree
            phase_tree = get_phase_tree()
            print(f"✓ Successfully retrieved phase tree with {len(phase_tree) if isinstance(phase_tree, list) else 1} root node(s)")

        except Exception as e:
            print(f"✗ Failed to parse todo.md directly: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Test listing phases
        phases = list_phases()
        print(f"✓ Successfully listed {len(phases)} phases via API")

        # Test getting phase details
        if phases:
            first_phase = phases[0]
            details = get_phase_details(first_phase.phase_id)
            if details:
                print(f"✓ Successfully retrieved details for phase: {details.label}")

        print("✓ All integration tests passed!")
        return True
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_markdown_integration()
    if success:
        print("\n✓ Markdown integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Markdown integration test failed!")
        sys.exit(1)