#!/usr/bin/env python3
"""
Tests for playbook functionality
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
import unittest

from playbook_manager import PlaybookManager, Playbook


class TestPlaybookFunctionality(unittest.TestCase):
    """Test the playbook functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.maestro_dir = Path(self.test_dir) / ".maestro"
        self.maestro_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_playbook_schema_validation(self):
        """Test that playbook validation works correctly."""
        manager = PlaybookManager(str(self.maestro_dir))
        
        # Valid playbook data
        valid_playbook = {
            "id": "cpp_to_c",
            "title": "C++ → C lowering (no runtime)",
            "version": "1.0",
            "applies_to": {
                "source_language": "C++",
                "target_language": "C"
            },
            "intent": "high_to_low_level",
            "principles": [
                "No hidden runtime",
                "Explicit memory ownership"
            ],
            "required_losses": [
                "RAII",
                "exceptions"
            ],
            "forbidden_constructs": {
                "target": ["new", "delete", "throw", "try", "catch"]
            },
            "preferred_patterns": [
                "init/cleanup pairs"
            ],
            "checkpoint_policy": {
                "after_files": 5,
                "on_semantic_loss": True
            },
            "validation_policy": {
                "mode": "vectors_only",
                "require_behavior_envelope": True
            }
        }
        
        # Should succeed
        self.assertTrue(manager.create_playbook(valid_playbook))
        
        # Invalid playbook - missing required fields
        invalid_playbook = {
            "id": "invalid",  # Missing other required fields
        }
        
        # Should fail
        self.assertFalse(manager.create_playbook(invalid_playbook))
    
    def test_playbook_creation_and_loading(self):
        """Test creating and loading a playbook."""
        manager = PlaybookManager(str(self.maestro_dir))
        
        playbook_data = {
            "id": "test_playbook",
            "title": "Test Playbook",
            "version": "1.0",
            "applies_to": {
                "source_language": "Python",
                "target_language": "JavaScript"
            },
            "intent": "language_to_language",
            "principles": ["Test principle"],
            "required_losses": [],
            "forbidden_constructs": {"target": []},
            "preferred_patterns": [],
            "checkpoint_policy": {},
            "validation_policy": {}
        }
        
        # Create the playbook
        self.assertTrue(manager.create_playbook(playbook_data))
        
        # Load the playbook
        loaded_playbook = manager.load_playbook("test_playbook")
        self.assertIsNotNone(loaded_playbook)
        self.assertEqual(loaded_playbook.id, "test_playbook")
        self.assertEqual(loaded_playbook.title, "Test Playbook")
        self.assertEqual(loaded_playbook.version, "1.0")
        self.assertEqual(loaded_playbook.intent, "language_to_language")
    
    def test_list_playbooks(self):
        """Test listing playbooks."""
        manager = PlaybookManager(str(self.maestro_dir))
        
        # Create a few test playbooks
        playbook1 = {
            "id": "test1",
            "title": "Test Playbook 1",
            "version": "1.0",
            "applies_to": {
                "source_language": "Python",
                "target_language": "JavaScript"
            },
            "intent": "language_to_language",
            "principles": ["Test principle"],
            "required_losses": [],
            "forbidden_constructs": {"target": []},
            "preferred_patterns": [],
            "checkpoint_policy": {},
            "validation_policy": {}
        }
        
        playbook2 = {
            "id": "test2",
            "title": "Test Playbook 2",
            "version": "1.1",
            "applies_to": {
                "source_language": "C++",
                "target_language": "C"
            },
            "intent": "high_to_low_level",
            "principles": ["Test principle"],
            "required_losses": [],
            "forbidden_constructs": {"target": []},
            "preferred_patterns": [],
            "checkpoint_policy": {},
            "validation_policy": {}
        }
        
        manager.create_playbook(playbook1)
        manager.create_playbook(playbook2)
        
        playbooks = manager.list_playbooks()
        self.assertEqual(len(playbooks), 2)
        
        # Check that both playbooks are in the list
        playbook_ids = {pb['id'] for pb in playbooks}
        self.assertIn('test1', playbook_ids)
        self.assertIn('test2', playbook_ids)
    
    def test_playbook_binding(self):
        """Test binding a playbook to a conversion."""
        manager = PlaybookManager(str(self.maestro_dir))
        
        playbook_data = {
            "id": "binding_test",
            "title": "Binding Test Playbook",
            "version": "1.0",
            "applies_to": {
                "source_language": "Python",
                "target_language": "JavaScript"
            },
            "intent": "language_to_language",
            "principles": ["Test principle"],
            "required_losses": [],
            "forbidden_constructs": {"target": []},
            "preferred_patterns": [],
            "checkpoint_policy": {},
            "validation_policy": {}
        }
        
        # Create and bind the playbook
        self.assertTrue(manager.create_playbook(playbook_data))
        self.assertTrue(manager.bind_playbook("binding_test"))
        
        # Check that the binding exists
        binding = manager.get_active_playbook_binding()
        self.assertIsNotNone(binding)
        self.assertEqual(binding['playbook_id'], 'binding_test')
        self.assertEqual(binding['playbook_version'], '1.0')
    
    def test_override_functionality(self):
        """Test recording and retrieving overrides."""
        manager = PlaybookManager(str(self.maestro_dir))
        
        # Record an override
        self.assertTrue(manager.record_override("task_123", "forbidden_construct", "Required for legacy compatibility"))
        
        # Retrieve overrides
        overrides = manager.get_overrides()
        self.assertEqual(len(overrides), 1)
        self.assertEqual(overrides[0]['task_id'], 'task_123')
        self.assertEqual(overrides[0]['violation_type'], 'forbidden_construct')
        self.assertEqual(overrides[0]['reason'], 'Required for legacy compatibility')


def test_playbook_cli_commands():
    """Test the CLI commands by calling them."""
    import subprocess
    import sys
    
    # Create a temp directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        maestro_dir = Path(temp_dir) / ".maestro"
        maestro_dir.mkdir()
        
        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Test playbook list command
            result = subprocess.run([
                sys.executable, "convert_orchestrator.py", "playbook", "list"
            ], capture_output=True, text=True)
            
            # Should succeed even if no playbooks exist
            assert result.returncode == 0
            
            # Create a test playbook directly
            manager = PlaybookManager()
            test_playbook = {
                "id": "cli_test",
                "title": "CLI Test Playbook",
                "version": "1.0",
                "applies_to": {
                    "source_language": "Python",
                    "target_language": "JavaScript"
                },
                "intent": "language_to_language",
                "principles": ["Test principle"],
                "required_losses": [],
                "forbidden_constructs": {"target": ["eval"]},
                "preferred_patterns": [],
                "checkpoint_policy": {},
                "validation_policy": {}
            }
            manager.create_playbook(test_playbook)
            
            # Now list should show the playbook
            result = subprocess.run([
                sys.executable, "convert_orchestrator.py", "playbook", "list"
            ], capture_output=True, text=True)
            
            assert result.returncode == 0
            assert "cli_test" in result.stdout
            
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    # Run the unit tests
    unittest.main(verbosity=2)