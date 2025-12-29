"""Tests for the work command functionality."""

import asyncio
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from maestro.commands.work import (
    parse_todo_md,
    load_issues,
    load_available_work,
    ai_select_work_items,
    handle_work_track,
    handle_work_phase,
    handle_work_issue,
    handle_work_any,
    handle_work_any_pick,
    simple_priority_sort
)
from maestro.work_session import WorkSession, create_session


class TestWorkCommand(unittest.TestCase):
    """Test cases for work command functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('maestro.commands.work.Path.exists')
    @patch('maestro.commands.work.Path.read_text')
    def test_parse_todo_md_empty(self, mock_read_text, mock_exists):
        """Test parsing an empty todo.md file."""
        mock_exists.return_value = True
        mock_read_text.return_value = "# Empty todo file"
        
        result = parse_todo_md()
        self.assertEqual(result["tracks"], [])
        self.assertEqual(result["phases"], [])

    @patch('maestro.commands.work.Path.exists')
    @patch('maestro.commands.work.Path.read_text')
    def test_parse_todo_md_with_content(self, mock_read_text, mock_exists):
        """Test parsing a todo.md file with tracks and phases."""
        mock_exists.return_value = True
        mock_read_text.return_value = """
## ws1_Session_Infrastructure
- [ ] Design session infrastructure
- [ ] Implement session creation
- [ ] Add session persistence

### ws1p1_Create_Session
- [ ] Create session class
- [ ] Implement creation method

### ws1p2_Store_Session
- [ ] Create storage interface
- [ ] Implement storage method

## ws2_Breadcrumb_System
- [ ] Design breadcrumb system
- [ ] Implement breadcrumb creation
"""
        
        result = parse_todo_md()
        self.assertEqual(len(result["tracks"]), 2)
        self.assertEqual(len(result["phases"]), 2)
        
        # Check first track
        track1 = result["tracks"][0]
        self.assertEqual(track1["id"], "ws1")
        self.assertEqual(track1["name"], "Session_Infrastructure")
        self.assertEqual(track1["type"], "track")
        
        # Check first phase
        phase1 = result["phases"][0]
        self.assertEqual(phase1["id"], "ws1p1")
        self.assertEqual(phase1["name"], "Create_Session")
        self.assertEqual(phase1["track"], "ws1")

    @patch('maestro.commands.work.Path.exists')
    @patch('maestro.commands.work.Path.glob')
    def test_load_issues_empty(self, mock_glob, mock_exists):
        """Test loading issues when no issues exist."""
        mock_exists.return_value = False
        mock_glob.return_value = []
        
        result = load_issues()
        self.assertEqual(result, [])

    @patch('maestro.commands.work.Path.exists')
    @patch('maestro.commands.work.Path.glob')
    @patch('maestro.commands.work.Path.read_text')
    def test_load_issues_with_content(self, mock_read_text, mock_glob, mock_exists):
        """Test loading issues from the issues directory."""
        mock_exists.return_value = True
        
        # Mock issue files
        issue_file = Mock()
        issue_file.stem = "issue1"
        issue_file.read_text.return_value = "# Issue 1\nThis is issue 1 content"
        
        mock_glob.return_value = [issue_file]
        
        result = load_issues()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "issue1")
        self.assertEqual(result[0]["title"], "Issue 1")
        self.assertEqual(result[0]["status"], "open")

    def test_load_available_work(self):
        """Test loading available work combines tracks, phases, and issues."""
        with patch('maestro.commands.work.parse_todo_md') as mock_parse, \
             patch('maestro.commands.work.load_issues') as mock_load_issues:
            
            mock_parse.return_value = {
                "tracks": [{"id": "track1", "status": "todo"}],
                "phases": [{"id": "phase1", "status": "todo"}]
            }
            mock_load_issues.return_value = [{"id": "issue1", "status": "open"}]
            
            result = load_available_work()
            self.assertEqual(len(result["tracks"]), 1)
            self.assertEqual(len(result["phases"]), 1)
            self.assertEqual(len(result["issues"]), 1)

    @patch('maestro.commands.work.get_engine')
    def test_ai_select_work_items_best_mode(self, mock_get_engine):
        """Test AI selection algorithm in best mode."""
        # Mock the engine and its generate method
        mock_engine = Mock()
        mock_engine.generate.return_value = json.dumps({
            "selected": [
                {
                    "id": "test1",
                    "type": "track",
                    "name": "Test Track",
                    "reason": "High priority",
                    "confidence": 0.9
                }
            ],
            "reasoning": "Selected based on priority"
        })
        mock_get_engine.return_value = mock_engine

        items = [
            {"id": "test1", "type": "track", "name": "Test Track"},
            {"id": "test2", "type": "phase", "name": "Test Phase"}
        ]

        result = ai_select_work_items(items, mode="best")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test1")

    @patch('maestro.commands.work.get_engine')
    def test_ai_select_work_items_top_n_mode(self, mock_get_engine):
        """Test AI selection algorithm in top_n mode."""
        # Mock the engine and its generate method
        mock_engine = Mock()
        mock_engine.generate.return_value = json.dumps({
            "selected": [
                {
                    "id": "test1",
                    "type": "track",
                    "name": "Test Track",
                    "reason": "High priority",
                    "confidence": 0.9
                },
                {
                    "id": "test2",
                    "type": "phase",
                    "name": "Test Phase",
                    "reason": "Medium priority",
                    "confidence": 0.7
                }
            ],
            "reasoning": "Selected based on priority"
        })
        mock_get_engine.return_value = mock_engine

        items = [
            {"id": "test1", "type": "track", "name": "Test Track"},
            {"id": "test2", "type": "phase", "name": "Test Phase"},
            {"id": "test3", "type": "issue", "name": "Test Issue"}
        ]

        result = ai_select_work_items(items, mode="top_n")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_simple_priority_sort(self):
        """Test the fallback simple priority sort function."""
        items = [
            {"id": "issue1", "type": "issue", "name": "Issue 1"},
            {"id": "track1", "type": "track", "name": "Track 1"},
            {"id": "phase1", "type": "phase", "name": "Phase 1"}
        ]
        
        # Test best mode
        result_best = simple_priority_sort(items, mode="best")
        self.assertEqual(result_best["type"], "phase")  # Phases should be first
        
        # Test top_n mode
        result_top_n = simple_priority_sort(items, mode="top_n")
        self.assertIsInstance(result_top_n, list)
        self.assertEqual(len(result_top_n), 3)

    @patch('maestro.commands.work.load_available_work')
    @patch('maestro.commands.work.ai_select_work_items')
    @patch('maestro.commands.work.create_session')
    @patch('maestro.commands.work._run_ai_interaction_with_breadcrumb')
    @patch('maestro.commands.work.check_work_gates')
    def test_handle_work_any(self, mock_gates, mock_ai_interact, mock_create_session, mock_ai_select, mock_load_work):
        """Test the work any command handler."""
        mock_gates.return_value = True
        mock_load_work.return_value = {
            "tracks": [{"id": "track1", "type": "track", "name": "Test Track"}],
            "phases": [{"id": "phase1", "type": "phase", "name": "Test Phase"}],
            "issues": [{"id": "issue1", "type": "issue", "name": "Test Issue"}]
        }

        mock_ai_select.return_value = {
            "id": "track1",
            "type": "track",
            "name": "Test Track",
            "reason": "Selected by AI"
        }

        mock_session = Mock(spec=WorkSession)
        mock_create_session.return_value = mock_session
        mock_ai_interact.return_value = "Mocked AI response"

        # Mock args
        class Args:
            pick = None
            ignore_gates = False

        args = Args()

        # Test async function
        async def run_test():
            await handle_work_any(args)

        # Run the test
        asyncio.run(run_test())

        # Verify the mocks were called
        mock_load_work.assert_called_once()
        mock_ai_select.assert_called_once()
        mock_create_session.assert_called_once()

    @patch('builtins.input', return_value='1')
    @patch('maestro.commands.work.load_available_work')
    @patch('maestro.commands.work.ai_select_work_items')
    @patch('maestro.commands.work.create_session')
    @patch('maestro.commands.work._run_ai_interaction_with_breadcrumb')
    @patch('maestro.commands.work.check_work_gates')
    def test_handle_work_any_pick(self, mock_gates, mock_ai_interact, mock_create_session, mock_ai_select, mock_load_work, mock_input):
        """Test the work any pick command handler."""
        mock_gates.return_value = True
        mock_load_work.return_value = {
            "tracks": [{"id": "track1", "type": "track", "name": "Test Track"}],
            "phases": [{"id": "phase1", "type": "phase", "name": "Test Phase"}],
            "issues": [{"id": "issue1", "type": "issue", "name": "Test Issue"}]
        }

        mock_ai_select.return_value = [
            {
                "id": "track1",
                "type": "track",
                "name": "Test Track",
                "reason": "High priority"
            }
        ]

        mock_session = Mock(spec=WorkSession)
        mock_create_session.return_value = mock_session
        mock_ai_interact.return_value = "Mocked AI response"

        # Mock args
        class Args:
            pick = True
            ignore_gates = False

        args = Args()

        # Test async function
        async def run_test():
            await handle_work_any_pick(args)

        # Run the test
        asyncio.run(run_test())

        # Verify the mocks were called
        mock_load_work.assert_called_once()
        mock_ai_select.assert_called_once()
        mock_input.assert_called_once()
        mock_create_session.assert_called_once()


class TestWorkCommandIntegration(unittest.TestCase):
    """Integration tests for work command functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test directories and files
        os.makedirs("docs", exist_ok=True)
        os.makedirs("docs/issues", exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_workflow_integration(self):
        """Test full workflow with test files."""
        # Create a test todo.md file
        todo_content = """
## ws1_Session_Infrastructure
- [ ] Design session infrastructure
- [ ] Implement session creation

### ws1p1_Create_Session
- [ ] Create session class

## ws2_Breadcrumb_System
- [ ] Design breadcrumb system
"""
        with open("docs/todo.md", "w") as f:
            f.write(todo_content)

        # Create a test issue file
        issue_content = """# Test Issue
This is a test issue description

**Status: Open**
"""
        with open("docs/issues/test_issue.md", "w") as f:
            f.write(issue_content)

        # Test that available work can be loaded
        work_items = load_available_work()
        self.assertGreater(len(work_items["tracks"]), 0)
        self.assertGreater(len(work_items["phases"]), 0)
        self.assertGreater(len(work_items["issues"]), 0)

        # Test AI selection
        all_items = (
            work_items["tracks"] + 
            work_items["phases"] + 
            work_items["issues"]
        )
        
        # Since we can't call the real AI in tests, test the fallback
        with patch('maestro.commands.work.get_engine', side_effect=Exception("AI not available")):
            selected_item = ai_select_work_items(all_items, mode="best")
            self.assertIsInstance(selected_item, dict)

            top_items = ai_select_work_items(all_items, mode="top_n")
            self.assertIsInstance(top_items, list)


if __name__ == '__main__':
    unittest.main()