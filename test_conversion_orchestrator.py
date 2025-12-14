import json
import os
import tempfile
import shutil
from pathlib import Path
from inventory_generator import generate_inventory, save_inventory
from planner import generate_conversion_plan, validate_conversion_plan
from execution_engine import execute_conversion
from coverage_report import generate_coverage_report, validate_coverage_success

def test_inventory_generation():
    """Test that inventory generation works correctly."""
    print("Testing inventory generation...")
    
    # Create a temporary test directory with some sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        os.makedirs(os.path.join(temp_dir, "src"))
        os.makedirs(os.path.join(temp_dir, "tests"))
        
        # Create sample files with different extensions and purposes
        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write("# Main application file\nprint('Hello World')")
        
        with open(os.path.join(temp_dir, "src", "utils.py"), "w") as f:
            f.write("# Utility functions\n")
        
        with open(os.path.join(temp_dir, "tests", "test_main.py"), "w") as f:
            f.write("# Test file\n")
        
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# Test Project\n")
        
        # Generate inventory
        inventory = generate_inventory(temp_dir)
        
        # Verify expected properties
        assert inventory['total_count'] == 4, f"Expected 4 files, got {inventory['total_count']}"
        assert "Python" in inventory['by_language'], "Python language should be detected"
        assert "Markdown" in inventory['by_language'], "Markdown language should be detected"
        assert "documentation" in inventory['by_role'], "Documentation files should be identified"
        assert "test" in inventory['by_role'], "Test files should be identified"
        # Check if code-related roles exist (source, entrypoint, etc.)
        code_roles = ['source', 'entrypoint', 'configuration']
        has_code_file = any(role in inventory['by_role'] for role in code_roles)
        assert has_code_file, f"Expected code-related files to be identified, but found roles: {list(inventory['by_role'].keys())}"

        print("✓ Inventory generation test passed")
        return True

def test_plan_generation():
    """Test that plan generation creates proper JSON structure."""
    print("Testing plan generation...")
    
    with tempfile.TemporaryDirectory() as temp_source, tempfile.TemporaryDirectory() as temp_target:
        # Create sample files in source directory
        os.makedirs(os.path.join(temp_source, "src"))
        with open(os.path.join(temp_source, "main.py"), "w") as f:
            f.write("print('Hello World')")
        
        # Generate source inventory
        source_inventory = generate_inventory(temp_source)
        save_inventory(source_inventory, ".maestro/convert/inventory/source_files.json")
        
        # Generate target inventory (empty)
        target_inventory = generate_inventory(temp_target)
        save_inventory(target_inventory, ".maestro/convert/inventory/target_files.json")
        
        # Generate conversion plan
        plan_path = ".maestro/convert/plan/plan.json"
        plan = generate_conversion_plan(temp_source, temp_target, plan_path)
        
        # Validate plan structure
        errors = validate_conversion_plan(plan)
        assert not errors, f"Plan validation failed: {errors}"
        
        # Verify plan has required phases
        assert "scaffold_tasks" in plan
        assert "file_tasks" in plan
        assert "final_sweep_tasks" in plan
        
        # Verify file tasks exist and have proper structure
        assert len(plan['file_tasks']) > 0, "Should have file conversion tasks"
        
        # Verify each task has required fields
        for task in (plan['scaffold_tasks'] + plan['file_tasks'] + plan['final_sweep_tasks']):
            required_fields = ["task_id", "phase", "source_files", "engine", "prompt_ref", "acceptance_criteria", "deliverables", "depends_on", "status"]
            for field in required_fields:
                assert field in task, f"Task missing required field: {field}"
        
        print("✓ Plan generation test passed")
        return True

def test_execution_engine():
    """Test that execution engine can process tasks."""
    print("Testing execution engine...")
    
    with tempfile.TemporaryDirectory() as temp_source, tempfile.TemporaryDirectory() as temp_target:
        # Create sample files in source directory
        os.makedirs(os.path.join(temp_source, "src"))
        with open(os.path.join(temp_source, "main.py"), "w") as f:
            f.write("print('Hello World')")
        
        # Generate inventories
        source_inventory = generate_inventory(temp_source)
        target_inventory = generate_inventory(temp_target)
        
        save_inventory(source_inventory, ".maestro/convert/inventory/source_files.json")
        save_inventory(target_inventory, ".maestro/convert/inventory/target_files.json")
        
        # Generate plan
        plan_path = ".maestro/convert/plan/plan.json"
        plan = generate_conversion_plan(temp_source, temp_target, plan_path)
        
        # Limit execution to just a few tasks for testing
        success = execute_conversion(temp_source, temp_target, limit=2)
        
        assert success, "Execution should succeed"
        
        # Check that some outputs were created
        assert os.path.exists(".maestro/convert/outputs"), "Output directory should exist"
        
        print("✓ Execution engine test passed")
        return True

def test_coverage_report():
    """Test that coverage report generation works."""
    print("Testing coverage report generation...")
    
    with tempfile.TemporaryDirectory() as temp_source, tempfile.TemporaryDirectory() as temp_target:
        # Create sample files
        with open(os.path.join(temp_source, "main.py"), "w") as f:
            f.write("print('Hello World')")
        
        # Generate and save inventories
        source_inventory = generate_inventory(temp_source)
        target_inventory = generate_inventory(temp_target)
        
        save_inventory(source_inventory, ".maestro/convert/inventory/source_files.json")
        save_inventory(target_inventory, ".maestro/convert/inventory/target_files.json")
        
        # Generate a simple plan
        plan_path = ".maestro/convert/plan/plan.json"
        plan = generate_conversion_plan(temp_source, temp_target, plan_path)
        
        # Generate coverage report
        report_path = ".maestro/convert/reports/coverage.json"
        report = generate_coverage_report(
            ".maestro/convert/inventory/source_files.json",
            ".maestro/convert/inventory/target_files.json", 
            plan_path,
            report_path
        )
        
        # Verify report structure
        assert "total_source_files" in report
        assert "coverage_percentage" in report
        assert "unmapped_count" in report
        
        # Verify that we have the expected number of source files
        expected_files = len(source_inventory['files'])
        assert report['total_source_files'] == expected_files
        
        print("✓ Coverage report test passed")
        return True

def test_completion_guarantee():
    """Test that all source files are accounted for in the conversion plan."""
    print("Testing completion guarantee...")
    
    with tempfile.TemporaryDirectory() as temp_source, tempfile.TemporaryDirectory() as temp_target:
        # Create several files in source directory
        files_to_create = [
            "main.py",
            "utils.py", 
            "config.json",
            "README.md",
            "src/helper.py"
        ]
        
        for file_path in files_to_create:
            full_path = os.path.join(temp_source, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(f"Content of {file_path}")
        
        # Generate inventories
        source_inventory = generate_inventory(temp_source)
        target_inventory = generate_inventory(temp_target)
        
        save_inventory(source_inventory, ".maestro/convert/inventory/source_files.json")
        save_inventory(target_inventory, ".maestro/convert/inventory/target_files.json")
        
        # Generate plan
        plan_path = ".maestro/convert/plan/plan.json"
        plan = generate_conversion_plan(temp_source, temp_target, plan_path)
        
        # Count all source files mentioned in tasks
        all_source_files_in_tasks = set()
        for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
            for task in plan.get(phase, []):
                for source_file in task.get('source_files', []):
                    all_source_files_in_tasks.add(source_file)
        
        # Compare with files in source inventory
        source_files_in_inventory = {f['path'] for f in source_inventory['files']}
        
        assert all_source_files_in_tasks == source_files_in_inventory, \
            f"Not all source files are accounted for in plan: missing {source_files_in_inventory - all_source_files_in_tasks}"
        
        print("✓ Completion guarantee test passed")
        return True

def run_all_tests():
    """Run all generic conversion tests."""
    print("Running comprehensive conversion orchestrator tests...\n")
    
    tests = [
        test_inventory_generation,
        test_plan_generation, 
        test_execution_engine,
        test_coverage_report,
        test_completion_guarantee
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {str(e)}")
    
    print(f"\nTest results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Generic AI-driven conversion orchestrator is working correctly.")
        return True
    else:
        print("✗ Some tests failed.")
        return False

if __name__ == "__main__":
    run_all_tests()