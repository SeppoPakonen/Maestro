#!/bin/bash

# Maestro Chaos Rehearsal - Intentional Broken-Code Scenarios
# Shell harness for running the test scenarios

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TESTS_DIR="$REPO_ROOT/.maestro/tests"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --list                    List available scenarios without running"
    echo "  --keep-going              Continue running scenarios even if some fail"
    echo "  --help                    Show this help message"
    echo ""
    echo "This script runs Maestro's chaos rehearsal scenarios to test"
    echo "the build + fix machinery with intentional failures."
    exit 1
}

# Parse command line arguments
LIST_ONLY=false
KEEP_GOING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --list)
            LIST_ONLY=true
            shift
            ;;
        --keep-going)
            KEEP_GOING=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo -e "${BLUE}Starting Maestro Chaos Rehearsal${NC}"
echo -e "${BLUE}================================${NC}"

cd "$REPO_ROOT"

if [ "$LIST_ONLY" = true ]; then
    echo "Available scenarios:"
    python "$TESTS_DIR/run_scenarios.py" --list
else
    echo -e "${YELLOW}Running all scenarios...${NC}"
    echo ""
    
    if [ "$KEEP_GOING" = true ]; then
        python "$TESTS_DIR/run_scenarios.py" --keep-going
    else
        python "$TESTS_DIR/run_scenarios.py"
    fi
    
    echo ""
    echo -e "${GREEN}Maestro Chaos Rehearsal completed!${NC}"
    echo -e "${GREEN}Check .maestro/reports/ for improvement suggestions.${NC}"
fi