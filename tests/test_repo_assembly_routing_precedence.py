"""
Test for assembly routing precedence fix.
This test verifies that non-virtual packages are assigned to the closest non-root assembly
instead of being incorrectly assigned to the root assembly.
"""
import os
import tempfile
from pathlib import Path

import pytest

from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model


def test_uup_closest_assembly_wins():
    """Test that U++ packages route to closest assembly, not root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create U++ style directory structure similar to the example:
        # uppsrc/GameEngine/GameEngine.upp
        # uppsrc/GameEngineLib/GameEngineLib.upp
        # uppsrc/RainbowGame/RainbowGame.upp
        # docs/README.md
        # scripts/run_all_tests.sh
        uppsrc_dir = temp_path / "uppsrc"
        game_engine_dir = uppsrc_dir / "GameEngine"
        game_engine_lib_dir = uppsrc_dir / "GameEngineLib"
        rainbow_game_dir = uppsrc_dir / "RainbowGame"
        docs_dir = temp_path / "docs"
        scripts_dir = temp_path / "scripts"
        
        uppsrc_dir.mkdir()
        game_engine_dir.mkdir()
        game_engine_lib_dir.mkdir()
        rainbow_game_dir.mkdir()
        docs_dir.mkdir()
        scripts_dir.mkdir()
        
        # Create U++ package files
        (game_engine_dir / "GameEngine.upp").write_text("// GameEngine package")
        (game_engine_lib_dir / "GameEngineLib.upp").write_text("// GameEngineLib package")
        (rainbow_game_dir / "RainbowGame.upp").write_text("// RainbowGame package")
        
        # Create some docs and scripts files
        (docs_dir / "README.md").write_text("# Documentation")
        (scripts_dir / "run_all_tests.sh").write_text("#!/bin/bash\necho test")
        
        # Set MAESTRO_DOCS_ROOT
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
        
        # Create mappings for easier access
        assembly_by_id = {asm["assembly_id"]: asm for asm in assemblies}
        package_by_id = {pkg["package_id"]: pkg for pkg in packages}
        
        # Find the uppsrc assembly (should be kind "upp" with root "uppsrc")
        uppsrc_assemblies = [asm for asm in assemblies if asm["kind"] == "upp" and asm["root_relpath"] == "uppsrc"]
        docs_assembly = next((asm for asm in assemblies if asm["kind"] == "docs"), None)
        scripts_assembly = next((asm for asm in assemblies if asm["kind"] == "scripts"), None)
        
        # Find root assembly
        root_assemblies = [asm for asm in assemblies if asm["kind"] == "root"]
        
        # Assertions
        assert len(uppsrc_assemblies) >= 1, f"Should have at least one uppsrc assembly, found {len(uppsrc_assemblies)}"
        assert docs_assembly is not None, "Docs assembly should exist"
        assert scripts_assembly is not None, "Scripts assembly should exist"
        
        uppsrc_asm = uppsrc_assemblies[0]
        
        # Map package IDs to assembly info
        uppsrc_packages = [package_by_id[pkg_id] for pkg_id in uppsrc_asm["package_ids"]]
        
        # Find the U++ packages that should be in the uppsrc assembly
        game_engine_pkg = next((pkg for pkg in packages if pkg["name"] == "GameEngine"), None)
        game_engine_lib_pkg = next((pkg for pkg in packages if pkg["name"] == "GameEngineLib"), None)
        rainbow_game_pkg = next((pkg for pkg in packages if pkg["name"] == "RainbowGame"), None)
        
        # The U++ packages should be in the uppsrc assembly, not the root assembly
        assert game_engine_pkg is not None, "GameEngine package should exist"
        assert game_engine_lib_pkg is not None, "GameEngineLib package should exist"
        assert rainbow_game_pkg is not None, "RainbowGame package should exist"
        
        # Check that these packages are assigned to the uppsrc assembly
        assert game_engine_pkg["package_id"] in uppsrc_asm["package_ids"], \
            f"GameEngine package should be in uppsrc assembly"
        assert game_engine_lib_pkg["package_id"] in uppsrc_asm["package_ids"], \
            f"GameEngineLib package should be in uppsrc assembly"
        assert rainbow_game_pkg["package_id"] in uppsrc_asm["package_ids"], \
            f"RainbowGame package should be in uppsrc assembly"
        
        # Root assembly should NOT contain these U++ packages
        for root_asm in root_assemblies:
            root_pkg_ids = set(root_asm["package_ids"])
            assert game_engine_pkg["package_id"] not in root_pkg_ids, \
                f"Root assembly should not contain GameEngine package"
            assert game_engine_lib_pkg["package_id"] not in root_pkg_ids, \
                f"Root assembly should not contain GameEngineLib package"
            assert rainbow_game_pkg["package_id"] not in root_pkg_ids, \
                f"Root assembly should not contain RainbowGame package"


def test_uup_trash_assembly_wins_for_trash_uppsrc():
    """Test that packages in trash/uppsrc route to trash/uppsrc assembly, not root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure:
        # trash/uppsrc/OldGame/OldGame.upp
        trash_dir = temp_path / "trash"
        trash_uppsrc_dir = trash_dir / "uppsrc"
        old_game_dir = trash_uppsrc_dir / "OldGame"
        
        trash_dir.mkdir()
        trash_uppsrc_dir.mkdir()
        old_game_dir.mkdir()
        
        # Create U++ package file
        (old_game_dir / "OldGame.upp").write_text("// OldGame package")
        
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
        
        # Find assemblies and packages
        assemblies = repo_model.get("assemblies", [])
        packages = repo_model.get("packages", [])
        
        # Find the trash/uppsrc assembly (should be kind "upp" with root "trash/uppsrc")
        trash_uppsrc_assemblies = [asm for asm in assemblies if asm["kind"] == "upp" and asm["root_relpath"] == "trash/uppsrc"]
        
        # Find root assembly
        root_assemblies = [asm for asm in assemblies if asm["kind"] == "root"]
        
        # Assertions
        assert len(trash_uppsrc_assemblies) >= 1, f"Should have at least one trash/uppsrc assembly, found {len(trash_uppsrc_assemblies)}"
        
        trash_uppsrc_asm = trash_uppsrc_assemblies[0]
        
        # Find the OldGame package
        old_game_pkg = next((pkg for pkg in packages if pkg["name"] == "OldGame"), None)
        
        assert old_game_pkg is not None, "OldGame package should exist"
        
        # The OldGame package should be in the trash/uppsrc assembly, not the root assembly
        assert old_game_pkg["package_id"] in trash_uppsrc_asm["package_ids"], \
            f"OldGame package should be in trash/uppsrc assembly"
        
        # Root assembly should NOT contain the OldGame package
        for root_asm in root_assemblies:
            root_pkg_ids = set(root_asm["package_ids"])
            assert old_game_pkg["package_id"] not in root_pkg_ids, \
                f"Root assembly should not contain OldGame package"


def test_batchscriptshell_kind_wins_still_holds():
    """Test that BatchScriptShell 'kind wins' behavior still works."""
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
        
        # Create a CMakeLists.txt to ensure we get a non-virtual package
        (temp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\nproject(Test)")
        (temp_path / "main.cpp").write_text("int main() { return 0; }")
        
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
        
        # Find specific assemblies by kind
        scripts_assembly = next((asm for asm in assemblies if asm["kind"] == "scripts"), None)
        docs_assembly = next((asm for asm in assemblies if asm["kind"] == "docs"), None)
        tests_assembly = next((asm for asm in assemblies if asm["kind"] == "tests"), None)
        
        # Find root assembly
        root_assemblies = [asm for asm in assemblies if asm["kind"] == "root"]
        
        # Assertions
        assert scripts_assembly is not None, "Scripts assembly should exist"
        assert docs_assembly is not None, "Docs assembly should exist"
        assert tests_assembly is not None, "Tests assembly should exist"
        assert len(root_assemblies) >= 1, "Root assembly should exist"
        
        root_asm = root_assemblies[0]
        
        # Find virtual packages
        scripts_virtual_packages = [pkg for pkg in packages if pkg["name"].startswith("scripts-")]
        docs_virtual_packages = [pkg for pkg in packages if pkg["name"].startswith("docs-")]
        tests_virtual_packages = [pkg for pkg in packages if pkg["name"].startswith("tests-")]
        
        # Virtual packages should go to their kind assemblies, not root
        for pkg in scripts_virtual_packages:
            assert pkg["package_id"] in scripts_assembly["package_ids"], \
                f"Scripts virtual package {pkg['name']} should be in scripts assembly"
        
        for pkg in docs_virtual_packages:
            assert pkg["package_id"] in docs_assembly["package_ids"], \
                f"Docs virtual package {pkg['name']} should be in docs assembly"
        
        for pkg in tests_virtual_packages:
            assert pkg["package_id"] in tests_assembly["package_ids"], \
                f"Tests virtual package {pkg['name']} should be in tests assembly"
        
        # Root assembly should NOT contain virtual packages
        root_pkg_ids = set(root_asm["package_ids"])
        for pkg in scripts_virtual_packages + docs_virtual_packages + tests_virtual_packages:
            assert pkg["package_id"] not in root_pkg_ids, \
                f"Root assembly should not contain virtual package {pkg['name']}"


def test_deterministic_membership_ordering():
    """Test that assembly package ordering is deterministic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create U++ style directory structure
        uppsrc_dir = temp_path / "uppsrc"
        game_engine_dir = uppsrc_dir / "GameEngine"
        game_engine_lib_dir = uppsrc_dir / "GameEngineLib"
        
        uppsrc_dir.mkdir()
        game_engine_dir.mkdir()
        game_engine_lib_dir.mkdir()
        
        # Create U++ package files
        (game_engine_dir / "GameEngine.upp").write_text("// GameEngine package")
        (game_engine_lib_dir / "GameEngineLib.upp").write_text("// GameEngineLib package")
        
        # Set MAESTRO_DOCS_ROOT
        os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path / "docs" / "maestro")
        (temp_path / "docs").mkdir(exist_ok=True)
        
        # Run the repo scan twice to ensure deterministic results
        scan_result1 = scan_upp_repo_v2(
            str(temp_path),
            verbose=False,
            include_user_config=False,
            collect_files=True,
            scan_unknown_paths=True,
        )
        
        # Write the repo artifacts
        write_repo_artifacts(str(temp_path), scan_result1, verbose=False)
        
        # Load the repo model to verify the results
        repo_model1 = load_repo_model(str(temp_path))
        
        # Create a second temp directory to ensure clean state
        with tempfile.TemporaryDirectory() as temp_dir2:
            temp_path2 = Path(temp_dir2)
            
            # Recreate the same structure
            uppsrc_dir2 = temp_path2 / "uppsrc"
            game_engine_dir2 = uppsrc_dir2 / "GameEngine"
            game_engine_lib_dir2 = uppsrc_dir2 / "GameEngineLib"
            
            uppsrc_dir2.mkdir()
            game_engine_dir2.mkdir()
            game_engine_lib_dir2.mkdir()
            
            (game_engine_dir2 / "GameEngine.upp").write_text("// GameEngine package")
            (game_engine_lib_dir2 / "GameEngineLib.upp").write_text("// GameEngineLib package")
            
            os.environ["MAESTRO_DOCS_ROOT"] = str(temp_path2 / "docs" / "maestro")
            (temp_path2 / "docs").mkdir(exist_ok=True)
            
            scan_result2 = scan_upp_repo_v2(
                str(temp_path2),
                verbose=False,
                include_user_config=False,
                collect_files=True,
                scan_unknown_paths=True,
            )
            
            write_repo_artifacts(str(temp_path2), scan_result2, verbose=False)
            repo_model2 = load_repo_model(str(temp_path2))
            
            # Find the uppsrc assemblies in both models
            assemblies1 = repo_model1.get("assemblies", [])
            assemblies2 = repo_model2.get("assemblies", [])

            uppsrc_asm1 = next((asm for asm in assemblies1 if asm["kind"] == "upp" and asm["root_relpath"] == "uppsrc"), None)
            uppsrc_asm2 = next((asm for asm in assemblies2 if asm["kind"] == "upp" and asm["root_relpath"] == "uppsrc"), None)

            assert uppsrc_asm1 is not None, "First uppsrc assembly should exist"
            assert uppsrc_asm2 is not None, "Second uppsrc assembly should exist"

            # Get the packages for each assembly
            packages1 = repo_model1.get("packages", [])
            packages2 = repo_model2.get("packages", [])

            # Map package IDs to package names for both runs
            pkg_id_to_name1 = {pkg["package_id"]: pkg["name"] for pkg in packages1}
            pkg_id_to_name2 = {pkg["package_id"]: pkg["name"] for pkg in packages2}

            # Get package names in order for both assemblies
            pkg_names1 = [pkg_id_to_name1[pkg_id] for pkg_id in uppsrc_asm1["package_ids"]]
            pkg_names2 = [pkg_id_to_name2[pkg_id] for pkg_id in uppsrc_asm2["package_ids"]]

            # The package names should be in the same order between runs (deterministic)
            assert pkg_names1 == pkg_names2, \
                f"Package names should be ordered deterministically: {pkg_names1} vs {pkg_names2}"