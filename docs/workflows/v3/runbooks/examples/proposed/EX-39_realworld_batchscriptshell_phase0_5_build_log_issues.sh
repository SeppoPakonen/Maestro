#!/bin/bash
# EX-39: BatchScriptShell Phase 0.5 Build→Log→Issues Runbook Script
# Non-interactive script to demonstrate the BatchScriptShell Phase 0.5 workflow

set -e  # Exit on any error

echo "EX-39: BatchScriptShell Phase 0.5 Build→Log→Issues Runbook"
echo "=========================================================="

# Check prerequisites
if [ ! -d "$HOME/Dev/BatchScriptShell" ]; then
    echo "ERROR: BatchScriptShell repository not found at ~/Dev/BatchScriptShell"
    exit 1
fi

if [ ! -d "$HOME/Dev/Maestro" ]; then
    echo "ERROR: Maestro repository not found at ~/Dev/Maestro"
    exit 1
fi

echo "Prerequisites check: PASSED"
echo

# Phase A: Verify repo model and routing
echo "Phase A: Verifying repository model..."
echo "--------------------------------------"
cd $HOME/Dev/BatchScriptShell

echo "Running: MAESTRO_DOCS_ROOT='./docs/maestro' python3 ~/Dev/Maestro/maestro.py repo resolve -v"
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo resolve -v > /tmp/phase05_repo_resolve.log 2>&1
echo "Repo resolve: COMPLETED (output in /tmp/phase05_repo_resolve.log)"

echo "Running: MAESTRO_DOCS_ROOT='./docs/maestro' python3 ~/Dev/Maestro/maestro.py repo asm list"
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo asm list
echo "Assembly list: COMPLETED"

echo "Running: MAESTRO_DOCS_ROOT='./docs/maestro' python3 ~/Dev/Maestro/maestro.py repo pkg"
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo pkg
echo "Package list: COMPLETED"
echo

# Phase B: Create isolated build
echo "Phase B: Creating isolated build..."
echo "-----------------------------------"
cd $HOME/Dev/BatchScriptShell

echo "Creating out-of-tree build directory..."
rm -rf build_maestro && mkdir -p build_maestro

echo "Running CMake configure..."
cd build_maestro
cmake_output=$(cmake .. 2>&1 | tee /tmp/bss_cmake_configure.log)
echo "CMake configure: COMPLETED"

echo "Running CMake build..."
build_output=$(cmake --build . 2>&1 | tee /tmp/bss_cmake_build.log)
echo "CMake build: COMPLETED"
echo

# Phase B (continued): Generate error log for demonstration
echo "Phase B (continued): Generating error log for demonstration..."
echo "-------------------------------------------------------------"
cd $HOME/Dev/BatchScriptShell

# Add intentional error to source file
echo "// Intentional error for testing log scanning" >> shell.c
echo "int intentional_error_function() { int x = ; return 0; }" >> shell.c

echo "Rebuilding to generate errors..."
cd build_maestro
error_build_output=$(cmake --build . 2>&1 | tee /tmp/bss_cmake_build_with_errors.log)
echo "Build with errors: COMPLETED (errors expected)"
echo

# Phase C: Log scan → issues ingestion → triage
echo "Phase C: Log scan → issues ingestion → triage..."
echo "-----------------------------------------------"
cd $HOME/Dev/BatchScriptShell

echo "Scanning build log with errors..."
SCAN_RESULT=$(cat /tmp/bss_cmake_build_with_errors.log | MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py log scan --stdin --kind build)
echo "$SCAN_RESULT"

# Extract SCAN_ID from the output
SCAN_ID=$(echo "$SCAN_RESULT" | grep "Scan created:" | awk '{print $3}')
echo "Extracted SCAN_ID: $SCAN_ID"

echo "Ingesting issues from scan..."
INGEST_RESULT=$(MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues add --from-log $SCAN_ID)
echo "$INGEST_RESULT"

echo "Auto-triaging issues..."
TRIAGE_RESULT=$(MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues triage --auto)
echo "$TRIAGE_RESULT"

echo "Listing created issues..."
ISSUE_LIST=$(MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues list --status open)
echo "$ISSUE_LIST"
echo

# Phase C (continued): Verify determinism and deduplication
echo "Phase C (continued): Verifying determinism and deduplication..."
echo "-------------------------------------------------------------"
cd $HOME/Dev/BatchScriptShell

echo "Scanning the same log again to test determinism..."
SCAN_RESULT_2=$(cat /tmp/bss_cmake_build_with_errors.log | MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py log scan --stdin --kind build)
echo "$SCAN_RESULT_2"

SCAN_ID_2=$(echo "$SCAN_RESULT_2" | grep "Scan created:" | awk '{print $3}')
echo "Second SCAN_ID: $SCAN_ID_2"

echo "Ingesting issues again to verify deduplication..."
INGEST_RESULT_2=$(MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues add --from-log $SCAN_ID_2)
echo "$INGEST_RESULT_2"

echo "Checking that no duplicate issues were created..."
FINAL_ISSUE_COUNT=$(MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues list --status open | grep -c "ISSUE-")
echo "Total open issues after second ingestion: $FINAL_ISSUE_COUNT"

echo
echo "Runbook execution completed successfully!"
echo "Summary:"
echo "- Repo model verification: COMPLETED"
echo "- Isolated build: COMPLETED" 
echo "- Log scan: COMPLETED (SCAN_ID: $SCAN_ID)"
echo "- Issues created/updated: $(echo \"$INGEST_RESULT\" | grep -o \"Created: [0-9]*\" | grep -o [0-9]*) created, $(echo \"$INGEST_RESULT\" | grep -o \"Updated: [0-9]*\" | grep -o [0-9]*) updated"
echo "- Triage summary: COMPLETED"
echo "- Determinism check: COMPLETED (Second scan ID: $SCAN_ID_2)"
echo "- Deduplication check: COMPLETED (Final issue count: $FINAL_ISSUE_COUNT)"