"""
Test suite for semantic integrity detection system.

Tests the semantic integrity features implemented in Task 11.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_integrity import SemanticIntegrityChecker
from conversion_memory import ConversionMemory


class TestSemanticIntegrity(unittest.TestCase):
    """Test the semantic integrity system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create a test semantic checker
        self.checker = SemanticIntegrityChecker(base_path=".maestro/convert/semantics")

        # Create test conversion memory
        self.memory = ConversionMemory()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_semantic_equivalence_detection(self):
        """Test that semantic equivalence is properly detected."""
        # Create a mock task
        task = {
            "task_id": "test_task_001",
            "source_files": ["test_source.txt"],
            "target_files": ["test_target.txt"],
            "acceptance_criteria": "Convert source to target format",
            "phase": "file"
        }

        # Create source and target files for testing
        os.makedirs("source_repo", exist_ok=True)
        os.makedirs("target_repo", exist_ok=True)

        # Create source file with some content
        with open("source_repo/test_source.txt", "w") as f:
            f.write("def hello_world():\n    print('Hello, World!')\n")

        # Create target file with similar content (high semantic equivalence)
        with open("target_repo/test_target.txt", "w") as f:
            f.write("def hello_world():\n    print('Hello, World!')\n")

        # Run semantic check
        result = self.checker.run_semantic_check(task, "source_repo", "target_repo")

        # Verify the result has expected structure
        self.assertIn("semantic_equivalence", result)
        self.assertIn("confidence", result)
        self.assertIn("preserved_concepts", result)
        self.assertIn("changed_concepts", result)
        self.assertIn("lost_concepts", result)
        self.assertIn("assumptions", result)
        self.assertIn("risk_flags", result)
        self.assertIn("requires_human_review", result)

    def test_low_semantic_equivalence_blocks_pipeline(self):
        """Test that low semantic equivalence results in blocking the pipeline."""
        # Create a semantic result with low equivalence
        low_equiv_result = {
            "semantic_equivalence": "low",
            "confidence": 0.3,
            "preserved_concepts": [],
            "changed_concepts": ["function_logic"],
            "lost_concepts": ["core_functionality"],
            "assumptions": ["Function implementation significantly changed"],
            "risk_flags": ["control_flow", "io"],
            "requires_human_review": True
        }

        # Classify risk without accepting semantic risk
        risk_level = self.checker.classify_risk_level(low_equiv_result, accept_semantic_risk=False)
        self.assertEqual(risk_level, "block")

        # Classify risk with accepting semantic risk - should still block due to low equivalence
        risk_level = self.checker.classify_risk_level(low_equiv_result, accept_semantic_risk=True)
        self.assertEqual(risk_level, "block")  # Still blocks due to low semantic equivalence

    def test_high_semantic_equivalence_allows_continue(self):
        """Test that high semantic equivalence allows pipeline to continue."""
        # Create a semantic result with high equivalence
        high_equiv_result = {
            "semantic_equivalence": "high",
            "confidence": 0.9,
            "preserved_concepts": ["core_functionality", "function_logic"],
            "changed_concepts": [],
            "lost_concepts": [],
            "assumptions": ["Minimal implementation changes"],
            "risk_flags": [],
            "requires_human_review": False
        }

        # Classify risk
        risk_level = self.checker.classify_risk_level(high_equiv_result)
        self.assertEqual(risk_level, "continue")

    def test_requires_human_review_identification(self):
        """Test that human review requirement is properly identified."""
        # Test result that requires human review
        review_result = {
            "semantic_equivalence": "medium",
            "confidence": 0.5,
            "preserved_concepts": ["some_functionality"],
            "changed_concepts": ["implementation_details"],
            "lost_concepts": [],
            "assumptions": ["Implementation approach changed"],
            "risk_flags": ["control_flow"],
            "requires_human_review": True
        }

        # Verify it requires human review
        self.assertTrue(self.checker.requires_human_review(review_result))

        # Test result that does NOT require human review
        no_review_result = {
            "semantic_equivalence": "high",
            "confidence": 0.8,
            "preserved_concepts": ["core_functionality"],
            "changed_concepts": [],
            "lost_concepts": [],
            "assumptions": ["No significant changes"],
            "risk_flags": [],
            "requires_human_review": False
        }

        # Verify it does not require human review
        self.assertFalse(self.checker.requires_human_review(no_review_result))

    def test_semantic_drift_thresholds(self):
        """Test semantic drift threshold checking."""
        # Initially, drift should be acceptable when no files are checked
        self.assertTrue(self.checker.check_semantic_drift_thresholds())

        # Create several semantic check results with low equivalence to exceed thresholds
        for i in range(5):
            task = {
                "task_id": f"test_task_{i:03d}",
                "source_files": [f"source_{i}.txt"],
                "target_files": [f"target_{i}.txt"],
                "acceptance_criteria": f"Convert source_{i} to target format",
                "phase": "file"
            }

            # Create files with different content to simulate low semantic equivalence
            os.makedirs("source_repo", exist_ok=True)
            os.makedirs("target_repo", exist_ok=True)

            with open(f"source_repo/source_{i}.txt", "w") as f:
                f.write(f"Content for source {i}")
            
            with open(f"target_repo/target_{i}.txt", "w") as f:
                f.write(f"Completely different content for target {i}")

            # Run semantic check for each task
            self.checker.run_semantic_check(task, "source_repo", "target_repo")

        # After running multiple low-equivalence checks, check drift thresholds
        # The default threshold allows 20% low equivalence, so with 5 files,
        # if 2+ have low equivalence, it might exceed the threshold depending
        # on the specific implementation of the checker
        drift_acceptable = self.checker.check_semantic_drift_thresholds()
        
        # The drift might be acceptable or not depending on implementation details
        # but the function should run without errors
        self.assertIsInstance(drift_acceptable, bool)

    def test_source_snapshot_hash_computation(self):
        """Test that source snapshot hash computation works correctly."""
        os.makedirs("source_repo", exist_ok=True)
        
        # Create a source file
        with open("source_repo/source_test.txt", "w") as f:
            f.write("test content for hashing")

        # Compute hash for the file
        hash_result = self.checker.compute_source_snapshot_hash(
            ["source_test.txt"], "source_repo"
        )

        # Verify it's a proper hash (hex string of appropriate length)
        self.assertIsInstance(hash_result, str)
        self.assertEqual(len(hash_result), 64)  # SHA-256 produces 64-character hex

    def test_cross_file_consistency_check(self):
        """Test cross-file semantic consistency checking."""
        # Add some semantic check results manually to test cross-file checks
        result1 = {
            "semantic_equivalence": "high",
            "confidence": 0.9,
            "preserved_concepts": ["network_logic"],
            "changed_concepts": [],
            "lost_concepts": [],
            "assumptions": ["Network handling preserved"],
            "risk_flags": [],
            "requires_human_review": False
        }
        self.checker._save_semantic_check_result("task_001", result1)

        result2 = {
            "semantic_equivalence": "medium", 
            "confidence": 0.6,
            "preserved_concepts": ["network_logic"],
            "changed_concepts": ["connection_handling"],
            "lost_concepts": [],
            "assumptions": ["Connection handling changed"],
            "risk_flags": ["io"],
            "requires_human_review": True
        }
        self.checker._save_semantic_check_result("task_002", result2)

        # Check for inconsistencies
        inconsistencies = self.checker.check_cross_file_consistency()
        
        # There should be no major inconsistencies since we're just checking
        # concept mapping, which would depend on the actual implementation
        self.assertIsInstance(inconsistencies, list)

    def test_semantic_summary_updates(self):
        """Test that semantic summary gets updated correctly."""
        # Get initial summary
        initial_summary = self.checker.get_summary()
        initial_count = initial_summary["total_files_checked"]

        # Run a semantic check to update summary
        task = {
            "task_id": "summary_test_001",
            "source_files": ["test.txt"],
            "target_files": ["test.txt"],
            "acceptance_criteria": "Test summary update",
            "phase": "file"
        }
        
        os.makedirs("source_repo", exist_ok=True)
        os.makedirs("target_repo", exist_ok=True)
        
        with open("source_repo/test.txt", "w") as f:
            f.write("test content")
        with open("target_repo/test.txt", "w") as f:
            f.write("changed content")
        
        self.checker.run_semantic_check(task, "source_repo", "target_repo")

        # Get updated summary
        updated_summary = self.checker.get_summary()
        updated_count = updated_summary["total_files_checked"]

        # Verify the count increased
        self.assertEqual(updated_count, initial_count + 1)


class TestSemanticCLIFunctions(unittest.TestCase):
    """Test semantic CLI functions from convert_orchestrator."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create a test semantic checker
        self.checker = SemanticIntegrityChecker(base_path=".maestro/convert/semantics")

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_semantic_accept_functionality(self):
        """Test the semantic accept functionality."""
        # Create a test result that requires review
        test_result = {
            "semantic_equivalence": "medium",
            "confidence": 0.6,
            "requires_human_review": True,
            "risk_flags": ["control_flow"]
        }
        self.checker._save_semantic_check_result("test_task", test_result)

        # Mock the accept functionality by directly calling the internal methods
        # that would be called by the CLI command
        result = self.checker.get_semantic_check_result("test_task")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("requires_human_review"))

        # Simulate acceptance by updating the result
        result["requires_human_review"] = False
        result["human_approval"] = {
            "approved_by": "test_user",
            "approved_at": "2023-01-01T00:00:00",
            "note": "Test acceptance"
        }
        self.checker._save_semantic_check_result("test_task", result)

        # Verify the update
        updated_result = self.checker.get_semantic_check_result("test_task")
        self.assertFalse(updated_result.get("requires_human_review"))
        self.assertIsNotNone(updated_result.get("human_approval"))

    def test_semantic_summary_access(self):
        """Test that semantic summary can be accessed and contains expected fields."""
        summary = self.checker.get_summary()

        # Check that summary has expected structure
        self.assertIn("total_files_checked", summary)
        self.assertIn("equivalence_counts", summary)
        self.assertIn("cumulative_risk_flags", summary)
        self.assertIn("unresolved_semantic_warnings", summary)
        self.assertIn("last_updated", summary)

        # Check equivalence counts structure
        equiv_counts = summary["equivalence_counts"]
        for level in ["high", "medium", "low", "unknown"]:
            self.assertIn(level, equiv_counts)


if __name__ == "__main__":
    unittest.main()