#!/usr/bin/env python3
"""
Test script for planner templates functionality.
This script tests that the planner template functions generate proper prompts
and that the JSON validation works correctly.
"""

import json
import tempfile
import os
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
        current_target_json="{}",
        user_goals="Build the project",
        pipeline_summary="Initial build"
    )
    
    print(f"Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "[ACCEPTANCE CRITERIA]" in prompt
    assert "[DELIVERABLES]" in prompt
    assert "build target JSON definition" in prompt
    assert "strict JSON output only" in prompt
    print("✓ Build target template generates proper prompt format")


def test_fix_rulebook_template():
    """Test the fix rulebook planner template."""
    print("Testing fix rulebook planner template...")
    
    prompt = fix_rulebook_planner_template(
        current_rulebook_json="{}",
        diagnostic_examples="Error: undefined reference",
        repo_info="MyRepo"
    )
    
    print(f"Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "[ACCEPTANCE CRITERIA]" in prompt
    assert "[DELIVERABLES]" in prompt
    assert "fix rulebook JSON definition" in prompt
    assert "strict JSON output only" in prompt
    print("✓ Fix rulebook template generates proper prompt format")


def test_conversion_pipeline_template():
    """Test the conversion pipeline planner template."""
    print("Testing conversion pipeline planner template...")
    
    prompt = conversion_pipeline_planner_template(
        repo_inventory="C++ project with Makefiles",
        conversion_goal="C++ to Rust conversion",
        constraints="Must maintain API compatibility"
    )
    
    print(f"Generated prompt length: {len(prompt)} characters")
    assert "[GOAL]" in prompt
    assert "[CONTEXT]" in prompt
    assert "[REQUIREMENTS]" in prompt
    assert "[ACCEPTANCE CRITERIA]" in prompt
    assert "[DELIVERABLES]" in prompt
    assert "conversion pipeline plan" in prompt
    assert "strict JSON output only" in prompt
    print("✓ Conversion pipeline template generates proper prompt format")


def test_json_validation():
    """Test basic JSON validation functionality."""
    print("Testing JSON validation...")
    
    # Valid JSON
    valid_json = '{"test": "value", "number": 42}'
    try:
        parsed = json.loads(valid_json)
        assert parsed["test"] == "value"
        assert parsed["number"] == 42
        print("✓ Valid JSON parsing works")
    except json.JSONDecodeError:
        assert False, "Valid JSON should parse successfully"
    
    # Invalid JSON
    invalid_json = '{"test": "value", "number":}'  # Missing value
    try:
        json.loads(invalid_json)
        assert False, "Invalid JSON should raise exception"
    except json.JSONDecodeError:
        print("✓ Invalid JSON correctly raises exception")


def test_template_context_inclusion():
    """Test that templates properly include context values."""
    print("Testing context inclusion in templates...")
    
    # Test build target template includes context
    prompt = build_target_planner_template(
        repo_root="/my/project",
        current_target_json='{"existing": "config"}',
        user_goals="Compile the application",
        pipeline_summary="Previous build succeeded"
    )
    assert "/my/project" in prompt
    assert "Compile the application" in prompt
    assert "Previous build succeeded" in prompt
    print("✓ Build target template includes context values")
    
    # Test fix rulebook template includes context
    prompt = fix_rulebook_planner_template(
        current_rulebook_json='{"rules": []}',
        diagnostic_examples="Segmentation fault in main.cpp",
        repo_info="Backend services"
    )
    assert "Segmentation fault in main.cpp" in prompt
    assert "Backend services" in prompt
    print("✓ Fix rulebook template includes context values")
    
    # Test conversion pipeline template includes context
    prompt = conversion_pipeline_planner_template(
        repo_inventory="Legacy Java codebase",
        conversion_goal="Java to Kotlin conversion",
        constraints="Maintain backward compatibility"
    )
    assert "Legacy Java codebase" in prompt
    assert "Java to Kotlin conversion" in prompt
    assert "Maintain backward compatibility" in prompt
    print("✓ Conversion pipeline template includes context values")


if __name__ == "__main__":
    print("Testing planner templates functionality...\n")
    
    try:
        test_build_target_template()
        test_fix_rulebook_template()
        test_conversion_pipeline_template()
        test_json_validation()
        test_template_context_inclusion()
        
        print("\n🎉 All tests passed! Planner templates are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)