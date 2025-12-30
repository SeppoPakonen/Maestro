#!/usr/bin/env bash
# EX-38: Ops Doctor Detects Open Subwork and Guides Remediation
# Tags: ops, doctor, subwork, managed-mode, gates
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
echo "EX-38: Ops Doctor Detects Open Subwork and Guides Remediation"
echo "========================================================================"
echo ""

# Step 1: Start parent session (simulate)
echo -e "${YELLOW}Step 1: Start parent work session${NC}"
echo "Replace <TASK_ID> with a real task ID."
run maestro work task "<TASK_ID>" --simulate || true
run maestro wsession list
echo "Copy the most recent session_id as PARENT_ID."
echo ""

# Step 2: Start subwork
echo -e "${YELLOW}Step 2: Start subwork${NC}"
echo "Replace <PARENT_ID> and <TASK_ID>."
run maestro work subwork start "<PARENT_ID>" --purpose "Investigate build failure" --context "task:<TASK_ID>"
echo "Copy the child session_id as CHILD_ID."
echo ""

# Step 3: Ops doctor should report open subwork
echo -e "${YELLOW}Step 3: Run ops doctor${NC}"
run maestro ops doctor
echo ""

# Step 4: Close child and resume parent
echo -e "${YELLOW}Step 4: Close child subwork${NC}"
echo "Replace <CHILD_ID>."
run maestro work subwork close "<CHILD_ID>" --summary "Build fails in target X; fix Makefile include path." --status ok
echo ""

# Step 5: Ops doctor should be clean
echo -e "${YELLOW}Step 5: Re-run ops doctor${NC}"
run maestro ops doctor
echo ""

echo "========================================================================"
echo "EX-38 Complete!"
echo "========================================================================"
