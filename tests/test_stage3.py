#!/usr/bin/env python3
"""
Test script for Stage 3 (grow_from_main) implementation
"""
import os
import json
import tempfile
import shutil
from maestro.main import (
    ConversionPipeline, 
    ConversionStage, 
    create_conversion_pipeline,
    handle_convert_run,
    handle_convert_show,
    load_conversion_pipeline,
    run_grow_from_main_stage
)

def test_stage3_basic():
    """Test basic Stage 3 functionality"""
    print("Testing Stage 3 (grow_from_main) implementation...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")
        
        # Create some test files to simulate a codebase
        os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
        
        # Create main.py as entrypoint
        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write("#!/usr/bin/env python3\nprint('Hello, World!')\n")
        
        # Create a dependent module
        with open(os.path.join(temp_dir, "src", "helper.py"), "w") as f:
            f.write("# Helper module\ndef helper_function():\n    return 'Hello from helper'\n")
        
        # Change to temp directory to run tests
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Create a conversion pipeline
            pipeline = create_conversion_pipeline("test_pipeline", temp_dir, temp_dir)
            print(f"Created pipeline: {pipeline.name} (ID: {pipeline.id})")
            
            # Find the grow_from_main stage and run it
            grow_stage = next((s for s in pipeline.stages if s.name == "grow_from_main"), None)
            if grow_stage:
                print(f"Found grow_from_main stage: {grow_stage.status}")
                
                # Run the grow_from_main stage
                print("Running grow_from_main stage...")
                run_grow_from_main_stage(pipeline, grow_stage, verbose=True)
                
                print(f"Stage completed with status: {grow_stage.status}")
                print(f"Stage details: {json.dumps(grow_stage.details, indent=2)}")
                
                # Verify artifacts were created
                stage_dir = os.path.join(".maestro", "convert", "stages", "grow_from_main")
                expected_files = [
                    os.path.join(stage_dir, "stage.json"),
                    os.path.join(stage_dir, "inventory.json"),
                    os.path.join(stage_dir, "frontier.json"),
                    os.path.join(stage_dir, "included_set.json"),
                    os.path.join(stage_dir, "progress.json")
                ]
                
                print("\nChecking for expected artifacts:")
                for file_path in expected_files:
                    exists = os.path.exists(file_path)
                    print(f"  {file_path}: {'✓' if exists else '✗'}")
                
                # Test convert show command
                print("\nTesting convert show command:")
                handle_convert_show(verbose=True)
                
            else:
                print("ERROR: grow_from_main stage not found!")
                return False
                
        except Exception as e:
            print(f"ERROR during test: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            os.chdir(original_cwd)
    
    print("\nStage 3 basic test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_stage3_basic()
    if not success:
        exit(1)