#!/usr/bin/env bash
# BatchScriptShell Green Loop Smoke Test
#
# Tests the full "green loop" workflow on a real repository:
# build → log scan → issues ingest → decompose → enact → run
#
# Usage:
#   BSS_REPO=~/Dev/BatchScriptShell bash tools/smoke/batchscriptshell_green_loop.sh
#   bash tools/smoke/batchscriptshell_green_loop.sh --execute  # Run with --execute flag

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $*"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

# Configuration
BSS_REPO="${BSS_REPO:-$HOME/Dev/BatchScriptShell}"
MAESTRO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPS_PLAN="$MAESTRO_ROOT/tests/fixtures/ops_plans/plan_batchscriptshell_build.yaml"
EXECUTE_FLAG=""

# Parse arguments
if [[ "${1:-}" == "--execute" ]]; then
    EXECUTE_FLAG="--execute"
    echo_info "Execute mode: write steps will be executed"
else
    echo_info "Dry-run mode: write steps will be skipped (use --execute to enable)"
fi

# Verify prerequisites
echo_info "Checking prerequisites..."

if [[ ! -d "$BSS_REPO" ]]; then
    echo_error "BatchScriptShell repository not found at: $BSS_REPO"
    echo_error "Set BSS_REPO environment variable to the correct path"
    exit 1
fi

if [[ ! -f "$OPS_PLAN" ]]; then
    echo_error "Ops plan not found at: $OPS_PLAN"
    exit 1
fi

echo_success "Prerequisites OK"
echo_info "  BSS_REPO: $BSS_REPO"
echo_info "  OPS_PLAN: $OPS_PLAN"
echo_info "  MAESTRO_ROOT: $MAESTRO_ROOT"

# Create temporary docs root for isolation
TEMP_DOCS=$(mktemp -d)
export MAESTRO_DOCS_ROOT="$TEMP_DOCS"
export MAESTRO_BIN="python -m maestro"

echo_info "Using temporary MAESTRO_DOCS_ROOT: $MAESTRO_DOCS_ROOT"

# Cleanup function
cleanup() {
    if [[ -d "$TEMP_DOCS" ]]; then
        echo_info "Cleaning up temporary directory: $TEMP_DOCS"
        rm -rf "$TEMP_DOCS"
    fi
}
trap cleanup EXIT

# Change to BatchScriptShell repo
cd "$BSS_REPO"
echo_info "Working directory: $(pwd)"

# Run the ops plan
echo_info "Running ops plan..."
RUN_OUTPUT=$(cd "$MAESTRO_ROOT" && python -m maestro ops run "$OPS_PLAN" --continue-on-error $EXECUTE_FLAG 2>&1 || true)
echo "$RUN_OUTPUT"

# Extract run ID from output
RUN_ID=$(echo "$RUN_OUTPUT" | grep -oP "Ops run created: \K\S+" || echo "")

if [[ -z "$RUN_ID" ]]; then
    echo_error "Failed to extract run ID from output"
    echo_error "Output was:"
    echo "$RUN_OUTPUT"
    exit 1
fi

echo_success "Ops run completed: $RUN_ID"

# Verify run record structure
echo_info "Verifying run record structure..."
RUN_DIR="$TEMP_DOCS/docs/maestro/ops/runs/$RUN_ID"

if [[ ! -d "$RUN_DIR" ]]; then
    echo_error "Run directory not found: $RUN_DIR"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "meta.json"
    "steps.jsonl"
    "stdout.txt"
    "stderr.txt"
    "summary.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$RUN_DIR/$file" ]]; then
        echo_error "Missing required file: $file"
        exit 1
    fi
    echo_success "  Found: $file"
done

# Verify metadata capture
echo_info "Checking metadata extraction..."

# Check for scan_id in steps
if grep -q '"scan_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    SCAN_ID=$(grep -oP '"scan_id":\s*"\K[^"]+' "$RUN_DIR/steps.jsonl" | head -1)
    echo_success "  Scan ID captured: $SCAN_ID"
else
    echo_warn "  No scan ID found in step results"
fi

# Check for workgraph_id in steps
if grep -q '"workgraph_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    WG_ID=$(grep -oP '"workgraph_id":\s*"\K[^"]+' "$RUN_DIR/steps.jsonl" | head -1)
    echo_success "  WorkGraph ID captured: $WG_ID"
else
    echo_warn "  No WorkGraph ID found in step results"
fi

# Check for workgraph_run_id in steps
if grep -q '"workgraph_run_id"' "$RUN_DIR/steps.jsonl" 2>/dev/null; then
    WG_RUN_ID=$(grep -oP '"workgraph_run_id":\s*"\K[^"]+' "$RUN_DIR/steps.jsonl" | head -1)
    echo_success "  WorkGraph run ID captured: $WG_RUN_ID"
else
    echo_warn "  No WorkGraph run ID found in step results"
fi

# Verify step execution
echo_info "Verifying step execution..."
STEP_COUNT=$(grep -c '^{' "$RUN_DIR/steps.jsonl" || echo "0")
echo_info "  Total steps executed: $STEP_COUNT"

if [[ "$STEP_COUNT" -lt 5 ]]; then
    echo_warn "  Expected at least 5 steps (repo resolve, make clean, make, log scan, ...)"
fi

# Check summary
echo_info "Checking summary..."
if command -v jq &> /dev/null; then
    TOTAL_STEPS=$(jq -r '.total_steps' "$RUN_DIR/summary.json")
    SUCCESSFUL_STEPS=$(jq -r '.successful_steps' "$RUN_DIR/summary.json")
    FAILED_STEPS=$(jq -r '.failed_steps' "$RUN_DIR/summary.json")
    EXIT_CODE=$(jq -r '.exit_code' "$RUN_DIR/summary.json")

    echo_info "  Total steps: $TOTAL_STEPS"
    echo_info "  Successful: $SUCCESSFUL_STEPS"
    echo_info "  Failed: $FAILED_STEPS"
    echo_info "  Exit code: $EXIT_CODE"

    if [[ "$EXIT_CODE" != "0" ]] && [[ -z "$EXECUTE_FLAG" ]]; then
        echo_warn "  Some steps failed (expected in dry-run mode)"
    fi
else
    echo_warn "  jq not installed, skipping summary parsing"
fi

# Verify artifacts created (if in execute mode)
if [[ -n "$EXECUTE_FLAG" ]]; then
    echo_info "Verifying artifacts (execute mode)..."

    # Check for issues
    ISSUES_DIR="$TEMP_DOCS/docs/maestro/issues"
    if [[ -d "$ISSUES_DIR" ]]; then
        ISSUE_COUNT=$(find "$ISSUES_DIR" -name "*.json" | wc -l)
        echo_success "  Issues directory created with $ISSUE_COUNT issue(s)"
    else
        echo_warn "  No issues directory found"
    fi

    # Check for workgraphs
    WORKGRAPHS_DIR="$TEMP_DOCS/docs/maestro/plans/workgraphs"
    if [[ -d "$WORKGRAPHS_DIR" ]]; then
        WG_COUNT=$(find "$WORKGRAPHS_DIR" -name "*.json" | wc -l)
        echo_success "  WorkGraphs directory created with $WG_COUNT workgraph(s)"
    else
        echo_warn "  No workgraphs directory found"
    fi

    # Check for tracks/phases/tasks
    TRACKS_DIR="$TEMP_DOCS/docs/maestro/tracks"
    if [[ -d "$TRACKS_DIR" ]]; then
        TRACK_COUNT=$(find "$TRACKS_DIR" -name "*.json" | wc -l)
        echo_success "  Tracks directory created with $TRACK_COUNT track(s)"
    else
        echo_warn "  No tracks directory found"
    fi
else
    echo_info "Skipping artifact verification (dry-run mode)"
fi

echo ""
echo_success "=== Smoke test completed successfully ==="
echo_info "Run ID: $RUN_ID"
echo_info "Run record: $RUN_DIR"
echo ""
echo_info "To inspect the results:"
echo_info "  cat $RUN_DIR/meta.json"
echo_info "  cat $RUN_DIR/summary.json"
echo_info "  cat $RUN_DIR/steps.jsonl | jq ."
echo ""

# Keep temp dir if TEST_KEEP_TEMP is set
if [[ "${TEST_KEEP_TEMP:-}" == "1" ]]; then
    echo_info "Keeping temporary directory (TEST_KEEP_TEMP=1): $TEMP_DOCS"
    trap - EXIT  # Disable cleanup
fi
