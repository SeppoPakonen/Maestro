#!/usr/bin/env bash
# EX-37: Managed Mode Subwork Stacking (Patch then Resume)
# Tags: work, subwork, wsession, managed-mode, handoff
# Status: proposed
# Sprint: P2 Sprint 4.8

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

run() {
    echo -e "${GREEN}→${NC} $*"
    "$@"
}

echo "========================================================================"
echo "EX-37: Managed Mode Subwork Stacking (Patch then Resume)"
echo "========================================================================"
echo ""

# Step 1: Start parent work session (simulate, no AI)
echo -e "${YELLOW}Step 1: Start parent work session (simulate)${NC}"
echo "Replace <TASK_ID> with a real task ID."
run maestro work task "<TASK_ID>" --simulate || true
# EXPECT: Session created, prompt printed
# STORES: docs/sessions/<PARENT_ID>/session.json
echo ""

# Step 2: Capture parent session ID
echo -e "${YELLOW}Step 2: Capture parent session ID${NC}"
run maestro wsession list
echo "Copy the most recent session_id as PARENT_ID."
echo ""

# Step 3: Start subwork (pause parent)
echo -e "${YELLOW}Step 3: Start subwork${NC}"
echo "Replace <PARENT_ID> and <TASK_ID>."
run maestro work subwork start "<PARENT_ID>" --purpose "Diagnose failing tests" --context "task:<TASK_ID>"
# EXPECT: Child session created, parent paused
# STORES: docs/sessions/<PARENT_ID>/<CHILD_ID>/session.json
echo ""

# Step 4: List subwork sessions
echo -e "${YELLOW}Step 4: List subwork sessions${NC}"
run maestro work subwork list "<PARENT_ID>"
echo ""

# Step 5: Close child with summary + status
echo -e "${YELLOW}Step 5: Close child session${NC}"
echo "Replace <CHILD_ID>."
run maestro work subwork close "<CHILD_ID>" --summary "Tests fail in module X; missing fixture in test data." --status ok
# EXPECT: Child closed, parent resumed, parent breadcrumb written
echo ""

# Step 6: Validate parent resume and breadcrumb
echo -e "${YELLOW}Step 6: Validate parent state and breadcrumb${NC}"
run maestro wsession show "<PARENT_ID>"
run maestro wsession tree
run maestro wsession breadcrumbs "<PARENT_ID>" --summary
echo ""

echo "========================================================================"
echo "EX-37 Complete!"
echo "========================================================================"
