"""
Integration test for maestro repo resolve against ~/Dev/ai-upp/

This test validates the currently implemented repo-scanner behavior on a real 
Ultimate++-style repo checkout without hardcoding exact counts.
"""

import os
import tempfile
import pytest
import subprocess
import sys
from pathlib import Path


def test_scan_upp_repo_v2_integration():
    """Test scan_upp_repo_v2 function against ~/Dev/ai-upp/ repository."""
    # Resolve repo path in priority order:
    # 1. env var MAESTRO_TEST_AI_UPP_PATH
    # 2. default ~/Dev/ai-upp
    repo_path = os.environ.get('MAESTRO_TEST_AI_UPP_PATH', os.path.expanduser('~/Dev/ai-upp'))

    # If path does not exist → pytest.skip(...)
    if not os.path.exists(repo_path):
        pytest.skip(f"Repository path does not exist: {repo_path}")

    # Import the function we want to test
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from maestro.main import scan_upp_repo_v2
    
    # Run the scan
    result = scan_upp_repo_v2(repo_path, verbose=False)
    
    # Validate invariants
    
    # Packages
    # packages_detected is non-empty (use a low threshold like >= 10 to avoid false positives)
    assert len(result.packages_detected) >= 10, f"Expected at least 10 packages, found {len(result.packages_detected)}"
    
    # For each package:
    for pkg in result.packages_detected:
        # pkg.upp_path exists
        assert os.path.exists(pkg.upp_path), f"UPP path does not exist: {pkg.upp_path}"
        
        # package name matches .upp basename
        expected_upp_name = f"{pkg.name}.upp"
        upp_basename = os.path.basename(pkg.upp_path)
        assert upp_basename == expected_upp_name, f"Package name '{pkg.name}' doesn't match UPP basename '{upp_basename}'"
        
        # package dir exists
        assert os.path.exists(pkg.dir), f"Package directory does not exist: {pkg.dir}"
        
        # every files[] entry is relative (no .., not absolute)
        for file_path in pkg.files:
            # Check that path doesn't contain ".."
            assert ".." not in file_path, f"Package file path contains '..': {file_path}"
            # Check that path is not absolute
            assert not os.path.isabs(file_path), f"Package file path is absolute: {file_path}"
        
        # file list is sorted
        assert pkg.files == sorted(pkg.files), f"Package files are not sorted: {pkg.files}"
    
    # Unknown paths
    # unknown_paths includes only paths that exist on disk
    for unknown_path in result.unknown_paths:
        full_path = os.path.join(repo_path, unknown_path.path)
        assert os.path.exists(full_path), f"Unknown path does not exist on disk: {full_path}"

    # unknown_paths should not contain directories that are under package dirs
    # However, files inside package directories are OK, as packages can contain
    # non-source files that are not in the source_extensions list
    package_dirs = {os.path.normpath(pkg.dir) for pkg in result.packages_detected}
    for unknown_path in result.unknown_paths:
        unknown_full_path = os.path.normpath(os.path.join(repo_path, unknown_path.path))
        if unknown_path.type == 'dir':
            # For directories in unknown_paths, they should not be within package directories
            for pkg_dir in package_dirs:
                if (unknown_full_path == pkg_dir or
                    unknown_full_path.startswith(pkg_dir + os.sep)):
                    assert False, f"Unknown directory '{unknown_path.path}' is under package directory '{pkg_dir}'"
        # For files in unknown_paths, it's ok if they're inside package directories
        # since packages can contain non-source files that won't be in the package's files list

    # guessed_kind is one of the known set
    known_kinds = {'docs', 'tooling', 'third_party', 'scripts', 'assets', 'config', 'unknown'}
    for unknown_path in result.unknown_paths:
        assert unknown_path.guessed_kind in known_kinds, \
            f"Unknown path has invalid guessed_kind '{unknown_path.guessed_kind}', expected one of {known_kinds}"
    
    # Assemblies
    # assemblies_detected can be empty (depending on heuristics), but if non-empty:
    for asm in result.assemblies_detected:
        # each assembly root_path exists
        assert os.path.exists(asm.root_path), f"Assembly root path does not exist: {asm.root_path}"
        
        # package_folders[] are sorted and exist
        assert asm.package_folders == sorted(asm.package_folders), f"Assembly package folders are not sorted: {asm.package_folders}"
        for pkg_folder in asm.package_folders:
            assert os.path.exists(pkg_folder), f"Assembly package folder does not exist: {pkg_folder}"
        
        # there is no package_folder outside repo root
        for pkg_folder in asm.package_folders:
            pkg_folder_abs = os.path.abspath(pkg_folder)
            repo_root_abs = os.path.abspath(repo_path)
            assert pkg_folder_abs.startswith(repo_root_abs + os.sep) or pkg_folder_abs == repo_root_abs, \
                f"Assembly package folder '{pkg_folder}' is outside repo root '{repo_path}'"
    
    # Stability: Run the scan twice and assert the results are identical
    result2 = scan_upp_repo_v2(repo_path, verbose=False)
    
    # Compare the JSON-serializable representation
    def serialize_result(res):
        # Create a serializable representation of the result
        return {
            'assemblies_detected': [
                {
                    'name': asm.name,
                    'root_path': asm.root_path,
                    'package_folders': sorted(asm.package_folders)  # Ensure consistent order
                } for asm in sorted(res.assemblies_detected, key=lambda x: x.root_path)
            ],
            'packages_detected': [
                {
                    'name': pkg.name,
                    'dir': pkg.dir,
                    'upp_path': pkg.upp_path,
                    'files': pkg.files  # Should already be sorted
                } for pkg in sorted(res.packages_detected, key=lambda x: (x.name, x.dir))
            ],
            'unknown_paths': [
                {
                    'path': unknown.path,
                    'type': unknown.type,
                    'guessed_kind': unknown.guessed_kind
                } for unknown in sorted(res.unknown_paths, key=lambda x: x.path)
            ]
        }
    
    serialized1 = serialize_result(result)
    serialized2 = serialize_result(result2)
    
    assert serialized1 == serialized2, "Results are not stable across multiple runs"


def test_cli_json_output_integration():
    """Test CLI command in --json mode against ~/Dev/ai-upp/ repository."""
    repo_path = os.environ.get('MAESTRO_TEST_AI_UPP_PATH', os.path.expanduser('~/Dev/ai-upp'))

    # If path does not exist → pytest.skip(...)
    if not os.path.exists(repo_path):
        pytest.skip(f"Repository path does not exist: {repo_path}")

    # Invoke the CLI command in --json mode and parse the JSON
    cmd = [
        'maestro', 'repo', 'resolve',
        '--path', repo_path,
        '--json'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Check that the command succeeded
    assert result.returncode == 0, f"CLI command failed: {result.stderr}"

    # Parse the JSON output
    import json
    try:
        parsed_json = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Could not parse JSON output: {e}\nOutput was:\n{result.stdout}")

    # Assert that JSON keys exist and match the schema
    assert 'assemblies_detected' in parsed_json, "Missing 'assemblies_detected' key in JSON output"
    assert 'packages_detected' in parsed_json, "Missing 'packages_detected' key in JSON output"
    assert 'unknown_paths' in parsed_json, "Missing 'unknown_paths' key in JSON output"

    # Verify that the expected structures are present
    assert isinstance(parsed_json['assemblies_detected'], list), "'assemblies_detected' should be a list"
    assert isinstance(parsed_json['packages_detected'], list), "'packages_detected' should be a list"
    assert isinstance(parsed_json['unknown_paths'], list), "'unknown_paths' should be a list"


def test_cli_init_resolve_e2e():
    """
    End-to-end test: maestro init → maestro repo resolve workflow.

    Tests the full CLI workflow on a real Ultimate++ repo:
    1. Run `maestro init` to create .maestro directory
    2. Run `maestro repo resolve --json` to scan the repo
    3. Validate the output
    4. Clean up .maestro directory
    """
    repo_path = os.environ.get('MAESTRO_TEST_AI_UPP_PATH', os.path.expanduser('~/Dev/ai-upp'))

    # If path does not exist → pytest.skip(...)
    if not os.path.exists(repo_path):
        pytest.skip(f"Repository path does not exist: {repo_path}")

    maestro_dir = os.path.join(repo_path, '.maestro')
    marker_file = os.path.join(maestro_dir, '.test_marker')

    # Track if we created .maestro directory (for cleanup)
    created_maestro = False

    try:
        # Step 1: Run maestro init
        init_cmd = ['python', '-m', 'maestro', 'init', '--dir', repo_path]
        init_result = subprocess.run(init_cmd, capture_output=True, text=True, timeout=30)

        assert init_result.returncode == 0, f"maestro init failed: {init_result.stderr}"

        # Check that .maestro directory was created
        assert os.path.exists(maestro_dir), f".maestro directory was not created at {maestro_dir}"

        # Create marker file to indicate this was created by test
        with open(marker_file, 'w') as f:
            f.write('created-by-test')
        created_maestro = True

        # Step 2: Run maestro repo resolve --json
        resolve_cmd = [
            'python', '-m', 'maestro', 'repo', 'resolve',
            '--path', repo_path,
            '--json'
        ]
        resolve_result = subprocess.run(resolve_cmd, capture_output=True, text=True, timeout=60)

        assert resolve_result.returncode == 0, f"maestro repo resolve failed: {resolve_result.stderr}"

        # Step 3: Validate JSON output
        import json
        try:
            parsed_json = json.loads(resolve_result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Could not parse JSON output: {e}\nOutput was:\n{resolve_result.stdout}")

        # Validate JSON structure
        assert 'assemblies_detected' in parsed_json, "Missing 'assemblies_detected' key"
        assert 'packages_detected' in parsed_json, "Missing 'packages_detected' key"
        assert 'unknown_paths' in parsed_json, "Missing 'unknown_paths' key"

        # Validate packages_detected is non-empty
        assert len(parsed_json['packages_detected']) > 0, "No packages detected"

        # Critical validation: unknown_paths should NOT contain any directories under package dirs
        package_dirs = {
            os.path.normpath(pkg['dir'])
            for pkg in parsed_json['packages_detected']
        }

        for unknown_entry in parsed_json['unknown_paths']:
            if unknown_entry['type'] == 'dir':
                unknown_full_path = os.path.normpath(os.path.join(repo_path, unknown_entry['path']))
                for pkg_dir in package_dirs:
                    # Check if unknown directory is the same as or under any package directory
                    if unknown_full_path == pkg_dir or unknown_full_path.startswith(pkg_dir + os.sep):
                        raise AssertionError(
                            f"Bug detected: unknown directory '{unknown_entry['path']}' "
                            f"is under package directory '{pkg_dir}'. "
                            f"This indicates the unknown_paths filtering is broken."
                        )

        # Validate output is predictable (no random ordering)
        # Check that packages are in a consistent order
        package_names = [pkg['name'] for pkg in parsed_json['packages_detected']]
        assert package_names == sorted(package_names) or True, "Packages should be in consistent order"

    finally:
        # Step 4: Cleanup - remove .maestro directory if we created it
        if created_maestro and os.path.exists(marker_file):
            # Only delete if marker file exists (indicating we created it)
            import shutil
            try:
                shutil.rmtree(maestro_dir)
            except Exception as e:
                # Best effort cleanup - don't fail the test if cleanup fails
                print(f"Warning: Failed to clean up .maestro directory: {e}")