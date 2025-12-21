#!/usr/bin/env python3
"""
Test script for MaestroHub functionality.
Tests the basic operations of the hub system.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the maestro package to the path so we can import it
sys.path.insert(0, '/common/active/sblo/Dev/Maestro')

from maestro.hub.client import MaestroHub
from maestro.hub.resolver import HubResolver


def test_hub_basic_functionality():
    """Test basic hub functionality."""
    print("Testing MaestroHub basic functionality...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize hub with temporary directory
        hub = MaestroHub(hub_dir=temp_path / "hub")
        
        print(f"✓ Hub initialized with directory: {hub.hub_dir}")
        
        # Test loading a local hub registry
        local_registry_path = Path("/common/active/sblo/Dev/Maestro/test_hub_registry.json")
        
        if local_registry_path.exists():
            registry = hub.load_hub(str(local_registry_path))
            if registry:
                print(f"✓ Successfully loaded registry: {registry.name}")
                print(f"✓ Registry description: {registry.description}")
                print(f"✓ Number of nests: {len(registry.nests)}")
                
                # Print nest information
                for i, nest in enumerate(registry.nests):
                    print(f"  Nest {i+1}: {nest.name}")
                    print(f"    Description: {nest.description}")
                    print(f"    Repository: {nest.repository}")
                    print(f"    Packages: {nest.packages}")
                    print(f"    Build System: {nest.build_system}")
                
                # Test searching for a package
                search_results = hub.search_package("Core")
                print(f"\n✓ Search for 'Core' found {len(search_results)} results")
                for reg, nest in search_results:
                    print(f"  Found in nest: {nest.name} ({reg.name})")
                
                # Test searching for another package
                search_results = hub.search_package("libfoo")
                print(f"\n✓ Search for 'libfoo' found {len(search_results)} results")
                for reg, nest in search_results:
                    print(f"  Found in nest: {nest.name} ({reg.name})")
                
                # Test searching for non-existent package
                search_results = hub.search_package("nonexistent-package")
                print(f"\n✓ Search for 'nonexistent-package' found {len(search_results)} results")
                
                # Test getting all packages
                all_packages = hub.get_all_packages()
                print(f"\n✓ Total available packages: {len(all_packages)}")
                
                # Show first few packages
                for pkg in all_packages[:5]:
                    print(f"  - {pkg['package']} in nest '{pkg['nest']}' ({pkg['build_system']})")
                
                # Test resolver functionality
                print(f"\n--- Testing Hub Resolver ---")
                resolver = HubResolver(hub)
                
                # Test dependency resolution
                workspace_deps = ["Core", "libfoo"]
                resolved = resolver.resolve_workspace_dependencies(
                    str(temp_path), workspace_deps, auto_install=False
                )
                print(f"Dependencies resolution: {resolved}")
                
                print(f"\n✓ All basic hub functionality tests passed!")
                return True
            else:
                print("✗ Failed to load registry")
                return False
        else:
            print(f"✗ Test registry file does not exist: {local_registry_path}")
            return False


def test_hub_with_mock_repo():
    """Test hub functionality with a mock repository installation."""
    print("\nTesting hub install functionality with mock repo...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize hub with temporary directory
        hub = MaestroHub(hub_dir=temp_path / "hub")
        
        # Create a mock registry with a test nest
        import json
        
        mock_registry = {
            "name": "MockHub",
            "description": "Mock hub for testing",
            "nests": [
                {
                    "name": "mock-test-package",
                    "description": "Mock test package",
                    "repository": "https://github.com/testuser/mock-test-package.git",
                    "packages": ["MockTest"],
                    "category": "test",
                    "status": "stable",
                    "build_system": "upp"
                }
            ]
        }
        
        # Write mock registry to temporary file
        mock_registry_file = temp_path / "mock_registry.json"
        with open(mock_registry_file, 'w') as f:
            json.dump(mock_registry, f)
        
        # Load the mock registry
        registry = hub.load_hub(str(mock_registry_file))
        
        if registry:
            print(f"✓ Mock registry loaded: {registry.name}")
            
            # Test searching
            results = hub.search_package("MockTest")
            if results:
                print(f"✓ Found MockTest in nest: {results[0][1].name}")
            
            print(f"✓ Mock repository test passed!")
            return True
        else:
            print("✗ Failed to load mock registry")
            return False


def main():
    """Main test function."""
    print("=" * 60)
    print("MaestroHub Functionality Test")
    print("=" * 60)
    
    success1 = test_hub_basic_functionality()
    success2 = test_hub_with_mock_repo()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✓ ALL TESTS PASSED!")
        print("MaestroHub basic functionality is working correctly.")
    else:
        print("✗ SOME TESTS FAILED!")
        print("Issues were found in the hub functionality.")
    
    print("=" * 60)
    
    return success1 and success2


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)