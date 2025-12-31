"""
Test for assembly package membership fix.
This test verifies that virtual packages are correctly assigned to their respective assemblies.
"""
import os
import tempfile
from pathlib import Path

import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model


def test_virtual_package_assembly_membership():
    """Test that virtual packages are correctly assigned to assemblies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure
        docs_dir = temp_path / "docs"
        docs_commands_dir = docs_dir / "commands"
        tests_dir = temp_path / "tests"
        foo_file = temp_path / "foo.bat"
        
        docs_dir.mkdir()
        docs_commands_dir.mkdir()
        tests_dir.mkdir()
        
        # Create some test files
        (docs_commands_dir / "batch_script_echo.md").write_text("# Echo command")
        (docs_commands_dir / "batch_script_dir.md").write_text("# Dir command")
        (tests_dir / "test_one.sh").write_text("#!/bin/bash\necho test")
        foo_file.write_text("@echo off\necho Hello")
        
        # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        
        # Run the repo scan using the same internal API used by `m repo resolve`
        scan_result = scan_upp_repo_v2(
            str(temp_path),
            verbose=False,
            include_user_config=False,
            collect_files=True,
            scan_unknown_paths=True,
        )
        
        # Write the repo artifacts
        write_repo_artifacts(str(temp_path), scan_result, verbose=False)
        
        # Load the repo model to verify the results
        repo_model = load_repo_model(str(temp_path))
        
        # Find assemblies and packages in the model
        assemblies = repo_model.get("assemblies", [])
        packages = repo_model.get("packages", [])
        
        # Find the docs assembly
        docs_assembly = None
        tests_assembly = None
        root_assembly = None
        
        for asm in assemblies:
            if asm["name"] == "docs":
                docs_assembly = asm
            elif asm["name"] == "tests":
                tests_assembly = asm
            elif asm["root_relpath"] == ".":
                root_assembly = asm
        
        # Assertions
        assert docs_assembly is not None, "Docs assembly should exist"
        assert tests_assembly is not None, "Tests assembly should exist"
        assert root_assembly is not None, "Root assembly should exist"
        
        # The docs assembly should have packages
        assert len(docs_assembly["package_ids"]) >= 1, f"Docs assembly should have packages, but has {len(docs_assembly['package_ids'])}"
        
        # The tests assembly should have packages
        assert len(tests_assembly["package_ids"]) >= 1, f"Tests assembly should have packages, but has {len(tests_assembly['package_ids'])}"
        
        # The root assembly should have packages that are not in any other more specific assembly
        # Calculate expected count: total packages minus those in docs and tests assemblies
        docs_pkg_count = len(docs_assembly["package_ids"])
        tests_pkg_count = len(tests_assembly["package_ids"])
        expected_root_pkg_count = len(packages) - docs_pkg_count - tests_pkg_count
        assert len(root_assembly["package_ids"]) == expected_root_pkg_count, \
            f"Root assembly should have {expected_root_pkg_count} packages (total: {len(packages)} - docs: {docs_pkg_count} - tests: {tests_pkg_count}), but has {len(root_assembly['package_ids'])}"
        
        # Verify that all package_ids referenced by assemblies exist in repo_model.packages
        all_package_ids = {pkg["package_id"] for pkg in packages}
        for asm in [docs_assembly, tests_assembly, root_assembly]:
            for pkg_id in asm["package_ids"]:
                assert pkg_id in all_package_ids, f"Package ID {pkg_id} referenced by assembly {asm['name']} does not exist in packages"
        
        # Check that docs packages are assigned to docs assembly, not others
        docs_package_ids = set(docs_assembly["package_ids"])
        tests_package_ids = set(tests_assembly["package_ids"])
        
        # Ensure no overlap between docs and tests packages
        assert not docs_package_ids.intersection(tests_package_ids), \
            "Docs and tests assemblies should not share packages"


def test_multiple_virtual_packages_in_docs():
    """Test that multiple virtual packages under docs are all assigned to docs assembly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure with multiple docs packages
        docs_dir = temp_path / "docs"
        docs_config_dir = docs_dir / "configuration"
        docs_api_dir = docs_dir / "api"
        tests_dir = temp_path / "tests"
        
        docs_dir.mkdir()
        docs_config_dir.mkdir()
        docs_api_dir.mkdir()
        tests_dir.mkdir()
        
        # Create some test files
        (docs_config_dir / "settings.md").write_text("# Settings")
        (docs_api_dir / "api.md").write_text("# API")
        (docs_dir / "index.md").write_text("# Index")
        (tests_dir / "test1.py").write_text("print('test')")
        (tests_dir / "test2.py").write_text("print('test2')")
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        
        # Run the repo scan
        scan_result = scan_upp_repo_v2(
            str(temp_path),
            verbose=False,
            include_user_config=False,
            collect_files=True,
            scan_unknown_paths=True,
        )
        
        # Write the repo artifacts
        write_repo_artifacts(str(temp_path), scan_result, verbose=False)
        
        # Load the repo model to verify the results
        repo_model = load_repo_model(str(temp_path))
        
        # Find assemblies
        assemblies = repo_model.get("assemblies", [])
        docs_assembly = next((asm for asm in assemblies if asm["name"] == "docs"), None)
        tests_assembly = next((asm for asm in assemblies if asm["name"] == "tests"), None)
        
        # Assertions
        assert docs_assembly is not None, "Docs assembly should exist"
        assert tests_assembly is not None, "Tests assembly should exist"
        
        # The docs assembly should have packages
        assert len(docs_assembly["package_ids"]) >= 1, f"Docs assembly should have packages, but has {len(docs_assembly['package_ids'])}"
        
        # The tests assembly should have packages
        assert len(tests_assembly["package_ids"]) >= 1, f"Tests assembly should have packages, but has {len(tests_assembly['package_ids'])}"
        
        # Verify that docs assembly contains ALL docs-* packages
        packages = repo_model.get("packages", [])
        docs_packages = [pkg for pkg in packages if pkg["name"].startswith("docs-")]
        docs_assembly_package_ids = set(docs_assembly["package_ids"])
        
        for pkg in docs_packages:
            assert pkg["package_id"] in docs_assembly_package_ids, \
                f"Docs package {pkg['name']} with ID {pkg['package_id']} should be in docs assembly"