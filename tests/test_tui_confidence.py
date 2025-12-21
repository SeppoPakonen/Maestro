"""
Test suite for Confidence Scoreboard TUI functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the project root to the path to import maestro modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from maestro.ui_facade.confidence import (
    get_confidence, get_confidence_components, get_confidence_gates, 
    get_confidence_trend, explain_confidence, simulate_promotion_gate,
    ConfidenceTier, ConfidenceComponent, ConfidenceGate, ConfidenceReport
)


class TestConfidenceFacade(unittest.TestCase):
    """Test the confidence facade functions."""
    
    def test_get_confidence(self):
        """Test getting confidence report."""
        report = get_confidence(scope="repo")
        
        # Check that we get a valid report
        self.assertIsInstance(report, ConfidenceReport)
        self.assertEqual(report.scope, "repo")
        self.assertGreaterEqual(report.overall_score, 0.0)
        self.assertLessEqual(report.overall_score, 1.0)
        self.assertIsInstance(report.tier, ConfidenceTier)
        self.assertIsInstance(report.components, list)
        self.assertIsInstance(report.gates, list)
        self.assertIn(report.promotion_ready, ["safe", "review_needed", "blocked"])
        
    def test_get_confidence_components(self):
        """Test getting confidence components."""
        components = get_confidence_components(scope="repo")
        
        self.assertIsInstance(components, list)
        self.assertGreater(len(components), 0)  # Should have at least one component
        
        for comp in components:
            self.assertIsInstance(comp, ConfidenceComponent)
            self.assertIsInstance(comp.id, str)
            self.assertIsInstance(comp.name, str)
            self.assertGreaterEqual(comp.score, 0.0)
            self.assertLessEqual(comp.score, 1.0)
            self.assertIn(comp.trend, ['up', 'down', 'stable', 'new'])
            self.assertIsInstance(comp.description, str)
            self.assertIsInstance(comp.evidence_link, str)
            self.assertIsInstance(comp.explanation, str)
    
    def test_get_confidence_gates(self):
        """Test getting confidence gates."""
        gates = get_confidence_gates(scope="repo")
        
        self.assertIsInstance(gates, list)
        self.assertGreater(len(gates), 0)  # Should have at least one gate
        
        for gate in gates:
            self.assertIsInstance(gate, ConfidenceGate)
            self.assertIsInstance(gate.id, str)
            self.assertIsInstance(gate.name, str)
            self.assertIsInstance(gate.status, bool)
            self.assertIsInstance(gate.reason, str)
            self.assertIsInstance(gate.priority, int)
    
    def test_get_confidence_trend(self):
        """Test getting confidence trend data."""
        trend_data = get_confidence_trend(scope="repo")
        
        self.assertIsInstance(trend_data, list)
        self.assertGreater(len(trend_data), 0)  # Should have at least one data point
        
        for point in trend_data:
            self.assertIsInstance(point, dict)
            self.assertIn('timestamp', point)
            self.assertIn('score', point)
            self.assertIn('label', point)
            self.assertGreaterEqual(point['score'], 0.0)
            self.assertLessEqual(point['score'], 1.0)
    
    def test_explain_confidence(self):
        """Test explaining confidence components."""
        explanation = explain_confidence("semantic_integrity")
        
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 0)
        
        # Test with invalid component ID
        invalid_explanation = explain_confidence("invalid_component")
        self.assertIn("No detailed explanation", invalid_explanation)
    
    def test_simulate_promotion_gate(self):
        """Test promotion gate simulation."""
        simulation = simulate_promotion_gate(scope="repo")
        
        self.assertIsInstance(simulation, dict)
        self.assertIn("would_pass_strict", simulation)
        self.assertIn("would_pass_standard", simulation)
        self.assertIn("would_pass_permissive", simulation)
        self.assertIn("critical_failures", simulation)
        self.assertIn("warnings", simulation)
        self.assertIn("recommendation", simulation)
        
        self.assertIsInstance(simulation["would_pass_strict"], bool)
        self.assertIsInstance(simulation["would_pass_standard"], bool)
        self.assertIsInstance(simulation["would_pass_permissive"], bool)
        self.assertIsInstance(simulation["critical_failures"], list)
        self.assertIsInstance(simulation["warnings"], list)
        self.assertIn(simulation["recommendation"], ["safe", "review_needed", "blocked"])


class TestConfidenceScreen(unittest.TestCase):
    """Test the confidence screen functionality."""
    
    @patch('maestro.ui_facade.confidence.get_confidence')
    def test_confidence_screen_initialization(self, mock_get_confidence):
        """Test that the confidence screen initializes correctly."""
        # Mock a confidence report
        mock_report = Mock(spec=ConfidenceReport)
        mock_report.id = "repo_confidence_test"
        mock_report.scope = "repo"
        mock_report.timestamp = datetime.now()
        mock_report.overall_score = 0.85
        mock_report.tier = ConfidenceTier.GREEN
        mock_report.components = []
        mock_report.gates = []
        mock_report.promotion_ready = "safe"
        mock_report.blocking_reasons = []
        mock_report.trend_data = []
        
        mock_get_confidence.return_value = mock_report
        
        # Import here to avoid issues with Textual dependency in test environments
        from maestro.tui.screens.confidence import ConfidenceScreen, ScoreBreakdown, GatesAndPromotion
        
        # Test ScoreBreakdown initialization
        score_breakdown = ScoreBreakdown(scope="repo")
        self.assertEqual(score_breakdown.scope, "repo")
        self.assertIsNone(score_breakdown.entity_id)
        
        # Test GatesAndPromotion initialization
        gates_promotion = GatesAndPromotion(scope="repo")
        self.assertEqual(gates_promotion.scope, "repo")
        self.assertIsNone(gates_promotion.entity_id)


class TestConfidenceIntegration(unittest.TestCase):
    """Test integration of confidence functionality."""
    
    def test_consistency_between_functions(self):
        """Test that related confidence functions return consistent data."""
        # Get the main confidence report
        main_report = get_confidence(scope="repo")
        
        # Get components and gates separately
        components = get_confidence_components(scope="repo")
        gates = get_confidence_gates(scope="repo")
        trend = get_confidence_trend(scope="repo")
        
        # Verify that the data is consistent
        self.assertEqual(len(components), len(main_report.components))
        self.assertEqual(len(gates), len(main_report.gates))
        self.assertEqual(len(trend), len(main_report.trend_data))
        
        # Verify that the overall score makes sense based on components
        if components:
            avg_score = sum(comp.score for comp in components) / len(components)
            # Allow for some difference due to internal calculations but they should be close
            self.assertAlmostEqual(main_report.overall_score, avg_score, places=1)
    
    def test_different_scopes(self):
        """Test that different scopes return different results."""
        repo_report = get_confidence(scope="repo")
        run_report = get_confidence(scope="run")
        baseline_report = get_confidence(scope="baseline")
        batch_report = get_confidence(scope="batch")
        
        # Each should be a valid report
        self.assertIsInstance(repo_report, ConfidenceReport)
        self.assertIsInstance(run_report, ConfidenceReport)
        self.assertIsInstance(baseline_report, ConfidenceReport)
        self.assertIsInstance(batch_report, ConfidenceReport)
        
        # Each should have the correct scope
        self.assertEqual(repo_report.scope, "repo")
        self.assertEqual(run_report.scope, "run")
        self.assertEqual(baseline_report.scope, "baseline")
        self.assertEqual(batch_report.scope, "batch")


if __name__ == '__main__':
    unittest.main()