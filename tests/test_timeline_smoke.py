"""
Smoke test for TimelinePane to ensure it can be created and basic functionality works.
"""
import unittest
from maestro.tui.panes.timeline import TimelinePane


class TestTimelinePaneSmoke(unittest.TestCase):
    """Smoke tests for TimelinePane."""
    
    def test_timeline_pane_creation(self):
        """Test that TimelinePane can be created without errors."""
        pane = TimelinePane()
        
        # Basic assertions
        self.assertIsNotNone(pane)
        self.assertEqual(pane.pane_id, "timeline")
        self.assertEqual(pane.pane_title, "Event Timeline")
    
    def test_timeline_pane_has_required_methods(self):
        """Test that TimelinePane has all required methods from MCPane protocol."""
        pane = TimelinePane()
        
        # Check that required methods exist
        self.assertTrue(hasattr(pane, 'on_mount'))
        self.assertTrue(hasattr(pane, 'on_focus'))
        self.assertTrue(hasattr(pane, 'on_blur'))
        self.assertTrue(hasattr(pane, 'refresh'))
        self.assertTrue(hasattr(pane, 'get_menu_spec'))
        
        # Check that they are callable
        self.assertTrue(callable(pane.on_mount))
        self.assertTrue(callable(pane.on_focus))
        self.assertTrue(callable(pane.on_blur))
        self.assertTrue(callable(pane.refresh))
        self.assertTrue(callable(pane.get_menu_spec))


def run_smoke_tests():
    """Run the smoke tests."""
    unittest.main()


if __name__ == "__main__":
    run_smoke_tests()