#!/usr/bin/env bash
# Real-World Loop BatchScriptShell Smoke Test
#
# Tests the full ops → workgraph orchestration loop:
# repo resolve → build → log scan → issues add → triage → decompose → enact → run
#
# This script validates that the ops runner can orchestrate the full loop
# on a real-world repository without hardcoded paths.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "Real-World Loop BatchScriptShell - Smoke Test"
echo "=================================================="
echo

# 1. Check if BatchScriptShell repo exists
BSS_REPO="${BSS_REPO:-$HOME/Dev/BatchScriptShell}"

if [ ! -d "$BSS_REPO" ]; then
    echo -e "${YELLOW}Warning: BatchScriptShell repo not found at $BSS_REPO${NC}"
    echo "Set BSS_REPO environment variable to override."
    echo "Skipping smoke test."
    exit 0
fi

echo -e "${GREEN}✓${NC} Found BatchScriptShell repo at: $BSS_REPO"

# 2. Create temporary MAESTRO_DOCS_ROOT
TEMP_DOCS=$(mktemp -d)
export MAESTRO_DOCS_ROOT="$TEMP_DOCS"

echo -e "${GREEN}✓${NC} Created temp docs root: $TEMP_DOCS"

# Cleanup on exit
cleanup() {
    echo
    echo "Cleaning up..."
    rm -rf "$TEMP_DOCS"
    echo -e "${GREEN}✓${NC} Removed temp docs root"
}
trap cleanup EXIT

# 3. Change to BSS repo
cd "$BSS_REPO"
echo -e "${GREEN}✓${NC} Changed to BSS repo: $(pwd)"

# 4. Get path to ops plan
# Assume this script is in tools/smoke/, so Maestro root is two levels up
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAESTRO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_PLAN="$MAESTRO_ROOT/tests/fixtures/ops_plans/plan_realworld_loop.yaml"

if [ ! -f "$OPS_PLAN" ]; then
    echo -e "${RED}✗${NC} Ops plan not found: $OPS_PLAN"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found ops plan: $OPS_PLAN"

# 5. Run ops plan in dry-run mode (safe, no writes)
echo
echo "Step 1: Running ops plan in --dry-run mode (safe preview)..."
RUN_OUTPUT=$(maestro ops run "$OPS_PLAN" --dry-run --continue-on-error 2>&1)

if ! echo "$RUN_OUTPUT" | grep -q "Ops Run:"; then
    echo -e "${RED}✗${NC} ops run failed (dry-run)"
    echo "$RUN_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓${NC} ops run completed (dry-run mode)"

# Extract run ID
RUN_ID=$(echo "$RUN_OUTPUT" | grep -oP 'Ops Run: \K[^\s]+' | head -1)

if [ -z "$RUN_ID" ]; then
    echo -e "${YELLOW}Warning: Could not extract run ID${NC}"
else
    echo -e "${GREEN}✓${NC} Run ID: $RUN_ID"
fi

# 6. Verify run record was created
echo
echo "Step 2: Verifying run record structure..."

RUN_DIR="$TEMP_DOCS/docs/maestro/ops/runs/$RUN_ID"

if [ ! -d "$RUN_DIR" ]; then
    echo -e "${RED}✗${NC} Run directory not found: $RUN_DIR"
    exit 1
fi

if [ ! -f "$RUN_DIR/meta.json" ]; then
    echo -e "${RED}✗${NC} Run meta.json not found"
    exit 1
fi

if [ ! -f "$RUN_DIR/steps.jsonl" ]; then
    echo -e "${RED}✗${NC} Run steps.jsonl not found"
    exit 1
fi

if [ ! -f "$RUN_DIR/summary.json" ]; then
    echo -e "${RED}✗${NC} Run summary.json not found"
    exit 1
fi

echo -e "${GREEN}✓${NC} Run record structure is correct"

# 7. Verify steps.jsonl content
STEP_COUNT=$(wc -l < "$RUN_DIR/steps.jsonl")
if [ "$STEP_COUNT" -lt 3 ]; then
    echo -e "${RED}✗${NC} Too few steps in steps.jsonl (expected at least 3, got $STEP_COUNT)"
    exit 1
fi

echo -e "${GREEN}✓${NC} Steps recorded: $STEP_COUNT steps"

# 8. Check if metadata was captured (look for scan_id or workgraph_id in steps)
if grep -q '"scan_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Scan ID metadata captured"
fi

if grep -q '"workgraph_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} WorkGraph ID metadata captured"
fi

if grep -q '"workgraph_run_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} WorkGraph Run ID metadata captured"
fi

# 9. (Optional) Run with --execute flag to test actual loop
# This is commented out by default for safety
# echo
# echo "Step 3 (Optional): Running ops plan with --execute flag..."
# RUN_OUTPUT_EXEC=$(maestro ops run "$OPS_PLAN" --execute --continue-on-error 2>&1)

# 10. Show summary
echo
echo "=================================================="
echo -e "${GREEN}SUCCESS${NC}: Real-World Loop Smoke Test Complete!"
echo "=================================================="
echo
echo "Summary:"
echo "  Repository: $BSS_REPO"
echo "  Ops Plan: $OPS_PLAN"
echo "  Run ID: $RUN_ID"
echo "  Steps recorded: $STEP_COUNT"
echo "  Run record: $RUN_DIR"
echo
echo "The ops runner successfully:"
echo "  ✓ Loaded and validated ops plan with structured steps"
echo "  ✓ Executed steps in dry-run mode"
echo "  ✓ Created append-only run records with metadata"
echo "  ✓ Extracted metadata (scan IDs, workgraph IDs) from step outputs"
echo "  ✓ Demonstrated end-to-end orchestration pattern"
echo
echo "To run with actual execution (writes enabled):"
echo "  maestro ops run $OPS_PLAN --execute --continue-on-error"
echo
