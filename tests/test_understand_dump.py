"""
Tests for the understand dump command and functionality.
"""
import os
import tempfile
from pathlib import Path
import pytest
from maestro.understand.introspector import ProjectIntrospector
from maestro.understand.renderer import MarkdownRenderer
from maestro.understand.command import handle_understand_dump


def test_introspector_gather_all():
    """Test that the introspector gathers all required data."""
    introspector = ProjectIntrospector()
    data = introspector.gather_all()
    
    # Check that all required sections exist
    assert "identity" in data
    assert "authority_model" in data
    assert "rule_gates" in data
    assert "mutation_boundaries" in data
    assert "automation_long_run" in data
    assert "directory_semantics" in data
    assert "contracts" in data
    assert "evidence_index" in data
    
    # Check that specific elements are present
    assert "plan_ops" in str(data["contracts"]).lower()
    assert "project_ops" in str(data["contracts"]).lower()
    assert any("invalid json" in item.lower() for item in data["rule_gates"].get("hard_stops", []))
    # Check for explore in automation_long_run content
    auto_run_str = str(data["automation_long_run"]).lower()
    assert "explore" in auto_run_str


def test_markdown_renderer():
    """Test that the markdown renderer produces expected output."""
    introspector = ProjectIntrospector()
    renderer = MarkdownRenderer(introspector)
    markdown_content = renderer.render()
    
    # Check that required sections are present in the output
    assert "## Identity" in markdown_content
    assert "## Authority Model" in markdown_content
    assert "## Assertive Rule Gates" in markdown_content
    assert "## Mutation Boundaries" in markdown_content
    assert "## Automation & Long-Run Mode" in markdown_content
    assert "## Directory Semantics" in markdown_content
    assert "## Contracts" in markdown_content
    assert "## Evidence Index" in markdown_content
    
    # Check that specific elements are mentioned
    assert "plan_ops" in markdown_content
    assert "project_ops" in markdown_content
    assert "explore" in markdown_content  # Look for "explore" instead of "explore sessions"
    assert ".maestro/" in markdown_content
    assert "$HOME/.maestro/" in markdown_content


def test_snapshot_generation_deterministic():
    """Test that snapshot generation is deterministic (same output for same input)."""
    introspector = ProjectIntrospector()
    renderer = MarkdownRenderer(introspector)
    
    # Generate the snapshot twice
    content1 = renderer.render()
    content2 = renderer.render()
    
    # They should be identical
    assert content1 == content2


def test_snapshot_command_with_output():
    """Test the snapshot command with custom output path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "custom_snapshot.md")
        
        # Run the command
        result = handle_understand_dump(output_path=output_path, check=False)
        
        # Should succeed
        assert result == 0
        
        # File should exist
        assert os.path.exists(output_path)
        
        # File should contain expected content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "## Identity" in content
            assert "## Authority Model" in content


def test_snapshot_command_check_mode_no_change():
    """Test the snapshot command with --check when no change is expected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "snapshot.md")
        
        # Generate initial snapshot
        result = handle_understand_dump(output_path=output_path, check=False)
        assert result == 0
        
        # Run in check mode - should succeed since no change
        result = handle_understand_dump(output_path=output_path, check=True)
        assert result == 0


def test_snapshot_command_check_mode_with_change():
    """Test the snapshot command with --check when change is expected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "snapshot.md")
        
        # Create a file with different content
        Path(output_path).write_text("Old content", encoding='utf-8')
        
        # Run in check mode - should fail since content differs
        result = handle_understand_dump(output_path=output_path, check=True)
        assert result == 1


def test_directory_semantics_section():
    """Test that directory semantics section exists and contains expected values."""
    introspector = ProjectIntrospector()
    renderer = MarkdownRenderer(introspector)
    markdown_content = renderer.render()
    
    # Check that directory semantics section exists and has the expected entries
    assert "## Directory Semantics" in markdown_content
    assert ".maestro/" in markdown_content
    assert "$HOME/.maestro/" in markdown_content


if __name__ == "__main__":
    pytest.main([__file__])