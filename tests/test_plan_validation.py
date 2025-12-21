import os
import json
import tempfile
import unittest
from pathlib import Path

# Import the convert orchestrator to test its functionality
import convert_orchestrator


class TestConversionPlanSchema(unittest.TestCase):
    """Test the conversion plan schema and validation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "source")
        self.target_dir = os.path.join(self.test_dir, "target")
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.target_dir, exist_ok=True)
        
        # Create a test source file
        with open(os.path.join(self.source_dir, "test.py"), "w") as f:
            f.write("# Test Python file\nprint('hello')\n")
    
    def test_schema_exists(self):
        """Test that the schema file exists."""
        schema_path = ".maestro/convert/schemas/plan.schema.json"
        self.assertTrue(os.path.exists(schema_path), f"Schema file does not exist at {schema_path}")
    
    def test_plan_generation_creates_valid_json(self):
        """Test that plan generation creates valid JSON output."""
        # Set up directories in the .maestro structure
        os.makedirs(".maestro/convert/inventory", exist_ok=True)
        os.makedirs(".maestro/convert/plan", exist_ok=True)
        
        # Create basic inventory files
        source_inventory = {
            "files": [{"path": "test.py", "language": "Python", "size": 20}],
            "total_count": 1,
            "size_summary": {"total_bytes": 20}
        }
        target_inventory = {
            "files": [],
            "total_count": 0,
            "size_summary": {"total_bytes": 0}
        }
        
        with open(".maestro/convert/inventory/source_files.json", "w") as f:
            json.dump(source_inventory, f)
        
        with open(".maestro/convert/inventory/target_files.json", "w") as f:
            json.dump(target_inventory, f)
        
        # Import and use planner to generate a plan
        from planner import generate_conversion_plan
        
        plan_path = ".maestro/convert/plan/plan.json"
        plan = generate_conversion_plan(self.source_dir, self.target_dir, plan_path)
        
        # Check that plan contains required fields
        required_fields = ["plan_version", "pipeline_id", "intent", "created_at", "source", "target", "scaffold_tasks", "file_tasks", "final_sweep_tasks"]
        for field in required_fields:
            self.assertIn(field, plan, f"Plan missing required field: {field}")
        
        # Check that tasks exist and have required fields
        all_tasks = plan.get("scaffold_tasks", []) + plan.get("file_tasks", []) + plan.get("final_sweep_tasks", [])
        self.assertGreater(len(all_tasks), 0, "Plan should contain at least one task")
        
        # Check each task has required fields
        required_task_fields = ["task_id", "phase", "title", "engine", "status", "prompt_ref", "depends_on", "acceptance_criteria", "deliverables"]
        for task in all_tasks:
            for field in required_task_fields:
                self.assertIn(field, task, f"Task missing required field: {field}")
        
        # Check that the plan can be loaded from file
        with open(plan_path, "r") as f:
            loaded_plan = json.load(f)
        self.assertEqual(plan, loaded_plan)
    
    def test_validate_plan_function(self):
        """Test the validate_plan function with valid and invalid plans."""
        # Test with a valid plan structure
        valid_plan = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [],
            "final_sweep_tasks": [],
            "source_inventory": "/fake/path/that/does/not/exist.json"  # Make sure no real inventory exists
        }
        
        errors = convert_orchestrator.validate_plan(valid_plan)
        self.assertEqual(len(errors), 0, f"Valid plan should have no errors, but got: {errors}")
        
        # Test with a missing required field
        invalid_plan = valid_plan.copy()
        del invalid_plan["plan_version"]
        errors = convert_orchestrator.validate_plan(invalid_plan)
        self.assertGreater(len(errors), 0, "Invalid plan should have errors")
        self.assertTrue(any("plan_version" in error for error in errors), "Should report missing plan_version")
    
    def test_duplicate_task_ids_detection(self):
        """Test that duplicate task IDs are detected."""
        plan_with_duplicates = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "duplicate_id",
                    "phase": "file",
                    "title": "Test task 1",
                    "engine": "qwen",
                    "status": "pending",
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": [],
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test.py"],
                    "target_files": ["test.py"]
                },
                {
                    "task_id": "duplicate_id",  # Same ID
                    "phase": "file",
                    "title": "Test task 2",
                    "engine": "qwen",
                    "status": "pending",
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": [],
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test2.py"],
                    "target_files": ["test2.py"]
                }
            ],
            "final_sweep_tasks": []
        }
        
        errors = convert_orchestrator.validate_plan(plan_with_duplicates)
        self.assertGreater(len(errors), 0, "Plan with duplicate IDs should have errors")
        self.assertTrue(any("duplicate" in error.lower() for error in errors), "Should report duplicate task IDs")
    
    def test_invalid_status_detection(self):
        """Test that invalid statuses are detected."""
        plan_with_invalid_status = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "task_1",
                    "phase": "file",
                    "title": "Test task",
                    "engine": "qwen",
                    "status": "invalid_status",  # This is invalid
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": [],
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test.py"],
                    "target_files": ["test.py"]
                }
            ],
            "final_sweep_tasks": []
        }
        
        errors = convert_orchestrator.validate_plan(plan_with_invalid_status)
        self.assertGreater(len(errors), 0, "Plan with invalid status should have errors")
        self.assertTrue(any("status" in error.lower() for error in errors), "Should report invalid status")
    
    def test_invalid_engine_detection(self):
        """Test that invalid engines are detected."""
        plan_with_invalid_engine = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "task_1",
                    "phase": "file",
                    "title": "Test task",
                    "engine": "invalid_engine",  # This is not allowed
                    "status": "pending",
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": [],
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test.py"],
                    "target_files": ["test.py"]
                }
            ],
            "final_sweep_tasks": []
        }
        
        errors = convert_orchestrator.validate_plan(plan_with_invalid_engine)
        self.assertGreater(len(errors), 0, "Plan with invalid engine should have errors")
        self.assertTrue(any("engine" in error.lower() for error in errors), "Should report invalid engine")
    
    def test_dependency_cycle_detection(self):
        """Test that dependency cycles are detected."""
        plan_with_cycle = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "task_1",
                    "phase": "file",
                    "title": "Test task 1",
                    "engine": "qwen",
                    "status": "pending",
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": ["task_2"],  # Depends on task_2
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test.py"],
                    "target_files": ["test.py"]
                },
                {
                    "task_id": "task_2",
                    "phase": "file",
                    "title": "Test task 2",
                    "engine": "qwen",
                    "status": "pending",
                    "prompt_ref": "inputs/test.txt",
                    "depends_on": ["task_1"],  # Depends on task_1 - creating cycle
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test2.py"],
                    "target_files": ["test2.py"]
                }
            ],
            "final_sweep_tasks": []
        }
        
        errors = convert_orchestrator.validate_plan(plan_with_cycle)
        self.assertGreater(len(errors), 0, "Plan with dependency cycle should have errors")
        self.assertTrue(any("circular dependency" in error.lower() for error in errors), "Should report dependency cycle")
    
    def test_prompt_ref_validation(self):
        """Test that prompt_ref paths must be under inputs/."""
        plan_with_invalid_prompt_ref = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "intent": "test conversion",
            "created_at": "2023-01-01T00:00:00Z",
            "source": {"path": "/source"},
            "target": {"path": "/target"},
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "task_1",
                    "phase": "file",
                    "title": "Test task",
                    "engine": "qwen",
                    "status": "pending",
                    "prompt_ref": "invalid/path.txt",  # Not under inputs/
                    "depends_on": [],
                    "acceptance_criteria": ["Test criterion"],
                    "deliverables": ["test.txt"],
                    "source_files": ["test.py"],
                    "target_files": ["test.py"]
                }
            ],
            "final_sweep_tasks": []
        }
        
        errors = convert_orchestrator.validate_plan(plan_with_invalid_prompt_ref)
        self.assertGreater(len(errors), 0, "Plan with invalid prompt_ref should have errors")
        # JSON schema validation catches this error, which is the correct behavior
        self.assertTrue(any("does not match" in error for error in errors) or
                        any("not under inputs/" in error for error in errors), "Should report invalid prompt_ref path")


if __name__ == "__main__":
    unittest.main()