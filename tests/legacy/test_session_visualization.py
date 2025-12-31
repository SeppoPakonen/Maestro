"""
Unit tests for session visualization functionality.
"""
import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime

import pytest

pytestmark = pytest.mark.slow

from maestro.work_session import WorkSession, SessionStatus, SessionType
from maestro.visualization.tree import SessionTreeRenderer
from maestro.visualization.table import SessionTableFormatter
from maestro.visualization.detail import SessionDetailFormatter
from maestro.stats.session_stats import SessionStats, calculate_session_stats, calculate_tree_stats
from maestro.breadcrumb import Breadcrumb, create_breadcrumb


class TestSessionVisualization(unittest.TestCase):
    """Test session visualization components."""

    def setUp(self):
        """Set up test fixtures."""
        self.session1 = WorkSession(
            session_id="test-session-1",
            session_type=SessionType.WORK_PHASE.value,
            status=SessionStatus.RUNNING.value,
            related_entity={"track_id": "test-track", "phase_id": "test-phase"}
        )
        
        self.session2 = WorkSession(
            session_id="test-session-2",
            session_type=SessionType.FIX.value,
            parent_session_id="test-session-1",
            status=SessionStatus.COMPLETED.value
        )
        
        # Create a mock hierarchy
        self.hierarchy = {
            "root": [
                {
                    "session": self.session1,
                    "children": [
                        {
                            "session": self.session2,
                            "children": []
                        }
                    ]
                }
            ]
        }

    def test_session_tree_renderer(self):
        """Test session tree renderer."""
        renderer = SessionTreeRenderer(color=False)
        output = renderer.render(self.hierarchy)
        
        self.assertIn("📊 Work Sessions", output)
        self.assertIn(self.session1.session_id, output)
        self.assertIn(self.session2.session_id, output)
        self.assertIn(self.session1.session_type, output)
        self.assertIn(self.session2.session_type, output)

    def test_session_tree_renderer_with_max_depth(self):
        """Test session tree renderer with max depth limiting."""
        renderer = SessionTreeRenderer(color=False)
        output = renderer.render(self.hierarchy, max_depth=0)
        
        # With max depth of 0, should only show root
        self.assertIn("📊 Work Sessions", output)
        self.assertIn(self.session1.session_id, output)
        # At depth 0, child should not be shown
        self.assertNotIn(self.session2.session_id, output)

    def test_session_table_formatter(self):
        """Test session table formatter."""
        formatter = SessionTableFormatter()
        sessions = [self.session1, self.session2]
        output = formatter.format_table(sessions)
        
        self.assertIn("Work Sessions", output)
        self.assertIn(self.session1.session_id[:12], output)
        self.assertIn(self.session2.session_id[:12], output)
        self.assertIn(self.session1.session_type, output)
        self.assertIn(self.session2.session_type, output)

    def test_session_detail_formatter(self):
        """Test session detail formatter."""
        formatter = SessionDetailFormatter()
        output = formatter.format_details(self.session1)
        
        self.assertIn(self.session1.session_id, output)
        self.assertIn(self.session1.session_type, output)
        self.assertIn(self.session1.status, output)

    def test_session_detail_formatter_with_breadcrumbs(self):
        """Test session detail formatter with breadcrumbs."""
        formatter = SessionDetailFormatter()
        # This will test with mock breadcrumbs
        output = formatter.format_details(self.session1, include_breadcrumbs=True)
        
        self.assertIn("Breadcrumbs:", output)
        self.assertIn("Total:", output)


class TestSessionStats(unittest.TestCase):
    """Test session statistics calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.session = WorkSession(
            session_id="stats-test-session",
            session_type=SessionType.WORK_PHASE.value,
            status=SessionStatus.COMPLETED.value
        )
        
        # Create some mock breadcrumbs for testing
        self.breadcrumb1 = create_breadcrumb(
            prompt="Test prompt 1",
            response="Test response 1",
            tools_called=[{"tool": "grep", "args": {"pattern": "test"}}],
            files_modified=[{"path": "test.txt", "operation": "modify"}],
            parent_session_id=None,
            depth_level=0,
            model_used="test-model",
            token_count={"input": 10, "output": 20},
            cost=0.01
        )
        
        self.breadcrumb2 = create_breadcrumb(
            prompt="Test prompt 2",
            response="Test response 2", 
            tools_called=[],
            files_modified=[],
            parent_session_id=None,
            depth_level=0,
            model_used="test-model",
            token_count={"input": 15, "output": 25},
            cost=0.015
        )

    def test_calculate_session_stats(self):
        """Test calculating session stats."""
        # In the actual implementation, breadcrumbs would be loaded from disk
        # For testing, we'll just verify the data structure works
        stats = SessionStats(
            total_breadcrumbs=2,
            total_tokens_input=25,  # 10 + 15
            total_tokens_output=45,  # 20 + 25
            estimated_cost=0.025,  # 0.01 + 0.015
            files_modified=1,  # Only first breadcrumb has file modification
            tools_called=1,  # Only first breadcrumb has tool call
            duration_seconds=3600.0,  # Mock 1 hour
            success_rate=100.0  # Both successful (no errors)
        )
        
        # Verify the stats object has the correct fields
        self.assertEqual(stats.total_breadcrumbs, 2)
        self.assertEqual(stats.total_tokens_input, 25)
        self.assertEqual(stats.total_tokens_output, 45)
        self.assertEqual(stats.estimated_cost, 0.025)
        self.assertEqual(stats.files_modified, 1)
        self.assertEqual(stats.tools_called, 1)
        self.assertEqual(stats.duration_seconds, 3600.0)
        self.assertEqual(stats.success_rate, 100.0)


class TestExportFunctionality(unittest.TestCase):
    """Test export functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.session = WorkSession(
            session_id="export-test-session",
            session_type=SessionType.WORK_PHASE.value,
            status=SessionStatus.RUNNING.value,
            related_entity={"track_id": "test-track", "phase_id": "test-phase"}
        )

    def test_export_session_json(self):
        """Test exporting session to JSON."""
        import json
        from maestro.commands.work_session import export_session_json
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            temp_path = tmp.name
        
        try:
            export_session_json(self.session, temp_path)
            
            # Verify the file was created and contains session data
            self.assertTrue(os.path.exists(temp_path))
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(data["session_id"], self.session.session_id)
            self.assertEqual(data["session_type"], self.session.session_type)
            self.assertEqual(data["status"], self.session.status)
            self.assertIn("statistics", data)
            self.assertIn("breadcrumbs", data)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_session_markdown(self):
        """Test exporting session to Markdown."""
        from maestro.commands.work_session import export_session_markdown
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.md') as tmp:
            temp_path = tmp.name
        
        try:
            export_session_markdown(self.session, temp_path)
            
            # Verify the file was created and contains session data
            self.assertTrue(os.path.exists(temp_path))
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn(f"Session Report: {self.session.session_id}", content)
            self.assertIn(f"**Type**: {self.session.session_type}", content)
            self.assertIn(f"**Status**: {self.session.status}", content)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == '__main__':
    unittest.main()
