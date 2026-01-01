"""
Unit tests for assemblies->packages functionality in BatchScriptShell-like fixture.
"""
import os
import tempfile
from pathlib import Path
import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.repo.assembly import detect_assemblies


def create_batchscriptshell_fixture():
    """
    Create a temporary directory with BatchScriptShell-like structure:
    - top-level: CMakeLists.txt, configure.ac, shell.c, redirection_function.c
    - docs/commands/*.md (at least 2)
    - tests/*.bat and tests/*.sh (at least 1 each)
    - scripts or top-level *.bat (at least 1)
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="batchscriptshell_test_")
    repo_path = Path(temp_dir)

    # Create top-level files
    (repo_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\nproject(BatchScriptShell)")
    (repo_path / "configure.ac").write_text("AC_INIT([bss], [1.0])\nAC_OUTPUT")
    (repo_path / "shell.c").write_text("#include <stdio.h>\nint main() { return 0; }")
    (repo_path / "redirection_function.c").write_text("#include <stdio.h>\nvoid redirect() { }")

    # Create docs directory with markdown files
    docs_dir = repo_path / "docs" / "commands"
    docs_dir.mkdir(parents=True)
    (docs_dir / "install.md").write_text("# Install Command\nThis command installs the software.")
    (docs_dir / "run.md").write_text("# Run Command\nThis command runs the software.")

    # Create tests directory with batch and shell scripts
    tests_dir = repo_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test1.bat").write_text("@echo off\necho Running test 1")
    (tests_dir / "test2.sh").write_text("#!/bin/bash\necho Running test 2")

    # Create scripts directory with batch files
    scripts_dir = repo_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "build.bat").write_text("@echo off\necho Building...")
    (scripts_dir / "clean.sh").write_text("#!/bin/bash\necho Cleaning...")

    # Create top-level batch file
    (repo_path / "setup.bat").write_text("@echo off\necho Setting up...")

    return str(repo_path)


def test_assemblies_contain_packages():
    """Test that assemblies contain packages after scanning."""
    repo_path = create_batchscriptshell_fixture()

    try:
        # Scan the repository
        scan_result = scan_upp_repo_v2(repo_path, verbose=True, collect_files=True)

        # Get assemblies from scan result
        assemblies = scan_result.assemblies_detected
        packages = scan_result.packages_detected

        # Verify that assemblies exist
        assert len(assemblies) > 0, "Should have at least one assembly"

        # Verify that each assembly has a package count > 0
        for asm in assemblies:
            package_count = len(asm.package_ids)
            print(f"Assembly: {asm.name} has {package_count} packages")
            # At least the docs, tests, and scripts assemblies should have packages
            # The root assembly might have build system packages
            if asm.name in ['docs', 'tests', 'scripts']:
                assert package_count > 0, f"Assembly {asm.name} should have packages"

        # Verify that we have virtual packages in docs assembly
        docs_assemblies = [asm for asm in assemblies if asm.name == 'docs']
        if docs_assemblies:
            docs_asm = docs_assemblies[0]
            docs_pkg_count = len(docs_asm.package_ids)
            assert docs_pkg_count > 0, "Docs assembly should have virtual packages"

        # Verify that we have virtual packages in tests assembly
        tests_assemblies = [asm for asm in assemblies if asm.name == 'tests']
        if tests_assemblies:
            tests_asm = tests_assemblies[0]
            tests_pkg_count = len(tests_asm.package_ids)
            assert tests_pkg_count > 0, "Tests assembly should have virtual packages"

        # Verify that we have virtual packages in scripts assembly
        scripts_assemblies = [asm for asm in assemblies if asm.name == 'scripts']
        if scripts_assemblies:
            scripts_asm = scripts_assemblies[0]
            scripts_pkg_count = len(scripts_asm.package_ids)
            assert scripts_pkg_count > 0, "Scripts assembly should have virtual packages"

    finally:
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(repo_path)


def test_virtual_packages_created():
    """Test that virtual packages are created for docs, tests, and scripts."""
    repo_path = create_batchscriptshell_fixture()

    try:
        # Scan the repository
        scan_result = scan_upp_repo_v2(repo_path, verbose=True, collect_files=True)

        # Check that virtual packages exist for docs
        docs_path = os.path.join(repo_path, 'docs')
        if os.path.exists(docs_path):
            # Virtual packages should be created for docs
            docs_packages = [pkg for pkg in scan_result.packages_detected
                            if pkg.is_virtual and pkg.virtual_type == 'docs']
            assert len(docs_packages) > 0, f"Should have virtual packages for docs, found: {[p.name for p in docs_packages]}"

        # Check that virtual packages exist for tests
        tests_path = os.path.join(repo_path, 'tests')
        if os.path.exists(tests_path):
            tests_packages = [pkg for pkg in scan_result.packages_detected
                             if pkg.is_virtual and pkg.virtual_type == 'tests']
            assert len(tests_packages) > 0, f"Should have virtual packages for tests, found: {[p.name for p in tests_packages]}"

        # Check that virtual packages exist for scripts
        scripts_path = os.path.join(repo_path, 'scripts')
        if os.path.exists(scripts_path):
            scripts_packages = [pkg for pkg in scan_result.packages_detected
                               if pkg.is_virtual and pkg.virtual_type == 'scripts']
            assert len(scripts_packages) > 0, f"Should have virtual packages for scripts, found: {[p.name for p in scripts_packages]}"

    finally:
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(repo_path)


if __name__ == "__main__":
    test_assemblies_contain_packages()
    test_virtual_packages_created()
    print("All tests passed!")