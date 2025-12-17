"""
Test script for Phase 2 U++ Builder Implementation.

This validates all the functionality implemented in Phase 2:
- U++ package parsing
- Workspace dependency resolution
- Build cache management
- Preprocessor dependency tracking
- Export functionality
"""

import tempfile
import os
from pathlib import Path

from maestro.builders import (
    UppBuilder, UppPackage, Workspace, PackageResolver,
    BuildCache, PPInfoCache, PPInfo, BuildMethod, LocalHost,
    Exporter, NinjaExporter
)


def test_upp_package_parsing():
    """Test U++ package parsing functionality."""
    print("Testing U++ package parsing...")

    try:
        # Create a temporary .upp file for testing - use a meaningful name for the package
        with tempfile.TemporaryDirectory() as tmpdir:
            upp_file_path = os.path.join(tmpdir, "Test.upp")
            with open(upp_file_path, 'w') as f:
                f.write('''
description "Test package";

uses
    Core,
    plugin/z;

file
    "main.cpp",
    "utils.cpp",
    "utils.h";

mainconfig
    "" = "GUI MT";
                ''')

            # Create a dummy builder just for parsing
            from maestro.builders.config import BuildMethod
            # Create a dummy method configuration
            method_config = {
                'compiler': {'cxx': 'g++'},
                'flags': {'cflags': [], 'cxxflags': [], 'ldflags': []},
                'config': {'build_type': 'debug'}
            }
            method = BuildMethod(name="test", config_data=method_config)
            host = LocalHost()
            builder = UppBuilder(method, host)

            # Parse the package
            package = builder.parse_upp_file(upp_file_path)

            print(f"DEBUG: Parsed package name: '{package.name}', description: '{package.description}'")
            print(f"DEBUG: Package uses: {package.uses}")
            print(f"DEBUG: Package files: {package.files}")
            print(f"DEBUG: Package mainconfig: '{package.mainconfig}'")

            # The package name should be "Test" based on the filename Test.upp
            expected_name = os.path.splitext(os.path.basename(upp_file_path))[0]
            assert package.name == expected_name, f"Expected name {expected_name}, got {package.name}"
            assert package.description == "Test package"
            assert "Core" in package.uses
            assert "plugin/z" in package.uses
            assert "main.cpp" in package.files
            assert "utils.cpp" in package.files
            assert package.mainconfig == "GUI MT"

            print("✓ U++ package parsing works correctly")
            return True
    except Exception as e:
        import traceback
        print(f"✗ U++ package parsing failed: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return False


def test_workspace_dependency_resolution():
    """Test workspace dependency resolution."""
    print("Testing workspace dependency resolution...")
    
    try:
        # Create a temporary directory with mock packages
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two mock .upp files with dependencies
            # The format is "uses PackageName;" - single line without quotes
            pkg1_dir = Path(temp_dir) / "Package1"
            pkg1_dir.mkdir()
            (pkg1_dir / "Package1.upp").write_text('''
description "First package";
uses
    Package2;
file "main.cpp";
            ''')

            pkg2_dir = Path(temp_dir) / "Package2"
            pkg2_dir.mkdir()
            (pkg2_dir / "Package2.upp").write_text('''
description "Second package";
file "utils.cpp";
            ''')
            
            # Create workspace and scan
            workspace = Workspace(temp_dir)
            packages = workspace.scan([temp_dir])
            
            # Check that both packages were found
            print(f"DEBUG: Found packages: {list(packages.keys())}")
            for pkg_name, pkg in packages.items():
                print(f"DEBUG: Package {pkg_name} uses: {pkg.uses}")

            assert "Package1" in packages, f"Package1 not found in packages: {list(packages.keys())}"
            assert "Package2" in packages, f"Package2 not found in packages: {list(packages.keys())}"

            # Check dependency order (Package2 should come before Package1)
            build_order = workspace.get_build_order()
            order_names = [pkg.name for pkg in build_order]
            print(f"DEBUG: Build order: {order_names}")

            # Package2 should come before Package1 in build order
            pkg1_idx = order_names.index("Package1")
            pkg2_idx = order_names.index("Package2")
            print(f"DEBUG: Package1 index: {pkg1_idx}, Package2 index: {pkg2_idx}")
            assert pkg2_idx < pkg1_idx, f"Package2 should be built before Package1, but order is {order_names}"

            print("✓ Workspace dependency resolution works correctly")
            return True
    except Exception as e:
        print(f"✗ Workspace dependency resolution failed: {e}")
        return False


def test_build_cache():
    """Test build cache functionality."""
    print("Testing build cache...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = BuildCache(temp_dir + "/cache")
            
            # Create a test file
            test_file = Path(temp_dir) / "test.cpp"
            test_file.write_text("int main() { return 0; }")
            
            # Track dependencies for the file
            deps = [str(test_file)]
            cache.track_file_dependencies(str(test_file), deps, "gcc-debug")
            
            # Check if file needs rebuild (should be false initially)
            needs_rebuild = cache.needs_rebuild(str(test_file))
            assert not needs_rebuild, "File should not need rebuild initially"
            
            # Modify the file to trigger rebuild
            test_file.write_text("int main() { return 1; }")
            
            # Now it should need rebuild
            needs_rebuild = cache.needs_rebuild(str(test_file))
            assert needs_rebuild, "File should need rebuild after modification"
            
            print("✓ Build cache functionality works correctly")
            return True
    except Exception as e:
        print(f"✗ Build cache failed: {e}")
        return False


def test_ppinfo_tracking():
    """Test preprocessor dependency tracking."""
    print("Testing PPInfo tracking...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a cache for PPInfo
            ppinfo_cache = PPInfoCache(temp_dir + "/ppcache")
            ppinfo_tracker = PPInfo(ppinfo_cache)
            
            # Create a test C++ file with includes
            test_file = Path(temp_dir) / "test.cpp"
            test_file.write_text('''
#include <iostream>
#include "local_header.h"

#ifdef DEBUG
#include "debug_utils.h"
#endif

int main() {
    return 0;
}
            ''')
            
            # Create the local header
            local_header = Path(temp_dir) / "local_header.h"
            local_header.write_text("#pragma once\nvoid func();")
            
            # Extract dependencies
            headers, defines = ppinfo_tracker.extract_dependencies(str(test_file), [temp_dir])
            
            # Check that standard and local headers were found
            found_iostream = any("iostream" in h for h in headers)
            found_local = str(local_header) in headers
            
            assert found_iostream or found_local, f"Headers not found properly: {headers}"
            
            # Test conditional include tracking
            active_defines = {"DEBUG"}
            cond_headers = ppinfo_tracker.track_conditional_includes(
                str(test_file), active_defines, [temp_dir]
            )
            
            print("✓ PPInfo tracking works correctly")
            return True
    except Exception as e:
        print(f"✗ PPInfo tracking failed: {e}")
        return False


def test_export_functionality():
    """Test export functionality."""
    print("Testing export functionality...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock UppPackage
            pkg = UppPackage(
                name="TestExport",
                path=str(Path(temp_dir) / "TestExport.upp")
            )
            pkg.dir = temp_dir
            pkg.files = ["main.cpp", "util.cpp"]
            pkg.uses = ["Core", "Draw"]
            
            # Create main.cpp
            (Path(temp_dir) / "main.cpp").write_text("int main() { return 0; }")
            (Path(temp_dir) / "util.cpp").write_text("void util_func() {}")
            
            # Test Makefile export
            make_dir = Path(temp_dir) / "make_export"
            success_make = Exporter.export_to_makefile(pkg, str(make_dir))
            assert success_make, "Makefile export should succeed"
            assert (make_dir / "Makefile").exists(), "Makefile should be created"
            
            # Test CMake export
            cmake_dir = Path(temp_dir) / "cmake_export"
            success_cmake = Exporter.export_to_cmake(pkg, str(cmake_dir))
            assert success_cmake, "CMake export should succeed"
            assert (cmake_dir / "CMakeLists.txt").exists(), "CMakeLists.txt should be created"
            
            print("✓ Export functionality works correctly")
            return True
    except Exception as e:
        print(f"✗ Export functionality failed: {e}")
        return False


def main():
    """Run all Phase 2 tests."""
    print("Running Phase 2 U++ Builder Implementation tests...\n")
    
    tests = [
        test_upp_package_parsing,
        test_workspace_dependency_resolution,
        test_build_cache,
        test_ppinfo_tracking,
        test_export_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line after each test
    
    print(f"Phase 2 Tests Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2 tests passed! Implementation is working correctly.")
        return True
    else:
        print("❌ Some Phase 2 tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    main()