#!/usr/bin/env bash
#
# Smoke test for qwen blindfold UX loop runner.
#
# This script requires qwen to be installed and uses real repositories.
# It's meant for manual verification, not automated CI.
#
# Usage:
#   tools/smoke/qwen_blindfold_maestro.sh [OPTIONS]
#
# Options:
#   --execute    Allow write operations (default: safe mode)
#   --repo PATH  Use specific repo (default: BatchScriptShell if available)
#

set -euo pipefail

# Check if qwen is installed
if ! command -v qwen &>/dev/null; then
    echo "Error: qwen is not installed or not in PATH" >&2
    echo "" >&2
    echo "Please install qwen first:" >&2
    echo "  pip install qwen-cli  # (or your qwen installation method)" >&2
    echo "" >&2
    exit 1
fi

# Find Maestro root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAESTRO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Defaults
REPO=""
EXECUTE_FLAG=""
GOAL="Create an actionable runbook for building and testing this repo"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --execute)
            EXECUTE_FLAG="--execute"
            shift
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --goal)
            GOAL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--execute] [--repo PATH] [--goal \"...\"]" >&2
            exit 1
            ;;
    esac
done

# Determine repo
if [[ -z "$REPO" ]]; then
    # Try to find BatchScriptShell
    if [[ -d "$HOME/Dev/BatchScriptShell" ]]; then
        REPO="$HOME/Dev/BatchScriptShell"
    elif [[ -d "/e/active/sblo/Dev/BatchScriptShell" ]]; then
        REPO="/e/active/sblo/Dev/BatchScriptShell"
    else
        echo "Error: No repo specified and BatchScriptShell not found" >&2
        echo "Use --repo PATH to specify a repository" >&2
        exit 1
    fi
fi

# Resolve repo to absolute path
REPO="$(cd "$REPO" && pwd)"

# Determine maestro binary
if [[ -f "$MAESTRO_ROOT/maestro.py" ]]; then
    MAESTRO_BIN="python $MAESTRO_ROOT/maestro.py"
elif command -v maestro &>/dev/null; then
    MAESTRO_BIN="maestro"
else
    MAESTRO_BIN="python -m maestro"
fi

echo "========================================"
echo "Qwen Blindfold UX Smoke Test"
echo "========================================"
echo "Repo: $REPO"
echo "Maestro: $MAESTRO_BIN"
echo "Goal: $GOAL"
echo "Execute mode: ${EXECUTE_FLAG:-false (safe mode)}"
echo "Qwen: $(which qwen)"
echo ""

# Build command
CMD=(
    python "$MAESTRO_ROOT/tools/ux_qwen_loop/run.py"
    --maestro-bin "$MAESTRO_BIN"
    --repo-root "$REPO"
    --goal "$GOAL"
    -v
)

if [[ -n "$EXECUTE_FLAG" ]]; then
    CMD+=("$EXECUTE_FLAG")
    CMD+=(--postmortem)
    CMD+=(--profile investor)
fi

echo "Running command:"
echo "${CMD[@]}"
echo ""

# Run
"${CMD[@]}"

echo ""
echo "========================================"
echo "Smoke test complete"
echo "========================================"
