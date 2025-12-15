import unittest
import json
import os
import tempfile
from maestro.confidence import ConfidenceScorer, BatchConfidenceAggregator, ConfidenceScore, ScoringModel
from datetime import datetime


class TestConfidenceScorer(unittest.TestCase):
    """Tests for the ConfidenceScorer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.test_dir, "model.json")
        
        # Create a test model
        test_model = {
            "version": "1.0",
            "scale": [0, 100],
            "weights": {
                "semantic_integrity": 0.35,
                "semantic_diff": 0.20,
                "drift_idempotency": 0.20,
                "checkpoints": 0.10,
                "open_issues": 0.10,
                "validation": 0.05
            },
            "penalties": {
                "semantic_low": 40,
                "semantic_medium": 15,
                "semantic_unknown": 8,
                "lost_concept": 3,
                "checkpoint_blocked": 10,
                "checkpoint_overridden": 6,
                "idempotency_failure": 20,
                "drift_detected": 15,
                "non_convergent": 25,
                "open_issue": 2,
                "validation_fail": 25
            },
            "floors": {
                "any_semantic_low": 30
            }
        }
        
        with open(self.model_path, 'w') as f:
            json.dump(test_model, f)
    
    def test_load_model(self):
        """Test loading a scoring model."""
        scorer = ConfidenceScorer(self.model_path)
        self.assertEqual(scorer.model.version, "1.0")
        self.assertEqual(scorer.model.weights["semantic_integrity"], 0.35)
    
    def test_compute_score_with_no_issues(self):
        """Test computing score when there are no issues (high confidence)."""
        scorer = ConfidenceScorer(self.model_path)
        
        # Create a test artifacts directory with good data
        artifacts_dir = tempfile.mkdtemp()
        
        # Create semantic summary with no issues
        semantic_summary = {
            "low_confidence_count": 0,
            "medium_confidence_count": 0,
            "unknown_count": 0,
            "total_issues": 0
        }
        with open(os.path.join(artifacts_dir, "semantic_summary.json"), 'w') as f:
            json.dump(semantic_summary, f)
        
        # Create diff report with no lost concepts
        diff_report = {"lost_concepts": 0}
        with open(os.path.join(artifacts_dir, "diff_report.json"), 'w') as f:
            json.dump(diff_report, f)
        
        # Create drift report with no issues
        drift_report = {
            "drift_detected_count": 0,
            "idempotency_failures": 0,
            "non_convergent_count": 0
        }
        with open(os.path.join(artifacts_dir, "drift_report.json"), 'w') as f:
            json.dump(drift_report, f)
        
        # Compute score
        score = scorer.compute_score("test_run_123", artifacts_dir)
        
        # The score should be high since there are no issues
        self.assertGreater(score.score, 70.0)
        self.assertIn(score.grade, ["A", "B"])
    
    def test_compute_score_with_semantic_low_penalty(self):
        """Test that semantic_low penalty is applied and floor is enforced."""
        scorer = ConfidenceScorer(self.model_path)
        
        # Create a test artifacts directory with semantic low issues
        artifacts_dir = tempfile.mkdtemp()
        
        # Create semantic summary with low confidence issues
        semantic_summary = {
            "low_confidence_count": 5,  # This should trigger the floor penalty
            "medium_confidence_count": 0,
            "unknown_count": 0,
            "total_issues": 5
        }
        with open(os.path.join(artifacts_dir, "semantic_summary.json"), 'w') as f:
            json.dump(semantic_summary, f)
        
        # Compute score - should be floored to 30 due to any_semantic_low rule
        score = scorer.compute_score("test_run_123", artifacts_dir)
        
        # Score should be at or below the floor (30)
        self.assertLessEqual(score.score, 30.0)

        # Check that the floor penalty was applied
        floor_penalty = next((p for p in score.penalties_applied
                             if p['penalty'] == 'floor_any_semantic_low'), None)
        self.assertIsNotNone(floor_penalty)
    
    def test_compute_score_with_checkpoints(self):
        """Test that checkpoint penalties are applied."""
        # Create a test artifacts directory first
        artifacts_dir = tempfile.mkdtemp()

        # Create semantic summary with no issues
        semantic_summary = {
            "low_confidence_count": 0,
            "medium_confidence_count": 0,
            "unknown_count": 0,
            "total_issues": 0
        }
        with open(os.path.join(artifacts_dir, "semantic_summary.json"), 'w') as f:
            json.dump(semantic_summary, f)

        # Create checkpoint report with blocked checkpoints
        checkpoint_report = {
            "checkpoint_blocked_count": 3,
            "checkpoint_overridden_count": 2
        }
        with open(os.path.join(artifacts_dir, "checkpoint_report.json"), 'w') as f:
            json.dump(checkpoint_report, f)

        # Now create the scorer and compute score
        scorer = ConfidenceScorer(self.model_path)
        score = scorer.compute_score("test_run_123", artifacts_dir)

        # Check that checkpoint penalties were applied
        checkpoint_penalties = [p for p in score.penalties_applied
                               if p['penalty'] in ['checkpoint_blocked', 'checkpoint_overridden']]

        # There should be at least one checkpoint-related penalty
        self.assertGreater(len(checkpoint_penalties), 0, f"No checkpoint penalties found. All penalties: {score.penalties_applied}")

        # Check if both specific penalties exist
        checkpoint_blocked_penalty = next((p for p in score.penalties_applied
                                          if p['penalty'] == 'checkpoint_blocked'), None)
        checkpoint_overridden_penalty = next((p for p in score.penalties_applied
                                             if p['penalty'] == 'checkpoint_overridden'), None)

        if checkpoint_blocked_penalty:
            self.assertEqual(checkpoint_blocked_penalty['count'], 3)
        if checkpoint_overridden_penalty:
            self.assertEqual(checkpoint_overridden_penalty['count'], 2)
    
    def test_save_confidence_report(self):
        """Test saving confidence report in both JSON and Markdown formats."""
        scorer = ConfidenceScorer(self.model_path)
        
        # Create a test artifacts directory
        artifacts_dir = tempfile.mkdtemp()
        
        # Create semantic summary
        semantic_summary = {
            "low_confidence_count": 0,
            "medium_confidence_count": 1,
            "unknown_count": 0,
            "total_issues": 1
        }
        with open(os.path.join(artifacts_dir, "semantic_summary.json"), 'w') as f:
            json.dump(semantic_summary, f)
        
        # Compute score
        score = scorer.compute_score("test_run_123", artifacts_dir)
        
        # Save the report
        scorer.save_confidence_report(score, artifacts_dir)
        
        # Check that both files were created
        json_path = os.path.join(artifacts_dir, "confidence.json")
        md_path = os.path.join(artifacts_dir, "confidence.md")
        
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))
        
        # Check that JSON file contains the score data
        with open(json_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["score"], score.score)
            self.assertEqual(data["grade"], score.grade)
            self.assertEqual(data["run_id"], score.run_id)


class TestBatchConfidenceAggregator(unittest.TestCase):
    """Tests for the BatchConfidenceAggregator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.test_dir, "model.json")
        
        # Create a test model
        test_model = {
            "version": "1.0",
            "scale": [0, 100],
            "weights": {
                "semantic_integrity": 0.35,
                "semantic_diff": 0.20,
                "drift_idempotency": 0.20,
                "checkpoints": 0.10,
                "open_issues": 0.10,
                "validation": 0.05
            },
            "penalties": {
                "semantic_low": 40,
                "semantic_medium": 15,
                "semantic_unknown": 8,
                "lost_concept": 3,
                "checkpoint_blocked": 10,
                "checkpoint_overridden": 6,
                "idempotency_failure": 20,
                "drift_detected": 15,
                "non_convergent": 25,
                "open_issue": 2,
                "validation_fail": 25
            },
            "floors": {
                "any_semantic_low": 30
            }
        }
        
        with open(self.model_path, 'w') as f:
            json.dump(test_model, f)
    
    def test_aggregate_min_method(self):
        """Test aggregation using min method."""
        aggregator = BatchConfidenceAggregator(self.model_path)
        
        # Create test scores
        score1 = ConfidenceScore(
            score=85.0,
            grade="B",
            breakdown={"semantic_integrity": 90, "drift_idempotency": 80},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        score2 = ConfidenceScore(
            score=75.0,
            grade="C",
            breakdown={"semantic_integrity": 80, "drift_idempotency": 70},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        score3 = ConfidenceScore(
            score=95.0,
            grade="A",
            breakdown={"semantic_integrity": 95, "drift_idempotency": 90},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        
        # Aggregate using min method
        result = aggregator.aggregate_scores([score1, score2, score3], "min")
        
        # Should return the minimum score
        self.assertEqual(result.score, 75.0)
        self.assertEqual(result.grade, "C")
    
    def test_aggregate_mean_method(self):
        """Test aggregation using mean method."""
        aggregator = BatchConfidenceAggregator(self.model_path)
        
        # Create test scores
        score1 = ConfidenceScore(
            score=85.0,
            grade="B",
            breakdown={"semantic_integrity": 90, "drift_idempotency": 80},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        score2 = ConfidenceScore(
            score=75.0,
            grade="C",
            breakdown={"semantic_integrity": 80, "drift_idempotency": 70},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        score3 = ConfidenceScore(
            score=95.0,
            grade="A",
            breakdown={"semantic_integrity": 95, "drift_idempotency": 90},
            penalties_applied=[],
            recommendations=[],
            evidence_refs=[]
        )
        
        # Aggregate using mean method
        result = aggregator.aggregate_scores([score1, score2, score3], "mean")
        
        # Should return the mean score
        expected_mean = (85.0 + 75.0 + 95.0) / 3
        self.assertAlmostEqual(result.score, expected_mean, places=1)
    
    def test_aggregate_empty_list(self):
        """Test aggregation with empty list."""
        aggregator = BatchConfidenceAggregator(self.model_path)
        
        # Aggregate empty list
        result = aggregator.aggregate_scores([], "min")
        
        # Should return default score
        self.assertEqual(result.score, 0)
        self.assertEqual(result.grade, "F")


if __name__ == '__main__':
    unittest.main()