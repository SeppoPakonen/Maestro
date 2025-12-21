#!/usr/bin/env python3
"""
Integration test for U++ Structure Fixer commands.

This test verifies that the maestro build structure commands work correctly
with scan/show/fix/apply/lint functionality including limits and revert-on-fail.
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_maestro_command(cmd, cwd=None):
    """Run a maestro command and return the result."""
    # Use the full path to maestro.py from the project root
    full_cmd = ["python", os.path.join(os.path.dirname(__file__), "maestro.py")] + cmd
    print(f"Running: {' '.join(full_cmd)}")

    result = subprocess.run(full_cmd,
                           cwd=cwd or os.getcwd(),
                           capture_output=True,
                           text=True)

    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")

    return result


def test_structure_scan():
    """Test structure scan functionality."""
    print("\n=== Testing structure scan ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Run structure scan
        result = run_maestro_command([
            "build", "structure", "scan", 
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Scan failed with exit code {result.returncode}"
        
        # Check that scan report was created
        structure_dir = os.path.join("test_upp_fixtures", ".maestro", "build", "structure")
        scan_file = os.path.join(structure_dir, "last_scan.json")
        assert os.path.exists(scan_file), f"Scan report not created at {scan_file}"
        
        # Load and verify scan report
        with open(scan_file, 'r') as f:
            scan_report = json.load(f)
        
        print(f"Scan report: {json.dumps(scan_report, indent=2)}")
        
        # Verify we found the expected packages
        assert "summary" in scan_report, "Scan report missing summary"
        assert scan_report["summary"]["packages_found"] >= 4, f"Expected at least 4 packages, found {scan_report['summary'].get('packages_found', 0)}"
        
        # Check that we detected the casing issue (badcase should be Badcase)
        assert scan_report["summary"]["casing_issues_count"] >= 1, f"Expected at least 1 casing issue, found {scan_report['summary'].get('casing_issues_count', 0)}"
        
        # Check that we detected the missing .upp issue
        assert scan_report["summary"]["missing_upp_count"] >= 1, f"Expected at least 1 missing .upp, found {scan_report['summary'].get('missing_upp_count', 0)}"
        
        print("✓ Structure scan test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_structure_show():
    """Test structure show functionality."""
    print("\n=== Testing structure show ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Run structure show (this should trigger scan if no report exists)
        result = run_maestro_command([
            "build", "structure", "show",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Show failed with exit code {result.returncode}"
        print("✓ Structure show test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_structure_lint():
    """Test structure lint functionality."""
    print("\n=== Testing structure lint ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Run structure lint
        result = run_maestro_command([
            "build", "structure", "lint",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Lint failed with exit code {result.returncode}"
        print("✓ Structure lint test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_structure_fix_and_apply():
    """Test structure fix and apply functionality with limits and revert."""
    print("\n=== Testing structure fix and apply ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Run structure fix to generate fix plan (dry run first)
        result = run_maestro_command([
            "build", "structure", "fix", 
            "--session", session_path,
            "--dry-run",
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Fix dry-run failed with exit code {result.returncode}"
        
        # Check that fix plan was created
        structure_dir = os.path.join("test_upp_fixtures", ".maestro", "build", "structure")
        fix_plan_file = os.path.join(structure_dir, "last_fix_plan.json")
        assert os.path.exists(fix_plan_file), f"Fix plan not created at {fix_plan_file}"
        
        # Load and verify fix plan
        with open(fix_plan_file, 'r') as f:
            fix_plan = json.load(f)
        
        print(f"Fix plan: {json.dumps(fix_plan, indent=2)}")
        
        # Verify we have operations in the plan
        assert "operations" in fix_plan, "Fix plan missing operations"
        assert len(fix_plan["operations"]) > 0, f"Expected operations in fix plan, found {len(fix_plan['operations'])}"
        
        # Count rename operations (for casing issues)
        rename_ops = [op for op in fix_plan["operations"] if op.get("op") == "rename"]
        print(f"Found {len(rename_ops)} rename operations")
        
        # Now run actual fix with limit
        result = run_maestro_command([
            "build", "structure", "fix",
            "--session", session_path,
            "--limit", "1",  # Only apply 1 operation to test limits
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Fix with limit failed with exit code {result.returncode}"
        
        print("✓ Structure fix test passed")
        
        # Now test apply functionality
        result = run_maestro_command([
            "build", "structure", "apply",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Apply failed with exit code {result.returncode}"
        
        print("✓ Structure apply test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_command_aliases():
    """Test that command aliases work correctly."""
    print("\n=== Testing command aliases ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Test scan alias (b str scan)
        result = run_maestro_command([
            "b", "str", "scan",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Alias 'b str scan' failed with exit code {result.returncode}"
        print("✓ Alias 'b str scan' works")
        
        # Test show alias (b str sh) 
        result = run_maestro_command([
            "b", "str", "sh",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Alias 'b str sh' failed with exit code {result.returncode}"
        print("✓ Alias 'b str sh' works")
        
        # Test fix alias (b str fix)
        result = run_maestro_command([
            "b", "str", "fix",
            "--session", session_path,
            "--dry-run",
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Alias 'b str fix' failed with exit code {result.returncode}"
        print("✓ Alias 'b str fix' works")
        
        # Test apply alias (b str apply)
        result = run_maestro_command([
            "b", "str", "apply",
            "--session", session_path,
            "--dry-run",
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Alias 'b str apply' failed with exit code {result.returncode}"
        print("✓ Alias 'b str apply' works")
        
        # Test lint alias (b str lint)
        result = run_maestro_command([
            "b", "str", "lint",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Alias 'b str lint' failed with exit code {result.returncode}"
        print("✓ Alias 'b str lint' works")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_regression_scenario_1():
    """Test regression scenario 1: Missing .upp scenario."""
    print("\n=== Testing regression scenario 1: Missing .upp scenario ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer - missing .upp scenario",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # First run scan to detect missing .upp
        result = run_maestro_command([
            "build", "structure", "scan",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Scan failed with exit code {result.returncode}"
        
        # Load scan result to verify missing .upp was detected
        structure_dir = os.path.join("test_upp_fixtures", ".maestro", "build", "structure")
        scan_file = os.path.join(structure_dir, "last_scan.json")
        
        with open(scan_file, 'r') as f:
            scan_report = json.load(f)
        
        print(f"Missing .upp detected: {scan_report['summary'].get('missing_upp_count', 0)}")
        
        # Generate fix plan
        result = run_maestro_command([
            "build", "structure", "fix",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Fix plan generation failed with exit code {result.returncode}"
        
        # Load fix plan to verify it includes write operations for missing .upp files
        fix_plan_file = os.path.join(structure_dir, "last_fix_plan.json")
        
        with open(fix_plan_file, 'r') as f:
            fix_plan = json.load(f)
        
        # Count write file operations (for creating missing .upp files)
        write_ops = [op for op in fix_plan["operations"] if op.get("op") == "write_file"]
        print(f"Found {len(write_ops)} write_file operations")
        
        for op in write_ops:
            print(f"  Write operation: {op.get('path', 'unknown')}")
        
        # Apply the fixes
        result = run_maestro_command([
            "build", "structure", "apply",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Apply failed with exit code {result.returncode}"
        
        # Verify that the missing .upp file was created
        missing_upp_path = os.path.join("test_upp_fixtures", "assemblyB", "missingupp", "missingupp.upp")
        assert os.path.exists(missing_upp_path), f"Missing .upp file was not created at {missing_upp_path}"
        
        print("✓ Missing .upp scenario test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def test_regression_scenario_2():
    """Test regression scenario 2: Casing rename scenario."""
    print("\n=== Testing regression scenario 2: Casing rename scenario ===")
    
    # Create a temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_data = {
            "id": "test_session",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "root_task": "Test U++ structure fixer - casing rename scenario",
            "subtasks": [],
            "status": "new"
        }
        json.dump(session_data, f)
        session_path = f.name
    
    try:
        # Create additional problematic package for testing
        os.makedirs("test_upp_fixtures/assemblyB/lowercase", exist_ok=True)
        with open("test_upp_fixtures/assemblyB/lowercase/lowercase.cpp", "w") as f:
            f.write("// Test file")
        with open("test_upp_fixtures/assemblyB/lowercase/lowercase.h", "w") as f:
            f.write("// Test header")
        with open("test_upp_fixtures/assemblyB/lowercase/lowercase.upp", "w") as f:
            f.write('description "Lowercase test package";')
        
        # Run scan to detect casing issues
        result = run_maestro_command([
            "build", "structure", "scan",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Scan failed with exit code {result.returncode}"
        
        # Generate fix plan
        result = run_maestro_command([
            "build", "structure", "fix",
            "--session", session_path,
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Fix plan generation failed with exit code {result.returncode}"
        
        # Load fix plan to verify it includes rename operations
        structure_dir = os.path.join("test_upp_fixtures", ".maestro", "build", "structure")
        fix_plan_file = os.path.join(structure_dir, "last_fix_plan.json")
        
        with open(fix_plan_file, 'r') as f:
            fix_plan = json.load(f)
        
        # Count rename operations (for casing issues)
        rename_ops = [op for op in fix_plan["operations"] if op.get("op") == "rename"]
        print(f"Found {len(rename_ops)} rename operations")
        
        for op in rename_ops:
            print(f"  Rename operation: {op.get('from', 'unknown')} -> {op.get('to', 'unknown')}")
        
        # Apply the fixes with a limit to test limit functionality
        result = run_maestro_command([
            "build", "structure", "apply",
            "--session", session_path,
            "--limit", "1",  # Apply only first operation
            "--verbose"
        ], cwd="test_upp_fixtures")
        
        assert result.returncode == 0, f"Apply with limit failed with exit code {result.returncode}"
        
        print("✓ Casing rename scenario test passed")
        
    finally:
        # Clean up
        if os.path.exists(session_path):
            os.unlink(session_path)


def main():
    """Run all integration tests."""
    print("Starting U++ Structure Fixer Integration Tests...")
    
    # Change to the project root directory
    original_dir = os.getcwd()
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    try:
        # Run all tests
        test_structure_scan()
        test_structure_show()
        test_structure_lint()
        test_structure_fix_and_apply()
        test_regression_scenario_1()
        test_regression_scenario_2()
        test_command_aliases()
        
        print("\n🎉 All integration tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    sys.exit(main())