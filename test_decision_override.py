#!/usr/bin/env python3
"""
Tests for Decision Override functionality
This tests the backend logic without requiring UI interaction.
"""

import unittest
import tempfile
import shutil
import os
from maestro.ui_facade.decisions import DecisionManager, OverrideResult


class TestDecisionOverride(unittest.TestCase):
    """Test the decision override functionality."""

    def setUp(self):
        """Set up a temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        # Temporarily change the decisions directory for testing
        self.original_decisions_dir = "./.maestro/convert/decisions"
        self.test_decisions_dir = os.path.join(self.test_dir, ".maestro", "convert", "decisions")
        
        # Create the test directory structure
        os.makedirs(self.test_decisions_dir, exist_ok=True)
        
        # Mock the decision manager to use test directory
        self.dm = DecisionManager()
        self.dm.decisions_dir = self.test_decisions_dir

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_list_decisions_initial(self):
        """Test that initial decisions are loaded correctly."""
        decisions = self.dm.list_decisions()
        self.assertIsNotNone(decisions)
        self.assertGreater(len(decisions), 0)
        
        # Check that we have the expected initial decisions
        decision_ids = [d['id'] for d in decisions]
        self.assertIn('D-001', decision_ids)
        self.assertIn('D-002', decision_ids)

    def test_override_decision_creates_new_entry(self):
        """Test that overriding a decision creates a new entry."""
        # Get initial decisions
        initial_decisions = self.dm.list_decisions()
        initial_count = len(initial_decisions)
        
        # Override an existing decision
        old_decision_id = initial_decisions[0]['id']
        result = self.dm.override_decision(
            decision_id=old_decision_id,
            new_value="New decision value after override",
            reason="Testing override functionality",
            auto_replan=True
        )
        
        # Verify result structure
        self.assertIsInstance(result, OverrideResult)
        self.assertEqual(result.old_decision_id, old_decision_id)
        self.assertIsNotNone(result.new_decision_id)
        self.assertNotEqual(result.old_decision_id, result.new_decision_id)
        self.assertIsNotNone(result.old_fingerprint)
        self.assertIsNotNone(result.new_fingerprint)
        self.assertTrue(result.plan_is_stale)
        
        # Check that we now have more decisions
        updated_decisions = self.dm.list_decisions()
        self.assertEqual(len(updated_decisions), initial_count + 1)
        
        # Find the old and new decisions
        old_decision = None
        new_decision = None
        for d in updated_decisions:
            if d['id'] == old_decision_id:
                old_decision = d
            elif d['id'] == result.new_decision_id:
                new_decision = d
        
        # Verify old decision was marked as superseded
        self.assertIsNotNone(old_decision)
        self.assertEqual(old_decision['status'], 'superseded')
        self.assertEqual(old_decision['superseded_by'], result.new_decision_id)
        
        # Verify new decision is active and has correct properties
        self.assertIsNotNone(new_decision)
        self.assertEqual(new_decision['status'], 'active')
        self.assertEqual(new_decision['origin'], 'human_override')
        self.assertEqual(new_decision['override_reason'], 'Testing override functionality')
        self.assertEqual(new_decision['value'], 'New decision value after override')
        self.assertIn(old_decision_id, new_decision.get('supersedes', []))

    def test_override_nonexistent_decision_raises_error(self):
        """Test that attempting to override a nonexistent decision raises an error."""
        with self.assertRaises(ValueError) as context:
            self.dm.override_decision(
                decision_id="NONEXISTENT-123",
                new_value="This should fail",
                reason="Testing error handling",
                auto_replan=True
            )
        
        self.assertIn("not found", str(context.exception))

    def test_override_with_empty_values(self):
        """Test that the override function properly stores new values."""
        # Get an existing decision to override
        initial_decisions = self.dm.list_decisions()
        original_decision = initial_decisions[0]
        original_id = original_decision['id']
        
        # Override with specific new values
        result = self.dm.override_decision(
            decision_id=original_id,
            new_value="Completely new decision value",
            reason="Updated due to new requirements",
            auto_replan=False
        )
        
        # Verify the override happened correctly
        updated_decisions = self.dm.list_decisions()
        
        # Find the new decision
        new_decision = None
        for d in updated_decisions:
            if d['id'] == result.new_decision_id:
                new_decision = d
                break
        
        self.assertIsNotNone(new_decision)
        self.assertEqual(new_decision['value'], 'Completely new decision value')
        self.assertEqual(new_decision['reason'], 'Updated due to new requirements')
        self.assertFalse(result.plan_is_stale)  # Since auto_replan was False

    def test_decision_fingerprint_changes(self):
        """Test that fingerprints are different before and after override."""
        # Get an existing decision to override
        initial_decisions = self.dm.list_decisions()
        original_decision = initial_decisions[0]
        original_id = original_decision['id']
        
        # Override the decision
        result = self.dm.override_decision(
            decision_id=original_id,
            new_value="Modified decision content",
            reason="Fingerprint test",
            auto_replan=True
        )
        
        # The fingerprints should be different
        self.assertNotEqual(result.old_fingerprint, result.new_fingerprint)


def test_decision_override_facade_function():
    """Test the facade function directly."""
    print("Testing decision override facade function...")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    original_decisions_dir = "./.maestro/convert/decisions"
    test_decisions_dir = os.path.join(test_dir, ".maestro", "convert", "decisions")
    os.makedirs(test_decisions_dir, exist_ok=True)
    
    # Temporarily redirect the decisions manager to use test directory
    import maestro.ui_facade.decisions
    original_manager = maestro.ui_facade.decisions._decision_manager
    test_manager = DecisionManager()
    test_manager.decisions_dir = test_decisions_dir
    maestro.ui_facade.decisions._decision_manager = test_manager
    
    try:
        # Test the facade function
        from maestro.ui_facade.decisions import list_decisions, override_decision
        
        # List initial decisions
        decisions = list_decisions()
        print(f"Found {len(decisions)} initial decisions")
        
        if len(decisions) > 0:
            # Override the first decision
            old_id = decisions[0]['id']
            result = override_decision(
                decision_id=old_id,
                new_value="Test override via facade",
                reason="Testing facade function",
                auto_replan=True
            )
            
            print(f"Override result: {result.old_decision_id} -> {result.new_decision_id}")
            print("✅ Facade function test passed")
            return True
        else:
            print("❌ No decisions available for testing")
            return False
    except Exception as e:
        print(f"❌ Facade function test failed: {e}")
        return False
    finally:
        # Restore original manager
        maestro.ui_facade.decisions._decision_manager = original_manager
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Running Decision Override tests...\n")
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run facade test
    print("\n" + "="*50)
    print("Testing facade function...")
    facade_test_passed = test_decision_override_facade_function()
    
    if facade_test_passed:
        print("🎉 All Decision Override tests passed!")
    else:
        print("💥 Some tests failed!")
        exit(1)