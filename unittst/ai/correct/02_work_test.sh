#!/bin/bash
# Unit Test 2: Work-test
# Objective: Verify the work feature with breadcrumbs and AI synchronization

# Setup:
# - Remove ./tmp directory if it exists
# - Create a fresh ./tmp directory in the project root
# - Verify that ./tmp is listed in .gitignore (it should be already)
# - The point is to use "python ../maestro.py" from the ./tmp directory

# USER: Remove tmp directory if it exists and create fresh one
rm -rf tmp
mkdir tmp
cd tmp

# USER: Initialize the project
../maestro.py init

# USER: Create a track, phase and task using maestro.py
../maestro.py track add "scientific-calculator" "Track for building a scientific calculator CLI"
../maestro.py phase add "scientific-calculator" "implementation" "Implementation phase for the scientific calculator"

# USER: Create tasks for each of the 5 points
../maestro.py task add "Implement basic calculation function" --phase implementation --id calc-basic
../maestro.py task add "Add input validation" --phase implementation --id calc-validation
../maestro.py task add "Create output formatting" --phase implementation --id calc-formatting
../maestro.py task add "Add error handling" --phase implementation --id calc-error-handling
../maestro.py task add "Optimize performance" --phase implementation --id calc-optimization

# USER: Define 5 points for the task (foobar points - be creative):
# Point A: Implement basic calculation function
# Point B: Add input validation
# Point C: Create output formatting
# Point D: Add error handling
# Point E: Optimize performance

# AI: Execute work on the track which should handle all tasks including our 5 points
# The AI should automatically create breadcrumbs between each point and use ai sync
../maestro.py work track scientific-calculator

# AI: Display breadcrumbs after working on the track
# Check if session command supports breadcrumbs functionality
if ../maestro.py session --help | grep -q "breadcrumbs\|wsession"; then
    # If wsession breadcrumbs command is available
    if ../maestro.py --help | grep -q "wsession"; then
        ../maestro.py wsession breadcrumbs --summary latest
    else
        # Otherwise try session breadcrumbs if available
        ../maestro.py session breadcrumbs --summary latest
    fi
else
    # If no specific breadcrumb command, check session list to see created sessions
    ../maestro.py session list
fi

# AI: Display session timeline to show breadcrumb progression
if ../maestro.py --help | grep -q "wsession"; then
    ../maestro.py wsession timeline latest
elif ../maestro.py session --help 2>/dev/null | grep -q "timeline"; then
    ../maestro.py session timeline latest
else
    echo "Timeline command not available, checking sessions directory directly"
    find docs/sessions -name "*.json" -type f | head -10
fi

# AI: Check session statistics to verify work completion
if ../maestro.py --help | grep -q "wsession"; then
    ../maestro.py wsession stats latest
elif ../maestro.py session --help 2>/dev/null | grep -q "stats"; then
    ../maestro.py session stats latest
else
    echo "Stats command not available"
fi

# AI: Show detailed session information
if ../maestro.py --help | grep -q "wsession"; then
    ../maestro.py wsession show latest
elif ../maestro.py session list 2>/dev/null; then
    ../maestro.py session show latest
else
    echo "Show command not available"
fi

# AI: After completing all 5 points, AI should respond as JSON using internal ai sync
# This happens automatically as part of the work process
../maestro.py ai sync

# AI: Display all breadcrumbs, responses, and AI synchronizations
# Use the session command to see the recorded interactions (if available)
# If the wsession command is not available, we'll check the sessions directory directly
if ../maestro.py session --help | grep -q "list"; then
    ../maestro.py session list
else
    echo "Session command not available, checking docs/sessions directly"
    find docs/sessions -name "*.json" -type f | head -10
fi

# Expected Success Criteria:
# - Breadcrumbs are properly recorded between each point
# - AI responds with JSON after the 5th point
# - The command to display breadcrumbs shows all recorded breadcrumbs and responses
# - AI synchronization works as expected