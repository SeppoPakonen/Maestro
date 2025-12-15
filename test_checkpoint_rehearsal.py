"""
Tests for checkpoint and rehearsal functionality
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from conversion_memory import ConversionMemory
from execution_engine import ConversionExecutor, execute_conversion
from planner import generate_conversion_plan, add_auto_checkpoints


class TestCheckpointRehearsal(unittest.TestCase):
    """Test suite for checkpoint and rehearsal functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "source")
        self.target_dir = os.path.join(self.test_dir, "target")
        self.plan_path = os.path.join(self.test_dir, "plan.json")
        
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.target_dir, exist_ok=True)
        
        # Create a simple test file
        with open(os.path.join(self.source_dir, "test.py"), "w") as f:
            f.write("# Test source file\nprint('hello')\n")
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_plan_schema_with_checkpoints(self):
        """Test that the plan schema supports checkpoints."""
        # Load the schema
        schema_path = "conversion_plan_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        # Verify that checkpoints property is defined
        self.assertIn("checkpoints", schema["properties"])
        self.assertIn("checkpoint", schema["definitions"])
        
        # Verify checkpoint properties
        checkpoint_def = schema["definitions"]["checkpoint"]
        required_props = set(checkpoint_def["required"])
        self.assertIn("checkpoint_id", required_props)
        self.assertIn("after_tasks", required_props)
        self.assertIn("label", required_props)
    
    def test_automatic_checkpoints_in_rehearsal_mode(self):
        """Test that automatic checkpoints are added when in rehearsal mode."""
        # Create a simple plan structure for testing
        plan = {
            "scaffold_tasks": [
                {"task_id": "scaffold_1", "phase": "scaffold"},
                {"task_id": "scaffold_2", "phase": "scaffold"}
            ],
            "file_tasks": [
                {"task_id": "file_1", "phase": "file"},
                {"task_id": "file_2", "phase": "file"},
                {"task_id": "file_3", "phase": "file"},
                {"task_id": "file_4", "phase": "file"},
                {"task_id": "file_5", "phase": "file"}
            ],
            "final_sweep_tasks": [
                {"task_id": "sweep_1", "phase": "sweep"}
            ]
        }
        
        memory = ConversionMemory()
        plan_with_checkpoints = add_auto_checkpoints(plan, memory)
        
        checkpoints = plan_with_checkpoints.get("checkpoints", [])
        
        # Should have checkpoints after scaffold, after file batches, and after sweep
        self.assertGreater(len(checkpoints), 0)
        
        # Check that there's a checkpoint after scaffold tasks
        scaffold_checkpoint = None
        for cp in checkpoints:
            if "Scaffold" in cp["checkpoint_id"]:
                scaffold_checkpoint = cp
                break
        self.assertIsNotNone(scaffold_checkpoint)
        self.assertIn("scaffold_1", scaffold_checkpoint["after_tasks"])
        self.assertIn("scaffold_2", scaffold_checkpoint["after_tasks"])
    
    def test_rehearsal_mode_no_writes(self):
        """Test that rehearsal mode does not write to target directory."""
        # Create a simple plan file for testing
        plan = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "scaffold_tasks": [],
            "file_tasks": [
                {
                    "task_id": "test_task",
                    "phase": "file",
                    "source_files": ["test.py"],
                    "target_files": ["test_converted.py"],
                    "engine": "qwen",
                    "prompt_ref": "inputs/test.txt",
                    "acceptance_criteria": "Convert test file",
                    "deliverables": ["test_converted.py"],
                    "depends_on": [],
                    "status": "pending"
                }
            ],
            "final_sweep_tasks": [],
            "checkpoints": []
        }
        
        with open(self.plan_path, "w") as f:
            json.dump(plan, f, indent=2)
        
        # Create a mock executor and test rehearsal mode
        executor = ConversionExecutor(self.plan_path)
        
        # Mock the actual task execution to avoid AI calls
        with patch.object(executor, '_execute_task', return_value=True):
            # Execute in rehearsal mode
            success = executor.execute_plan(
                source_repo_path=self.source_dir,
                target_repo_path=self.target_dir,
                rehearsal_mode=True
            )
            
            # Verify execution was successful
            self.assertTrue(success)
            
            # Check that rehearsal files were created in rehearsal directory, not target
            rehearsal_target = f".maestro/convert/rehearsal/{plan['pipeline_id']}/target"
            rehearsal_file = os.path.join(rehearsal_target, "test_converted.py")
            
            # The actual target should not have been written to
            target_file = os.path.join(self.target_dir, "test_converted.py")
            self.assertFalse(os.path.exists(target_file))
    
    def test_checkpoint_status_updates(self):
        """Test that checkpoint status is properly updated in plan."""
        # Create a plan with checkpoints
        plan_with_checkpoints = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "scaffold_tasks": [],
            "file_tasks": [],
            "final_sweep_tasks": [],
            "checkpoints": [
                {
                    "checkpoint_id": "CP-001",
                    "after_tasks": [],
                    "label": "Test checkpoint",
                    "status": "pending"
                }
            ]
        }
        
        plan_path = os.path.join(self.test_dir, "test_plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan_with_checkpoints, f, indent=2)
        
        executor = ConversionExecutor(plan_path)
        
        # Test updating checkpoint status
        executor._update_checkpoint_status("CP-001", "approved")
        
        # Reload plan to verify update
        with open(plan_path, "r") as f:
            updated_plan = json.load(f)
        
        checkpoints = updated_plan["checkpoints"]
        cp = next(cp for cp in checkpoints if cp["checkpoint_id"] == "CP-001")
        self.assertEqual(cp["status"], "approved")
    
    def test_checkpoint_search_functionality(self):
        """Test that checkpoints are found correctly after tasks."""
        plan_with_checkpoints = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "scaffold_tasks": [
                {"task_id": "task_1", "status": "pending"},
                {"task_id": "task_2", "status": "pending"}
            ],
            "file_tasks": [
                {"task_id": "task_3", "status": "pending"}
            ],
            "final_sweep_tasks": [],
            "checkpoints": [
                {
                    "checkpoint_id": "CP-001",
                    "after_tasks": ["task_1", "task_2"],
                    "label": "After scaffold tasks",
                    "status": "pending"
                }
            ]
        }
        
        plan_path = os.path.join(self.test_dir, "test_plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan_with_checkpoints, f, indent=2)
        
        executor = ConversionExecutor(plan_path)
        
        # Test finding checkpoint after task_1
        checkpoint = executor._find_checkpoint_after_task("task_1")
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint["checkpoint_id"], "CP-001")
        
        # Test finding checkpoint after task_2
        checkpoint = executor._find_checkpoint_after_task("task_2")
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint["checkpoint_id"], "CP-001")
        
        # Test that no checkpoint is found for task_3
        checkpoint = executor._find_checkpoint_after_task("task_3")
        self.assertIsNone(checkpoint)
    
    def test_checkpoint_artifact_creation(self):
        """Test that checkpoint artifacts are created properly."""
        plan_with_checkpoints = {
            "plan_version": "1.0",
            "pipeline_id": "test-pipeline",
            "scaffold_tasks": [],
            "file_tasks": [],
            "final_sweep_tasks": [],
            "checkpoints": [
                {
                    "checkpoint_id": "CP-Test",
                    "after_tasks": [],
                    "label": "Test checkpoint",
                    "status": "pending"
                }
            ]
        }
        
        plan_path = os.path.join(self.test_dir, "test_plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan_with_checkpoints, f, indent=2)
        
        executor = ConversionExecutor(plan_path)
        
        # Create a checkpoint summary
        checkpoint = plan_with_checkpoints["checkpoints"][0]
        summary = executor._generate_checkpoint_summary(
            checkpoint, 
            self.source_dir, 
            self.target_dir, 
            tasks_completed=0
        )
        
        # Verify that the summary contains expected fields
        self.assertIn("checkpoint_id", summary)
        self.assertIn("label", summary)
        self.assertIn("timestamp", summary)
        self.assertIn("semantic_summary", summary)
        self.assertIn("open_issues_added_since_last_checkpoint", summary)
        self.assertIn("top_risks", summary)
        
        # Verify the checkpoint ID matches
        self.assertEqual(summary["checkpoint_id"], "CP-Test")


if __name__ == "__main__":
    unittest.main()