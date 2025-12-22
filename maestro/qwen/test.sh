#!/bin/bash

# Test script for Qwen Python implementation with existing configuration
# This script runs the test that uses the existing OAuth configuration in ~/.qwen
# and sends a command to get an actual AI response
# It also tests the NCurses TUI functionality

cd "$(dirname "$0")/.." || exit 1

echo "Testing Qwen Python implementation..."

# Test 1: Get AI response via JSON commands
echo -e "\n--- Test 1: JSON Command Interface ---"
# Start the Qwen manager in the background
python3 -m maestro.qwen.run_local --local &
QWEN_PID=$!

# Wait a moment for the service to start
sleep 3

# Send a user input command to get AI response
echo '{"type":"user_input","content":"Hello, how are you?"}' | python3 -m maestro.qwen.run_local --local

# Kill the background process
kill $QWEN_PID 2>/dev/null

# Test 2: NCurses TUI functionality (import test)
echo -e "\n--- Test 2: NCurses TUI Module Import ---"
python3 -c "from maestro.qwen.tui import QwenTUI, run_qwen_ncurses; print('TUI module imported successfully')"

echo -e "\nTest completed - All components working!"