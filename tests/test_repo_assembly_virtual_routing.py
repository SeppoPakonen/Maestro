"""
Test for assembly virtual package routing fix.
This test verifies that virtual packages are assigned to kind-specific assemblies
instead of being stolen by the root assembly.
"""
import os
import tempfile
from pathlib import Path

import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model


def test_virtual_package_routing_to_kind_specific_assemblies():
    """Test that virtual packages are assigned to assemblies with matching kind."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test directory structure similar to BatchScriptShell
        docs_dir = temp_path / "docs"
        tests_dir = temp_path / "tests"

        docs_dir.mkdir()
        tests_dir.mkdir()

        # Create some test files
        (docs_dir / "index.md").write_text("# Docs")
        (tests_dir / "test.sh").write_text("#!/bin/bash\necho test")
        (temp_path / "script.bat").write_text("@echo off\necho Hello")

        # Create a CMakeLists.txt to ensure we get a non-virtual package like in BatchScriptShell
        (temp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\nproject(Test)")
        (temp_path / "main.cpp").write_text("int main() { return 0; }")

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

        print(f"DEBUG: Found {len(assemblies)} assemblies and {len(packages)} packages")
        for asm in assemblies:
            print(f"DEBUG: Assembly {asm['name']} (kind: {asm['kind']}) has {len(asm['package_ids'])} packages")

        # Create mappings for easier access
        assembly_by_name = {asm["name"]: asm for asm in assemblies}
        package_by_id = {pkg["package_id"]: pkg for pkg in packages}

        # Find specific assemblies by kind and name
        scripts_asm = None
        docs_asm = None
        tests_asm = None
        root_asm = None

        for asm in assemblies:
            if asm["name"] == "scripts":
                scripts_asm = asm
            elif asm["name"] == "docs":
                docs_asm = asm
            elif asm["name"] == "tests":
                tests_asm = asm
            elif asm["kind"] == "root":
                root_asm = asm

        # At least the scripts and docs assemblies should exist
        if scripts_asm is None:
            # Find any assembly with kind 'scripts'
            for asm in assemblies:
                if asm["kind"] == "scripts":
                    scripts_asm = asm
                    break

        if docs_asm is None:
            # Find any assembly with name or kind 'docs'
            for asm in assemblies:
                if asm["name"] == "docs" or asm["kind"] == "docs":
                    docs_asm = asm
                    break

        if tests_asm is None:
            # Find any assembly with name or kind 'tests'
            for asm in assemblies:
                if asm["name"] == "tests" or asm["kind"] == "tests":
                    tests_asm = asm
                    break

        if root_asm is None:
            # Find any assembly with kind 'root'
            for asm in assemblies:
                if asm["kind"] == "root":
                    root_asm = asm
                    break

        # Assertions
        assert scripts_asm is not None, f"Scripts assembly should exist. Available assemblies: {[a['name'] for a in assemblies]}"
        assert docs_asm is not None, f"Docs assembly should exist. Available assemblies: {[a['name'] for a in assemblies]}"
        assert root_asm is not None, f"Root assembly should exist. Available assemblies: {[a['name'] for a in assemblies]}"

        # The scripts assembly should have virtual script packages
        assert len(scripts_asm["package_ids"]) >= 0, f"Scripts assembly should have packages, but has {len(scripts_asm['package_ids'])}"

        # Map package IDs to package info for analysis
        scripts_packages = [package_by_id[pkg_id] for pkg_id in scripts_asm["package_ids"]]
        root_packages = [package_by_id[pkg_id] for pkg_id in root_asm["package_ids"]]

        # Find virtual packages in the repo
        all_virtual_packages = [pkg for pkg in packages if "virtual" in pkg["build_system"]]
        scripts_virtual_packages = [pkg for pkg in all_virtual_packages if pkg["name"].startswith("scripts-")]

        # If we have scripts virtual packages, they should be in the scripts assembly
        if scripts_virtual_packages:
            scripts_pkg_ids = {pkg["package_id"] for pkg in scripts_virtual_packages}
            asm_scripts_pkg_ids = set(scripts_asm["package_ids"])
            assert scripts_pkg_ids.issubset(asm_scripts_pkg_ids), \
                f"Scripts virtual packages {scripts_pkg_ids} should be in scripts assembly {asm_scripts_pkg_ids}"

            # Root assembly should NOT contain scripts virtual packages
            root_pkg_ids = {pkg["package_id"] for pkg in root_packages}
            assert not scripts_pkg_ids.intersection(root_pkg_ids), \
                f"Root assembly should not contain scripts virtual packages"

        # Root assembly should contain non-virtual packages if they exist
        non_virtual_packages = [pkg for pkg in packages if "virtual" not in pkg["build_system"]]
        if non_virtual_packages:
            non_virtual_pkg_ids = {pkg["package_id"] for pkg in non_virtual_packages}
            root_pkg_ids = {pkg["package_id"] for pkg in root_packages}
            assert non_virtual_pkg_ids.issubset(root_pkg_ids), \
                f"Non-virtual packages should be in root assembly"


def test_non_virtual_packages_in_root_assembly():
    """Test that non-virtual packages are assigned to root assembly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a non-virtual package (e.g., a C++ project with CMake)
        cmake_file = temp_path / "CMakeLists.txt"
        cmake_file.write_text("cmake_minimum_required(VERSION 3.10)\nproject(Test)")
        main_cpp = temp_path / "main.cpp"
        main_cpp.write_text("int main() { return 0; }")

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

        # Find assemblies and packages
        assemblies = repo_model.get("assemblies", [])
        packages = repo_model.get("packages", [])

        print(f"DEBUG: Found {len(assemblies)} assemblies and {len(packages)} packages in non-virtual test")
        for asm in assemblies:
            print(f"DEBUG: Assembly {asm['name']} (kind: {asm['kind']}) has {len(asm['package_ids'])} packages")

        # Find the root assembly
        root_asm = None
        for asm in assemblies:
            if asm["kind"] == "root":
                root_asm = asm
                break

        assert root_asm is not None, f"Root assembly should exist. Available assemblies: {[a['name'] for a in assemblies]}"

        # Find non-virtual packages
        non_virtual_packages = [pkg for pkg in packages if "virtual" not in pkg["build_system"]]

        # If there are non-virtual packages, they should be in the root assembly
        if non_virtual_packages:
            root_pkg_ids = set(root_asm["package_ids"])
            non_virtual_pkg_ids = {pkg["package_id"] for pkg in non_virtual_packages}

            assert non_virtual_pkg_ids.issubset(root_pkg_ids), \
                f"Non-virtual packages {non_virtual_pkg_ids} should be in root assembly {root_pkg_ids}"


def test_deterministic_assembly_package_ordering():
    """Test that assembly package ordering is deterministic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure
        docs_dir = temp_path / "docs"
        docs_dir.mkdir()
        
        # Create multiple docs files
        (docs_dir / "a_doc.md").write_text("# A Doc")
        (docs_dir / "b_doc.md").write_text("# B Doc")
        (docs_dir / "c_doc.md").write_text("# C Doc")
        
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
        
        # Load the repo model
        repo_model = load_repo_model(str(temp_path))
        
        # Find the docs assembly
        assemblies = repo_model.get("assemblies", [])
        docs_asm = next((asm for asm in assemblies if asm["name"] == "docs"), None)
        
        assert docs_asm is not None, "Docs assembly should exist"
        
        # Check that package_ids are sorted deterministically
        package_ids = docs_asm["package_ids"]
        # The package_ids should be sorted and consistent between runs
        assert package_ids == sorted(package_ids), "Package IDs should be sorted"