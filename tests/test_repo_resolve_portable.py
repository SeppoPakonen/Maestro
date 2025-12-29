"""
Portable integration test for maestro repo resolve.

This test validates repo-scanner behavior on a small portable test repository
without requiring external dependencies like ~/Dev/ai-upp/
"""

import os
import shlex
import tempfile
import pytest
import subprocess
import sys
from pathlib import Path

CLI_TIMEOUT = int(os.environ.get("MAESTRO_CLI_TIMEOUT", "60"))
CLI_INIT_TIMEOUT = int(os.environ.get("MAESTRO_CLI_INIT_TIMEOUT", "15"))

pytestmark = pytest.mark.fast


def _maestro_cmd() -> list[str]:
    maestro_bin = os.environ.get("MAESTRO_BIN")
    if maestro_bin:
        return shlex.split(maestro_bin)
    repo_root = Path(__file__).resolve().parents[1]
    return [sys.executable, str(repo_root / "maestro.py")]


def _get_test_repo() -> str:
    """Get path to portable test repository."""
    test_dir = Path(__file__).parent
    return str(test_dir / "fixtures" / "upp_repo_medium")


def test_scan_portable_repo_v2():
    """Test scan_upp_repo_v2 function against portable test repository."""
    repo_path = _get_test_repo()
    
    # Import the function we want to test
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from maestro.main import scan_upp_repo_v2
    
    # Run the scan
    result = scan_upp_repo_v2(repo_path, verbose=False)
    
    # Validate invariants
    
    # Packages
    # Should find 15 packages in our test fixture
    assert len(result.packages_detected) == 15, \
        f"Expected 15 packages, found {len(result.packages_detected)}"
    
    # For each package:
    for pkg in result.packages_detected:
        # pkg.upp_path exists
        assert os.path.exists(pkg.upp_path), f"UPP path does not exist: {pkg.upp_path}"
        
        # package name matches .upp basename
        expected_upp_name = f"{pkg.name}.upp"
        upp_basename = os.path.basename(pkg.upp_path)
        assert upp_basename == expected_upp_name, \
            f"Package name '{pkg.name}' doesn't match UPP basename '{upp_basename}'"
        
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
    package_dirs = {os.path.normpath(pkg.dir) for pkg in result.packages_detected}
    for unknown_path in result.unknown_paths:
        unknown_full_path = os.path.normpath(os.path.join(repo_path, unknown_path.path))
        if unknown_path.type == 'dir':
            # For directories in unknown_paths, they should not be within package directories
            for pkg_dir in package_dirs:
                if (unknown_full_path == pkg_dir or
                    unknown_full_path.startswith(pkg_dir + os.sep)):
                    assert False, \
                        f"Unknown directory '{unknown_path.path}' is under package directory '{pkg_dir}'"
    
    # guessed_kind is one of the known set
    known_kinds = {'docs', 'tooling', 'third_party', 'scripts', 'assets', 'config', 'unknown'}
    for unknown_path in result.unknown_paths:
        assert unknown_path.guessed_kind in known_kinds, \
            f"Unknown path has invalid guessed_kind '{unknown_path.guessed_kind}', expected one of {known_kinds}"
    
    # Stability: Run the scan twice and assert the results are identical
    result2 = scan_upp_repo_v2(repo_path, verbose=False)
    
    # Compare the JSON-serializable representation
    def serialize_result(res):
        return {
            'assemblies_detected': [
                {
                    'name': asm.name,
                    'root_path': asm.root_path,
                    'package_folders': sorted(asm.package_folders)
                } for asm in sorted(res.assemblies_detected, key=lambda x: x.root_path)
            ],
            'packages_detected': [
                {
                    'name': pkg.name,
                    'dir': pkg.dir,
                    'upp_path': pkg.upp_path,
                    'files': pkg.files
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


def test_cli_json_output_portable():
    """Test CLI command in --json mode against portable test repository."""
    repo_path = _get_test_repo()

    # Invoke the CLI command in --json mode and parse the JSON
    cmd = _maestro_cmd() + [
        "repo", "resolve",
        "--path", repo_path,
        "--json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)

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
    
    # Should find 15 packages
    assert len(parsed_json['packages_detected']) == 15, \
        f"Expected 15 packages, found {len(parsed_json['packages_detected'])}"


def test_cli_init_resolve_e2e_portable():
    """
    End-to-end test: maestro init → maestro repo resolve workflow on portable repo.
    """
    repo_path = _get_test_repo()

    # Use a temporary directory for docs/maestro
    with tempfile.TemporaryDirectory() as tmpdir:
        test_repo = Path(tmpdir) / "test_repo"
        
        # Copy test fixture to temp location
        import shutil
        shutil.copytree(repo_path, test_repo)
        
        repo_truth_dir = test_repo / 'docs' / 'maestro'

        # Step 1: Run maestro init
        init_cmd = _maestro_cmd() + ["init", "--dir", str(test_repo)]
        init_result = subprocess.run(init_cmd, capture_output=True, text=True, timeout=CLI_INIT_TIMEOUT)

        assert init_result.returncode == 0, f"maestro init failed: {init_result.stderr}"

        # Check that docs/maestro directory was created
        assert repo_truth_dir.exists(), f"docs/maestro directory was not created at {repo_truth_dir}"

        # Step 2: Run maestro repo resolve --json
        resolve_cmd = _maestro_cmd() + [
            "repo", "resolve",
            "--path", str(test_repo),
            "--json",
        ]
        resolve_result = subprocess.run(resolve_cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)

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
        assert len(parsed_json['packages_detected']) == 15, \
            f"Expected 15 packages, found {len(parsed_json['packages_detected'])}"

        # Validate unknown_paths should NOT contain any directories under package dirs
        package_dirs = {
            os.path.normpath(pkg['dir'])
            for pkg in parsed_json['packages_detected']
        }

        for unknown_entry in parsed_json['unknown_paths']:
            if unknown_entry['type'] == 'dir':
                unknown_full_path = os.path.normpath(os.path.join(str(test_repo), unknown_entry['path']))
                for pkg_dir in package_dirs:
                    if unknown_full_path == pkg_dir or unknown_full_path.startswith(pkg_dir + os.sep):
                        raise AssertionError(
                            f"Bug detected: unknown directory '{unknown_entry['path']}' "
                            f"is under package directory '{pkg_dir}'. "
                            f"This indicates the unknown_paths filtering is broken."
                        )


def test_repo_workflow_e2e_portable():
    """
    Test the complete repo workflow: init → repo resolve → repo show on portable repo.
    """
    repo_path = _get_test_repo()

    # Use a temporary directory for the test
    with tempfile.TemporaryDirectory() as tmpdir:
        test_repo = Path(tmpdir) / "test_repo"
        
        # Copy test fixture to temp location
        import shutil
        shutil.copytree(repo_path, test_repo)
        
        repo_truth_dir = test_repo / 'docs' / 'maestro'

        # Step 1: Run maestro init
        init_cmd = _maestro_cmd() + ["init", "--dir", str(test_repo)]
        init_result = subprocess.run(
            init_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_INIT_TIMEOUT,
            cwd=str(test_repo),
        )

        assert init_result.returncode == 0, f"maestro init failed: {init_result.stderr}"
        assert repo_truth_dir.exists(), f"docs/maestro directory was not created at {repo_truth_dir}"

        # Step 2: Run maestro repo resolve
        resolve_cmd = _maestro_cmd() + ["repo", "resolve", "--json"]
        resolve_result = subprocess.run(
            resolve_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT,
            cwd=str(test_repo)
        )

        assert resolve_result.returncode == 0, f"maestro repo resolve failed: {resolve_result.stderr}"

        # Step 3: Verify artifacts were created
        repo_model = repo_truth_dir / 'repo_model.json'
        repo_state = repo_truth_dir / 'repo_state.json'

        assert repo_model.exists(), f"repo_model.json not created at {repo_model}"
        assert repo_state.exists(), f"repo_state.json not created at {repo_state}"

        # Step 4: Validate repo_model.json structure
        import json
        with open(repo_model, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        assert 'assemblies_detected' in index_data, "Missing 'assemblies_detected' in repo_model.json"
        assert 'packages_detected' in index_data, "Missing 'packages_detected' in repo_model.json"
        assert 'unknown_paths' in index_data, "Missing 'unknown_paths' in repo_model.json"

        # Validate packages were detected
        assert len(index_data['packages_detected']) == 15, \
            f"Expected 15 packages, found {len(index_data['packages_detected'])}"

        # Step 5: Validate repo_state.json structure
        with open(repo_state, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        assert 'last_resolved_at' in state_data, "Missing 'last_resolved_at' in state.json"
        assert 'repo_root' in state_data, "Missing 'repo_root' in state.json"
        assert 'packages_count' in state_data, "Missing 'packages_count' in state.json"
        assert 'scanner_version' in state_data, "Missing 'scanner_version' in state.json"

        assert state_data['packages_count'] == len(index_data['packages_detected']), \
            "Package count mismatch between state.json and repo_model.json"

        # Step 6: Run maestro repo show --json
        show_cmd = _maestro_cmd() + ["repo", "show", "--json"]
        show_result = subprocess.run(
            show_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_INIT_TIMEOUT,
            cwd=str(test_repo)
        )

        assert show_result.returncode == 0, f"maestro repo show failed: {show_result.stderr}"

        # Parse and validate JSON output
        try:
            show_json = json.loads(show_result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Could not parse JSON from repo show: {e}\nOutput: {show_result.stdout}")

        assert 'assemblies_detected' in show_json, "Missing 'assemblies_detected' in show output"
        assert 'packages_detected' in show_json, "Missing 'packages_detected' in show output"
        assert 'unknown_paths' in show_json, "Missing 'unknown_paths' in show output"

        # Step 7: Run maestro repo show (human-readable)
        show_text_cmd = _maestro_cmd() + ["repo", "show"]
        show_text_result = subprocess.run(
            show_text_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_INIT_TIMEOUT,
            cwd=str(test_repo)
        )

        assert show_text_result.returncode == 0, f"maestro repo show (text) failed: {show_text_result.stderr}"
        assert 'REPOSITORY INDEX' in show_text_result.stdout or 'Repository:' in show_text_result.stdout, \
            f"Unexpected output from repo show: {show_text_result.stdout}"
