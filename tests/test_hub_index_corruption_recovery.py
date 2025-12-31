import os
import tempfile
import json
from pathlib import Path
import pytest
from unittest.mock import patch

from maestro.repo.hub.index import HubIndexManager


def test_hub_index_corruption_recovery():
    """Test that corrupt hub index is quarantined and rebuilt."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a temporary hub directory
        hub_dir = Path(temp_dir) / ".maestro" / "hub"
        hub_dir.mkdir(parents=True)
        
        # Create a corrupt index file with invalid JSON
        index_file = hub_dir / "index.json"
        with open(index_file, 'w') as f:
            f.write('{ "invalid": json with control char \x00 }')  # Invalid JSON with control character
        
        # Create HubIndexManager and try to load the index
        manager = HubIndexManager(hub_dir=hub_dir)
        
        # This should handle the corruption gracefully and create a new index
        index = manager.load_index()
        
        # Check that we got a valid (new) index
        assert index is not None
        assert index.version == "1.0"
        
        # Check that the corrupt file was moved to quarantine
        corrupt_files = list(hub_dir.glob("index.corrupt.*.json"))
        assert len(corrupt_files) == 1, f"Expected 1 quarantined file, found {len(corrupt_files)}"
        
        # Check that the original corrupt file no longer exists as index.json
        assert not index_file.exists(), "Original corrupt index.json should have been moved"
        
        # Check that the quarantined file contains the original corrupt content
        with open(corrupt_files[0], 'r') as f:
            quarantined_content = f.read()
        assert "invalid" in quarantined_content
        assert "\\x00" in quarantined_content or "\x00" in quarantined_content


if __name__ == "__main__":
    test_hub_index_corruption_recovery()
    print("Test passed: Hub index corruption is quarantined and rebuilt")