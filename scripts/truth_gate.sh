#!/bin/bash
# Truth Gate - CI Gate for Maestro
# Validates that docs are truth + rule-assertive contracts

set -e  # Exit immediately if a command exits with a non-zero status

# Check if verbose mode is enabled
if [ "${TRUTH_GATE_VERBOSE}" = "1" ]; then
    set -x  # Print commands and their arguments as they are executed
    VERBOSE="--verbose"
else
    VERBOSE=""
fi

echo "Running Maestro Truth Gate..."
echo "================================"

# 1) Initialize the repository if needed (for clean checkout support)
echo "Step 1: Bootstrap repository if needed..."
if [ ! -d "docs" ]; then
    echo "Initializing Maestro project..."
    python -m maestro init
fi

# Create a basic UNDERSTANDING_SNAPSHOT.md if it doesn't exist
if [ ! -f "docs/UNDERSTANDING_SNAPSHOT.md" ]; then
    echo "# Maestro Understanding Snapshot" > docs/UNDERSTANDING_SNAPSHOT.md
    echo "" >> docs/UNDERSTANDING_SNAPSHOT.md
    echo "This is a placeholder for the understanding snapshot." >> docs/UNDERSTANDING_SNAPSHOT.md
fi

# 2) Check snapshot drift
echo "Step 2: Checking snapshot drift..."
if python -m maestro understand dump --check; then
    echo "✓ Snapshot is up to date"
else
    echo "✗ Snapshot is stale - run 'maestro understand dump'"
    exit 1
fi

# 3) Validate plan ops fixtures (valid)
echo "Step 3: Validating plan ops valid fixture..."
if python -m maestro plan ops validate tests/fixtures/plan_ops_valid_1.json ${VERBOSE}; then
    echo "✓ Valid plan ops fixture validates correctly"
else
    echo "✗ Valid plan ops fixture failed validation"
    exit 1
fi

# 4) Validate plan ops fixtures (invalid) - should fail
echo "Step 4: Validating plan ops invalid fixture (should fail)..."
if python -m maestro plan ops validate tests/fixtures/plan_ops_invalid_1.json ${VERBOSE} 2>/dev/null; then
    echo "✗ Invalid plan ops fixture should have failed validation but didn't"
    exit 1
else
    echo "✓ Invalid plan ops fixture correctly fails validation"
fi

# 5) Validate project ops fixtures (valid)
echo "Step 5: Validating project ops valid fixture..."
if python -m maestro ops validate tests/fixtures/project_ops_valid_1.json ${VERBOSE}; then
    echo "✓ Valid project ops fixture validates correctly"
else
    echo "✗ Valid project ops fixture failed validation"
    exit 1
fi

# 6) Validate project ops fixtures (invalid) - should fail
echo "Step 6: Validating project ops invalid fixture (should fail)..."
if python -m maestro ops validate tests/fixtures/project_ops_invalid_1.json ${VERBOSE} 2>/dev/null; then
    echo "✗ Invalid project ops fixture should have failed validation but didn't"
    exit 1
else
    echo "✓ Invalid project ops fixture correctly fails validation"
fi

# 7) Optional smoke checks (no AI)
echo "Step 7: Running smoke checks..."
if python -m maestro plan list ${VERBOSE} >/dev/null 2>&1; then
    echo "✓ Plan list command works"
else
    echo "✗ Plan list command failed"
    exit 1
fi

if python -m maestro plan ops preview tests/fixtures/plan_ops_valid_1.json ${VERBOSE} >/dev/null 2>&1; then
    echo "✓ Plan ops preview works"
else
    echo "✗ Plan ops preview failed"
    exit 1
fi

if python -m maestro ops preview tests/fixtures/project_ops_valid_1.json ${VERBOSE} >/dev/null 2>&1; then
    echo "✓ Project ops preview works"
else
    echo "✗ Project ops preview failed"
    exit 1
fi

echo ""
echo "================================"
echo "✓ All Truth Gate checks passed!"
echo "Maestro's 'docs are truth + rule-assertive contracts' model is enforced."
exit 0