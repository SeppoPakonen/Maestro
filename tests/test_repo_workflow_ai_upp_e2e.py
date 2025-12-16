"""
End-to-end workflow test for maestro repo commands on ~/Dev/ai-upp/

Tests the complete operator-grade workflow:
1. maestro init
2. maestro repo resolve (no --path needed)
3. maestro repo show

This validates that the natural CLI workflow works on a real U++ repository.
"""

import os
import pytest
import subprocess
import sys
import json
import shutil
from pathlib import Path


def test_repo_workflow_e2e():
    """
    Test the complete repo workflow: init → repo resolve → repo show.

    This test validates that:
    - maestro init creates .maestro/ directory
    - maestro repo resolve auto-detects repo root and writes artifacts
    - maestro repo show loads and displays the index
    """
    repo_path = os.environ.get('MAESTRO_TEST_AI_UPP_PATH', os.path.expanduser('~/Dev/ai-upp'))

    # Skip if path does not exist
    if not os.path.exists(repo_path):
        pytest.skip(f"Repository path does not exist: {repo_path}")

    maestro_dir = os.path.join(repo_path, '.maestro')
    marker_file = os.path.join(maestro_dir, '.test_marker')

    # Track if we created .maestro directory (for cleanup)
    created_maestro = False

    try:
        # Step 1: Run maestro init
        init_cmd = ['python', '-m', 'maestro', 'init', '--dir', repo_path]
        init_result = subprocess.run(init_cmd, capture_output=True, text=True, timeout=30, cwd=repo_path)

        assert init_result.returncode == 0, f"maestro init failed: {init_result.stderr}"

        # Check that .maestro directory was created
        assert os.path.exists(maestro_dir), f".maestro directory was not created at {maestro_dir}"

        # Create marker file to indicate this was created by test
        with open(marker_file, 'w') as f:
            f.write('created-by-test')
        created_maestro = True

        # Step 2: Run maestro repo resolve (no --path argument, should auto-detect)
        resolve_cmd = ['python', '-m', 'maestro', 'repo', 'resolve']
        resolve_result = subprocess.run(
            resolve_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=repo_path
        )

        assert resolve_result.returncode == 0, f"maestro repo resolve failed: {resolve_result.stderr}"

        # Verify output contains expected text
        assert 'REPOSITORY SCAN COMPLETE' in resolve_result.stdout or 'assemblies_detected' in resolve_result.stdout, \
            f"Unexpected output from repo resolve: {resolve_result.stdout}"

        # Step 3: Verify artifacts were created
        repo_dir = Path(maestro_dir) / 'repo'
        index_json = repo_dir / 'index.json'
        index_summary = repo_dir / 'index.summary.txt'
        state_json = repo_dir / 'state.json'

        assert index_json.exists(), f"index.json not created at {index_json}"
        assert index_summary.exists(), f"index.summary.txt not created at {index_summary}"
        assert state_json.exists(), f"state.json not created at {state_json}"

        # Step 4: Validate index.json structure
        with open(index_json, 'r') as f:
            index_data = json.load(f)

        assert 'assemblies_detected' in index_data, "Missing 'assemblies_detected' in index.json"
        assert 'packages_detected' in index_data, "Missing 'packages_detected' in index.json"
        assert 'unknown_paths' in index_data, "Missing 'unknown_paths' in index.json"

        # Validate packages were detected
        assert len(index_data['packages_detected']) > 0, "No packages detected"

        # Step 5: Validate state.json structure
        with open(state_json, 'r') as f:
            state_data = json.load(f)

        assert 'last_resolved_at' in state_data, "Missing 'last_resolved_at' in state.json"
        assert 'repo_root' in state_data, "Missing 'repo_root' in state.json"
        assert 'packages_count' in state_data, "Missing 'packages_count' in state.json"
        assert 'scanner_version' in state_data, "Missing 'scanner_version' in state.json"

        assert state_data['packages_count'] == len(index_data['packages_detected']), \
            "Package count mismatch between state.json and index.json"

        # Step 6: Run maestro repo show --json
        show_cmd = ['python', '-m', 'maestro', 'repo', 'show', '--json']
        show_result = subprocess.run(
            show_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=repo_path
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
        show_text_cmd = ['python', '-m', 'maestro', 'repo', 'show']
        show_text_result = subprocess.run(
            show_text_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=repo_path
        )

        assert show_text_result.returncode == 0, f"maestro repo show (text) failed: {show_text_result.stderr}"
        assert 'REPOSITORY INDEX' in show_text_result.stdout or 'Repository:' in show_text_result.stdout, \
            f"Unexpected output from repo show: {show_text_result.stdout}"

        # Verify the workflow is complete and coherent
        print("\n✓ Workflow test passed!")
        print(f"  - Init created .maestro/")
        print(f"  - Resolve auto-detected repo and wrote {len(index_data['packages_detected'])} packages")
        print(f"  - Show successfully loaded and displayed index")

    finally:
        # Cleanup - remove .maestro directory if we created it
        if created_maestro and os.path.exists(marker_file):
            # Only delete if marker file exists (indicating we created it)
            try:
                shutil.rmtree(maestro_dir)
            except Exception as e:
                # Best effort cleanup - don't fail the test if cleanup fails
                print(f"Warning: Failed to clean up .maestro directory: {e}")
