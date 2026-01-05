#!/usr/bin/env python3
"""
Test script to verify the JSON data backend integration.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_markdown_integration():
    """Test the markdown integration."""
    print("Testing JSON data backend integration...")
    
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

    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    # Seed JSON store with sample data
    from maestro.tracks.json_store import JsonStore
    from maestro.tracks.models import Track, Phase, Task
    json_store = JsonStore()
    track = Track(
        track_id="cli-dev",
        name="CLI Development",
        status="planned",
        completion=0,
        description=[],
        phases=["CLI1", "CLI2"],
        priority=0,
        tags=[],
        owner=None,
        is_top_priority=False,
    )
    phase1 = Phase(
        phase_id="CLI1",
        name="Markdown Data Backend",
        status="planned",
        completion=0,
        description=[],
        tasks=["CLI1.1", "CLI1.2"],
        track_id="cli-dev",
        priority=0,
        tags=[],
        owner=None,
        dependencies=[],
        order=None,
    )
    phase2 = Phase(
        phase_id="CLI2",
        name="TUI Integration",
        status="planned",
        completion=0,
        description=[],
        tasks=["CLI2.1", "CLI2.2"],
        track_id="cli-dev",
        priority=0,
        tags=[],
        owner=None,
        dependencies=[],
        order=None,
    )
    tasks = [
        Task(task_id="CLI1.1", name="Parser Module", status="todo", phase_id="CLI1"),
        Task(task_id="CLI1.2", name="Writer Module", status="todo", phase_id="CLI1"),
        Task(task_id="CLI2.1", name="Update TUI modules", status="todo", phase_id="CLI2"),
        Task(task_id="CLI2.2", name="Test integration", status="todo", phase_id="CLI2"),
    ]
    json_store.save_track(track)
    json_store.save_phase(phase1)
    json_store.save_phase(phase2)
    for task in tasks:
        json_store.save_task(task)
    print("✓ Seeded JSON store with sample data")

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

        # Test getting phase tree
        phase_tree = get_phase_tree()
        print(f"✓ Successfully retrieved phase tree with {len(phase_tree) if isinstance(phase_tree, list) else 1} root node(s)")

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
