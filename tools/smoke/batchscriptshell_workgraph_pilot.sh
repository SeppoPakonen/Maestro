#!/usr/bin/env bash
# BatchScriptShell WorkGraph Pilot - End-to-End Smoke Test
#
# Tests the full WorkGraph flow:
# 1. repo resolve (discover BSS repo)
# 2. runbook resolve (create runbook or WorkGraph)
# 3. plan enact (materialize WorkGraph to Track/Phase/Task)
# 4. plan run (execute WorkGraph with runner)
#
# This script validates that the WorkGraph runner works on a real-world repository
# without hardcoded paths (beyond common locations).

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "BatchScriptShell WorkGraph Pilot - Smoke Test"
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

# 4. Run maestro repo resolve
echo
echo "Step 1: Running 'maestro repo resolve lite'..."
if maestro repo resolve lite 2>&1 | grep -q "Error"; then
    echo -e "${RED}✗${NC} repo resolve failed"
    exit 1
fi
echo -e "${GREEN}✓${NC} repo resolve completed"

# 5. Run maestro runbook resolve
echo
echo "Step 2: Running 'maestro runbook resolve' (may fall back to WorkGraph)..."

# Check if docs/commands/ exists (for BSS-specific help)
if [ -d "docs/commands" ]; then
    REQUEST="Use docs/commands/*.md and ./build_maestro/bss --help to produce a user-facing runbook for BSS commands"
else
    REQUEST="Create a runbook for building and testing this application"
fi

OUTPUT=$(maestro runbook resolve -v "$REQUEST" 2>&1)

# Check if fallback to WorkGraph occurred
if echo "$OUTPUT" | grep -q "created WorkGraph instead"; then
    echo -e "${YELLOW}→${NC} Runbook resolve fell back to WorkGraph (as expected for complex repos)"

    # Extract WorkGraph ID from output
    WG_ID=$(echo "$OUTPUT" | grep -oP 'WorkGraph ID: \K[^\s]+' | head -1)

    if [ -z "$WG_ID" ]; then
        echo -e "${RED}✗${NC} Failed to extract WorkGraph ID from output"
        echo "$OUTPUT"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} WorkGraph created: $WG_ID"
else
    echo -e "${GREEN}✓${NC} Runbook created successfully"
    # If runbook was created, we don't have a WorkGraph to test, so we're done
    echo
    echo "=================================================="
    echo -e "${GREEN}SUCCESS${NC}: Runbook resolve succeeded (no WorkGraph to test)"
    echo "=================================================="
    exit 0
fi

# 6. Run maestro plan enact
echo
echo "Step 3: Running 'maestro plan enact $WG_ID'..."
if ! maestro plan enact "$WG_ID" 2>&1 | grep -q "WorkGraph materialized"; then
    echo -e "${RED}✗${NC} plan enact failed"
    exit 1
fi
echo -e "${GREEN}✓${NC} plan enact completed"

# 7. Run maestro plan run (dry-run)
echo
echo "Step 4: Running 'maestro plan run $WG_ID --dry-run -v --max-steps 5'..."
RUN_OUTPUT=$(maestro plan run "$WG_ID" --dry-run -v --max-steps 5 2>&1)

if ! echo "$RUN_OUTPUT" | grep -q "Run completed"; then
    echo -e "${RED}✗${NC} plan run failed"
    echo "$RUN_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓${NC} plan run completed (dry-run)"

# Extract run ID
RUN_ID=$(echo "$RUN_OUTPUT" | grep -oP 'Run completed: \K[^\s]+' | head -1)

if [ -z "$RUN_ID" ]; then
    echo -e "${YELLOW}Warning: Could not extract run ID${NC}"
else
    echo -e "${GREEN}✓${NC} Run ID: $RUN_ID"
fi

# 8. Verify run record was created
echo
echo "Step 5: Verifying run record structure..."

RUN_DIR="$TEMP_DOCS/plans/workgraphs/$WG_ID/runs/$RUN_ID"

if [ ! -d "$RUN_DIR" ]; then
    echo -e "${RED}✗${NC} Run directory not found: $RUN_DIR"
    exit 1
fi

if [ ! -f "$RUN_DIR/meta.json" ]; then
    echo -e "${RED}✗${NC} Run meta.json not found"
    exit 1
fi

if [ ! -f "$RUN_DIR/events.jsonl" ]; then
    echo -e "${RED}✗${NC} Run events.jsonl not found"
    exit 1
fi

echo -e "${GREEN}✓${NC} Run record structure is correct"

# 9. Verify events.jsonl content
EVENT_COUNT=$(wc -l < "$RUN_DIR/events.jsonl")
if [ "$EVENT_COUNT" -lt 3 ]; then
    echo -e "${RED}✗${NC} Too few events in events.jsonl (expected at least 3, got $EVENT_COUNT)"
    exit 1
fi

echo -e "${GREEN}✓${NC} Events recorded: $EVENT_COUNT events"

# 10. Show summary
echo
echo "=================================================="
echo -e "${GREEN}SUCCESS${NC}: BatchScriptShell WorkGraph Pilot Complete!"
echo "=================================================="
echo
echo "Summary:"
echo "  Repository: $BSS_REPO"
echo "  WorkGraph ID: $WG_ID"
echo "  Run ID: $RUN_ID"
echo "  Events recorded: $EVENT_COUNT"
echo "  Run record: $RUN_DIR"
echo
echo "The WorkGraph runner successfully:"
echo "  ✓ Discovered repository structure"
echo "  ✓ Generated WorkGraph from freeform request"
echo "  ✓ Materialized WorkGraph to Track/Phase/Task"
echo "  ✓ Executed WorkGraph with deterministic runner"
echo "  ✓ Created append-only run records"
echo
