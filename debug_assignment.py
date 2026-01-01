#!/usr/bin/env python3
"""
Debug script to understand the package assignment logic.
"""
import os
import tempfile
from pathlib import Path

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model


def debug_assignment():
    """Debug the package assignment logic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure similar to BatchScriptShell
        docs_dir = temp_path / "docs"
        tests_dir = temp_path / "tests"
        foo_file = temp_path / "foo.bat"
        
        docs_dir.mkdir()
        tests_dir.mkdir()
        
        # Create some test files
        (docs_dir / "index.md").write_text("# Docs")
        (tests_dir / "test.sh").write_text("#!/bin/bash\necho test")
        foo_file.write_text("@echo off\necho Hello")
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        
        # Run the repo scan
        scan_result = scan_upp_repo_v2(
            str(temp_path),
            verbose=True,
            include_user_config=False,
            collect_files=True,
            scan_unknown_paths=True,
        )
        
        print(f"Found {len(scan_result.packages_detected)} packages:")
        for i, pkg in enumerate(scan_result.packages_detected):
            print(f"  {i+1}. {pkg.name} (dir: {pkg.dir}, is_virtual: {getattr(pkg, 'is_virtual', 'N/A')}, virtual_type: {getattr(pkg, 'virtual_type', 'N/A')})")
        
        print(f"\nFound {len(scan_result.assemblies_detected)} assemblies:")
        for i, asm in enumerate(scan_result.assemblies_detected):
            print(f"  {i+1}. {asm.name} (kind: {getattr(asm, 'assembly_type', 'N/A')}, root: {asm.root_path})")
        
        # Write the repo artifacts
        write_repo_artifacts(str(temp_path), scan_result, verbose=True)
        
        # Load the repo model to verify the results
        repo_model = load_repo_model(str(temp_path))
        
        print(f"\nAssemblies in repo model:")
        for asm in repo_model.get("assemblies", []):
            print(f"  {asm['name']} ({asm['kind']}) - {len(asm['package_ids'])} packages")
        
        print(f"\nPackages in repo model:")
        for pkg in repo_model.get("packages", []):
            print(f"  {pkg['name']} -> assembly_id: {pkg['assembly_id']}")


if __name__ == "__main__":
    debug_assignment()