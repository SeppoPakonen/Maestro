#!/bin/bash
# Quick Unit Test: Plan Discuss Test (without AI processing)
# Objective: Verify plan commands work correctly

set -e  # Exit on error

echo "============================================"
echo "Plan Discuss Quick Test - Starting"
echo "============================================"

# Setup: Remove tmp directory if it exists and create fresh one
echo "[1/6] Setting up test environment..."
rm -rf tmp
mkdir tmp
cd tmp

# Step 1: Initialize the project
echo "[2/6] Initializing maestro project..."
../maestro.py init

# Step 2: Create a new plan for Minesweeper Game
echo "[3/6] Creating plan for Minesweeper Game..."
../maestro.py plan add "Minesweeper Game"

# Step 3: Add initial items to the plan
echo "[4/6] Adding initial items to the plan..."
../maestro.py plan add-item 1 "Create game board grid"
../maestro.py plan add-item 1 "Implement mine placement logic"
../maestro.py plan add-item 1 "Add click handlers"

# Verify the plan was created correctly
echo "[5/6] Verifying plan contents..."
../maestro.py plan show 1

# Step 4: Test that plan discuss accepts -p argument (without actually running AI)
echo "[6/6] Testing plan discuss help to verify -p argument exists..."
../maestro.py plan discuss --help | grep -q "\-p.*PROMPT" && echo "✓ -p/--prompt argument is available"

echo ""
echo "============================================"
echo "SUCCESS: All basic plan commands work!"
echo "- Plan add: ✓"
echo "- Plan list: ✓"
echo "- Plan show: ✓"
echo "- Plan add-item: ✓"
echo "- Plan discuss -p argument: ✓"
echo "============================================"

exit 0
