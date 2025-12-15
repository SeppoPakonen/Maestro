"""
Tests for the vault UI facade functionality
"""
import os
import tempfile
import shutil
from datetime import datetime
from maestro.ui_facade.vault import (
    list_items, 
    get_item, 
    get_item_content, 
    get_item_metadata, 
    find_related, 
    export_items, 
    export_filtered, 
    export_run_related,
    VaultItem,
    VaultFilter,
    SourceType
)


def test_vault_list_items():
    """Test listing vault items"""
    # Create a temporary directory structure to simulate vault locations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock files that simulate vault content
        log_dir = os.path.join(temp_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        artifact_dir = os.path.join(temp_dir, "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        
        # Create test log file
        log_file = os.path.join(log_dir, "test.log")
        with open(log_file, 'w') as f:
            f.write("This is a test log file\nWith multiple lines\nFor testing purposes")
        
        # Create test artifact file
        artifact_file = os.path.join(artifact_dir, "test_artifact.json")
        with open(artifact_file, 'w') as f:
            f.write('{"test": "data", "value": 123}')
        
        # Temporarily update vault locations for testing
        from maestro.ui_facade import vault
        original_locations = vault.VAULT_LOCATIONS[:]
        vault.VAULT_LOCATIONS[0] = temp_dir  # Replace first location with temp dir
        
        try:
            # Test listing items
            items = list_items()
            assert len(items) >= 2  # Should have at least our 2 test files
            
            # Check that we have both log and artifact types
            log_items = [item for item in items if item.source_type == "logs"]
            artifact_items = [item for item in items if item.source_type == "artifacts"]
            
            assert len(log_items) >= 1
            assert len(artifact_items) >= 1
            
            print(f"✓ Found {len(items)} vault items")
            print(f"✓ Found {len(log_items)} log items")
            print(f"✓ Found {len(artifact_items)} artifact items")
            
        finally:
            # Restore original locations
            vault.VAULT_LOCATIONS[:] = original_locations


def test_vault_item_details():
    """Test getting details for a specific vault item"""
    # Create a temporary directory structure to simulate vault locations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock file
        log_dir = os.path.join(temp_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "test.log")
        with open(log_file, 'w') as f:
            f.write("Test log content")
        
        # Temporarily update vault locations for testing
        from maestro.ui_facade import vault
        original_locations = vault.VAULT_LOCATIONS[:]
        vault.VAULT_LOCATIONS[0] = temp_dir  # Replace first location with temp dir
        
        try:
            # Get items and test first one
            items = list_items()
            if items:
                item = items[0]
                
                # Test getting the item by ID
                retrieved_item = get_item(item.id)
                assert retrieved_item is not None
                assert retrieved_item.id == item.id
                print("✓ Successfully retrieved item by ID")
                
                # Test getting item content
                content = get_item_content(item.id)
                assert content is not None
                print("✓ Successfully retrieved item content")
                
                # Test getting item metadata
                metadata = get_item_metadata(item.id)
                assert metadata is not None
                assert metadata.path == item.path
                assert metadata.size == item.size
                print("✓ Successfully retrieved item metadata")
                
        finally:
            # Restore original locations
            vault.VAULT_LOCATIONS[:] = original_locations


def test_vault_filters():
    """Test vault filtering functionality"""
    # Create a temporary directory structure to simulate vault locations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock files
        log_dir = os.path.join(temp_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        artifact_dir = os.path.join(temp_dir, "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        
        # Create test files
        log_file = os.path.join(log_dir, "test.log")
        with open(log_file, 'w') as f:
            f.write("Test log content")
        
        artifact_file = os.path.join(artifact_dir, "test_artifact.json")
        with open(artifact_file, 'w') as f:
            f.write('{"test": "data"}')
        
        # Temporarily update vault locations for testing
        from maestro.ui_facade import vault
        original_locations = vault.VAULT_LOCATIONS[:]
        vault.VAULT_LOCATIONS[0] = temp_dir  # Replace first location with temp dir
        
        try:
            # Test filtering by source type
            log_filter = VaultFilter(source_types=["logs"])
            log_items = list_items(log_filter)
            assert all(item.source_type == "logs" for item in log_items)
            print(f"✓ Filtered by source type: {len(log_items)} log items")
            
            # Test filtering by subsystem
            artifact_filter = VaultFilter(source_types=["artifacts"])
            artifact_items = list_items(artifact_filter)
            assert all(item.source_type == "artifacts" for item in artifact_items)
            print(f"✓ Filtered by artifact type: {len(artifact_items)} artifact items")
            
        finally:
            # Restore original locations
            vault.VAULT_LOCATIONS[:] = original_locations


def test_vault_find_related():
    """Test finding related vault items"""
    # Create a temporary directory structure to simulate vault locations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock files
        task_dir = os.path.join(temp_dir, "task_test123")
        os.makedirs(task_dir, exist_ok=True)
        
        # Create related files with common identifiers
        log_file = os.path.join(task_dir, "task_test123.log")
        with open(log_file, 'w') as f:
            f.write("Test log for task")
        
        artifact_file = os.path.join(task_dir, "task_test123_artifact.json")
        with open(artifact_file, 'w') as f:
            f.write('{"task": "test123", "data": true}')
        
        # Temporarily update vault locations for testing
        from maestro.ui_facade import vault
        original_locations = vault.VAULT_LOCATIONS[:]
        vault.VAULT_LOCATIONS[0] = temp_dir  # Replace first location with temp dir
        
        try:
            # Get items and test related functionality
            items = list_items()
            if len(items) >= 2:
                # Get the first item and find related items
                first_item = items[0]
                related_items = find_related(first_item.id)
                print(f"✓ Found {len(related_items)} related items for: {first_item.description}")
                
        finally:
            # Restore original locations
            vault.VAULT_LOCATIONS[:] = original_locations


def test_vault_export():
    """Test vault export functionality"""
    # Create a temporary directory structure to simulate vault locations
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock files
        log_dir = os.path.join(temp_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        artifact_dir = os.path.join(temp_dir, "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        
        # Create test files
        log_file = os.path.join(log_dir, "test.log")
        with open(log_file, 'w') as f:
            f.write("Test log content")
        
        artifact_file = os.path.join(artifact_dir, "test_artifact.json")
        with open(artifact_file, 'w') as f:
            f.write('{"test": "data"}')
        
        # Temporarily update vault locations for testing
        from maestro.ui_facade import vault
        original_locations = vault.VAULT_LOCATIONS[:]
        vault.VAULT_LOCATIONS[0] = temp_dir  # Replace first location with temp dir
        
        try:
            # Get items and export them
            items = list_items()
            if items:
                item_ids = [item.id for item in items[:2]]  # Take first 2 items
                
                # Test export_items
                export_path = export_items(item_ids, output_format="zip")
                assert os.path.exists(export_path)
                print(f"✓ Successfully exported {len(item_ids)} items to: {export_path}")
                
                # Test export_filtered
                filter_obj = VaultFilter(source_types=["logs"])
                filtered_export_path = export_filtered(filter_obj, output_format="zip")
                assert os.path.exists(filtered_export_path)
                print(f"✓ Successfully exported filtered items to: {filtered_export_path}")
                
        finally:
            # Restore original locations
            vault.VAULT_LOCATIONS[:] = original_locations


def run_all_tests():
    """Run all vault tests"""
    print("Running vault functionality tests...")
    
    try:
        test_vault_list_items()
        print("✓ Vault list items test passed")
    except Exception as e:
        print(f"✗ Vault list items test failed: {e}")
    
    try:
        test_vault_item_details()
        print("✓ Vault item details test passed")
    except Exception as e:
        print(f"✗ Vault item details test failed: {e}")
    
    try:
        test_vault_filters()
        print("✓ Vault filters test passed")
    except Exception as e:
        print(f"✗ Vault filters test failed: {e}")
    
    try:
        test_vault_find_related()
        print("✓ Vault find related test passed")
    except Exception as e:
        print(f"✗ Vault find related test failed: {e}")
    
    try:
        test_vault_export()
        print("✓ Vault export test passed")
    except Exception as e:
        print(f"✗ Vault export test failed: {e}")
    
    print("All vault tests completed!")


if __name__ == "__main__":
    run_all_tests()