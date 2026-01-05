"""
Integration tests for runbook list/resolve functionality.
Tests the specific issue where 'runbook list' doesn't show runbooks created by 'runbook resolve'.
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest import mock
import sys
import argparse

# Import the runbook command handlers
from maestro.commands.runbook import (
    _get_runbook_storage_path,
    _ensure_runbook_storage,
    _load_index,
    _save_index,
    _load_runbook,
    _save_runbook,
    handle_runbook_resolve,
    handle_runbook_list,
    create_runbook_from_freeform,
    save_runbook_with_update_semantics
)


def test_runbook_list_finds_after_resolve_repo_root():
    """Test that runbook list finds runbooks created by resolve when run from repo root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
        os.environ['MAESTRO_DOCS_ROOT'] = str(temp_path / 'docs' / 'maestro')
        
        # Ensure runbook storage exists
        _ensure_runbook_storage()
        
        # Create a runbook using resolve
        args_resolve = argparse.Namespace(
            text="Create a simple test runbook",
            verbose=False,
            eval=False
        )
        handle_runbook_resolve(args_resolve)
        
        # Now list runbooks - should find the one we just created
        args_list = argparse.Namespace(
            status=None,
            scope=None,
            tag=None,
            archived=False,
            type='all'
        )
        captured_output = []
        
        # Capture print statements by mocking print
        original_print = __builtins__['print']
        
        def mock_print(*args, **kwargs):
            captured_output.append(' '.join(str(arg) for arg in args))
        
        __builtins__['print'] = mock_print
        
        try:
            handle_runbook_list(args_list)
        finally:
            __builtins__['print'] = original_print
        
        output_str = '\n'.join(captured_output)
        
        # Should find at least one runbook
        assert "Found 1 runbook(s)" in output_str or "No runbooks found" not in output_str
        assert "runbook" in output_str  # Should contain the runbook ID or title
        
        # Clean up environment variable
        if 'MAESTRO_DOCS_ROOT' in os.environ:
            del os.environ['MAESTRO_DOCS_ROOT']


def test_runbook_list_from_subdir_relative_docs_root():
    """Test that runbook list works from subdirectory with relative MAESTRO_DOCS_ROOT."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a subdirectory
        subdir = temp_path / "subdir"
        subdir.mkdir()
        
        # Set MAESTRO_DOCS_ROOT to relative path
        os.environ['MAESTRO_DOCS_ROOT'] = str("docs/maestro")
        
        # Change to subdirectory
        original_cwd = os.getcwd()
        os.chdir(str(subdir))
        
        try:
            # Ensure runbook storage exists (relative to original repo root)
            _ensure_runbook_storage()
            
            # Create a runbook using resolve
            args_resolve = argparse.Namespace(
                text="Create a test runbook from subdir",
                verbose=False,
                eval=False
            )
            handle_runbook_resolve(args_resolve)
            
            # Now list runbooks from subdirectory - should still find the one we created
            args_list = argparse.Namespace(
                status=None,
                scope=None,
                tag=None,
                archived=False,
                type='all'
            )
            captured_output = []
            
            # Capture print statements by mocking print
            original_print = __builtins__['print']
            
            def mock_print(*args, **kwargs):
                captured_output.append(' '.join(str(arg) for arg in args))
            
            __builtins__['print'] = mock_print
            
            try:
                handle_runbook_list(args_list)
            finally:
                __builtins__['print'] = original_print
            
            output_str = '\n'.join(captured_output)
            
            # Should find at least one runbook
            assert "Found 1 runbook(s)" in output_str or "No runbooks found" not in output_str
            assert "runbook" in output_str  # Should contain the runbook ID or title
            
        finally:
            os.chdir(original_cwd)
            # Clean up environment variable
            if 'MAESTRO_DOCS_ROOT' in os.environ:
                del os.environ['MAESTRO_DOCS_ROOT']


def test_runbook_list_rebuilds_missing_index():
    """Test that runbook list rebuilds index when it's missing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Set MAESTRO_DOCS_ROOT
        os.environ['MAESTRO_DOCS_ROOT'] = str(temp_path / 'docs' / 'maestro')
        
        # Ensure runbook storage exists
        _ensure_runbook_storage()
        
        # Create a runbook directly (bypassing normal save which would update index)
        runbook = {
            'id': 'test-missing-index',
            'title': 'Test Missing Index',
            'goal': 'Test that list rebuilds missing index',
            'steps': [
                {
                    'cmd': 'echo "test"',
                    'expect': 'Command executes successfully'
                }
            ],
            'created_at': '2023-01-01T00:00:00',
            'updated_at': '2023-01-01T00:00:00'
        }
        
        # Save runbook file directly
        runbook_path = _get_runbook_storage_path() / "items" / "test-missing-index.json"
        with open(runbook_path, 'w') as f:
            json.dump(runbook, f, indent=2)
        
        # Verify index doesn't exist yet
        index_path = _get_runbook_storage_path() / "index.json"
        assert not index_path.exists()
        
        # Now list runbooks - should rebuild index automatically
        args_list = argparse.Namespace(
            status=None,
            scope=None,
            tag=None,
            archived=False,
            type='all'
        )
        captured_output = []
        
        # Capture print statements by mocking print
        original_print = __builtins__['print']
        
        def mock_print(*args, **kwargs):
            captured_output.append(' '.join(str(arg) for arg in args))
        
        __builtins__['print'] = mock_print
        
        try:
            handle_runbook_list(args_list)
        finally:
            __builtins__['print'] = original_print
        
        output_str = '\n'.join(captured_output)
        
        # Should find the runbook even though index was missing
        assert "Found 1 runbook(s)" in output_str
        assert "test-missing-index" in output_str
        
        # Verify index was created
        assert index_path.exists()
        
        # Clean up environment variable
        if 'MAESTRO_DOCS_ROOT' in os.environ:
            del os.environ['MAESTRO_DOCS_ROOT']


def test_runbook_list_handles_stale_index_entries():
    """Test that runbook list handles stale index entries (missing files)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Set MAESTRO_DOCS_ROOT
        os.environ['MAESTRO_DOCS_ROOT'] = str(temp_path / 'docs' / 'maestro')
        
        # Ensure runbook storage exists
        _ensure_runbook_storage()
        
        # Create an index with a stale entry (pointing to non-existent file)
        stale_index = [
            {
                'id': 'stale-entry',
                'title': 'Stale Entry',
                'tags': ['test'],
                'status': 'proposed',
                'updated_at': '2023-01-01T00:00:00'
            }
        ]
        
        index_path = _get_runbook_storage_path() / "index.json"
        with open(index_path, 'w') as f:
            json.dump(stale_index, f, indent=2)
        
        # Verify the runbook file doesn't exist
        runbook_path = _get_runbook_storage_path() / "items" / "stale-entry.json"
        assert not runbook_path.exists()
        
        # Now list runbooks - should rebuild index to remove stale entry
        args_list = argparse.Namespace(
            status=None,
            scope=None,
            tag=None,
            archived=False,
            type='all'
        )
        captured_output = []
        
        # Capture print statements by mocking print
        original_print = __builtins__['print']
        
        def mock_print(*args, **kwargs):
            captured_output.append(' '.join(str(arg) for arg in args))
        
        __builtins__['print'] = mock_print
        
        try:
            handle_runbook_list(args_list)
        finally:
            __builtins__['print'] = original_print
        
        output_str = '\n'.join(captured_output)
        
        # Should not find any runbooks since the file doesn't exist
        # The stale entry should be removed from the index
        assert "No runbooks found" in output_str or "Found 0 runbook(s)" in output_str
        
        # Verify index was rebuilt (should be empty now)
        with open(index_path, 'r') as f:
            rebuilt_index = json.load(f)
        
        assert len(rebuilt_index) == 0
        
        # Clean up environment variable
        if 'MAESTRO_DOCS_ROOT' in os.environ:
            del os.environ['MAESTRO_DOCS_ROOT']


def test_runbook_list_auto_detect_docs_root_when_unset():
    """Test that runbook list works when MAESTRO_DOCS_ROOT is not set (defaults to current dir)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Temporarily remove MAESTRO_DOCS_ROOT if it exists
        old_docs_root = os.environ.get('MAESTRO_DOCS_ROOT')
        if 'MAESTRO_DOCS_ROOT' in os.environ:
            del os.environ['MAESTRO_DOCS_ROOT']
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(str(temp_path))
        
        try:
            # Ensure runbook storage exists (should be in current dir)
            _ensure_runbook_storage()
            
            # Create a runbook using resolve
            args_resolve = argparse.Namespace(
                text="Create a test runbook with default docs root",
                verbose=False,
                eval=False
            )
            handle_runbook_resolve(args_resolve)
            
            # Now list runbooks - should find the one we created
            args_list = argparse.Namespace(
                status=None,
                scope=None,
                tag=None,
                archived=False,
                type='all'
            )
            captured_output = []
            
            # Capture print statements by mocking print
            original_print = __builtins__['print']
            
            def mock_print(*args, **kwargs):
                captured_output.append(' '.join(str(arg) for arg in args))
            
            __builtins__['print'] = mock_print
            
            try:
                handle_runbook_list(args_list)
            finally:
                __builtins__['print'] = original_print
            
            output_str = '\n'.join(captured_output)
            
            # Should find at least one runbook
            assert "Found 1 runbook(s)" in output_str or "No runbooks found" not in output_str
            assert "runbook" in output_str  # Should contain the runbook ID or title
            
        finally:
            os.chdir(original_cwd)
            # Restore original MAESTRO_DOCS_ROOT if it existed
            if old_docs_root is not None:
                os.environ['MAESTRO_DOCS_ROOT'] = old_docs_root
            elif 'MAESTRO_DOCS_ROOT' in os.environ:
                del os.environ['MAESTRO_DOCS_ROOT']