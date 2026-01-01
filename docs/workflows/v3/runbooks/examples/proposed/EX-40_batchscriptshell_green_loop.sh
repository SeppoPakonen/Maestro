#!/usr/bin/env bash
# EX-40: BatchScriptShell Green Loop
#
# Demonstrates the complete workflow: build → scan → issues → workgraph → execute
#
# Prerequisites:
#   - BatchScriptShell cloned at ~/Dev/BatchScriptShell
#   - Maestro installed with ops run support
#
# Usage:
#   # Manual step-by-step:
#   bash docs/workflows/v3/runbooks/examples/proposed/EX-40_batchscriptshell_green_loop.sh manual
#
#   # Automated ops plan:
#   bash docs/workflows/v3/runbooks/examples/proposed/EX-40_batchscriptshell_green_loop.sh auto
#
#   # Automated with execute:
#   bash docs/workflows/v3/runbooks/examples/proposed/EX-40_batchscriptshell_green_loop.sh auto --execute

set -euo pipefail

# Configuration
BSS_REPO="${BSS_REPO:-$HOME/Dev/BatchScriptShell}"
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"
MODE="${1:-manual}"
EXECUTE_FLAG="${2:-}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_header() { echo -e "\n${BLUE}===${NC} $* ${BLUE}===${NC}\n"; }
echo_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $*"; }
echo_success() { echo -e "${GREEN}[✓]${NC} $*"; }

# Check prerequisites
if [[ ! -d "$BSS_REPO" ]]; then
    echo_error "BatchScriptShell repository not found at: $BSS_REPO"
    echo_error "Clone it or set BSS_REPO environment variable"
    exit 1
fi

if [[ "$MODE" == "manual" ]]; then
    echo_header "BatchScriptShell Green Loop - Manual Mode"
    echo_info "This will run each step individually with confirmation"
    echo ""

    # Phase 1: Build and Capture
    echo_header "Phase 1: Build and Capture"
    echo_info "Building BatchScriptShell and capturing output..."
    cd "$BSS_REPO"

    $MAESTRO_BIN make clean || true
    $MAESTRO_BIN make 2>&1 | tee build.log || {
        echo_warn "Build may have errors (expected for demo)"
    }

    echo_success "Build completed. Log saved to build.log"
    echo ""
    read -p "Press Enter to continue to Phase 2 (log scan)..."

    # Phase 2: Scan Build Output
    echo_header "Phase 2: Scan Build Output"
    echo_info "Scanning build.log for errors and warnings..."

    SCAN_OUTPUT=$($MAESTRO_BIN log scan --source build.log --kind build 2>&1)
    echo "$SCAN_OUTPUT"

    SCAN_ID=$(echo "$SCAN_OUTPUT" | grep -oP "Scan created: \K\S+" || echo "")

    if [[ -z "$SCAN_ID" ]]; then
        echo_warn "Could not extract scan ID from output"
        SCAN_ID="<SCAN_ID>"
    else
        echo_success "Scan created: $SCAN_ID"
    fi

    echo ""
    read -p "Press Enter to continue to Phase 3 (ingest issues)..."

    # Phase 3: Ingest Issues
    echo_header "Phase 3: Ingest Issues"
    echo_info "Converting log scan findings to trackable issues..."

    if [[ "$SCAN_ID" != "<SCAN_ID>" ]]; then
        $MAESTRO_BIN issues add --from-log "$SCAN_ID" || {
            echo_warn "Issues ingestion may have failed"
        }

        echo ""
        echo_info "Listing open issues:"
        $MAESTRO_BIN issues list --status open || true

        echo_success "Issues ingested"
    else
        echo_warn "Skipping issues ingest (no scan ID)"
    fi

    echo ""
    read -p "Press Enter to continue to Phase 4 (generate workgraph)..."

    # Phase 4: Generate WorkGraph
    echo_header "Phase 4: Generate WorkGraph from Issues"
    echo_info "Using AI to decompose issues into structured plan..."

    WG_OUTPUT=$($MAESTRO_BIN plan decompose --domain issues "Bring BatchScriptShell to green build" -e 2>&1)
    echo "$WG_OUTPUT"

    WG_ID=$(echo "$WG_OUTPUT" | grep -oP "WorkGraph created: \K\S+" || echo "")

    if [[ -z "$WG_ID" ]]; then
        echo_warn "Could not extract WorkGraph ID from output"
        WG_ID="<WG_ID>"
    else
        echo_success "WorkGraph created: $WG_ID"
    fi

    echo ""
    read -p "Press Enter to continue to Phase 5 (materialize workgraph)..."

    # Phase 5: Materialize WorkGraph
    echo_header "Phase 5: Materialize WorkGraph to Track/Phase/Task"
    echo_info "Converting WorkGraph to Maestro track structure..."

    if [[ "$WG_ID" != "<WG_ID>" ]]; then
        $MAESTRO_BIN plan enact "$WG_ID" || {
            echo_warn "WorkGraph materialization may have failed"
        }

        echo_success "WorkGraph materialized"
        echo_info "Created Track, Phases, and Tasks in docs/maestro/"
    else
        echo_warn "Skipping materialization (no WorkGraph ID)"
    fi

    echo ""
    read -p "Press Enter to continue to Phase 6 (execute plan dry-run)..."

    # Phase 6: Execute Plan (Dry-Run)
    echo_header "Phase 6: Execute Plan (Dry-Run)"
    echo_info "Previewing what the plan would do (no actual execution)..."

    if [[ "$WG_ID" != "<WG_ID>" ]]; then
        $MAESTRO_BIN plan run "$WG_ID" --dry-run -v --max-steps 5 || {
            echo_warn "Dry-run may have encountered issues"
        }

        echo_success "Dry-run completed"
    else
        echo_warn "Skipping execution (no WorkGraph ID)"
    fi

    echo ""
    echo_header "Manual Mode Complete"
    echo_info "To execute for real, run:"
    echo_info "  maestro plan run $WG_ID --execute -v --max-steps 5"
    echo ""
    echo_warn "WARNING: Only execute tasks you trust (check safe_to_execute field)"

elif [[ "$MODE" == "auto" ]]; then
    echo_header "BatchScriptShell Green Loop - Automated Mode"
    echo_info "This will run the complete workflow using an ops plan"
    echo ""

    # Find the ops plan
    MAESTRO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
    OPS_PLAN="$MAESTRO_ROOT/tests/fixtures/ops_plans/plan_batchscriptshell_build.yaml"

    if [[ ! -f "$OPS_PLAN" ]]; then
        echo_error "Ops plan not found at: $OPS_PLAN"
        exit 1
    fi

    echo_info "Ops plan: $OPS_PLAN"
    echo_info "Repository: $BSS_REPO"
    echo ""

    # Change to BSS repo
    cd "$BSS_REPO"
    echo_info "Working directory: $(pwd)"
    echo ""

    # Build command
    CMD="$MAESTRO_BIN ops run \"$OPS_PLAN\" --continue-on-error"

    if [[ -n "$EXECUTE_FLAG" ]]; then
        CMD="$CMD $EXECUTE_FLAG"
        echo_warn "Execute mode enabled: write steps will be executed"
    else
        echo_info "Dry-run mode: write steps will be skipped (use --execute to enable)"
    fi

    echo_info "Running: $CMD"
    echo ""

    # Run the ops plan
    eval "$CMD" || {
        EXIT_CODE=$?
        echo_error "Ops plan failed with exit code: $EXIT_CODE"
        exit $EXIT_CODE
    }

    echo ""
    echo_success "Ops plan completed successfully"
    echo ""
    echo_info "Check the run record in docs/maestro/ops/runs/ for details"

else
    echo_error "Unknown mode: $MODE"
    echo_error "Usage: $0 {manual|auto} [--execute]"
    exit 1
fi
