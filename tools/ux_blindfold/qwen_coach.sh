#!/usr/bin/env bash
#
# qwen_coach.sh - Wrapper script for qwen-driven blindfold UX audit
#
# Usage:
#   tools/ux_blindfold/qwen_coach.sh --goal "..." [--repo PATH] [--execute]
#

set -euo pipefail

# Parse arguments
GOAL=""
REPO=""
EXECUTE_FLAG=""
MAESTRO_BIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --goal)
            GOAL="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --execute)
            EXECUTE_FLAG="--execute"
            shift
            ;;
        --maestro-bin)
            MAESTRO_BIN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 --goal \"...\" [--repo PATH] [--execute] [--maestro-bin CMD]" >&2
            exit 1
            ;;
    esac
done

# Validate required args
if [[ -z "$GOAL" ]]; then
    echo "Error: --goal is required" >&2
    echo "Usage: $0 --goal \"...\" [--repo PATH] [--execute]" >&2
    exit 1
fi

# Determine repo root
if [[ -z "$REPO" ]]; then
    REPO="$(pwd)"
fi

# Convert to absolute path
REPO="$(cd "$REPO" && pwd)"

# Determine maestro binary
if [[ -z "$MAESTRO_BIN" ]]; then
    if [[ -f "$REPO/maestro.py" ]]; then
        MAESTRO_BIN="python $REPO/maestro.py"
    elif command -v maestro &>/dev/null; then
        MAESTRO_BIN="maestro"
    else
        # Try python -m maestro
        MAESTRO_BIN="python -m maestro"
    fi
fi

# Locate qwen_driver.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER="$SCRIPT_DIR/qwen_driver.py"

if [[ ! -f "$DRIVER" ]]; then
    echo "Error: qwen_driver.py not found at $DRIVER" >&2
    exit 1
fi

# Build command
CMD=(python "$DRIVER" --goal "$GOAL" --maestro-bin "$MAESTRO_BIN" --repo "$REPO")

if [[ -n "$EXECUTE_FLAG" ]]; then
    CMD+=("$EXECUTE_FLAG")
fi

# Run harness
echo "Running qwen blindfold UX audit..."
echo "Goal: $GOAL"
echo "Repo: $REPO"
echo "Maestro: $MAESTRO_BIN"
echo ""

exec "${CMD[@]}"
