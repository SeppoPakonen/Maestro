#!/usr/bin/env python3
"""
Integration tests for Decision Override functionality via convert facade
"""

import unittest
import tempfile
import shutil
import os
from maestro.ui_facade.convert import list_decisions, get_decision, override_decision
from maestro.ui_facade.decisions import OverrideResult


class TestDecisionOverrideConvertFacade(unittest.TestCase):
    """Test the decision override functionality through the convert facade."""

    def setUp(self):
        """Set up a temporary directory for testing and redirect decisions storage."""
        self.test_dir = tempfile.mkdtemp()
        self.original_decisions_dir = "./.maestro/convert/decisions"
        
        # We don't need to manually redirect since the decisions module handles the storage
        # The decisions module will create the directory structure as needed

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_list_decisions_via_convert_facade(self):
        """Test listing decisions via the convert facade."""
        decisions = list_decisions()
        self.assertIsNotNone(decisions)
        self.assertGreater(len(decisions), 0)
        
        # Check for expected initial decision IDs
        decision_ids = [d['id'] for d in decisions]
        self.assertIn('D-001', decision_ids)
        self.assertIn('D-002', decision_ids)

    def test_get_specific_decision_via_convert_facade(self):
        """Test getting a specific decision via the convert facade."""
        # Get the first decision ID
        decisions = list_decisions()
        if decisions:
            decision_id = decisions[0]['id']
            decision = get_decision(decision_id)
            self.assertIsNotNone(decision)
            self.assertEqual(decision['id'], decision_id)

    def test_override_decision_via_convert_facade(self):
        """Test overriding a decision via the convert facade."""
        # First, get available decisions
        initial_decisions = list_decisions()
        self.assertGreater(len(initial_decisions), 0)
        
        # Override the first decision
        old_decision = initial_decisions[0]
        old_decision_id = old_decision['id']
        
        # Perform the override via convert facade
        result = override_decision(
            decision_id=old_decision_id,
            new_value="Updated via convert facade",
            reason="Test override via convert facade",
            auto_replan=True
        )
        
        # Verify the result
        self.assertIsInstance(result, OverrideResult)
        self.assertEqual(result.old_decision_id, old_decision_id)
        self.assertIsNotNone(result.new_decision_id)
        self.assertNotEqual(result.old_decision_id, result.new_decision_id)
        self.assertIsNotNone(result.old_fingerprint)
        self.assertIsNotNone(result.new_fingerprint)
        self.assertTrue(result.plan_is_stale)
        
        # Verify that the old decision is now superseded
        old_decision_after = get_decision(old_decision_id)
        self.assertEqual(old_decision_after['status'], 'superseded')
        self.assertEqual(old_decision_after['superseded_by'], result.new_decision_id)
        
        # Verify that the new decision exists
        new_decision = get_decision(result.new_decision_id)
        self.assertIsNotNone(new_decision)
        self.assertEqual(new_decision['status'], 'active')
        self.assertEqual(new_decision['value'], 'Updated via convert facade')
        self.assertEqual(new_decision['override_reason'], 'Test override via convert facade')

    def test_override_with_auto_replan_false(self):
        """Test that auto_replan=False affects the result."""
        # Get an initial decision
        initial_decisions = list_decisions()
        old_decision_id = initial_decisions[0]['id']
        
        # Override with auto_replan=False
        result = override_decision(
            decision_id=old_decision_id,
            new_value="Override with no auto replan",
            reason="Testing auto_replan flag",
            auto_replan=False
        )
        
        # The result should show plan_is_stale is False
        self.assertFalse(result.plan_is_stale)

    def test_error_handling_for_invalid_decision_id(self):
        """Test error handling when overriding a non-existent decision."""
        with self.assertRaises(ValueError) as context:
            override_decision(
                decision_id="INVALID-ID-123",
                new_value="This should fail",
                reason="Testing error handling",
                auto_replan=True
            )
        
        self.assertIn("not found", str(context.exception))


def run_integration_tests():
    """Run the integration tests."""
    print("Running Decision Override Integration Tests via Convert Facade...\n")
    
    # Create test instance and run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDecisionOverrideConvertFacade)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    
    if success:
        print("\n🎉 All Decision Override Integration tests passed!")
    else:
        print("\n💥 Some integration tests failed!")
        exit(1)