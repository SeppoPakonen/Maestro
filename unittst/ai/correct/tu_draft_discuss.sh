#!/bin/bash
# Unit Test: TU Draft Discuss Test
# Objective: Verify tu draft command with -p prompt argument for automated testing

set -e  # Exit on error

# Parse command line arguments
VERBOSE=""
if [[ "$1" == "-v" ]] || [[ "$1" == "--verbose" ]]; then
    VERBOSE="-v"
    echo "Running in VERBOSE mode"
fi

echo "============================================"
echo "TU Draft Discuss Test - Starting"
echo "============================================"

# Setup: Remove tmp directory if it exists and create fresh one
echo "[1/8] Setting up test environment..."
rm -rf tmp
mkdir tmp
cd tmp

# Get the absolute path to the maestro.py file
MAESTRO_PATH=$(cd ../.. && pwd)/maestro.py
echo "Using maestro.py at: $MAESTRO_PATH"

# Step 1: Initialize the project
echo "[2/8] Initializing maestro project..."
python "$MAESTRO_PATH" init

# Step 2: Create a new plan for Minesweeper Game
echo "[3/8] Creating plan for Minesweeper Game..."
../../../maestro.py plan add "Minesweeper Game"

# Step 3: Add initial items to the plan
echo "[4/8] Adding initial items to the plan..."
../../../maestro.py plan add-item 1 "Create game board grid"
../../../maestro.py plan add-item 1 "Implement mine placement logic"
../../../maestro.py plan add-item 1 "Add click handlers"

# Verify the plan was created correctly
echo "[5/8] Verifying plan contents..."
../../../maestro.py plan show 1

# Step 4: Use plan discuss with -p argument to add new items
echo "[6/8] Using plan discuss to add scoring system..."
../../../maestro.py $VERBOSE plan discuss 1 -p "Add a new item 'Add scoring system' and sub-items for 'Track time', 'Count moves', and 'Show high scores'"

# Show the updated plan
echo "[6.5/8] Showing updated plan..."
../../../maestro.py plan show 1

# Step 5: Run plan explore to convert plan into project operations
# We'll use qwen for this with auto-apply
echo "[7/8] Running plan explore to create project structure..."
echo "This may take 10-20 minutes as the AI processes the plan..."

# Run plan explore with auto-apply and allow multiple iterations to create track, phases, and tasks
# We need at least 3 iterations: one for track, one for phase, one for tasks
timeout 1200 ../../../maestro.py $VERBOSE plan explore 1 --apply --auto-apply --max-iterations 5 --engine qwen || {
    echo "Plan explore timed out or failed"
    exit 1
}

# Step 6: Verify that the explore command created the expected structure
echo "[8/8] Verifying project structure was created..."

# Check if docs/todo.md exists
if [ ! -f docs/todo.md ]; then
    echo "ERROR: docs/todo.md was not created"
    exit 1
fi

# Parse docs/todo.md to verify structure
# We need at least 1 track, 1 phase, and 1 task

# Count tracks (lines starting with "## Track:")
TRACK_COUNT=$(grep -c "^## Track:" docs/todo.md || echo "0")
echo "Found $TRACK_COUNT track(s)"

if [ "$TRACK_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 track, found $TRACK_COUNT"
    cat docs/todo.md
    exit 1
fi

# Count phases (lines starting with "###" followed by "Phase")
PHASE_COUNT=$(grep -c "^### Phase" docs/todo.md || echo "0")
echo "Found $PHASE_COUNT phase(s)"

if [ "$PHASE_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 phase, found $PHASE_COUNT"
    cat docs/todo.md
    exit 1
fi

# Count tasks (lines starting with "- [ ]" or "- [x]")
TASK_COUNT=$(grep -c "^- \[" docs/todo.md || echo "0")
echo "Found $TASK_COUNT task(s)"

if [ "$TASK_COUNT" -lt 1 ]; then
    echo "ERROR: Expected at least 1 task, found $TASK_COUNT"
    cat docs/todo.md
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
echo "Final docs/todo.md contents:"
cat docs/todo.md

# Now let's test the TU draft functionality
echo ""
echo "============================================"
echo "Testing TU Draft Functionality"
echo "============================================"

# Create a simple Python file to test TU functionality
echo "[1/4] Creating sample Python file..."
mkdir -p src
cat > src/game.py << 'EOF'
class Game:
    def __init__(self):
        self.board = None
        self.mines = []
    
    def start_game(self):
        pass
    
    def place_mines(self):
        pass
EOF

# Step 1: Create draft classes using tu draft command
echo "[2/4] Creating draft classes and functions..."
../../../maestro.py $VERBOSE tu draft src --class GameBoard --class GameLogic --function calculate_score --lang python --link-phase "1" --link-task "1" -p "Create a basic game board class with methods for initializing the board, getting cell values, and updating the board state"

# Step 2: Verify draft files were created
echo "[3/4] Verifying draft files were created..."
if [ ! -f .maestro/tu/draft/GameBoard.py ]; then
    echo "ERROR: GameBoard.py draft file was not created"
    exit 1
fi

if [ ! -f .maestro/tu/draft/GameLogic.py ]; then
    echo "ERROR: GameLogic.py draft file was not created"
    exit 1
fi

if [ ! -f .maestro/tu/draft/calculate_score_impl.py ]; then
    echo "ERROR: calculate_score_impl.py draft file was not created"
    exit 1
fi

echo "Draft files created successfully:"
ls -la .maestro/tu/draft/

# Step 3: Verify that todo-classes.md was created/updated with links
echo "[4/4] Verifying todo-classes.md was updated..."
if [ ! -f docs/todo-classes.md ]; then
    echo "ERROR: docs/todo-classes.md was not created"
    exit 1
fi

echo "docs/todo-classes.md contents:"
cat docs/todo-classes.md

echo ""
echo "============================================"
echo "SUCCESS: TU Draft test completed successfully!"
echo "============================================"

exit 0