#!/bin/bash
# Unit Test 1: Init-test
# Objective: Verify basic maestro initialization and track/phase/task creation

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

# USER: Add tracks, phases and tasks to create a simple CLI program for scientific calculation
../maestro.py track add "scientific-calculator" "Track for building a scientific calculator CLI"

# USER: Add a phase for the scientific calculator track
../maestro.py phase add "scientific-calculator" "planning" "Planning phase for the scientific calculator"

# USER: Add tasks for the planning phase
../maestro.py task add "scientific-calculator" "planning" "research-existing-solutions" "Research existing scientific calculator CLI solutions"
../maestro.py task add "scientific-calculator" "planning" "define-features" "Define features for the scientific calculator"
../maestro.py task add "scientific-calculator" "planning" "design-architecture" "Design the architecture for the calculator"

# USER: Add another phase
../maestro.py phase add "scientific-calculator" "implementation" "Implementation phase for the scientific calculator"

# USER: Add tasks for the implementation phase
../maestro.py task add "scientific-calculator" "implementation" "setup-project-structure" "Set up the project structure"
../maestro.py task add "scientific-calculator" "implementation" "implement-core-functions" "Implement core calculation functions"
../maestro.py task add "scientific-calculator" "implementation" "create-cli-interface" "Create CLI interface"

# USER: Verify that the commands work correctly by listing tracks, phases and tasks
../maestro.py track list
../maestro.py phase list "scientific-calculator"
../maestro.py task list "scientific-calculator" "planning"
../maestro.py task list "scientific-calculator" "implementation"

# USER: Mark some tasks as done
../maestro.py task done "scientific-calculator" "planning" "research-existing-solutions"
../maestro.py task done "scientific-calculator" "planning" "define-features"

# USER: Verify that the tasks were marked as done
../maestro.py task list "scientific-calculator" "planning"

# Expected Success Criteria:
# - All commands execute without errors
# - Track/phase/task lists show the items that were created
# - Tracks, phases and tasks can be marked as done successfully