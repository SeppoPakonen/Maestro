#!/usr/bin/env python3
"""
Test script to verify the planner template functionality.
"""

import json
from maestro.planner_templates import (
    build_target_planner_template,
    fix_rulebook_planner_template,
    conversion_pipeline_planner_template
)

def test_build_target_template():
    """Test the build target planner template."""
    print("Testing build target planner template...")
    
    prompt = build_target_planner_template(
        repo_root="/path/to/repo",
        current_target_json='{"name": "example", "pipeline": {"steps": []}}',
        user_goals="Build the project with gcc",
        pipeline_summary="Previous builds were successful"
    )
    
    print(f"  Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "Repo root: /path/to/repo" in prompt
    assert "Strict JSON output only" in prompt
    print("  ✓ Build target template works correctly")


def test_fix_rulebook_template():
    """Test the fix rulebook planner template."""
    print("Testing fix rulebook planner template...")

    prompt = fix_rulebook_planner_template(
        current_rulebook_json='{"name": "example", "rules": []}',
        diagnostic_examples="Some diagnostic examples here",
        repo_info="Test repository"
    )

    print(f"  Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "Strict JSON output only" in prompt
    print("  ✓ Fix rulebook template works correctly")


def test_conversion_pipeline_template():
    """Test the conversion pipeline planner template."""
    print("Testing conversion pipeline planner template...")

    prompt = conversion_pipeline_planner_template(
        repo_inventory="Inventory of files",
        conversion_goal="Python to Go conversion",
        constraints="Must maintain functionality"
    )

    print(f"  Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "Strict JSON output only" in prompt
    print("  ✓ Conversion pipeline template works correctly")


def main():
    """Run all tests."""
    print("Running planner template tests...\n")
    
    test_build_target_template()
    test_fix_rulebook_template()
    test_conversion_pipeline_template()
    
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    main()