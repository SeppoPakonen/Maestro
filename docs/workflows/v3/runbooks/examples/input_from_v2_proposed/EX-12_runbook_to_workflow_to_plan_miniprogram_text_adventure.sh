#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-12: Micro "Game Loop" (Text Adventure) — Runbook→Workflow→Plan→Minimal Code

# Step 1: Initialize Maestro
run maestro init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create Runbook for Game Experience
run maestro runbook add --title "Text Adventure Game Loop" --scope product --tag game --tag greenfield
# EXPECT: Runbook text-adventure-game-loop.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3: Add Runbook Steps (Player Journey)
run maestro runbook step-add text-adventure-game-loop --actor manager --action "Define goal: minimal playable text adventure" --expected "Goal documented"
# EXPECT: Manager intent step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor user --action "Run: python adventure.py" --expected "Game starts, shows starting room description"
# EXPECT: User intent (start) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor user --action "Type: look" --expected "Displays room description and available exits"
# EXPECT: User intent (look) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor user --action "Type: go north" --expected "Player moves to forest, new room description shown"
# EXPECT: User intent (move) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor user --action "Type: take key" --expected "Key added to inventory"
# EXPECT: User intent (take item) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor user --action "Type: inventory" --expected "Shows: 'You are carrying: key'"
# EXPECT: User intent (check inventory) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor system --action "Parse user command (look/go/take), update world state" --expected "Command processed, state updated"
# EXPECT: Interface layer (game loop) step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add text-adventure-game-loop --actor ai --action "Implement adventure.py with rooms dict and command parser" --expected "Game loop functional"
# EXPECT: Code layer step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Export Runbook
run maestro runbook export text-adventure-game-loop --format md
# EXPECT: Markdown printed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 5: Create Workflow from Runbook
run maestro workflow init game-loop-workflow --from-runbook text-adventure-game-loop  # TODO_CMD
# EXPECT: Workflow JSON created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6: Add Workflow Nodes (Layered — Game Loop as Interface)
run maestro workflow node add game-loop-workflow --layer manager_intent --label "Goal: minimal playable adventure"  # TODO_CMD
run maestro workflow node add game-loop-workflow --layer user_intent --label "Player explores rooms, takes items"  # TODO_CMD
run maestro workflow node add game-loop-workflow --layer interface --label "Game loop: parse commands, update world state"  # TODO_CMD
run maestro workflow node add game-loop-workflow --layer code --label "adventure.py: rooms dict + command parser"  # TODO_CMD
# EXPECT: Workflow nodes added (layered, interface = game loop)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Validate Workflow
run maestro workflow validate game-loop-workflow  # TODO_CMD
# EXPECT: Validation passes
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 8: Create Track
run maestro track add "Sprint 1: Text Adventure MVP" --start 2025-01-01
# EXPECT: Track track-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 9: Create Phase
run maestro phase add track-001 "P1: Implement Game Loop"
# EXPECT: Phase phase-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 10: Create Task
run maestro task add phase-001 "Implement adventure.py with rooms and commands"
# EXPECT: Task task-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 11: Start Work Session
run maestro work task task-001
# EXPECT: Work session created, AI has runbook/workflow context
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 12: AI Implements Code (simulated - creates adventure.py)
echo ""
echo "# AI generates adventure.py with rooms dict and command parser"

# Step 13: Test Implementation
run python adventure.py
# EXPECT: Game starts, shows starting room
# (Interactive session would follow - omitted in dry-run)

# Step 14: Complete Task
run maestro task complete task-001  # TODO_CMD
# EXPECT: Task status → completed
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-12 Outcome A: Text adventure game loop modeled, implemented, playable"
echo "Runbook: ./docs/maestro/runbooks/text-adventure-game-loop.json"
echo "Workflow: ./docs/maestro/workflows/game-loop-workflow.json"
echo "Code: adventure.py (playable with look/go/take/inventory commands)"
echo "Key insight: Interface layer is the game loop, not CLI args"
