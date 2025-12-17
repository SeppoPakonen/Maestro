"""
Tests for the TimelinePane implementation.
"""
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from datetime import datetime

from maestro.tui.panes.timeline import TimelinePane, TimelineEvent
from maestro.ui_facade.timeline import (
    list_events, 
    get_event, 
    replay_from_event,
    branch_from_event,
    mark_event_explained,
    get_related_vault_items
)


class TestTimelinePane(unittest.TestCase):
    """Test cases for TimelinePane."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pane = TimelinePane()
    
    def test_pane_initialization(self):
        """Test that the timeline pane initializes correctly."""
        self.assertEqual(self.pane.pane_id, "timeline")
        self.assertEqual(self.pane.pane_title, "Event Timeline")
    
    def test_timeline_event_creation(self):
        """Test TimelineEvent dataclass."""
        event = TimelineEvent(
            id="test_event_1",
            timestamp=datetime.now(),
            event_type="run",
            summary="Test conversion run",
            risk_marker="low"
        )
        
        self.assertEqual(event.id, "test_event_1")
        self.assertEqual(event.event_type, "run")
        self.assertEqual(event.summary, "Test conversion run")
        self.assertEqual(event.risk_marker, "low")
    
    def test_list_events(self):
        """Test the list_events function."""
        events = list_events()
        
        # Should return a list
        self.assertIsInstance(events, list)
        
        # Should have some events
        self.assertGreater(len(events), 0)
        
        # Check that events have expected fields
        for event in events:
            self.assertIn("id", event)
            self.assertIn("timestamp", event)
            self.assertIn("type", event)
            self.assertIn("summary", event)
    
    def test_get_event(self):
        """Test the get_event function."""
        # Get the list of events first
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        # Get the first event ID
        event_id = all_events[0]["id"]
        
        # Get that specific event
        event = get_event(event_id)
        
        # Should return a dictionary
        self.assertIsInstance(event, dict)
        
        # Should have the same ID
        self.assertEqual(event["id"], event_id)
        
        # Should have expected fields
        self.assertIn("id", event)
        self.assertIn("timestamp", event)
        self.assertIn("type", event)
        self.assertIn("summary", event)
    
    def test_get_event_not_found(self):
        """Test get_event with non-existent ID."""
        event = get_event("nonexistent_event")
        self.assertIsNone(event)
    
    def test_replay_from_event_dry_run(self):
        """Test replay from event (dry run)."""
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Perform dry-run replay
        result = replay_from_event(event_id, apply=False)
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # Should have success status
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)
        self.assertIn("event_id", result)
        self.assertEqual(result["apply"], False)
    
    def test_replay_from_event_apply(self):
        """Test replay from event (apply)."""
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Perform apply replay
        result = replay_from_event(event_id, apply=True)
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # Should have success status
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)
        self.assertIn("event_id", result)
        self.assertEqual(result["apply"], True)
    
    def test_branch_from_event(self):
        """Test branch from event."""
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Create a branch
        result = branch_from_event(event_id, "Test recovery branch")
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # Should have success status
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)
        self.assertIn("event_id", result)
        self.assertIn("branch_id", result)
        self.assertEqual(result["reason"], "Test recovery branch")
    
    def test_mark_event_explained(self):
        """Test mark event as explained."""
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Mark event as explained
        result = mark_event_explained(event_id, "Test explanation note")
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # Should have success status
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)
        self.assertIn("event_id", result)
        self.assertIn("note", result)
        self.assertEqual(result["note"], "Test explanation note")
    
    def test_get_related_vault_items(self):
        """Test getting related vault items for an event."""
        all_events = list_events()
        if not all_events:
            self.fail("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Get related vault items
        related_items = get_related_vault_items(event_id)
        
        # Should return a list
        self.assertIsInstance(related_items, list)
        
        # Each item should have expected fields
        for item in related_items:
            self.assertIn("id", item)
            self.assertIn("source_type", item)
            self.assertIn("description", item)
            self.assertIn("timestamp", item)
            self.assertIn("path", item)


class TestTimelineFacade(unittest.TestCase):
    """Test the timeline facade functions directly."""
    
    def test_create_timeline_evidence(self):
        """Test that timeline evidence is created properly."""
        from maestro.ui_facade.timeline import create_timeline_evidence
        
        all_events = list_events()
        if not all_events:
            self.skipTest("No events available for testing")
        
        event_id = all_events[0]["id"]
        
        # Create evidence
        evidence_id = create_timeline_evidence(
            event_id,
            "Test evidence content",
            "Test evidence description"
        )
        
        # Should return an evidence ID
        self.assertIsNotNone(evidence_id)
        self.assertIsInstance(evidence_id, str)
        self.assertTrue(evidence_id.startswith("evidence_"))
    
    def test_event_vault_refs_basic(self):
        """Test basic vault references functionality."""
        from maestro.ui_facade.timeline import get_event_vault_refs, link_event_to_vault

        all_events = list_events()
        if not all_events:
            self.skipTest("No events available for testing")

        event_id = all_events[0]["id"]

        # Get initial vault references
        refs = get_event_vault_refs(event_id)
        self.assertIsInstance(refs, list)

        # Test that the link function returns a boolean (success/failure)
        # In the mock implementation, it should work
        success = link_event_to_vault(event_id, "test_vault_item_123")

        # Should return True indicating the operation was successful
        self.assertIsInstance(success, bool)


class TestTimelinePaneIntegration(unittest.TestCase):
    """Integration tests for TimelinePane with UI elements."""
    
    def test_pane_attributes(self):
        """Test pane attributes are set correctly."""
        pane = TimelinePane()

        # Test that required attributes are accessible
        self.assertEqual(pane.pane_id, "timeline")
        self.assertEqual(pane.pane_title, "Event Timeline")

        # Test reactive attributes are initialized
        self.assertIsNone(pane.selected_event)
        self.assertEqual(pane.events_list, [])
    
    def test_refresh_data(self):
        """Test data refresh functionality."""
        pane = TimelinePane()
        
        # Initially, events_list should be empty
        self.assertEqual(len(pane.events_list), 0)
        
        # Refresh data - this should populate the events list
        pane.refresh_data()
        
        # After refresh, we should have events
        self.assertGreater(len(pane.events_list), 0)
    
    def test_selected_event_reactivity(self):
        """Test that the selected_event reactive attribute works."""
        pane = TimelinePane()
        
        # Initially, selected_event should be None
        self.assertIsNone(pane.selected_event)
        
        # Create a test event
        test_event = TimelineEvent(
            id="test_select_event",
            timestamp=datetime.now(),
            event_type="test",
            summary="Test event for selection"
        )
        
        # Set the selected event
        pane.selected_event = test_event
        
        # Verify it was set
        self.assertEqual(pane.selected_event.id, "test_select_event")


def run_tests():
    """Run all timeline tests."""
    unittest.main()


if __name__ == "__main__":
    run_tests()