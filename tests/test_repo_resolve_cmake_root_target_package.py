import os
import tempfile
import json
from pathlib import Path
import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.repo.hub.index import HubIndexManager


def test_repo_resolve_cmake_root_target_package():
    """Test that CMake root target produces a package."""
    # Use the fixture directory
    fixture_dir = Path(__file__).parent / "fixtures" / "repos" / "batchscriptshell_min"

    # Run the scan
    result = scan_upp_repo_v2(str(fixture_dir), verbose=True)

    # Check that we have packages
    assert len(result.packages_detected) >= 1, f"Expected at least 1 package, got {len(result.packages_detected)}"

    # Check that we have the 'bss' package from the CMakeLists.txt
    package_names = [pkg.name for pkg in result.packages_detected]
    assert "bss" in package_names, f"Expected 'bss' package in {package_names}"

    # Check that we have the 'common_lib' package from the CMakeLists.txt
    assert "common_lib" in package_names, f"Expected 'common_lib' package in {package_names}"

    # Verify the packages have correct build system
    bss_package = next(pkg for pkg in result.packages_detected if pkg.name == "bss")
    assert bss_package.build_system == "cmake", f"Expected cmake build system, got {bss_package.build_system}"

    common_lib_package = next(pkg for pkg in result.packages_detected if pkg.name == "common_lib")
    assert common_lib_package.build_system == "cmake", f"Expected cmake build system, got {common_lib_package.build_system}"


if __name__ == "__main__":
    test_repo_resolve_cmake_root_target_package()
    print("Test passed: CMake root target produces a package")