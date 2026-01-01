"""
Debug script to see what's happening with virtual packages.
"""
import os
import tempfile
from pathlib import Path

from maestro.repo.scanner import scan_upp_repo_v2


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


def debug_virtual_packages():
    """Debug what's happening with virtual packages."""
    repo_path = create_batchscriptshell_fixture()
    
    try:
        # Scan the repository
        scan_result = scan_upp_repo_v2(repo_path, verbose=True, collect_files=True)
        
        print("\n--- ASSEMBLIES ---")
        for asm in scan_result.assemblies_detected:
            print(f"Assembly: {asm.name} (type: {asm.assembly_type})")
            print(f"  - Packages: {asm.packages}")
            print(f"  - Package IDs: {asm.package_ids}")
            print(f"  - Package Dirs: {asm.package_dirs}")
            print(f"  - Build Systems: {asm.build_systems}")
            print(f"  - Root: {asm.root_path}")
            print()
        
        print("\n--- PACKAGES ---")
        for pkg in scan_result.packages_detected:
            print(f"Package: {pkg.name}")
            print(f"  - Dir: {pkg.dir}")
            print(f"  - Build System: {pkg.build_system}")
            print(f"  - Is Virtual: {pkg.is_virtual}")
            print(f"  - Virtual Type: {pkg.virtual_type}")
            print(f"  - Files: {len(pkg.files)} files")
            print()
        
        print("\n--- UNKNOWN PATHS ---")
        for unknown in scan_result.unknown_paths:
            print(f"Unknown: {unknown.path} (type: {unknown.type}, kind: {unknown.guessed_kind})")
        
        print("\n--- INTERNAL PACKAGES ---")
        for internal_pkg in scan_result.internal_packages:
            print(f"Internal: {internal_pkg.name} (type: {internal_pkg.guessed_type})")
            print(f"  - Root: {internal_pkg.root_path}")
            print(f"  - Members: {len(internal_pkg.members)}")
        
    finally:
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(repo_path)


if __name__ == "__main__":
    debug_virtual_packages()