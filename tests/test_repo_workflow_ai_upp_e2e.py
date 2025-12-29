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
import shlex
from pathlib import Path

CLI_TIMEOUT = int(os.environ.get("MAESTRO_CLI_TIMEOUT", "300"))
CLI_INIT_TIMEOUT = int(os.environ.get("MAESTRO_CLI_INIT_TIMEOUT", "60"))
CLI_SHOW_TIMEOUT = int(os.environ.get("MAESTRO_CLI_SHOW_TIMEOUT", "60"))

pytestmark = pytest.mark.slow


def _maestro_cmd() -> list[str]:
    maestro_bin = os.environ.get("MAESTRO_BIN")
    if maestro_bin:
        return shlex.split(maestro_bin)
    repo_root = Path(__file__).resolve().parents[1]
    return [sys.executable, str(repo_root / "maestro.py")]


def test_repo_workflow_e2e():
    """
    Test the complete repo workflow: init → repo resolve → repo show.

    This test validates that:
    - maestro init creates docs/maestro/ directory
    - maestro repo resolve auto-detects repo root and writes artifacts
    - maestro repo show loads and displays the index
    """
    repo_path = os.environ.get('MAESTRO_TEST_AI_UPP_PATH', os.path.expanduser('~/Dev/ai-upp'))

    # Skip if path does not exist
    if not os.path.exists(repo_path):
        pytest.skip(f"Repository path does not exist: {repo_path}")

    repo_truth_dir = Path(repo_path) / 'docs' / 'maestro'
    marker_file = repo_truth_dir / '.test_marker'

    # Track if we created repo truth directory (for cleanup)
    created_repo_truth = False

    try:
        # Step 1: Run maestro init (if docs/maestro doesn't exist)
        if not repo_truth_dir.exists():
            init_cmd = _maestro_cmd() + ["init", "--dir", repo_path]
            init_result = subprocess.run(
                init_cmd,
                capture_output=True,
                text=True,
                timeout=CLI_INIT_TIMEOUT,
                cwd=repo_path,
            )

            assert init_result.returncode == 0, f"maestro init failed: {init_result.stderr}"

            # Check that docs/maestro directory was created
            assert repo_truth_dir.exists(), f"docs/maestro directory was not created at {repo_truth_dir}"

            # Create marker file to indicate this was created by test
            with open(marker_file, 'w', encoding='utf-8') as f:
                f.write('created-by-test')
            created_repo_truth = True
        else:
            print(f"\nℹ️  docs/maestro already exists at {repo_truth_dir}, skipping init")

        # Step 2: Run maestro repo resolve (no --path argument, should auto-detect)
        # Note: ai-upp is large (1400+ packages), so we use JSON mode for a faster scan
        resolve_cmd = _maestro_cmd() + ["repo", "resolve", "--json"]
        resolve_result = subprocess.run(
            resolve_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT,
            cwd=repo_path
        )

        assert resolve_result.returncode == 0, f"maestro repo resolve failed: {resolve_result.stderr}"

        # Verify output contains expected text
        assert 'REPOSITORY SCAN COMPLETE' in resolve_result.stdout or 'assemblies_detected' in resolve_result.stdout, \
            f"Unexpected output from repo resolve: {resolve_result.stdout}"

        # Step 3: Verify artifacts were created
        repo_model = repo_truth_dir / 'repo_model.json'
        repo_state = repo_truth_dir / 'repo_state.json'

        assert repo_model.exists(), f"repo_model.json not created at {repo_model}"
        assert repo_state.exists(), f"repo_state.json not created at {repo_state}"

        # Step 4: Validate index.json structure
        with open(repo_model, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        assert 'assemblies_detected' in index_data, "Missing 'assemblies_detected' in index.json"
        assert 'packages_detected' in index_data, "Missing 'packages_detected' in index.json"
        assert 'unknown_paths' in index_data, "Missing 'unknown_paths' in index.json"

        # Validate packages were detected
        assert len(index_data['packages_detected']) > 0, "No packages detected"

        # Step 5: Validate state.json structure
        with open(repo_state, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        assert 'last_resolved_at' in state_data, "Missing 'last_resolved_at' in state.json"
        assert 'repo_root' in state_data, "Missing 'repo_root' in state.json"
        assert 'packages_count' in state_data, "Missing 'packages_count' in state.json"
        assert 'scanner_version' in state_data, "Missing 'scanner_version' in state.json"

        assert state_data['packages_count'] == len(index_data['packages_detected']), \
            "Package count mismatch between state.json and index.json"

        # Step 6: Run maestro repo show --json
        show_cmd = _maestro_cmd() + ["repo", "show", "--json"]
        show_result = subprocess.run(
            show_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_SHOW_TIMEOUT,
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
        show_text_cmd = _maestro_cmd() + ["repo", "show"]
        show_text_result = subprocess.run(
            show_text_cmd,
            capture_output=True,
            text=True,
            timeout=CLI_SHOW_TIMEOUT,
            cwd=repo_path
        )

        assert show_text_result.returncode == 0, f"maestro repo show (text) failed: {show_text_result.stderr}"
        assert 'REPOSITORY INDEX' in show_text_result.stdout or 'Repository:' in show_text_result.stdout, \
            f"Unexpected output from repo show: {show_text_result.stdout}"

        # Verify the workflow is complete and coherent
        print("\n✓ Workflow test passed!")
        print(f"  - Init created docs/maestro/")
        print(f"  - Resolve auto-detected repo and wrote {len(index_data['packages_detected'])} packages")
        print(f"  - Show successfully loaded and displayed index")

    finally:
        # Cleanup - remove docs/maestro directory if we created it
        if created_repo_truth and marker_file.exists():
            # Only delete if marker file exists (indicating we created it)
            try:
                shutil.rmtree(repo_truth_dir)
            except Exception as e:
                # Best effort cleanup - don't fail the test if cleanup fails
                print(f"Warning: Failed to clean up docs/maestro directory: {e}")
