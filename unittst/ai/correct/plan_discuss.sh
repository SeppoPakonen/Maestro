#!/bin/bash
# Unit Test: Plan Discuss Test
# Objective: Verify plan discuss command with -p prompt argument for automated testing

set -e  # Exit on error

# Parse command line arguments
VERBOSE=""
if [[ "$1" == "-v" ]] || [[ "$1" == "--verbose" ]]; then
    VERBOSE="-v"
    echo "Running in VERBOSE mode"
fi

echo "============================================"
echo "Plan Discuss Test - Starting"
echo "============================================"

# Setup: Remove tmp directory if it exists and create fresh one
echo "[1/8] Setting up test environment..."
rm -rf tmp
mkdir tmp
cd tmp

# Step 1: Initialize the project
echo "[2/8] Initializing maestro project..."
../maestro.py init

# Step 2: Create a new plan for Minesweeper Game
echo "[3/8] Creating plan for Minesweeper Game..."
../maestro.py plan add "Minesweeper Game"

# Step 3: Add initial items to the plan
echo "[4/8] Adding initial items to the plan..."
../maestro.py plan add-item 1 "Create game board grid"
../maestro.py plan add-item 1 "Implement mine placement logic"
../maestro.py plan add-item 1 "Add click handlers"

# Verify the plan was created correctly
echo "[5/8] Verifying plan contents..."
../maestro.py plan show 1

# Step 4: Use plan discuss with -p argument to add new items
echo "[6/8] Using plan discuss to add scoring system..."
../maestro.py $VERBOSE plan discuss 1 -p "Add a new item 'Add scoring system' and sub-items for 'Track time', 'Count moves', and 'Show high scores'"

# Show the updated plan
echo "[6.5/8] Showing updated plan..."
../maestro.py plan show 1

# Step 5: Run plan explore to convert plan into project operations
# We'll use qwen for this with auto-apply
echo "[7/8] Running plan explore to create project structure..."
echo "This may take 10-20 minutes as the AI processes the plan..."

# Run plan explore with auto-apply and allow multiple iterations to create track, phases, and tasks
# We need at least 3 iterations: one for track, one for phase, one for tasks
timeout 1200 ../maestro.py $VERBOSE plan explore 1 --apply --auto-apply --max-iterations 5 --engine qwen || {
    echo "Plan explore timed out or failed"
    exit 1
}

# Step 6: Verify that the explore command created the expected structure
echo "[8/8] Verifying project structure was created..."

# Check if docs/maestro exists
if [ ! -d docs/maestro ]; then
    echo "ERROR: docs/maestro was not created"
    exit 1
fi

# Parse JSON store to verify structure
# We need at least 1 track, 1 phase, and 1 task

# Count tracks
TRACK_COUNT=$(find docs/maestro/tracks -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Found $TRACK_COUNT track(s)"

if [ "$TRACK_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 track, found $TRACK_COUNT"
    find docs/maestro -type f -name '*.json' 2>/dev/null
    exit 1
fi

# Count phases
PHASE_COUNT=$(find docs/maestro/phases -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Found $PHASE_COUNT phase(s)"

if [ "$PHASE_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 phase, found $PHASE_COUNT"
    find docs/maestro -type f -name '*.json' 2>/dev/null
    exit 1
fi

# Count tasks
TASK_COUNT=$(find docs/maestro/tasks -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Found $TASK_COUNT task(s)"

if [ "$TASK_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 task, found $TASK_COUNT"
    find docs/maestro -type f -name '*.json' 2>/dev/null
    exit 1
fi

echo ""
echo "============================================"
echo "SUCCESS: All assertions passed!"
echo "- Tracks: $TRACK_COUNT"
echo "- Phases: $PHASE_COUNT"
echo "- Tasks: $TASK_COUNT"
echo "============================================"

# Show the final structure
echo ""
echo "Final docs/maestro contents:"
find docs/maestro -type f -name '*.json' 2>/dev/null

exit 0
