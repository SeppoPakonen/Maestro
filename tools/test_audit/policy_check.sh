#!/usr/bin/env bash
# Policy check: Print test compliance statistics

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"

echo "=== Test Policy Compliance Check ==="
echo ""

# Count total test files
total_tests=$(find "$TESTS_DIR" -name "test_*.py" -type f | wc -l)
echo "Total test files: $total_tests"

# Count legacy test files (prefix)
legacy_prefix=$(find "$TESTS_DIR" -name "legacy_test_*.py" -type f | wc -l)
echo "Legacy test files (prefix): $legacy_prefix"

# Count test files with @pytest.mark.legacy
legacy_marked=$(grep -r "@pytest.mark.legacy" "$TESTS_DIR" --include="test_*.py" | wc -l || echo 0)
echo "Legacy test markers: $legacy_marked"

# Count compliant tests (total - legacy)
compliant=$((total_tests - legacy_prefix))
echo "Compliant test files: $compliant"

echo ""
echo "Compliance rate: $(awk "BEGIN {printf \"%.1f%%\", ($compliant/$total_tests)*100}")"
echo ""

# Show pytest configuration
echo "=== Pytest Configuration ==="
if [[ -f "$PROJECT_ROOT/pytest.ini" ]]; then
    grep -A 5 "addopts" "$PROJECT_ROOT/pytest.ini" || true
fi

echo ""
echo "✅ Policy check complete"
