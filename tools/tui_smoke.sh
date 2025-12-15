#!/bin/bash
# 
# TUI Smoke Test Helper Script
# 
# This script runs the TUI in smoke mode and verifies that it produces
# the expected success marker, ensuring that automated tests don't hang.

set -e  # Exit on any error

# Parse command line arguments
SMOKE_SECONDS="0.2"
SMOKE_ARGS="--smoke"

for arg in "$@"; do
    case $arg in
        --smoke-seconds=*)
            SMOKE_SECONDS="${arg#*=}"
            ;;
        --smoke-out=*)
            SMOKE_OUT="${arg#*=}"
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--smoke-seconds=SECONDS] [--smoke-out=PATH]"
            exit 1
            ;;
    esac
done

# Add smoke-out argument if provided
if [ -n "$SMOKE_OUT" ]; then
    SMOKE_ARGS="$SMOKE_ARGS --smoke-out=$SMOKE_OUT"
fi

# Check if smoke out file was provided
if [ -n "$SMOKE_OUT" ] && [ ! -f "$SMOKE_OUT" ]; then
    # Create the directory if it doesn't exist
    mkdir -p "$(dirname "$SMOKE_OUT")"
fi

echo "Running TUI smoke test with args: $SMOKE_ARGS --smoke-seconds $SMOKE_SECONDS"

# Run the TUI in smoke mode and capture the output
output=$(timeout 5s python -m maestro.tui $SMOKE_ARGS --smoke-seconds $SMOKE_SECONDS 2>&1) || {
    echo "ERROR: TUI smoke test failed or timed out"
    exit 1
}

# Check if the success marker is present in the output
if echo "$output" | grep -q "MAESTRO_TUI_SMOKE_OK"; then
    echo "SUCCESS: TUI smoke test completed with expected marker"
    echo "$output"
    exit 0
else
    echo "FAILURE: TUI smoke test did not produce expected MAESTRO_TUI_SMOKE_OK marker"
    echo "Actual output:"
    echo "$output"
    exit 1
fi