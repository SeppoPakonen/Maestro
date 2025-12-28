#!/usr/bin/env bash
# EX-32: Log Scan → Issue → Task → Work (Observability Pipeline)
#
# This script demonstrates the full observability pipeline:
# 1. Scan build log for errors
# 2. Ingest findings into issues
# 3. Work gets blocked by blocker issues
# 4. Link issues to tasks to clear gates
# 5. Resolve or override gates

set -euo pipefail

echo "==================================================================="
echo "EX-32: Log Scan → Issue → Task → Work (Observability Pipeline)"
echo "==================================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Scan build log
echo -e "${BLUE}Step 1: Scanning build log for errors${NC}"
echo "$ maestro log scan --source tests/fixtures/logs/build_error.log --kind build"
SCAN_ID=$(maestro log scan --source tests/fixtures/logs/build_error.log --kind build | grep "Scan created:" | awk '{print $3}')
echo -e "${GREEN}✓ Scan created: ${SCAN_ID}${NC}"
echo ""

# Step 2: List scans
echo -e "${BLUE}Step 2: Listing all scans${NC}"
echo "$ maestro log list"
maestro log list
echo ""

# Step 3: Show scan details
echo -e "${BLUE}Step 3: Showing scan details${NC}"
echo "$ maestro log show ${SCAN_ID}"
maestro log show "${SCAN_ID}"
echo ""

# Step 4: Ingest findings into issues
echo -e "${BLUE}Step 4: Ingesting findings into issues${NC}"
echo "$ maestro issues add --from-log ${SCAN_ID}"
maestro issues add --from-log "${SCAN_ID}"
echo -e "${GREEN}✓ Issues created from findings${NC}"
echo ""

# Step 5: List blocker issues
echo -e "${BLUE}Step 5: Listing blocker issues${NC}"
echo "$ maestro issues list --severity blocker --status open"
maestro issues list --severity blocker --status open
echo ""

# Step 6: Attempt to start work (should be blocked)
echo -e "${BLUE}Step 6: Attempting to start work (expect gate to block)${NC}"
echo "$ maestro work task TASK-123"
if maestro work task TASK-123 2>&1; then
    echo -e "${YELLOW}⚠ Warning: Work started despite blockers (gate may not be working)${NC}"
else
    echo -e "${GREEN}✓ Work blocked by BLOCKED_BY_ISSUES gate (as expected)${NC}"
fi
echo ""

# Step 7: Auto-triage issues
echo -e "${BLUE}Step 7: Auto-triaging issues${NC}"
echo "$ maestro issues triage --auto"
maestro issues triage --auto || true
echo ""

# Step 8: Link issue to task
echo -e "${BLUE}Step 8: Linking issue to task${NC}"
FIRST_ISSUE=$(maestro issues list --severity blocker --status open | head -1 | awk '{print $1}')
if [ -n "${FIRST_ISSUE}" ]; then
    echo "$ maestro issues link-task ${FIRST_ISSUE} TASK-123"
    maestro issues link-task "${FIRST_ISSUE}" TASK-123 || true
    echo -e "${GREEN}✓ Issue ${FIRST_ISSUE} linked to TASK-123${NC}"
else
    echo -e "${YELLOW}⚠ No blocker issues found to link${NC}"
fi
echo ""

# Step 9: Try work again (gate may be cleared if task is in_progress)
echo -e "${BLUE}Step 9: Attempting work again (may still be blocked if task not in_progress)${NC}"
echo "$ maestro work task TASK-123"
if maestro work task TASK-123 2>&1; then
    echo -e "${GREEN}✓ Work started (gate cleared)${NC}"
else
    echo -e "${YELLOW}⚠ Still blocked (task may not be in_progress status)${NC}"
fi
echo ""

# Step 10: Resolve issue
echo -e "${BLUE}Step 10: Resolving first issue${NC}"
if [ -n "${FIRST_ISSUE}" ]; then
    echo "$ maestro issues resolve ${FIRST_ISSUE} --reason 'Fixed in test commit'"
    maestro issues resolve "${FIRST_ISSUE}" --reason "Fixed in test commit" || true
    echo -e "${GREEN}✓ Issue ${FIRST_ISSUE} resolved${NC}"
fi
echo ""

# Step 11: Override gate
echo -e "${BLUE}Step 11: Overriding gate with --ignore-gates${NC}"
echo "$ maestro work task TASK-123 --ignore-gates"
maestro work task TASK-123 --ignore-gates || echo -e "${YELLOW}⚠ Command failed (may not be fully implemented)${NC}"
echo ""

# Verification: Check determinism
echo -e "${BLUE}Bonus: Verifying fingerprint determinism${NC}"
echo "Scanning same log twice to verify same fingerprints..."
SCAN_ID_2=$(maestro log scan --source tests/fixtures/logs/build_error.log --kind build | grep "Scan created:" | awk '{print $3}')
echo "First scan: ${SCAN_ID}"
echo "Second scan: ${SCAN_ID_2}"
echo ""
echo "Comparing fingerprints..."
maestro log show "${SCAN_ID}" | grep fingerprint | sort > /tmp/scan1_fingerprints.txt
maestro log show "${SCAN_ID_2}" | grep fingerprint | sort > /tmp/scan2_fingerprints.txt
if diff /tmp/scan1_fingerprints.txt /tmp/scan2_fingerprints.txt; then
    echo -e "${GREEN}✓ Fingerprints are identical (deterministic!)${NC}"
else
    echo -e "${RED}✗ Fingerprints differ (non-deterministic)${NC}"
fi
echo ""

echo "==================================================================="
echo -e "${GREEN}EX-32 Complete!${NC}"
echo "==================================================================="
echo ""
echo "Summary:"
echo "  - Build log scanned and findings extracted"
echo "  - Issues created with stable fingerprints"
echo "  - Work blocked by BLOCKED_BY_ISSUES gate"
echo "  - Issue linked to task to clear gate"
echo "  - Issue resolved when fixed"
echo "  - Gate override available for edge cases"
echo ""
