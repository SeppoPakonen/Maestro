import os
import tempfile
import json
from pathlib import Path
import pytest

from maestro.repo.scanner import scan_upp_repo_v2


def test_repo_assemblies_virtual_buckets():
    """Test that assemblies are created including virtual assemblies (docs/tests/scripts)."""
    # Use the fixture directory
    fixture_dir = Path(__file__).parent / "fixtures" / "repos" / "batchscriptshell_min"
    
    # Run the scan
    result = scan_upp_repo_v2(str(fixture_dir), verbose=True)
    
    # Check that we have assemblies
    assert len(result.assemblies_detected) >= 1, f"Expected at least 1 assembly, got {len(result.assemblies_detected)}"
    
    # Get assembly names
    assembly_names = [asm.name for asm in result.assemblies_detected]
    
    # Check that we have the expected virtual assemblies
    # The root assembly should contain the cmake packages
    expected_virtual_assemblies = ['docs', 'tests', 'scripts']
    found_virtual_assemblies = [name for name in expected_virtual_assemblies if name in assembly_names]
    
    assert len(found_virtual_assemblies) >= 1, f"Expected at least one virtual assembly from {expected_virtual_assemblies}, found {found_virtual_assemblies}"
    
    # Check that docs assembly exists if docs directory exists
    if (fixture_dir / "docs").exists():
        assert "docs" in assembly_names, f"Expected 'docs' assembly in {assembly_names}"
    
    # Check that tests assembly exists if tests directory exists
    if (fixture_dir / "tests").exists():
        assert "tests" in assembly_names, f"Expected 'tests' assembly in {assembly_names}"
    
    # Check that scripts assembly exists if script files exist
    script_files = [f for f in fixture_dir.iterdir() if f.suffix in ['.sh', '.bat', '.cmd', '.ps1', '.py', '.pl', '.rb', '.js', '.ts']]
    if script_files:
        assert "scripts" in assembly_names, f"Expected 'scripts' assembly in {assembly_names}"
    
    print(f"Found assemblies: {assembly_names}")
    print(f"Found virtual assemblies: {found_virtual_assemblies}")


if __name__ == "__main__":
    test_repo_assemblies_virtual_buckets()
    print("Test passed: Assemblies and virtual buckets are created")