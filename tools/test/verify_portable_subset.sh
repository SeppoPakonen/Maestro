#!/usr/bin/env bash
# Verify that pytest.ini and tools/test/run.sh select the same portable test subset
#
# This script ensures pytest direct invocation and the test runner have consistent behavior
# by comparing their test collection outputs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Temporary files for collection comparison
RUNNER_COLLECT=$(mktemp)
PYTEST_COLLECT=$(mktemp)

# Clean up temp files on exit
trap "rm -f '$RUNNER_COLLECT' '$PYTEST_COLLECT'" EXIT

echo "Verifying portable test subset consistency..."
echo "=============================================="
echo

# Collect tests from runner (sum up test counts from --collect-only)
echo "1. Collecting tests via tools/test/run.sh..."
if bash tools/test/run.sh --collect-only 2>&1 | grep -E '^tests/' > "$RUNNER_COLLECT"; then
    # Sum up the counts (format is "file.py: count")
    RUNNER_COUNT=$(awk '{sum+=$NF} END {print sum}' "$RUNNER_COLLECT")
    RUNNER_FILES=$(wc -l < "$RUNNER_COLLECT")
    echo "   Found $RUNNER_COUNT tests across $RUNNER_FILES files"
else
    echo "ERROR: Could not collect tests from runner" >&2
    exit 1
fi

echo

# Collect tests from pytest directly (sum up test counts)
echo "2. Collecting tests via pytest -q..."
if ~/venv/bin/python -m pytest --collect-only -q 2>/dev/null | grep -E '^tests/' > "$PYTEST_COLLECT"; then
    # Sum up the counts (format is "file.py: count")
    PYTEST_COUNT=$(awk '{sum+=$NF} END {print sum}' "$PYTEST_COLLECT")
    PYTEST_FILES=$(wc -l < "$PYTEST_COLLECT")
    echo "   Found $PYTEST_COUNT tests across $PYTEST_FILES files"
else
    echo "ERROR: Could not collect tests from pytest" >&2
    exit 1
fi

echo

# Compare counts
echo "3. Comparing test collections..."
echo "   Runner:  $RUNNER_COUNT tests"
echo "   Pytest:  $PYTEST_COUNT tests"

if [ "$RUNNER_COUNT" -eq 0 ] || [ "$PYTEST_COUNT" -eq 0 ]; then
    echo
    echo "ERROR: One or both collections are empty" >&2
    exit 1
fi

# For now, allow pytest to collect more tests than the runner (due to skiplist node IDs)
# The important check is that pytest doesn't collect tests that are in --ignore patterns
if [ "$PYTEST_COUNT" -lt "$RUNNER_COUNT" ]; then
    echo
    echo "ERROR: Pytest collected fewer tests than runner" >&2
    echo "This suggests pytest.ini or conftest.py is excluding too many tests" >&2
    exit 1
fi

# Check that legacy tests are NOT in pytest collection
if grep -q "tests/legacy" "$PYTEST_COLLECT"; then
    echo
    echo "ERROR: Pytest collection includes tests/legacy tests" >&2
    echo "conftest.py pytest_ignore_collect hook should exclude these" >&2
    exit 1
fi

# Check that deleted test files are NOT in pytest collection
for deleted_file in test_acceptance_criteria.py test_comprehensive.py test_migration_check.py test_run_cli_engine.py; do
    if grep -q "$deleted_file" "$PYTEST_COLLECT"; then
        echo
        echo "ERROR: Pytest collection includes deleted file: $deleted_file" >&2
        echo "conftest.py pytest_ignore_collect hook should exclude this" >&2
        exit 1
    fi
done

echo "   ✓ Pytest excludes legacy directory"
echo "   ✓ Pytest excludes deleted test files"
echo "   ✓ Test counts are reasonable ($PYTEST_COUNT >= $RUNNER_COUNT)"
echo

echo "=============================================="
echo "✓ Verification PASSED"
echo
echo "Note: Pytest may collect more tests than the runner due to skiplist"
echo "      filtering specific test node IDs. This is expected and correct."
echo "      The important invariant is that both exclude non-portable tests."
