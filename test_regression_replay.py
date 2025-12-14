#!/usr/bin/env python3
"""
Tests for the regression replay functionality.
"""

import unittest
import tempfile
import os
import json
import shutil
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regression_replay import (
    capture_run_manifest, 
    save_run_artifacts, 
    generate_drift_report,
    detect_structural_drift,
    detect_decision_drift,
    run_replay,
    analyze_convergence,
    get_all_runs,
    create_replay_baseline,
    get_baseline
)
from conversion_memory import ConversionMemory


class TestRegressionReplay(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "source")
        self.target_dir = os.path.join(self.test_dir, "target")
        os.makedirs(self.source_dir, exist_ok=True) 
        os.makedirs(self.target_dir, exist_ok=True)
        
        # Create some test files
        with open(os.path.join(self.source_dir, "test1.py"), 'w') as f:
            f.write("# Source file 1\nprint('hello')")
        with open(os.path.join(self.source_dir, "test2.py"), 'w') as f:
            f.write("# Source file 2\nx = 1")
        
        with open(os.path.join(self.target_dir, "test1.py"), 'w') as f:
            f.write("# Converted file 1\nprint('hello')")
        
        # Initialize conversion memory
        self.memory = ConversionMemory()
        
        # Set up .maestro directory
        os.makedirs(".maestro/convert/plan", exist_ok=True)
        os.makedirs(".maestro/convert/inventory", exist_ok=True)
        os.makedirs(".maestro/convert/runs", exist_ok=True)
        os.makedirs(".maestro/convert/baselines", exist_ok=True)
        
        # Create a simple plan file
        plan = {
            "scaffold_tasks": [],
            "file_tasks": [{
                "task_id": "convert_test1",
                "type": "file_conversion",
                "source_files": [os.path.join(self.source_dir, "test1.py")],
                "target_path": os.path.join(self.target_dir, "test1.py"),
                "status": "completed"
            }],
            "final_sweep_tasks": [],
            "decision_fingerprint": self.memory.compute_decision_fingerprint()
        }
        with open(".maestro/convert/plan/plan.json", 'w') as f:
            json.dump(plan, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(".maestro", ignore_errors=True)
    
    def test_capture_run_manifest(self):
        """Test capturing a run manifest."""
        flags_used = ["--limit 5", "--arbitrate"]
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        self.assertIsNotNone(manifest.run_id)
        self.assertEqual(manifest.source_path, self.source_dir)
        self.assertEqual(manifest.target_path, self.target_dir)
        self.assertEqual(manifest.flags_used, flags_used)
        self.assertEqual(manifest.engines_used, engines_used)
    
    def test_save_run_artifacts(self):
        """Test saving run artifacts."""
        flags_used = ["--limit 5"]
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        self.assertTrue(os.path.exists(run_dir))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "plan.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "decisions.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "environment.json")))
    
    def test_get_all_runs(self):
        """Test retrieving all runs."""
        # Create a test run
        flags_used = []
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        runs = get_all_runs()
        self.assertGreaterEqual(len(runs), 1)
        self.assertEqual(runs[0]["run_id"], manifest.run_id)
    
    def test_detect_structural_drift(self):
        """Test detecting structural drift."""
        # First save original state
        flags_used = []
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        # Create original hashes file for comparison
        import hashlib
        original_hashes = {}
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.target_dir)
                with open(file_path, 'rb') as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    original_hashes[rel_path] = file_hash
        
        # Save original hashes to replay artifacts
        replay_dir = os.path.join(run_dir, "replay")
        os.makedirs(replay_dir, exist_ok=True)
        target_before_path = os.path.join(replay_dir, "target_hashes_before.json")
        with open(target_before_path, 'w') as f:
            json.dump(original_hashes, f)
        
        # Test drift detection (should be no drift initially)
        drift_result = detect_structural_drift(manifest.run_id, self.target_dir)
        # This will return a message since we have original hashes now
        self.assertIn("drift_detected", drift_result)
    
    def test_detect_decision_drift(self):
        """Test detecting decision drift."""
        # Create a run
        flags_used = []
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        # Test decision drift detection
        drift_result = detect_decision_drift(manifest.run_id, self.memory)
        self.assertIn("drift_detected", drift_result)
    
    def test_generate_drift_report(self):
        """Test generating drift report."""
        # Create a run
        flags_used = []
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        # Generate drift report
        report = generate_drift_report(manifest.run_id, self.target_dir, self.memory)
        
        self.assertIsNotNone(report)
        self.assertEqual(report.run_id, manifest.run_id)
        self.assertIn("drift_detected", report.__dict__)
    
    def test_analyze_convergence(self):
        """Test convergence analysis."""
        # Create mock drift reports
        drift_reports = [
            {
                "structural_drift": {
                    "added_files": [],
                    "removed_files": [],
                    "modified_files": ["file1.py"]
                }
            },
            {
                "structural_drift": {
                    "added_files": [],
                    "removed_files": [],
                    "modified_files": []  # No changes = converged
                }
            }
        ]
        
        convergence = analyze_convergence(drift_reports, max_replay_rounds=2)
        
        self.assertTrue(convergence["is_convergent"])
        self.assertIn("converged", convergence)
    
    def test_create_replay_baseline(self):
        """Test creating a replay baseline."""
        # Create a run first
        flags_used = []
        engines_used = {"worker": "qwen", "judge": "codex"}
        
        manifest = capture_run_manifest(
            self.source_dir,
            self.target_dir,
            ".maestro/convert/plan/plan.json",
            self.memory,
            flags_used,
            engines_used
        )
        
        run_dir = save_run_artifacts(manifest, self.source_dir, self.target_dir, ".maestro/convert/plan/plan.json", self.memory)
        
        # Create baseline from run
        baseline_id = f"test_baseline_{manifest.run_id}"
        baseline_path = create_replay_baseline(manifest.run_id, baseline_id)
        
        self.assertTrue(os.path.exists(baseline_path))
        
        # Load and verify baseline
        baseline = get_baseline(baseline_id)
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline["baseline_id"], baseline_id)
        self.assertEqual(baseline["from_run_id"], manifest.run_id)


if __name__ == '__main__':
    # Create .maestro directory if it doesn't exist for the tests
    os.makedirs(".maestro/convert/plan", exist_ok=True)
    os.makedirs(".maestro/convert/inventory", exist_ok=True)
    os.makedirs(".maestro/convert/runs", exist_ok=True)
    os.makedirs(".maestro/convert/baselines", exist_ok=True)
    
    unittest.main()