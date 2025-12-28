#!/usr/bin/env bash
# Audit tests against allowed CLI commands from v3 runbooks
# Generates: docs/workflows/v3/reports/test_command_audit.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ALLOWED_COMMANDS="$PROJECT_ROOT/docs/workflows/v3/reports/allowed_commands.normalized.txt"
AUDIT_REPORT="$PROJECT_ROOT/docs/workflows/v3/reports/test_command_audit.md"
TESTS_DIR="$PROJECT_ROOT/tests"
TOOLS_DIR="$PROJECT_ROOT/tools"

# Check if allowed_commands.normalized.txt exists
if [[ ! -f "$ALLOWED_COMMANDS" ]]; then
    echo "ERROR: Canonical command list not found: $ALLOWED_COMMANDS"
    exit 1
fi

echo "=== Test Command Audit ==="
echo "Canonical commands: $ALLOWED_COMMANDS"
echo "Tests directory: $TESTS_DIR"
echo "Output report: $AUDIT_REPORT"
echo

# Load allowed commands into an array
mapfile -t ALLOWED < "$ALLOWED_COMMANDS"

# Extract command patterns (first 2-3 tokens after 'maestro')
declare -A ALLOWED_PATTERNS
for cmd in "${ALLOWED[@]}"; do
    # Skip empty lines
    [[ -z "$cmd" ]] && continue

    # Extract command pattern (e.g., "maestro ai qwen", "maestro build", etc.)
    # We'll use the first 3 tokens as the pattern
    pattern=$(echo "$cmd" | awk '{print $1, $2, $3}' | sed 's/ *$//')
    ALLOWED_PATTERNS["$pattern"]=1

    # Also add 2-token patterns for shorter commands
    pattern2=$(echo "$cmd" | awk '{print $1, $2}' | sed 's/ *$//')
    ALLOWED_PATTERNS["$pattern2"]=1
done

echo "Loaded ${#ALLOWED[@]} allowed commands"
echo "Generated ${#ALLOWED_PATTERNS[@]} command patterns"
echo

# Function to check if a command pattern is allowed
is_allowed() {
    local pattern="$1"
    [[ -n "${ALLOWED_PATTERNS[$pattern]:-}" ]]
}

# Temporary files for categorization
COMPLIANT=$(mktemp)
SUSPICIOUS=$(mktemp)
NONCOMPLIANT=$(mktemp)

trap "rm -f $COMPLIANT $SUSPICIOUS $NONCOMPLIANT" EXIT

# Scan test files
echo "Scanning test files..."

find "$TESTS_DIR" -name "*.py" -type f 2>/dev/null | while read -r test_file; do
    relative_path="${test_file#$PROJECT_ROOT/}"

    # Extract command invocations (maestro ..., ./maestro.py ..., python -m maestro ...)
    # Look for common patterns in test files
    grep -n -E "(maestro |./maestro\.py |python -m maestro |'maestro |\"maestro )" "$test_file" 2>/dev/null | while IFS=: read -r lineno line; do
        # Try to extract the command
        cmd_match=$(echo "$line" | grep -oE "(maestro|./maestro\.py|python -m maestro) [a-z_-]+ [a-z_-]+" || true)

        if [[ -n "$cmd_match" ]]; then
            # Normalize to "maestro ..." format
            normalized=$(echo "$cmd_match" | sed 's/\.\/maestro\.py/maestro/; s/python -m maestro/maestro/')

            # Check 3-token and 2-token patterns
            pattern3=$(echo "$normalized" | awk '{print $1, $2, $3}' | sed 's/ *$//')
            pattern2=$(echo "$normalized" | awk '{print $1, $2}' | sed 's/ *$//')

            if is_allowed "$pattern3" || is_allowed "$pattern2"; then
                echo "$relative_path:$lineno: $normalized" >> "$COMPLIANT"
            else
                # Check if it looks like a real command or just a substring
                if [[ "$line" =~ (def|class|import|#|str|print) ]]; then
                    echo "$relative_path:$lineno: $normalized (in code/comment)" >> "$SUSPICIOUS"
                else
                    echo "$relative_path:$lineno: $normalized" >> "$NONCOMPLIANT"
                fi
            fi
        fi
    done
done || true

# Scan smoke test scripts
echo "Scanning smoke test scripts..."

find "$TOOLS_DIR" -name "*smoke*.sh" -type f 2>/dev/null | while read -r script_file; do
    relative_path="${script_file#$PROJECT_ROOT/}"

    grep -n -E "(maestro |./maestro\.py |python -m maestro )" "$script_file" 2>/dev/null | while IFS=: read -r lineno line; do
        cmd_match=$(echo "$line" | grep -oE "(maestro|./maestro\.py|python -m maestro) [a-z_-]+ [a-z_-]+" || true)

        if [[ -n "$cmd_match" ]]; then
            normalized=$(echo "$cmd_match" | sed 's/\.\/maestro\.py/maestro/; s/python -m maestro/maestro/')

            pattern3=$(echo "$normalized" | awk '{print $1, $2, $3}' | sed 's/ *$//')
            pattern2=$(echo "$normalized" | awk '{print $1, $2}' | sed 's/ *$//')

            if is_allowed "$pattern3" || is_allowed "$pattern2"; then
                echo "$relative_path:$lineno: $normalized" >> "$COMPLIANT"
            else
                echo "$relative_path:$lineno: $normalized" >> "$NONCOMPLIANT"
            fi
        fi
    done
done || true

# Generate report
echo "Generating report..."

# Count results
compliant_count=$(wc -l < "$COMPLIANT" 2>/dev/null || echo 0)
suspicious_count=$(wc -l < "$SUSPICIOUS" 2>/dev/null || echo 0)
noncompliant_count=$(wc -l < "$NONCOMPLIANT" 2>/dev/null || echo 0)

# Write report header
{
    echo "# Test Command Audit Report"
    echo ""
    echo "**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo ""
    echo "**Policy:** [Test Command Truth Policy](test_command_truth_policy.md)"
    echo ""
    echo "**Canonical Commands:** \`allowed_commands.normalized.txt\`"
    echo ""
    echo "---"
    echo ""
    echo "## Summary"
    echo ""
    echo "- ✅ Compliant: $compliant_count command references"
    echo "- ⚠️  Suspicious: $suspicious_count potential matches (may be false positives)"
    echo "- ❌ Non-compliant: $noncompliant_count command references"
    echo ""
    echo "---"
    echo ""
    echo "## ✅ Compliant Tests"
    echo ""
    echo "These tests reference commands present in \`allowed_commands.normalized.txt\`."
    echo ""
} > "$AUDIT_REPORT"

if [[ -s "$COMPLIANT" ]]; then
    echo '```' >> "$AUDIT_REPORT"
    sort -u "$COMPLIANT" >> "$AUDIT_REPORT"
    echo '```' >> "$AUDIT_REPORT"
else
    echo "_No compliant command references found (possible audit tool issue)._" >> "$AUDIT_REPORT"
fi

{
    echo ""
    echo "---"
    echo ""
    echo "## ⚠️ Suspicious References"
    echo ""
    echo "These may be false positives (code examples, comments, etc.)."
    echo ""
} >> "$AUDIT_REPORT"

if [[ -s "$SUSPICIOUS" ]]; then
    echo '```' >> "$AUDIT_REPORT"
    sort -u "$SUSPICIOUS" >> "$AUDIT_REPORT"
    echo '```' >> "$AUDIT_REPORT"
else
    echo "_None detected._" >> "$AUDIT_REPORT"
fi

{
    echo ""
    echo "---"
    echo ""
    echo "## ❌ Non-Compliant Tests"
    echo ""
    echo "**These tests reference commands NOT in the allowed list.**"
    echo ""
    echo "**Action Required:**"
    echo "1. Mark with \`@pytest.mark.legacy\` OR"
    echo "2. Rename file with \`legacy_\` prefix OR"
    echo "3. Delete if obsolete and document below"
    echo ""
} >> "$AUDIT_REPORT"

if [[ -s "$NONCOMPLIANT" ]]; then
    echo '```' >> "$AUDIT_REPORT"
    sort -u "$NONCOMPLIANT" >> "$AUDIT_REPORT"
    echo '```' >> "$AUDIT_REPORT"
else
    echo "_None detected._" >> "$AUDIT_REPORT"
fi

{
    echo ""
    echo "---"
    echo ""
    echo "## 🗑️ Removed Tests"
    echo ""
    echo "**Tests deleted during this audit:**"
    echo ""
    echo "_No tests removed yet._"
    echo ""
    echo "---"
    echo ""
    echo "## Next Steps"
    echo ""
    echo "1. Review non-compliant tests"
    echo "2. Quarantine (mark as \`legacy\`) or remove"
    echo "3. Re-run \`pytest -q\` to verify compliance"
    echo "4. Update this report after changes"
    echo ""
} >> "$AUDIT_REPORT"

echo
echo "✅ Audit complete!"
echo "Report: $AUDIT_REPORT"
echo
echo "Summary:"
echo "  ✅ Compliant: $compliant_count"
echo "  ⚠️  Suspicious: $suspicious_count"
echo "  ❌ Non-compliant: $noncompliant_count"
