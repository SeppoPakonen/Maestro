"""
Test for assembly ID uniqueness and package deduplication fix.
This test verifies that:
1. Assembly IDs are unique even when assemblies have the same root path but different kinds
2. No duplicate packages exist within assembly membership
3. No duplicate package entries exist in the repo model
"""
import os
import tempfile
from pathlib import Path

import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model


def test_assembly_ids_differ_by_kind_same_root():
    """Test that assemblies with same root path but different kinds have different IDs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a structure similar to RainbowGame where multiple assemblies 
        # might have the same root path
        uppsrc_dir = temp_path / "uppsrc"
        game_dir = uppsrc_dir / "Game"
        
        uppsrc_dir.mkdir()
        game_dir.mkdir()
        
        # Create a U++ package
        (game_dir / "Game.upp").write_text("// Game package")
        
        # Create some gradle files to trigger multiple build system detection
        (temp_path / "build.gradle.kts").write_text("plugins { application }")
        (temp_path / "settings.gradle.kts").write_text('rootProject.name = "test"')
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        (temp_path / "docs").mkdir(exist_ok=True)
        
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
        
        # Find assemblies in the model
        assemblies = repo_model.get("assemblies", [])
        
        # Find assemblies that have the same root path but different kinds
        assemblies_by_root = {}
        for asm in assemblies:
            root = asm["root_relpath"]
            if root not in assemblies_by_root:
                assemblies_by_root[root] = []
            assemblies_by_root[root].append(asm)
        
        # Check that assemblies with same root but different kinds have different IDs
        for root_path, asm_list in assemblies_by_root.items():
            if len(asm_list) > 1:
                # Multiple assemblies with same root - they should have different IDs
                ids = [asm["assembly_id"] for asm in asm_list]
                kinds = [asm["kind"] for asm in asm_list]
                
                # All IDs should be unique
                assert len(ids) == len(set(ids)), f"Assemblies with root '{root_path}' should have unique IDs, but got {ids} for kinds {kinds}"
                
                # If they have different kinds, they definitely should have different IDs
                if len(set(kinds)) > 1:
                    assert len(set(ids)) == len(ids), f"Assemblies with same root '{root_path}' but different kinds {kinds} should have unique IDs {ids}"


def test_no_duplicate_package_ids_in_assemblies():
    """Test that no assembly contains duplicate package IDs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a structure that might cause duplicate package assignments
        uppsrc_dir = temp_path / "uppsrc"
        game_dir = uppsrc_dir / "Game"
        
        uppsrc_dir.mkdir()
        game_dir.mkdir()
        
        # Create a U++ package
        (game_dir / "Game.upp").write_text("// Game package")
        
        # Create some gradle files
        (temp_path / "build.gradle.kts").write_text("plugins { application }")
        (temp_path / "settings.gradle.kts").write_text('rootProject.name = "test"')
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        (temp_path / "docs").mkdir(exist_ok=True)
        
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
        
        # Check each assembly for duplicate package IDs
        assemblies = repo_model.get("assemblies", [])
        
        for asm in assemblies:
            package_ids = asm.get("package_ids", [])
            # Check that all package IDs in this assembly are unique
            assert len(package_ids) == len(set(package_ids)), \
                f"Assembly '{asm['name']}' (kind: {asm['kind']}) contains duplicate package IDs: {package_ids}"


def test_no_duplicate_packages_in_repo_model():
    """Test that there are no duplicate packages in the repo model."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a structure that might cause duplicate packages
        uppsrc_dir = temp_path / "uppsrc"
        game_dir = uppsrc_dir / "Game"
        
        uppsrc_dir.mkdir()
        game_dir.mkdir()
        
        # Create a U++ package
        (game_dir / "Game.upp").write_text("// Game package")
        
        # Create some gradle files
        (temp_path / "build.gradle.kts").write_text("plugins { application }")
        (temp_path / "settings.gradle.kts").write_text('rootProject.name = "test"')
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        (temp_path / "docs").mkdir(exist_ok=True)
        
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
        
        # Check for duplicate packages in the packages list
        packages = repo_model.get("packages", [])
        
        # Create a canonical key for each package to detect duplicates
        package_keys = []
        for pkg in packages:
            # Key includes name, directory, and build system to identify unique packages
            key = (pkg["name"], pkg["dir_relpath"], pkg.get("build_system", "unknown"))
            package_keys.append(key)
        
        # Check that all package keys are unique (no duplicate packages)
        assert len(package_keys) == len(set(package_keys)), \
            f"Repo model contains duplicate packages: {package_keys}"


def test_rainbowgame_trash_style_scenario():
    """Test a scenario similar to RainbowGame/trash with multiple assemblies at same root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a structure similar to RainbowGame/trash:
        # - Root with gradle project (creates root assembly)
        # - uppsrc directory with U++ packages (creates uppsrc assembly)
        uppsrc_dir = temp_path / "uppsrc"
        rainbow_game_dir = uppsrc_dir / "RainbowGame"
        android_dir = temp_path / "android"
        core_dir = temp_path / "core"
        
        uppsrc_dir.mkdir()
        rainbow_game_dir.mkdir()
        android_dir.mkdir()
        core_dir.mkdir()
        
        # Create U++ package in uppsrc
        (rainbow_game_dir / "RainbowGame.upp").write_text("// RainbowGame U++ package")
        
        # Create gradle project files
        (temp_path / "build.gradle.kts").write_text("""
plugins {
    id 'application'
}
application {
    mainClass = 'com.example.Main'
}
""")
        (temp_path / "settings.gradle.kts").write_text('rootProject.name = "RainbowGame"')
        
        # Create some source files for gradle modules
        android_src = android_dir / "src" / "main" / "java"
        android_src.mkdir(parents=True)
        (android_src / "MainActivity.java").write_text("// Android activity")
        
        core_src = core_dir / "src" / "main" / "java"
        core_src.mkdir(parents=True)
        (core_src / "CoreClass.java").write_text("// Core class")
        
        # Create docs and scripts directories to trigger virtual package creation
        docs_dir = temp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "README.md").write_text("# Documentation")
        
        scripts_dir = temp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "build.sh").write_text("#!/bin/bash\necho build")
        
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
        packages = repo_model.get("packages", [])
        
        print(f"Found {len(assemblies)} assemblies and {len(packages)} packages")
        for asm in assemblies:
            print(f"  Assembly: {asm['name']} (kind: {asm['kind']}, root: {asm['root_relpath']}) - {len(asm['package_ids'])} packages")
        
        # Verify that assembly IDs are unique
        assembly_ids = [asm["assembly_id"] for asm in assemblies]
        assert len(assembly_ids) == len(set(assembly_ids)), \
            f"Assemblies should have unique IDs, but got: {assembly_ids}"
        
        # Verify that no assembly has duplicate package IDs
        for asm in assemblies:
            package_ids = asm.get("package_ids", [])
            assert len(package_ids) == len(set(package_ids)), \
                f"Assembly '{asm['name']}' contains duplicate package IDs: {package_ids}"
        
        # Verify that packages are properly distributed (not duplicated across assemblies)
        all_package_ids_in_assemblies = []
        for asm in assemblies:
            all_package_ids_in_assemblies.extend(asm.get("package_ids", []))
        
        # The total number of package IDs across all assemblies should equal
        # the number of unique package IDs (no package should be in multiple assemblies)
        assert len(all_package_ids_in_assemblies) == len(set(all_package_ids_in_assemblies)), \
            f"Packages should not be duplicated across assemblies, but found duplicates in: {all_package_ids_in_assemblies}"