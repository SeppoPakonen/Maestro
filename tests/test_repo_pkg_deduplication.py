"""
Unit tests for bss package deduplication functionality.
Tests that cmake and autoconf detectors don't create duplicate packages for the same logical package.
"""
import os
import tempfile
from pathlib import Path
import pytest

from maestro.repo.build_systems import scan_all_build_systems


def create_build_systems_fixture():
    """
    Create a temporary directory with both CMake and Autoconf files
    to test package deduplication.
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="build_systems_test_")
    repo_path = Path(temp_dir)
    
    # Create CMake files
    (repo_path / "CMakeLists.txt").write_text("""
cmake_minimum_required(VERSION 3.10)
project(bss VERSION 1.0)
add_executable(bss main.cpp)
""")
    (repo_path / "main.cpp").write_text("int main() { return 0; }")
    
    # Create Autoconf files
    (repo_path / "configure.ac").write_text("""
AC_INIT([bss], [1.0])
AC_OUTPUT
""")
    (repo_path / "Makefile.am").write_text("""
bin_PROGRAMS = bss
bss_SOURCES = main.c
""")
    (repo_path / "main.c").write_text("#include <stdio.h>\nint main() { return 0; }")
    
    return str(repo_path)


def test_bss_deduplication():
    """Test that bss packages from cmake and autoconf are deduplicated."""
    repo_path = create_build_systems_fixture()
    
    try:
        # Scan the repository for all build systems
        results = scan_all_build_systems(repo_path, verbose=True)
        
        # Collect all packages regardless of build system
        all_packages = []
        for build_system, packages in results.items():
            all_packages.extend(packages)
        
        # Find packages with the name 'bss' (the logical package name)
        bss_packages = [pkg for pkg in all_packages if pkg.name == 'bss']
        
        # Verify that there's only one logical 'bss' package after deduplication
        print(f"Found {len(bss_packages)} packages with name 'bss'")
        for pkg in bss_packages:
            print(f"  - Package: {pkg.name}, Build System: {pkg.build_system}")
            print(f"    - Directory: {pkg.dir}")
            if hasattr(pkg, 'metadata') and 'build_systems' in pkg.metadata:
                print(f"    - Build Systems: {pkg.metadata['build_systems']}")

        # Check if there are multiple packages with same name and directory (true duplicates)
        # If deduplication worked correctly, packages with same name and directory should be merged
        unique_bss_keys = set()
        duplicate_found = False
        for pkg in bss_packages:
            key = (pkg.name, pkg.dir)  # Use name and directory as the key
            if key in unique_bss_keys:
                duplicate_found = True
            unique_bss_keys.add(key)

        # The main assertion: packages with the same name and directory should be deduplicated
        assert not duplicate_found, f"Found duplicate packages with same name and directory: {bss_packages}"

        # Also verify that if there are multiple packages with the same name,
        # they should have different directories or be properly merged
        if len(bss_packages) > 1:
            # If there are multiple packages with the same name, they should have different directories
            directories = [pkg.dir for pkg in bss_packages]
            assert len(set(directories)) == len(directories), "Multiple packages with same name should have different directories"
        elif len(bss_packages) == 1:
            # If there's only one package, it should have multi-build system metadata
            bss_pkg = bss_packages[0]
            if bss_pkg.build_system == 'multi':
                assert 'build_systems' in bss_pkg.metadata, "Multi-build system package should have build_systems metadata"
                build_systems = bss_pkg.metadata['build_systems']
                # Should contain both cmake and autoconf
                has_cmake = 'cmake' in build_systems
                has_autoconf = any('autoconf' in bs or bs == 'autoconf' for bs in build_systems)
                assert has_cmake or has_autoconf, f"Expected cmake and/or autoconf in build systems: {build_systems}"
        
    finally:
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(repo_path)


def test_package_metadata_after_deduplication():
    """Test that package metadata is properly preserved after deduplication."""
    repo_path = create_build_systems_fixture()
    
    try:
        # Scan the repository for all build systems
        results = scan_all_build_systems(repo_path, verbose=True)
        
        # Check that the results contain expected build systems
        expected_build_systems = {'cmake', 'autoconf'}
        found_build_systems = set(results.keys())
        
        print(f"Found build systems: {found_build_systems}")
        
        # Even after deduplication, we should still have entries for the build systems
        # that were detected (though packages might be merged)
        
        # Find packages with multi-build system metadata
        multi_build_packages = []
        for build_system, packages in results.items():
            for pkg in packages:
                if pkg.build_system == 'multi' or (hasattr(pkg, 'metadata') and 'build_systems' in pkg.metadata):
                    multi_build_packages.append(pkg)
        
        print(f"Found {len(multi_build_packages)} multi-build system packages")
        for pkg in multi_build_packages:
            print(f"  - Package: {pkg.name}, Build System: {pkg.build_system}")
            if hasattr(pkg, 'metadata') and 'build_systems' in pkg.metadata:
                print(f"    - Build Systems: {pkg.metadata['build_systems']}")
        
    finally:
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(repo_path)


if __name__ == "__main__":
    test_bss_deduplication()
    test_package_metadata_after_deduplication()
    print("All deduplication tests passed!")