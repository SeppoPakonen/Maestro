#!/usr/bin/env python3
"""
Test script to verify the realize worker implementation with plan_schema_fixture.
"""
import json
import os
import tempfile
import shutil
from pathlib import Path

def create_test_plan():
    """Create a simple test plan for the fixture scenario."""
    plan = {
        "plan_version": "1.0",
        "pipeline_id": "conversion-plan-test123",
        "intent": "Test conversion plan",
        "created_at": "2023-01-01T00:00:00Z",
        "source": {
            "path": "tools/convert_tests/scenarios/plan_schema_fixture/source_repo"
        },
        "target": {
            "path": "tools/convert_tests/scenarios/plan_schema_fixture/target_repo"
        },
        "scaffold_tasks": [],
        "file_tasks": [
            {
                "task_id": "task_file_convert_test",
                "phase": "file",
                "title": "Convert Python file",
                "source_files": ["main.py"],
                "target_files": ["main.py"],
                "engine": "qwen",
                "prompt_ref": "inputs/convert_python.txt",
                "acceptance_criteria": "Convert Python file to maintain functionality",
                "deliverables": ["main.py"],
                "depends_on": [],
                "status": "pending",
                "realization_action": "convert"
            }
        ],
        "final_sweep_tasks": [],
        "source_inventory": ".maestro/convert/inventory/source_files.json",
        "target_inventory": ".maestro/convert/inventory/target_files.json"
    }
    return plan

def main():
    print("Testing realize worker implementation...")
    
    # Create temporary directories for source and target
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = os.path.join(temp_dir, "source")
        target_dir = os.path.join(temp_dir, "target")
        
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy the fixture source files to our temp source directory
        fixture_source = "tools/convert_tests/scenarios/plan_schema_fixture/source_repo"
        if os.path.exists(fixture_source):
            for item in os.listdir(fixture_source):
                src_path = os.path.join(fixture_source, item)
                dst_path = os.path.join(source_dir, item)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                else:
                    shutil.copytree(src_path, dst_path)
        
        # Create a test plan
        plan = create_test_plan()
        plan_path = os.path.join(temp_dir, "plan.json")
        
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2)
        
        # Create the maestro directories
        os.makedirs(os.path.join(temp_dir, ".maestro", "convert", "plan"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, ".maestro", "convert", "inventory"), exist_ok=True)
        
        # Copy plan to the expected location
        expected_plan_path = os.path.join(temp_dir, ".maestro", "convert", "plan", "plan.json")
        shutil.copy2(plan_path, expected_plan_path)
        
        # Create dummy inventory files
        source_inventory = {
            "files": [
                {
                    "path": "main.py",
                    "language": "Python",
                    "size": 85
                }
            ],
            "total_count": 1,
            "size_summary": {
                "total_bytes": 85
            }
        }
        
        target_inventory = {
            "files": [],
            "total_count": 0,
            "size_summary": {
                "total_bytes": 0
            }
        }
        
        with open(os.path.join(temp_dir, ".maestro", "convert", "inventory", "source_files.json"), 'w', encoding='utf-8') as f:
            json.dump(source_inventory, f, indent=2)
        
        with open(os.path.join(temp_dir, ".maestro", "convert", "inventory", "target_files.json"), 'w', encoding='utf-8') as f:
            json.dump(target_inventory, f, indent=2)
        
        print(f"Created test environment in {temp_dir}")
        print(f"Source dir: {source_dir}")
        print(f"Target dir: {target_dir}")
        print(f"Plan path: {expected_plan_path}")
        
        # Test the execution engine with our file
        try:
            # Change to temp dir to make relative paths work correctly
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Import and run the execution engine
            from execution_engine import execute_conversion
            
            # Run only 1 task with limit to test the conversion
            success = execute_conversion(source_dir, target_dir, limit=1, resume=False)
            
            print(f"Conversion execution result: {'SUCCESS' if success else 'FAILED'}")
            
            # Check if output files were created
            target_main_py = os.path.join(target_dir, "main.py")
            if os.path.exists(target_main_py):
                print("✓ main.py was created in target directory")
                with open(target_main_py, 'r') as f:
                    content = f.read()
                    print(f"Target file content: {content[:100]}...")
            else:
                print("✗ main.py was NOT created in target directory")
            
            # Check if audit artifacts were created
            maestro_dir = os.path.join(temp_dir, ".maestro", "convert")
            inputs_dir = os.path.join(maestro_dir, "inputs")
            outputs_dir = os.path.join(maestro_dir, "outputs")
            snapshots_dir = os.path.join(maestro_dir, "snapshots")
            diffs_dir = os.path.join(maestro_dir, "diffs")
            
            print(f"Checking audit artifacts in {maestro_dir}:")
            print(f"  Inputs dir exists: {os.path.exists(inputs_dir)}")
            print(f"  Outputs dir exists: {os.path.exists(outputs_dir)}")
            print(f"  Snapshots dir exists: {os.path.exists(snapshots_dir)}")
            print(f"  Diffs dir exists: {os.path.exists(diffs_dir)}")
            
            if os.path.exists(inputs_dir):
                print(f"  Input files: {os.listdir(inputs_dir)}")
            if os.path.exists(outputs_dir):
                print(f"  Output files: {os.listdir(outputs_dir)}")
            if os.path.exists(snapshots_dir):
                print(f"  Snapshot files: {os.listdir(snapshots_dir)}")
            if os.path.exists(diffs_dir):
                print(f"  Diff files: {os.listdir(diffs_dir)}")
                
        except Exception as e:
            print(f"Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            os.chdir(original_cwd)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()