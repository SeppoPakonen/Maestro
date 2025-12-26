#!/bin/bash
# Unit Test: Work Minesweeper Test
# Objective: Test that code is actually written when running 'maestro work'
# This test creates a clean track/phase/task structure and verifies work command functionality

set -e  # Exit on error

# Parse command line arguments
VERBOSE=""
if [[ "$1" == "-v" ]] || [[ "$1" == "--verbose" ]]; then
    VERBOSE="-v"
    echo "Running in VERBOSE mode"
fi

echo "============================================"
echo "Work Minesweeper Test - Starting"
echo "============================================"

# Setup: Remove tmp directory if it exists and create fresh one
echo "[1/7] Setting up test environment..."
rm -rf tmp
mkdir tmp
cd tmp

# Get the absolute path to the maestro.py file
MAESTRO_PATH=$(cd ../../.. && pwd)/maestro.py
echo "Using maestro.py at: $MAESTRO_PATH"

# Step 1: Initialize the project
echo "[2/7] Initializing maestro project..."
python "$MAESTRO_PATH" init

echo ""
echo "============================================"
echo "VERBOSE INFO: Creating Track/Phase/Task Structure"
echo "============================================"

# Step 2: Create track using maestro command (to ensure proper JSON storage)
echo "[3/7] Creating Minesweeper Game track..."
echo "WHY: Using 'track add' command ensures proper JSON storage and avoids duplicates"
python "$MAESTRO_PATH" track add "Minesweeper Game" -d "A classic minesweeper game implementation"

# Get the track ID that was created
TRACK_ID=$(python "$MAESTRO_PATH" track list | grep -i "minesweeper" | head -1 | awk '{print $2}')
echo "Created track with ID: $TRACK_ID"

# Step 3: Create phases for the track
echo "[4/7] Creating phases for the Minesweeper Game track..."
echo "WHY: Creating structured phases helps organize tasks by functional area"

echo "  Creating 'Game Board Setup' phase..."
python "$MAESTRO_PATH" phase add "$TRACK_ID" "Game Board Setup" -d "Set up the game board grid and UI"

echo "  Creating 'Mine Logic' phase..."
python "$MAESTRO_PATH" phase add "$TRACK_ID" "Mine Logic" -d "Implement mine placement and detection logic"

echo "  Creating 'User Interaction' phase..."
python "$MAESTRO_PATH" phase add "$TRACK_ID" "User Interaction" -d "Handle user clicks and game controls"

# Get phase IDs
PHASE_BOARD=$(python "$MAESTRO_PATH" phase list "$TRACK_ID" | grep -i "board" | head -1 | awk '{print $2}')
PHASE_MINE=$(python "$MAESTRO_PATH" phase list "$TRACK_ID" | grep -i "mine" | head -1 | awk '{print $2}')
PHASE_UI=$(python "$MAESTRO_PATH" phase list "$TRACK_ID" | grep -i "interaction" | head -1 | awk '{print $2}')

echo "Phase IDs created:"
echo "  - Game Board Setup: $PHASE_BOARD"
echo "  - Mine Logic: $PHASE_MINE"
echo "  - User Interaction: $PHASE_UI"

# Step 4: Create tasks for each phase
echo "[5/7] Creating tasks for each phase..."
echo "WHY: Tasks define the specific work items that 'maestro work' will process"

echo ""
echo "Creating tasks for Game Board Setup phase..."
python "$MAESTRO_PATH" task add "$PHASE_BOARD" "Create HTML grid structure" -p P1
python "$MAESTRO_PATH" task add "$PHASE_BOARD" "Style the game board with CSS" -p P2
python "$MAESTRO_PATH" task add "$PHASE_BOARD" "Add cell rendering function" -p P2

echo ""
echo "Creating tasks for Mine Logic phase..."
python "$MAESTRO_PATH" task add "$PHASE_MINE" "Implement random mine placement algorithm" -p P1
python "$MAESTRO_PATH" task add "$PHASE_MINE" "Calculate adjacent mine counts" -p P1
python "$MAESTRO_PATH" task add "$PHASE_MINE" "Add mine detection on cell reveal" -p P2

echo ""
echo "Creating tasks for User Interaction phase..."
python "$MAESTRO_PATH" task add "$PHASE_UI" "Add left-click handler for cell reveal" -p P1
python "$MAESTRO_PATH" task add "$PHASE_UI" "Add right-click handler for flagging" -p P2
python "$MAESTRO_PATH" task add "$PHASE_UI" "Implement game over detection" -p P1

# Step 5: Verify the structure was created correctly
echo "[6/7] Verifying track/phase/task structure..."
echo ""

# Show track details
echo "Track structure:"
python "$MAESTRO_PATH" track show "$TRACK_ID"

echo ""
echo "Phase and task breakdown:"
python "$MAESTRO_PATH" phase list "$TRACK_ID"

echo ""
echo "All tasks that will be worked on:"
python "$MAESTRO_PATH" task list "$PHASE_BOARD"
python "$MAESTRO_PATH" task list "$PHASE_MINE"
python "$MAESTRO_PATH" task list "$PHASE_UI"

# Count entities
TRACK_COUNT=$(python "$MAESTRO_PATH" track list | grep -c "minesweeper" || echo "0")
PHASE_COUNT=$(python "$MAESTRO_PATH" phase list "$TRACK_ID" | grep -c "Phase" || echo "0")
TASK_COUNT_BOARD=$(python "$MAESTRO_PATH" task list "$PHASE_BOARD" | grep -c "^\s*[0-9]" || echo "0")
TASK_COUNT_MINE=$(python "$MAESTRO_PATH" task list "$PHASE_MINE" | grep -c "^\s*[0-9]" || echo "0")
TASK_COUNT_UI=$(python "$MAESTRO_PATH" task list "$PHASE_UI" | grep -c "^\s*[0-9]" || echo "0")
TOTAL_TASKS=$((TASK_COUNT_BOARD + TASK_COUNT_MINE + TASK_COUNT_UI))

echo ""
echo "Structure verification:"
echo "  Tracks: $TRACK_COUNT"
echo "  Phases: $PHASE_COUNT"
echo "  Tasks: $TOTAL_TASKS"
echo ""

if [ "$TOTAL_TASKS" -lt 1 ]; then
    echo "ERROR: Expected at least 1 task, found $TOTAL_TASKS"
    exit 1
fi

# Step 6: Start working on tasks using 'maestro work' command
echo "[7/7] Testing 'maestro work' command..."
echo ""
echo "============================================"
echo "VERBOSE INFO: Running 'maestro work'"
echo "============================================"
echo ""
echo "PURPOSE: Verify that 'maestro work' actually writes code for the tasks"
echo "CURRENT ISSUE: The command returns thinking/planning but doesn't write actual code"
echo "EXPECTED BEHAVIOR: Should create actual code files for the minesweeper game"
echo ""

# Set context to the first task
echo "Setting work context to first task..."
FIRST_TASK_ID=$(python "$MAESTRO_PATH" task list "$PHASE_BOARD" | grep "^\s*1\s" | awk '{print $2}' || echo "")

if [ -z "$FIRST_TASK_ID" ]; then
    echo "ERROR: Could not find first task ID"
    exit 1
fi

echo "First task ID: $FIRST_TASK_ID"
echo ""

# Run the work command with timeout
echo "Executing: maestro work $VERBOSE"
echo "This will attempt to work on task: $FIRST_TASK_ID"
echo ""

# Run work command and capture output
set +e  # Don't exit on error for this command
timeout 300 python "$MAESTRO_PATH" $VERBOSE work
WORK_EXIT_CODE=$?
set -e

echo ""
echo "============================================"
echo "Work command completed with exit code: $WORK_EXIT_CODE"
echo "============================================"
echo ""

# Check if any code files were created
echo "Checking for generated code files..."
CODE_FILE_COUNT=$(find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.html" -o -name "*.css" \) ! -path "./docs/*" | wc -l)
echo "Found $CODE_FILE_COUNT code files"

if [ "$CODE_FILE_COUNT" -gt 0 ]; then
    echo ""
    echo "Generated files:"
    find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.html" -o -name "*.css" \) ! -path "./docs/*" -exec ls -lh {} \;
    echo ""
    echo "SUCCESS: Code files were generated!"
else
    echo ""
    echo "WARNING: No code files were generated"
    echo "ISSUE CONFIRMED: 'maestro work' does not write actual code"
    echo ""
fi

# Show final structure
echo ""
echo "Final project structure:"
echo "============================================"
tree -L 2 -I 'docs' || find . -maxdepth 2 -type f ! -path "./docs/*" -exec ls -lh {} \;

echo ""
echo "============================================"
echo "Test Summary"
echo "============================================"
echo "Tracks created: $TRACK_COUNT"
echo "Phases created: $PHASE_COUNT"
echo "Tasks created: $TOTAL_TASKS"
echo "Code files generated: $CODE_FILE_COUNT"
echo "Work command exit code: $WORK_EXIT_CODE"
echo "============================================"

if [ "$CODE_FILE_COUNT" -gt 0 ]; then
    echo "STATUS: ✓ SUCCESS - Code was generated"
    exit 0
else
    echo "STATUS: ✗ FAILED - No code was generated"
    echo "NOTE: This confirms the issue that 'maestro work' doesn't write code"
    exit 1
fi
