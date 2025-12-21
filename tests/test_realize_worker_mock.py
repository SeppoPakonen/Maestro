#!/usr/bin/env python3
"""
Test script to verify the realize worker implementation with mocked AI output.
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
from realize_worker import execute_file_task

def create_test_plan():
    """Create a simple test plan for the fixture scenario."""
    plan = {
        "plan_version": "1.0",
        "pipeline_id": "conversion-plan-test123",
        "intent": "Test conversion plan",
        "created_at": "2023-01-01T00:00:00Z",
        "source": {
            "path": "/tmp/source"
        },
        "target": {
            "path": "/tmp/target"
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

def test_with_mock_output():
    print("Testing realize worker with mocked AI output...")
    
    # Create temporary directories for source and target
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = os.path.join(temp_dir, "source")
        target_dir = os.path.join(temp_dir, "target")
        
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(target_dir, exist_ok=True)
        
        # Create a source file
        source_file = os.path.join(source_dir, "main.py")
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write('''#!/usr/bin/env python3
"""
Sample Python script for testing conversion
"""

def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
''')

        # Create a plan file
        plan = create_test_plan()
        plan_path = os.path.join(temp_dir, "plan.json")
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2)

        # Create maestro directories
        maestro_dir = os.path.join(temp_dir, ".maestro", "convert")
        os.makedirs(maestro_dir, exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "plan"), exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "inventory"), exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "inputs"), exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(maestro_dir, "diffs"), exist_ok=True)
        
        # Copy plan to expected location
        expected_plan_path = os.path.join(maestro_dir, "plan", "plan.json")
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
        
        with open(os.path.join(maestro_dir, "inventory", "source_files.json"), 'w', encoding='utf-8') as f:
            json.dump(source_inventory, f, indent=2)
        
        with open(os.path.join(maestro_dir, "inventory", "target_files.json"), 'w', encoding='utf-8') as f:
            json.dump(target_inventory, f, indent=2)
        
        print(f"Created test environment in {temp_dir}")
        print(f"Source dir: {source_dir}")
        print(f"Target dir: {target_dir}")
        print(f"Plan path: {expected_plan_path}")
        
        # Mock the run_engine function to return expected JSON output
        original_run_engine = None
        try:
            from realize_worker import run_engine
            
            # Save original function
            original_run_engine = run_engine
            
            # Create a mock version that returns JSON output
            def mock_run_engine(engine, prompt, cwd, stream=True, timeout=300, extra_args=None, verbose=False):
                # Return a mock JSON response that fits the expected format
                mock_output = '''{
    "files": [
        {
            "path": "main.py",
            "content": "# Converted Python file\\\\n#!/usr/bin/env python3\\\\n\\\\n\\"\\"\\"\\\\nConverted Python script for testing conversion\\\\n\\\"\\\"\\\"\\\\n\\\\ndef hello_world():\\\\n    print(\\"Hello, Converted World!\\")\\\\n\\\\nif __name__ == \\"__main__\\":\\\\n    hello_world()\\\\n"
        }
    ],
    "notes": "File converted from source Python to target Python",
    "warnings": []
}'''
                return 0, mock_output, ""  # exit_code, stdout, stderr
            
            # Replace the function temporarily
            import realize_worker
            realize_worker.run_engine = mock_run_engine
            
            # Change to temp dir and execute
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Execute the file task
                success = execute_file_task(
                    task=plan['file_tasks'][0],
                    source_repo_path=source_dir,
                    target_repo_path=target_dir,
                    verbose=True,
                    plan_path=expected_plan_path
                )
                
                print(f"Task execution result: {'SUCCESS' if success else 'FAILED'}")
                
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
                inputs_dir = os.path.join(maestro_dir, "inputs")
                outputs_dir = os.path.join(maestro_dir, "outputs")
                snapshots_dir = os.path.join(maestro_dir, "snapshots")
                diffs_dir = os.path.join(maestro_dir, "diffs")
                
                print(f"Checking audit artifacts:")
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
                    
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore original function if it was replaced
            if original_run_engine:
                import realize_worker
                realize_worker.run_engine = original_run_engine
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_with_mock_output()