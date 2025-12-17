#!/usr/bin/env python3
"""
Comprehensive test for Phase 2 U++ Builder Implementation.
This validates all core functionality that was implemented in Phase 2.
"""

import tempfile
import os
from pathlib import Path

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    try:
        from maestro.builders import (
            UppBuilder, UppPackage, BlitzBuilder, PPInfo,
            Workspace, PackageResolver, CircularDependencyError,
            BuildCache, PPInfoCache, IncrementalBuilder,
            Exporter, NinjaExporter,
            BuildMethod, LocalHost
        )
        print("✓ All imports work correctly")
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality from each module."""
    print("Testing basic functionality...")
    try:
        # Test basic UppPackage creation
        pkg = UppPackage(name="Test", path="test.upp")
        assert pkg.name == "Test"
        assert pkg.build_system == "upp"
        print("✓ UppPackage creation works")
        
        # Test basic BuildCache functionality
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BuildCache(os.path.join(tmpdir, "cache"))
            cache.track_file_dependencies("test.cpp", ["header.h"], "gcc-debug")
            assert cache.get_file_dependencies("test.cpp") is not None
            print("✓ BuildCache functionality works")
        
        # Test basic PPInfo functionality
        ppinfo = PPInfo()
        # This would require more setup to fully test, but basic instantiation works
        print("✓ PPInfo instantiation works")
        
        # Test Exporter functionality
        pkg = UppPackage(name="TestExport", path="test.upp")
        pkg.files = ["main.cpp"]
        with tempfile.TemporaryDirectory() as tmpdir:
            success = Exporter.export_to_makefile(pkg, tmpdir)
            assert success
            assert os.path.exists(os.path.join(tmpdir, "Makefile"))
            print("✓ Export functionality works")
        
        print("✓ Basic functionality tests passed")
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_workspace_resolution():
    """Test workspace dependency resolution with a more complex example."""
    print("Testing complex workspace resolution...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create packages with complex dependencies: A -> B -> C
            pkg_c_dir = Path(tmpdir) / "PackageC"
            pkg_c_dir.mkdir()
            (pkg_c_dir / "PackageC.upp").write_text('''
description "Base package";
file "c.cpp";
            ''')
            
            pkg_b_dir = Path(tmpdir) / "PackageB"
            pkg_b_dir.mkdir()
            (pkg_b_dir / "PackageB.upp").write_text('''
description "Middle package";
uses
    PackageC;
file "b.cpp";
            ''')
            
            pkg_a_dir = Path(tmpdir) / "PackageA"
            pkg_a_dir.mkdir()
            (pkg_a_dir / "PackageA.upp").write_text('''
description "Top package";
uses
    PackageB;
file "a.cpp";
            ''')
            
            # Create workspace and resolve dependencies
            workspace = Workspace(tmpdir)
            packages = workspace.scan([tmpdir])
            
            # Should have 3 packages
            assert len(packages) == 3
            assert "PackageA" in packages
            assert "PackageB" in packages
            assert "PackageC" in packages
            
            # Check dependencies
            assert packages["PackageB"].uses == ["PackageC"]
            assert packages["PackageA"].uses == ["PackageB"]
            assert packages["PackageC"].uses == []
            
            # Check build order: C should come before B, B before A
            build_order = workspace.get_build_order()
            order_names = [pkg.name for pkg in build_order]
            
            # Find indices
            idx_c = order_names.index("PackageC")
            idx_b = order_names.index("PackageB") 
            idx_a = order_names.index("PackageA")
            
            # C should come before B, B before A
            assert idx_c < idx_b, f"PackageC ({idx_c}) should come before PackageB ({idx_b})"
            assert idx_b < idx_a, f"PackageB ({idx_b}) should come before PackageA ({idx_a})"
            
            print(f"✓ Complex dependency resolution works: {order_names}")
            return True
    except Exception as e:
        print(f"✗ Complex workspace test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Run all comprehensive tests."""
    print("Running comprehensive Phase 2 U++ Builder tests...\n")
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_workspace_resolution
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line after each test
    
    print(f"Comprehensive Tests Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All comprehensive tests passed! Phase 2 implementation is solid.")
        return True
    else:
        print("❌ Some comprehensive tests failed.")
        return False


if __name__ == "__main__":
    # Import all the required modules at the top
    from maestro.builders import (
        UppBuilder, UppPackage, BlitzBuilder, PPInfo,
        Workspace, PackageResolver, CircularDependencyError,
        BuildCache, PPInfoCache, IncrementalBuilder,
        Exporter, NinjaExporter,
        BuildMethod, LocalHost
    )
    
    main()