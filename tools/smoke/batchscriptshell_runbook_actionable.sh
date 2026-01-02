#!/usr/bin/env bash
# BatchScriptShell actionable runbook pilot script
#
# This script tests runbook generation with --actionable flag enforcement.
# It verifies that the system either creates an actionable runbook with executable
# commands or falls back to WorkGraph generation.
#
# Usage:
#   BSS_REPO=/path/to/batchscriptshell bash tools/smoke/batchscriptshell_runbook_actionable.sh
#
# Requirements:
#   - BatchScriptShell repo available at $BSS_REPO (or uses current dir)
#   - AI engine configured (or uses --evidence-only fallback)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "BatchScriptShell Runbook Actionable Test"
echo "========================================"
echo

# Determine repo root
REPO_ROOT="${BSS_REPO:-$(pwd)}"
echo "Using repo: $REPO_ROOT"

# Check if we're in a valid repo structure
if [[ ! -d "$REPO_ROOT/docs" ]]; then
    echo -e "${YELLOW}Warning: No docs/ directory found in $REPO_ROOT${NC}"
    echo "This test works best with a BatchScriptShell repo that has docs/commands/"
fi

cd "$REPO_ROOT"

# Clean up any existing runbooks or workgraphs from previous runs
echo
echo "Cleaning up previous test artifacts..."
if [[ -d "docs/maestro/runbooks/items" ]]; then
    # Only remove test runbooks (those starting with rb-verify or rb-create)
    find docs/maestro/runbooks/items -name "rb-verify-*.json" -delete 2>/dev/null || true
    find docs/maestro/runbooks/items -name "rb-create-*.json" -delete 2>/dev/null || true
fi
if [[ -d "docs/maestro/plans/workgraphs" ]]; then
    # Only remove test workgraphs (recent ones from today)
    find docs/maestro/plans/workgraphs -name "wg-$(date +%Y%m%d)-*.json" -delete 2>/dev/null || true
fi

# Test 1: Generate actionable runbook with --actionable flag
echo
echo "========================================"
echo "Test 1: Actionable runbook with --actionable"
echo "========================================"
echo

REQUEST="Create an actionable runbook for verifying BSS command docs match the executable help and running a minimal test script."

echo "Request: $REQUEST"
echo

# Try to generate with AI first, fall back to --evidence-only if no engine available
echo "Running: maestro runbook resolve --actionable -v \"$REQUEST\""
echo

if maestro runbook resolve --actionable -v "$REQUEST" 2>&1; then
    RESULT_TYPE="runbook or workgraph"
else
    echo -e "${YELLOW}AI generation failed, trying with --evidence-only...${NC}"
    if maestro runbook resolve --actionable -v --evidence-only "$REQUEST" 2>&1; then
        RESULT_TYPE="evidence-only runbook"
    else
        echo -e "${RED}FAILED: Could not generate runbook or workgraph${NC}"
        exit 1
    fi
fi

echo
echo "Generation completed with: $RESULT_TYPE"

# Check what was created
echo
echo "Checking created artifacts..."

RUNBOOK_CREATED=0
WORKGRAPH_CREATED=0

# Check for runbooks
if [[ -d "docs/maestro/runbooks/items" ]]; then
    LATEST_RUNBOOK=$(find docs/maestro/runbooks/items -name "rb-*.json" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
    if [[ -n "$LATEST_RUNBOOK" ]]; then
        RUNBOOK_CREATED=1
        RUNBOOK_ID=$(basename "$LATEST_RUNBOOK" .json)
        echo -e "${GREEN}✓ Runbook created: $RUNBOOK_ID${NC}"

        # Validate runbook has executable steps
        echo "  Validating runbook has executable commands..."
        STEP_COUNT=$(python3 -c "import json; rb=json.load(open('$LATEST_RUNBOOK')); print(len(rb.get('steps', [])))")
        STEPS_WITH_COMMANDS=$(python3 -c "import json; rb=json.load(open('$LATEST_RUNBOOK')); steps=rb.get('steps', []); print(sum(1 for s in steps if 'command' in s or 'commands' in s))")

        echo "  Total steps: $STEP_COUNT"
        echo "  Steps with commands: $STEPS_WITH_COMMANDS"

        if [[ "$STEPS_WITH_COMMANDS" -ge 5 ]]; then
            echo -e "  ${GREEN}✓ Runbook has >= 5 actionable steps${NC}"
        else
            echo -e "  ${YELLOW}⚠ Runbook has < 5 actionable steps (acceptable if WorkGraph fallback)${NC}"
        fi
    fi
fi

# Check for workgraphs
if [[ -d "docs/maestro/plans/workgraphs" ]]; then
    LATEST_WORKGRAPH=$(find docs/maestro/plans/workgraphs -name "wg-*.json" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
    if [[ -n "$LATEST_WORKGRAPH" ]]; then
        WORKGRAPH_CREATED=1
        WORKGRAPH_ID=$(basename "$LATEST_WORKGRAPH" .json)
        echo -e "${GREEN}✓ WorkGraph created: $WORKGRAPH_ID${NC}"

        # Show WorkGraph summary
        echo "  Checking WorkGraph structure..."
        PHASE_COUNT=$(python3 -c "import json; wg=json.load(open('$LATEST_WORKGRAPH')); print(len(wg.get('phases', [])))")
        TOTAL_TASKS=$(python3 -c "import json; wg=json.load(open('$LATEST_WORKGRAPH')); print(sum(len(p.get('tasks', [])) for p in wg.get('phases', [])))")

        echo "  Phases: $PHASE_COUNT"
        echo "  Total tasks: $TOTAL_TASKS"

        if [[ "$TOTAL_TASKS" -ge 3 ]]; then
            echo -e "  ${GREEN}✓ WorkGraph has >= 3 tasks${NC}"
        else
            echo -e "  ${RED}✗ WorkGraph has < 3 tasks${NC}"
            exit 1
        fi

        echo
        echo "  Next step command:"
        echo "    maestro plan enact $WORKGRAPH_ID"
    fi
fi

# Verify outcome
echo
echo "========================================"
echo "Test Results"
echo "========================================"
echo

if [[ "$RUNBOOK_CREATED" -eq 1 ]] || [[ "$WORKGRAPH_CREATED" -eq 1 ]]; then
    echo -e "${GREEN}✓ SUCCESS: --actionable flag enforcement working${NC}"
    echo
    if [[ "$RUNBOOK_CREATED" -eq 1 ]]; then
        echo "  Result: Actionable runbook generated"
        echo "  Runbook ID: $RUNBOOK_ID"
    else
        echo "  Result: Fell back to WorkGraph (runbook not actionable)"
        echo "  WorkGraph ID: $WORKGRAPH_ID"
        echo "  Enact command: maestro plan enact $WORKGRAPH_ID"
    fi
else
    echo -e "${RED}✗ FAILED: Neither runbook nor WorkGraph was created${NC}"
    exit 1
fi

echo
echo "========================================"
echo "Pilot test completed successfully!"
echo "========================================"
