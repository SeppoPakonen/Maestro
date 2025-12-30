"""
Pytest configuration and hooks for Maestro test suite.

This conftest.py handles:
1. Automatic marking of legacy tests (deprecated code paths)
2. Automatic skipping of tests that require optional dependencies (pexpect)
3. Preventing collection of files that would cause import errors
"""

import os
from pathlib import Path

import pytest


# Check for optional dependencies at module level
try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False


# List of test file names that are legacy (test deprecated/removed code)
LEGACY_TEST_FILES = {
    "test_batch_functionality.py",
    "test_build_default.py",
    "test_build_functionality.py",
    "test_build_plan_functionality.py",
    "test_checkpoint_rehearsal.py",
    "test_complete_workflow.py",
    "test_conversion_memory_stability.py",
    "test_conversion_orchestrator.py",
    "test_cross_repo_semantic_diff.py",
    "test_decision_override.py",
    "test_decision_override_integration.py",
    "test_force_replan.py",
    "test_include_guard_conventions.py",
    "test_interrupt_handling.py",
    "test_legacy_safety.py",
    "test_mc2_build_pane.py",
    "test_mc2_convert_pane.py",
    "test_mc2_plans_pane.py",
    "test_mc2_tasks_pane.py",
    "test_migration_enforcement.py",
    "test_new_features.py",
    "test_plan_functionality.py",
    "test_plan_uses_json.py",
    "test_plan_validation.py",
    "test_playbook_functionality.py",
    "test_quality_gates.py",
    "test_reactive_rules.py",
    "test_realize_worker_mock.py",
    "test_refactor_functionality.py",
    "test_regression_replay.py",
    "test_rulebook_matching.py",
    "test_safety_check.py",
    "test_screen_integration.py",
    "test_screen_navigation_smoke.py",
    "test_semantic_diff.py",
    "test_semantic_integrity.py",
    "test_semantic_integrity_legacy.py",
    "test_stage3.py",
    "test_structure_rulebooks.py",
    "test_structure_ux.py",
    "test_tui_smoke.py",
    "test_upp_discovery.py",
}

# Test file patterns that require pexpect
PEXPECT_TEST_PATTERNS = {
    "maestro/wrap/codex/test_",  # All codex tests
    "tests/test_tui_smoke_direct.py",
}

# Test files that require git operations
GIT_TEST_FILES = {
    "test_ops_doctor.py",
    "test_ops_doctor_subwork.py",
    "test_reactive_fix_loop.py",
    "test_safe_apply_revert.py",
}


def pytest_ignore_collect(collection_path, config):
    """
    Hook to ignore collection of certain files.

    This prevents import errors from files that require missing optional dependencies
    or from legacy tests that import deprecated code.
    Returns True to ignore/skip collection of the file.
    """
    # Convert path to string for pattern matching
    path_str = str(collection_path)

    # Get just the filename
    filename = collection_path.name

    # Skip entire tests/legacy directory
    if "tests/legacy" in path_str:
        return True

    # Skip deleted/removed test files that may still exist
    if filename in {
        "test_acceptance_criteria.py",
        "test_comprehensive.py",
        "test_migration_check.py",
        "test_run_cli_engine.py",
    }:
        return True

    # Skip pexpect tests if pexpect not available
    if not HAS_PEXPECT:
        # Skip all codex tests
        if "maestro/wrap/codex/test_" in path_str:
            return True
        # Skip specific pexpect tests
        if "tests/test_tui_smoke_direct.py" in path_str:
            return True

    # Skip legacy tests by default (unless explicitly running with -m "")
    # Check if we're running with legacy marker enabled
    marker_expr = config.option.markexpr if hasattr(config.option, 'markexpr') else ""

    # If markexpr is empty string (user passed -m ""), allow legacy collection
    # Otherwise, skip legacy tests to prevent import errors
    if marker_expr != "":
        if filename in LEGACY_TEST_FILES:
            return True

    return False


def pytest_collection_modifyitems(config, items):
    """
    Hook to modify test collection.

    Automatically marks:
    - Legacy tests with 'legacy' marker (skipped by default via pytest.ini)
    - Pexpect tests with 'pexpect' marker (for documentation)
    - Git tests with 'git' marker (opt-in via MAESTRO_TEST_ALLOW_GIT=1)
    """
    allow_git = os.environ.get("MAESTRO_TEST_ALLOW_GIT") == "1"
    for item in items:
        # Get the test file path
        test_file = item.nodeid
        test_filename = test_file.split("::")[-1] if "::" in test_file else test_file
        test_filename = test_filename.split("/")[-1]
        item_path = getattr(item, "path", None) or getattr(item, "fspath", None)
        if item_path:
            item_filename = Path(str(item_path)).name
        else:
            item_filename = test_filename

        # Mark legacy tests
        if item_filename in LEGACY_TEST_FILES:
            item.add_marker(pytest.mark.legacy)

        # Mark pexpect tests (for documentation, actual skipping done via pytest_ignore_collect)
        for pattern in PEXPECT_TEST_PATTERNS:
            if pattern in test_file:
                item.add_marker(pytest.mark.pexpect)
                break

        if item_filename.startswith("test_tui_"):
            item.add_marker(pytest.mark.tui)

        if item_filename in GIT_TEST_FILES:
            item.add_marker(pytest.mark.git)
            if not allow_git:
                item.add_marker(pytest.mark.skip(reason="requires MAESTRO_TEST_ALLOW_GIT=1"))
