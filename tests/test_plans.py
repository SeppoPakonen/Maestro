"""
Tests for the plan storage and CLI functionality.
"""
import os
import tempfile
import unittest
from pathlib import Path

from maestro.plans import PlanStore, Plan, PlanItem


class TestPlanStore(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.plans_file = Path(self.temp_dir) / "plans.md"
        self.store = PlanStore(str(self.plans_file))

    def tearDown(self):
        # Clean up the temporary file
        if self.plans_file.exists():
            self.plans_file.unlink()
        # Remove the temp directory
        os.rmdir(self.temp_dir)

    def test_initial_empty_plans(self):
        """Test that a new store has no plans initially."""
        plans = self.store.load()
        self.assertEqual(len(plans), 0)

    def test_add_plan(self):
        """Test adding a plan."""
        plan = self.store.add_plan("Test Plan")
        self.assertEqual(plan.title, "Test Plan")
        self.assertEqual(len(plan.items), 0)

        # Verify it was saved
        plans = self.store.load()
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].title, "Test Plan")

    def test_add_duplicate_plan(self):
        """Test that adding a duplicate plan title raises an error."""
        self.store.add_plan("Test Plan")
        
        # Try to add the same plan again (case-insensitive)
        with self.assertRaises(ValueError):
            self.store.add_plan("test plan")  # lowercase version

    def test_remove_plan(self):
        """Test removing a plan."""
        self.store.add_plan("Test Plan")
        self.store.add_plan("Another Plan")
        
        # Verify both plans exist
        plans = self.store.load()
        self.assertEqual(len(plans), 2)
        
        # Remove one plan
        result = self.store.remove_plan("Test Plan")
        self.assertTrue(result)
        
        # Verify only one plan remains
        plans = self.store.load()
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].title, "Another Plan")

    def test_get_plan_by_title(self):
        """Test getting a plan by title."""
        self.store.add_plan("Test Plan")
        plan = self.store.get_plan("Test Plan")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.title, "Test Plan")

    def test_get_plan_by_number(self):
        """Test getting a plan by number."""
        self.store.add_plan("First Plan")
        self.store.add_plan("Second Plan")
        
        # Get first plan by number
        plan = self.store.get_plan("1")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.title, "First Plan")
        
        # Get second plan by number
        plan = self.store.get_plan("2")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.title, "Second Plan")

    def test_add_item_to_plan(self):
        """Test adding an item to a plan."""
        self.store.add_plan("Test Plan")
        
        # Add an item
        result = self.store.add_item_to_plan("Test Plan", "Test item")
        self.assertTrue(result)
        
        # Verify the item was added
        plan = self.store.get_plan("Test Plan")
        self.assertEqual(len(plan.items), 1)
        self.assertEqual(plan.items[0].text, "Test item")

    def test_remove_item_from_plan(self):
        """Test removing an item from a plan."""
        self.store.add_plan("Test Plan")
        self.store.add_item_to_plan("Test Plan", "First item")
        self.store.add_item_to_plan("Test Plan", "Second item")
        
        # Verify both items exist
        plan = self.store.get_plan("Test Plan")
        self.assertEqual(len(plan.items), 2)
        
        # Remove the first item
        result = self.store.remove_item_from_plan("Test Plan", 1)
        self.assertTrue(result)
        
        # Verify only one item remains and it's the second one
        plan = self.store.get_plan("Test Plan")
        self.assertEqual(len(plan.items), 1)
        self.assertEqual(plan.items[0].text, "Second item")

    def test_parse_and_format_content(self):
        """Test parsing and formatting content."""
        content = """# Plans

## Plan 1
- Item 1
- Item 2

## Plan 2
- Item A
- Item B
"""
        self.plans_file.write_text(content)
        
        # Load and verify
        plans = self.store.load()
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].title, "Plan 1")
        self.assertEqual(len(plans[0].items), 2)
        self.assertEqual(plans[1].title, "Plan 2")
        self.assertEqual(len(plans[1].items), 2)
        
        # Save and verify content
        self.store.save(plans)
        saved_content = self.plans_file.read_text()
        # Verify the content contains expected elements
        self.assertIn("## Plan 1", saved_content)
        self.assertIn("- Item 1", saved_content)
        self.assertIn("## Plan 2", saved_content)
        self.assertIn("- Item A", saved_content)

    def test_malformed_content(self):
        """Test handling of malformed content."""
        # Add duplicate titles to test validation
        content = """# Plans

## Plan 1
- Item 1

## Plan 1
- Item 2
"""
        self.plans_file.write_text(content)
        
        with self.assertRaises(ValueError):
            self.store.load()

    def test_empty_items_plan(self):
        """Test a plan with no items."""
        content = """# Plans

## Empty Plan

## Regular Plan
- Item 1
"""
        self.plans_file.write_text(content)
        
        plans = self.store.load()
        self.assertEqual(len(plans), 2)
        empty_plan = next(p for p in plans if p.title == "Empty Plan")
        self.assertEqual(len(empty_plan.items), 0)


if __name__ == '__main__':
    unittest.main()