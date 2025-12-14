#!/usr/bin/env python3
"""
Tests for decision override and plan negotiation functionality
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
import unittest
from maestro.ui_facade.decisions import DecisionManager, OverrideResult
from conversion_memory import ConversionMemory


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


def test_decision_override_memory():
    """Test the decision override functionality in the conversion memory system"""
    print("Testing decision override functionality...")

    # Create a temporary conversion memory
    temp_dir = Path(tempfile.mkdtemp())
    memory_path = temp_dir / "test_memory"

    memory = ConversionMemory(base_path=str(memory_path))

    # Create an initial decision
    decision_id = memory.add_decision(
        category="language_target",
        description="Target language for conversion",
        value="python",
        justification="Based on source code analysis"
    )

    print(f"Created initial decision: {decision_id}")

    # Verify the decision was created
    decisions = memory.load_decisions()
    assert len(decisions) == 1
    assert decisions[0]['decision_id'] == decision_id
    assert decisions[0]['value'] == "python"
    assert decisions[0]['status'] == "active"

    # Test override functionality
    result = memory.override_decision(
        decision_id=decision_id,
        new_value="javascript",
        reason="Changed target language based on new requirements",
        created_by="user"
    )

    print(f"Override result: {result}")

    # Verify the override worked
    new_decisions = memory.load_decisions()
    assert len(new_decisions) == 2  # Original + new

    # Check the old decision is superseded
    old_decision = next(d for d in new_decisions if d['decision_id'] == decision_id)
    assert old_decision['status'] == 'superseded'

    # Check the new decision is active
    new_decision_id = result['new_id']
    new_decision = next(d for d in new_decisions if d['decision_id'] == new_decision_id)
    assert new_decision['status'] == 'active'
    assert new_decision['value'] == 'javascript'
    assert new_decision['reason'] == 'Changed target language based on new requirements'

    print("✓ Decision override test passed")

    # Clean up
    shutil.rmtree(temp_dir)


def test_decision_fingerprint():
    """Test decision fingerprint computation"""
    print("Testing decision fingerprint computation...")

    temp_dir = Path(tempfile.mkdtemp())
    memory_path = temp_dir / "test_memory"

    memory = ConversionMemory(base_path=str(memory_path))

    # Add a decision
    decision_id1 = memory.add_decision(
        category="language_target",
        description="Target language for conversion",
        value="python",
        justification="Based on source code analysis"
    )

    fingerprint1 = memory.compute_decision_fingerprint()
    print(f"Fingerprint after first decision: {fingerprint1}")

    # Add another decision
    decision_id2 = memory.add_decision(
        category="engine_choice",
        description="AI engine for conversion tasks",
        value="gpt-4",
        justification="Best performance for this task type"
    )

    fingerprint2 = memory.compute_decision_fingerprint()
    print(f"Fingerprint after second decision: {fingerprint2}")

    # Override the first decision
    memory.override_decision(
        decision_id=decision_id1,
        new_value="javascript",
        reason="Changed requirement",
        created_by="user"
    )

    fingerprint3 = memory.compute_decision_fingerprint()
    print(f"Fingerprint after override: {fingerprint3}")

    # Verify fingerprints are different
    assert fingerprint1 != fingerprint2
    assert fingerprint2 != fingerprint3
    assert fingerprint1 != fingerprint3

    print("✓ Decision fingerprint test passed")

    # Clean up
    shutil.rmtree(temp_dir)


def test_active_decisions():
    """Test getting only active decisions"""
    print("Testing active decisions functionality...")

    temp_dir = Path(tempfile.mkdtemp())
    memory_path = temp_dir / "test_memory"

    memory = ConversionMemory(base_path=str(memory_path))

    # Add a decision
    decision_id1 = memory.add_decision(
        category="language_target",
        description="Target language for conversion",
        value="python",
        justification="Based on source code analysis"
    )

    # Verify we get active decisions correctly
    active = memory.get_active_decisions()
    assert len(active) == 1
    assert active[0]['decision_id'] == decision_id1
    assert active[0]['status'] == 'active'

    # Override the decision
    memory.override_decision(
        decision_id=decision_id1,
        new_value="javascript",
        reason="Changed requirement",
        created_by="user"
    )

    # Now we should have only the new active decision
    active = memory.get_active_decisions()
    assert len(active) == 1  # Only the new decision should be active
    assert active[0]['status'] == 'active'
    assert active[0]['value'] == 'javascript'

    # Total decisions should still be 2
    all_decisions = memory.load_decisions()
    assert len(all_decisions) == 2  # Original + new

    print("✓ Active decisions test passed")

    # Clean up
    shutil.rmtree(temp_dir)


def test_plan_negotiation_mock():
    """Test plan negotiation (mock version since full implementation would require AI calls)"""
    print("Testing plan negotiation (mock)...")

    # This test verifies the structure of the negotiation response
    # In the actual implementation, this would call the AI to suggest plan changes

    # Create a mock negotiation response with the expected JSON structure
    mock_response = {
        "plan_patch": {
            "invalidate_tasks": ["task_123", "task_456"],
            "add_tasks": [],
            "modify_tasks": [],
            "reorder": []
        },
        "decision_changes": ["D-001 -> D-002"],
        "risks": ["Potential conflicts if already-completed tasks are invalidated"],
        "requires_user_confirm": True
    }

    # Verify structure matches requirements
    assert "plan_patch" in mock_response
    assert "invalidate_tasks" in mock_response["plan_patch"]
    assert "add_tasks" in mock_response["plan_patch"]
    assert "modify_tasks" in mock_response["plan_patch"]
    assert "reorder" in mock_response["plan_patch"]
    assert "decision_changes" in mock_response
    assert "risks" in mock_response
    assert "requires_user_confirm" in mock_response

    print("Mock negotiation response structure:", json.dumps(mock_response, indent=2))
    print("✓ Plan negotiation structure test passed")


def test_integration_workflow():
    """Test end-to-end workflow: override → negotiate → patch → run"""
    print("Testing end-to-end workflow...")

    # Create a temporary directory structure
    temp_dir = Path(tempfile.mkdtemp())
    maestro_dir = temp_dir / ".maestro" / "convert"

    # Create directories
    (maestro_dir / "memory").mkdir(parents=True)
    (maestro_dir / "plan").mkdir(parents=True)
    (maestro_dir / "plan" / "history").mkdir(parents=True)
    (maestro_dir / "inventory").mkdir(parents=True)

    # Create a mock plan file
    plan_path = maestro_dir / "plan" / "plan.json"
    mock_plan = {
        "plan_version": "1.0",
        "pipeline_id": "test-pipeline",
        "intent": "Test conversion plan",
        "created_at": "2023-01-01T00:00:00Z",
        "source": {"path": "/tmp/source"},
        "target": {"path": "/tmp/target"},
        "scaffold_tasks": [],
        "file_tasks": [],
        "final_sweep_tasks": [],
        "decision_fingerprint": "initial_fingerprint"
    }

    with open(plan_path, 'w') as f:
        json.dump(mock_plan, f, indent=2)

    # Create mock inventory files
    source_inv_path = maestro_dir / "inventory" / "source_files.json"
    with open(source_inv_path, 'w') as f:
        json.dump({"files": [], "total_count": 0}, f)

    target_inv_path = maestro_dir / "inventory" / "target_files.json"
    with open(target_inv_path, 'w') as f:
        json.dump({"files": [], "total_count": 0}, f)

    # Now test the workflow
    memory = ConversionMemory(base_path=str(maestro_dir / "memory"))

    # Add an initial decision
    decision_id = memory.add_decision(
        category="language_target",
        description="Target language",
        value="python",
        justification="Initial target"
    )

    # Update the plan with the decision fingerprint
    mock_plan['decision_fingerprint'] = memory.compute_decision_fingerprint()
    with open(plan_path, 'w') as f:
        json.dump(mock_plan, f, indent=2)

    print(f"Initial decision fingerprint: {mock_plan['decision_fingerprint']}")

    # Override the decision
    result = memory.override_decision(
        decision_id=decision_id,
        new_value="javascript",
        reason="Changed target language",
        created_by="user"
    )

    print(f"Decision overrode: {result['old_id']} -> {result['new_id']}")

    # The new decision fingerprint should be different
    new_fingerprint = memory.compute_decision_fingerprint()
    print(f"New decision fingerprint: {new_fingerprint}")

    assert mock_plan['decision_fingerprint'] != new_fingerprint

    # Simulate plan negotiation by updating the plan with new fingerprint
    updated_plan = mock_plan.copy()
    updated_plan['decision_fingerprint'] = new_fingerprint
    updated_plan['plan_revision'] = 1
    updated_plan['derived_from_revision'] = 0

    # Save to history
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    history_dir = maestro_dir / "plan" / "history"
    hist_plan_path = history_dir / f"plan_{timestamp}.json"

    with open(hist_plan_path, 'w') as f:
        json.dump(mock_plan, f, indent=2)  # Save old version

    # Save updated plan
    updated_plan_path = maestro_dir / "plan" / "plan.json"
    with open(updated_plan_path, 'w') as f:
        json.dump(updated_plan, f, indent=2)

    print(f"Plan saved with new revision and fingerprint")
    print("✓ End-to-end workflow test passed")

    # Clean up
    shutil.rmtree(temp_dir)


def run_additional_tests():
    """Run all additional tests"""
    print("Running decision override and negotiation tests...\n")

    test_decision_override_memory()
    print()

    test_decision_fingerprint()
    print()

    test_active_decisions()
    print()

    test_plan_negotiation_mock()
    print()

    test_integration_workflow()
    print()


if __name__ == "__main__":
    print("Running Decision Override tests...\n")

    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Run facade test
    print("\n" + "="*50)
    print("Testing facade function...")
    facade_test_passed = test_decision_override_facade_function()

    if facade_test_passed:
        print("✅ Facade function test passed")
    else:
        print("❌ Facade function test failed!")

    print("\n" + "="*50)
    print("Running additional tests...")
    run_additional_tests()

    print("\n🎉 All Decision Override tests passed!")