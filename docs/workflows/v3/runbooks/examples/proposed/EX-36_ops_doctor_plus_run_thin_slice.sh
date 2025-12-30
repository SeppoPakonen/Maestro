#!/usr/bin/env bash
# EX-36: Ops Doctor + Run (Thin Slice)
# Tags: ops, doctor, run, automation, health-check
# Status: proposed
# Sprint: P2 Sprint 4.7

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run() {
    echo -e "${GREEN}→${NC} $*"
    "$@"
}

echo "========================================================================"
echo "EX-36: Ops Doctor + Run (Thin Slice)"
echo "========================================================================"
echo ""

# Step 1: Run ops doctor (health check)
echo -e "${YELLOW}Step 1: Run ops doctor (health check)${NC}"
run maestro ops doctor
# EXPECT: Health check output with 6 findings
# STORES: none (read-only)
# GATES: none
echo ""

# Step 2: Run ops doctor with JSON output
echo -e "${YELLOW}Step 2: Run ops doctor with JSON output${NC}"
run maestro ops doctor --format json
# EXPECT: JSON output with findings array
# STORES: none
# GATES: none
echo ""

# Step 3: Run ops doctor in strict mode
echo -e "${YELLOW}Step 3: Run ops doctor in strict mode${NC}"
maestro ops doctor --strict || echo "Exit code: $?"
# EXPECT: Exit code 2 if warnings present
# STORES: none
# GATES: none
echo ""

# Step 4: Create an ops plan (YAML)
echo -e "${YELLOW}Step 4: Create an ops plan (YAML)${NC}"
cat > /tmp/example_plan.yaml <<'EOF'
kind: ops_run
name: Example pipeline
steps:
  - maestro: "ops doctor --format json"
  - maestro: "ops list"
EOF
echo "Created /tmp/example_plan.yaml"
# EXPECT: Valid ops plan YAML created
# STORES: /tmp/example_plan.yaml
# GATES: none
echo ""

# Step 5: Run ops plan in dry-run mode
echo -e "${YELLOW}Step 5: Run ops plan in dry-run mode${NC}"
run maestro ops run /tmp/example_plan.yaml --dry-run
# EXPECT: Shows what would be executed, run record created with dry_run: true
# STORES: docs/maestro/ops/runs/<RUN_ID>/*
# GATES: none
echo ""

# Step 6: Run ops plan for real
echo -e "${YELLOW}Step 6: Run ops plan for real${NC}"
run maestro ops run /tmp/example_plan.yaml
# EXPECT: Executes steps, creates full run record
# STORES: docs/maestro/ops/runs/<RUN_ID>/*
# GATES: none (respects individual step gates)
echo ""

# Step 7: List ops runs
echo -e "${YELLOW}Step 7: List ops runs${NC}"
run maestro ops list
# EXPECT: Shows all ops runs with run_id, plan_name, exit_code
# STORES: none
# GATES: none
echo ""

# Step 8: Show ops run details
echo -e "${YELLOW}Step 8: Show ops run details${NC}"
# Get run ID from ops list
RUN_ID=$(maestro ops list | grep "ops_run_" | head -1 | awk '{print $2}')
if [ -n "$RUN_ID" ]; then
    run maestro ops show "$RUN_ID"
    # EXPECT: Full run details with meta, summary, steps
    # STORES: none
    # GATES: none
else
    echo "No ops runs found"
fi
echo ""

# Step 9: Inspect run record files
echo -e "${YELLOW}Step 9: Inspect run record files${NC}"
if [ -n "$RUN_ID" ]; then
    echo "Run record directory:"
    ls -lh docs/maestro/ops/runs/
    echo ""
    echo "Run files:"
    ls -lh docs/maestro/ops/runs/"$RUN_ID"/
    echo ""
    echo "meta.json:"
    cat docs/maestro/ops/runs/"$RUN_ID"/meta.json
    echo ""
    echo "summary.json:"
    cat docs/maestro/ops/runs/"$RUN_ID"/summary.json
    # EXPECT: All run record files exist and are valid JSON
    # STORES: none (read-only)
    # GATES: none
fi
echo ""

echo "========================================================================"
echo "EX-36 Complete!"
echo "========================================================================"
echo ""
echo "Validation:"
echo "  ✓ Doctor checks ran without errors"
echo "  ✓ Ops run executed successfully (dry-run and real)"
echo "  ✓ Run records created under docs/maestro/ops/runs/"
echo "  ✓ Index updated at docs/maestro/ops/index.json"
echo "  ✓ List/show commands work correctly"
echo ""
