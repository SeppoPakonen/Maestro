"""
Test fixture for BatchScriptShell-like repository structure.
This creates a minimal repository with docs, tests, scripts, and build system files
to test the virtual packages and deduplication functionality.
"""
import os
import tempfile
from pathlib import Path


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


if __name__ == "__main__":
    fixture_path = create_batchscriptshell_fixture()
    print(f"Created BatchScriptShell fixture at: {fixture_path}")
    
    # List the contents
    for root, dirs, files in os.walk(fixture_path):
        level = root.replace(fixture_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")