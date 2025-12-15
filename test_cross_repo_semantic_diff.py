#!/usr/bin/env python3
"""
Tests for Cross-Repo Semantic Diff Module
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from cross_repo_semantic_diff import CrossRepoSemanticDiff


class TestCrossRepoSemanticDiff(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create .maestro/convert directory structure
        self.maestro_dir = Path(".maestro/convert")
        self.maestro_dir.mkdir(parents=True, exist_ok=True)
        
        # Create semantics directory
        self.semantics_dir = self.maestro_dir / "semantics"
        self.semantics_dir.mkdir(exist_ok=True)
        
        # Create summaries directory
        self.summaries_dir = self.maestro_dir / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def create_test_semantic_report(self, task_id: str, semantic_equivalence: str = "high", 
                                   confidence: float = 0.8, risk_flags: list = None, 
                                   lost_concepts: list = None):
        """Helper to create a test semantic report."""
        if risk_flags is None:
            risk_flags = []
        if lost_concepts is None:
            lost_concepts = []
            
        report = {
            "semantic_equivalence": semantic_equivalence,
            "confidence": confidence,
            "preserved_concepts": ["functionality_core", "api_surface"] if semantic_equivalence != "low" else [],
            "changed_concepts": ["implementation_details"] if semantic_equivalence == "medium" else [],
            "lost_concepts": lost_concepts,
            "assumptions": ["default_assumption"],
            "risk_flags": risk_flags,
            "requires_human_review": semantic_equivalence == "low" or len(risk_flags) > 0
        }
        
        report_path = self.semantics_dir / f"task_{task_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        return report_path

    def create_test_summary(self, task_id: str, source_files: list = None, target_files: list = None):
        """Helper to create a test task summary."""
        if source_files is None:
            source_files = [f"src/file_{task_id}.py"]
        if target_files is None:
            target_files = [f"tgt/file_{task_id}.js"]
        
        summary = {
            "task_id": task_id,
            "source_files": source_files,
            "target_files": target_files,
            "timestamp": "2023-01-01T00:00:00",
            "write_policy": "convert",
            "semantic_decisions_taken": ["decision_1"],
            "warnings": [],
            "errors": []
        }
        
        summary_path = self.summaries_dir / f"task_{task_id}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        return summary_path

    def test_mapping_index_generation(self):
        """Test that mapping index is generated correctly."""
        # Create some test artifacts
        plan_data = {
            "coverage_map": {
                "tgt/file1.js": {"source_file": "src/file1.py", "policy": "convert"},
                "tgt/file2.js": {"source_file": "src/file2.py", "policy": "copy"}
            },
            "stages": [
                {
                    "tasks": [
                        {"task_id": "task1", "file_policy": "convert", "target_files": ["tgt/file1.js"], "source_file": "src/file1.py"}
                    ]
                }
            ]
        }
        plan_path = self.maestro_dir / "plan.json"
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, indent=2)

        # Create coverage file
        coverage_data = {"total_files": 10, "converted": 5, "copied": 3, "skipped": 2}
        coverage_path = self.maestro_dir / "coverage.json"
        with open(coverage_path, 'w', encoding='utf-8') as f:
            json.dump(coverage_data, f, indent=2)

        # Create semantic reports
        self.create_test_semantic_report("task1", "high")
        self.create_test_semantic_report("task2", "medium")

        # Create summary files
        self.create_test_summary("task1")
        self.create_test_summary("task2")

        # Create source and target directories for testing
        Path("src").mkdir(exist_ok=True)
        Path("tgt").mkdir(exist_ok=True)
        with open("src/file1.py", 'w') as f:
            f.write("# Test source file")
        with open("tgt/file1.js", 'w') as f:
            f.write("// Test target file")

        # Create and run the diff tool
        diff_tool = CrossRepoSemanticDiff()
        mapping_index = diff_tool.generate_mapping_index()

        # Verify mapping index structure
        self.assertIn("generated_at", mapping_index)
        self.assertIn("file_mapping", mapping_index)
        self.assertIn("concept_mapping", mapping_index)
        self.assertIn("evidence_refs", mapping_index)
        self.assertIn("conversion_stats", mapping_index)

        # Verify file mappings
        self.assertIn("tgt/file1.js", mapping_index["file_mapping"])
        self.assertEqual(mapping_index["file_mapping"]["tgt/file1.js"]["policy"], "convert")

    def test_semantic_diff_execution(self):
        """Test that semantic diff runs and produces reports."""
        # Create test semantic reports with different equivalence levels
        self.create_test_semantic_report("task1", "high", confidence=0.9)
        self.create_test_semantic_report("task2", "medium", confidence=0.7)
        self.create_test_semantic_report("task3", "low", confidence=0.4, risk_flags=["control_flow"])
        self.create_test_semantic_report("task4", "unknown", confidence=0.2, lost_concepts=["important_function"])

        # Create summary files
        self.create_test_summary("task1")
        self.create_test_summary("task2")
        self.create_test_summary("task3")
        self.create_test_summary("task4")

        # Create source and target files for heuristics
        Path("src").mkdir(exist_ok=True)
        Path("tgt").mkdir(exist_ok=True)
        with open("src/file1.py", 'w') as f:
            f.write("def important_function(): pass\nclass MyClass:\n    def method(self): pass")
        with open("tgt/file1.js", 'w') as f:
            f.write("function importantFunction() {}\nclass MyClass {\n  method() {}\n}")

        with open("src/file2.py", 'w') as f:
            f.write("import json, os\nx = 1")
        with open("tgt/file2.js", 'w') as f:
            f.write("const fs = require('fs');\nlet x = 1")

        # Create and run the diff tool
        diff_tool = CrossRepoSemanticDiff()

        # Mock the checkpoint creation to avoid actual sys.exit
        with patch.object(diff_tool, '_create_checkpoint_if_needed') as mock_create_checkpoint:
            # Generate mapping index first
            diff_tool.generate_mapping_index()

            diff_report = diff_tool.run_semantic_diff(top_n=10, output_format="json")

            # Verify report structure
            self.assertIn("file_equivalence", diff_report)
            self.assertIn("concept_coverage", diff_report)
            self.assertIn("loss_ledger", diff_report)
            self.assertIn("top_risk_hotspots", diff_report)
            self.assertIn("heuristics_evidence", diff_report)
            self.assertIn("drift_threshold_analysis", diff_report)

            # Verify concept coverage stats
            cc = diff_report["concept_coverage"]
            self.assertGreaterEqual(cc["total_concepts"], 0)
            self.assertEqual(cc["preserved_count"] + cc["changed_count"] + cc["lost_count"], cc["total_concepts"])

            # Verify file equivalence
            fe_list = diff_report["file_equivalence"]
            self.assertGreaterEqual(len(fe_list), 4)  # We created 4 reports

            # Check that files with low equivalence are identified as risk hotspots
            risk_hotspots = diff_report["top_risk_hotspots"]
            low_equiv_tasks = [fe["task_id"] for fe in fe_list if fe.get("semantic_equivalence") == "low"]
            if low_equiv_tasks:
                # At least one low equivalence task should appear in risk hotspots
                hotspot_task_ids = [hs["task_id"] for hs in risk_hotspots]
                self.assertTrue(any(task_id in hotspot_task_ids for task_id in low_equiv_tasks))

            # Verify that _create_checkpoint_if_needed was called if there was drift
            drift_analysis = diff_report["drift_threshold_analysis"]
            if drift_analysis.get("requires_checkpoint", False):
                self.assertTrue(mock_create_checkpoint.called)

    def test_drift_threshold_detection(self):
        """Test that drift thresholds are properly detected and checkpoints created."""
        # Create semantic reports that should trigger checkpoints
        self.create_test_semantic_report("task1", "low", confidence=0.3)
        self.create_test_semantic_report("task2", "low", confidence=0.2)
        self.create_test_semantic_report("task3", "unknown", confidence=0.1, lost_concepts=["concept1", "concept2", "concept3"])

        # Create summary files
        self.create_test_summary("task1")
        self.create_test_summary("task2")
        self.create_test_summary("task3")

        # Create source and target files
        Path("src").mkdir(exist_ok=True)
        Path("tgt").mkdir(exist_ok=True)
        with open("src/file1.py", 'w') as f:
            f.write("def func(): pass")
        with open("tgt/file1.js", 'w') as f:
            f.write("")

        # Create and run the diff tool
        diff_tool = CrossRepoSemanticDiff()

        # Mock the checkpoint creation to avoid actual sys.exit
        with patch.object(diff_tool, '_create_checkpoint_if_needed') as mock_create_checkpoint:
            # Create mapping index first to avoid generating it inside run_semantic_diff
            diff_tool.generate_mapping_index()

            diff_report = diff_tool.run_semantic_diff(top_n=10, output_format="json")

            # Verify drift analysis
            drift_analysis = diff_report["drift_threshold_analysis"]
            self.assertTrue(drift_analysis["requires_checkpoint"])

            # Verify that checkpoint reasons are provided
            self.assertGreater(len(drift_analysis["checkpoint_reasons"]), 0)

            # Verify that _create_checkpoint_if_needed was called
            self.assertTrue(mock_create_checkpoint.called)

    def test_checkpoint_creation(self):
        """Test that checkpoints are created when drift thresholds are exceeded."""
        # Create a fake drift analysis that requires a checkpoint
        drift_analysis = {
            "core_files_low_equivalence": 2,
            "low_equivalence_exceeds_threshold": True,
            "lost_concepts_count": 5,
            "lost_concepts_exceeds_threshold": True,
            "requires_checkpoint": True,
            "checkpoint_reasons": ["Low equivalence files count exceeds threshold"]
        }
        
        diff_tool = CrossRepoSemanticDiff()
        
        # Create the checkpoints directory first
        checkpoints_dir = Path(".maestro/convert/checkpoints")
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock sys.exit to prevent test termination
        with patch('sys.exit'):
            diff_tool._create_checkpoint_if_needed(drift_analysis)
        
        # Check that a checkpoint file was created
        checkpoint_files = list(checkpoints_dir.glob("semantic_drift_*.json"))
        self.assertGreater(len(checkpoint_files), 0)
        
        # Load and verify the checkpoint content
        checkpoint_path = checkpoint_files[0]
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        self.assertEqual(checkpoint_data["label"], "Semantic drift checkpoint")
        self.assertEqual(checkpoint_data["description"], "Automatically created due to semantic drift detection")
        self.assertIn("semantic_ok", checkpoint_data["requires"])
        self.assertIn("human_review", checkpoint_data["requires"])

    def test_baseline_comparison(self):
        """Test baseline comparison functionality."""
        # Create current semantic reports
        self.create_test_semantic_report("task1", "high", confidence=0.9)
        self.create_test_semantic_report("task2", "medium", confidence=0.7)
        
        # Create summary files
        self.create_test_summary("task1")
        self.create_test_summary("task2")

        # Create baseline directory and report
        baseline_dir = self.maestro_dir / "baselines" / "test_baseline"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        
        baseline_report = {
            "generated_at": "2023-01-01T00:00:00",
            "file_equivalence": [
                {
                    "task_id": "task1",
                    "semantic_equivalence": "high",
                    "confidence": 0.85
                },
                {
                    "task_id": "task2", 
                    "semantic_equivalence": "high",  # Different from current (medium)
                    "confidence": 0.80
                }
            ],
            "concept_coverage": {
                "preserved_count": 10,
                "changed_count": 2, 
                "lost_count": 1
            },
            "loss_ledger": [
                {
                    "task_id": "task1",
                    "lost_concepts": []
                }
            ]
        }
        
        baseline_report_path = baseline_dir / "diff_report.json"
        with open(baseline_report_path, 'w', encoding='utf-8') as f:
            json.dump(baseline_report, f, indent=2)

        # Create and run baseline comparison
        diff_tool = CrossRepoSemanticDiff()
        baseline_report = diff_tool._compare_with_baseline("test_baseline", top_n=10, filter_pattern=None, output_format="json")

        # Verify the baseline comparison structure
        self.assertIn("baseline_compared", baseline_report)
        self.assertEqual(baseline_report["baseline_compared"], "test_baseline")
        self.assertIn("concept_coverage_drift", baseline_report)
        self.assertIn("equivalence_changes", baseline_report)
        self.assertIn("loss_changes", baseline_report)
        self.assertIn("drift_summary", baseline_report)

        # Check that equivalence changes were detected
        equiv_changes = baseline_report["equivalence_changes"]
        changes_for_task2 = [ec for ec in equiv_changes if ec["task_id"] == "task2"]
        self.assertEqual(len(changes_for_task2), 1)
        if changes_for_task2:
            self.assertEqual(changes_for_task2[0]["from"], "high")
            self.assertEqual(changes_for_task2[0]["to"], "medium")

    def test_coverage_command(self):
        """Test the coverage command functionality."""
        # Create test semantic reports
        self.create_test_semantic_report("task1", "high", risk_flags=["control_flow"])
        self.create_test_semantic_report("task2", "medium", risk_flags=["memory"])
        self.create_test_semantic_report("task3", "low", lost_concepts=["important_concept"])

        # Create summary files
        self.create_test_summary("task1")
        self.create_test_summary("task2")
        self.create_test_summary("task3")

        # Create source and target files
        Path("src").mkdir(exist_ok=True)
        Path("tgt").mkdir(exist_ok=True)
        with open("src/file1.py", 'w') as f:
            f.write("def func(): pass")
        with open("tgt/file1.js", 'w') as f:
            f.write("function func() {}")

        # Create and run the diff tool to generate mapping index
        diff_tool = CrossRepoSemanticDiff()
        diff_tool.generate_mapping_index()

        # Capture the output of generate_coverage_report
        import io
        import sys
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            diff_tool.generate_coverage_report()
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        
        # Verify that the coverage report contains expected information
        self.assertIn("Semantic Coverage Report", output)
        self.assertIn("Glossary Concepts Total:", output)
        self.assertIn("Top 10 Risk Flags:", output)

    def test_deterministic_heuristics(self):
        """Test that deterministic heuristics are computed correctly."""
        # Create mapping index
        mapping_index = {
            "file_mapping": {
                "tgt/test.js": {"source_file": "src/test.py"}
            }
        }
        
        semantic_reports = {"task1": self.create_test_semantic_report("task1", "high")}
        task_summaries = {"task1": self.create_test_summary("task1", ["src/test.py"], ["tgt/test.js"])}

        # Create test files for heuristic analysis
        Path("src").mkdir(exist_ok=True)
        Path("tgt").mkdir(exist_ok=True)
        
        with open("src/test.py", 'w') as f:
            f.write("""
import json
import os

def main_function():
    data = {'key': 'value'}
    return json.dumps(data)

class MyClass:
    def method(self):
        pass
""")
        
        with open("tgt/test.js", 'w') as f:
            f.write("""
const fs = require('fs');

function mainFunction() {
    const data = {key: 'value'};
    return JSON.stringify(data);
}

class MyClass {
    method() {}
}
""")

        # Create and run the diff tool
        diff_tool = CrossRepoSemanticDiff()
        heuristics = diff_tool._compute_deterministic_heuristics(mapping_index, semantic_reports, task_summaries)

        # Verify heuristics were computed
        self.assertIn("file_size_deltas", heuristics)
        self.assertIn("function_class_counts", heuristics)
        self.assertIn("dependency_graph_deltas", heuristics)

        if "tgt/test.js" in heuristics["file_size_deltas"]:
            size_delta = heuristics["file_size_deltas"]["tgt/test.js"]
            self.assertIn("source_size", size_delta)
            self.assertIn("target_size", size_delta)
            self.assertIn("delta", size_delta)

        if "tgt/test.js" in heuristics["function_class_counts"]:
            func_counts = heuristics["function_class_counts"]["tgt/test.js"]
            self.assertIn("source_count", func_counts)
            self.assertIn("target_count", func_counts)


def run_tests():
    """Run all tests."""
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCrossRepoSemanticDiff)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)