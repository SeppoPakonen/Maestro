#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-09: Greenfield "Hello CLI" in Python — Runbook→Workflow→Plan→Implemented Code

# Step 1: Initialize Maestro
run maestro init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create Runbook (Narrative First)
run maestro runbook add --title "Hello CLI Tool" --scope product --tag greenfield
# EXPECT: Runbook hello-cli-tool.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3: Add Runbook Steps (User Journey)
run maestro runbook step-add hello-cli-tool --actor manager --action "Define product goal: simple greeting CLI" --expected "Goal documented"
# EXPECT: Step 1 added (manager intent)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add hello-cli-tool --actor user --action "Run: hello --name Alice" --expected "Prints: Hello, Alice!"
# EXPECT: Step 2 added (user intent)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add hello-cli-tool --actor user --action "Run: hello (no args)" --expected "Prints: Hello, World!"
# EXPECT: Step 3 added (default behavior)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add hello-cli-tool --actor system --action "Parse CLI args using argparse" --expected "Arguments extracted"
# EXPECT: Step 4 added (interface layer)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add hello-cli-tool --actor ai --action "Implement hello.py with argparse" --expected "Code written and tested"
# EXPECT: Step 5 added (code layer)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Export Runbook to Markdown
run maestro runbook export hello-cli-tool --format md
# EXPECT: Markdown document printed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 5: Create Workflow Graph from Runbook
run maestro workflow init hello-cli-workflow --from-runbook hello-cli-tool  # TODO_CMD
# EXPECT: Workflow JSON created with nodes per layer
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6-7: Add Workflow Nodes and Edges
run maestro workflow node add hello-cli-workflow --layer manager_intent --label "Product goal: greeting CLI"  # TODO_CMD
run maestro workflow node add hello-cli-workflow --layer user_intent --label "User runs hello --name X"  # TODO_CMD
run maestro workflow node add hello-cli-workflow --layer interface --label "CLI: argparse parser"  # TODO_CMD
run maestro workflow node add hello-cli-workflow --layer code --label "hello.py main()"  # TODO_CMD
# EXPECT: Nodes added to workflow graph
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro workflow edge add hello-cli-workflow --from manager_intent_001 --to user_intent_001  # TODO_CMD
run maestro workflow edge add hello-cli-workflow --from user_intent_001 --to interface_001  # TODO_CMD
run maestro workflow edge add hello-cli-workflow --from interface_001 --to code_001  # TODO_CMD
# EXPECT: Edges linking layers added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 8: Validate and Render Workflow
run maestro workflow validate hello-cli-workflow  # TODO_CMD
# EXPECT: Validation passes
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

run maestro workflow render hello-cli-workflow --format puml  # TODO_CMD
# EXPECT: .puml and .svg created
# STORES_WRITE: (exports directory)
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 9: Create Track
run maestro track add "Sprint 1: Hello CLI" --start 2025-01-01
# EXPECT: Track track-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 10: Create Phase
run maestro phase add track-001 "P1: Implement Core"
# EXPECT: Phase phase-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 11: Create Task
run maestro task add phase-001 "Implement hello.py with argparse"
# EXPECT: Task task-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 12: Start Work Session
run maestro work task task-001
# EXPECT: Work session cookie created, AI context loaded
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 13: AI Updates Breadcrumbs (during work)
run maestro wsession breadcrumb task-001 --cookie '<cookie>' --status "Implementing argparse parser"  # TODO_CMD
# EXPECT: Breadcrumb updated in IPC mailbox
# STORES_WRITE: IPC_MAILBOX
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 14: Test Implementation (manual or via work session)
run python hello.py --name Alice
# EXPECT: Prints: Hello, Alice!

run python hello.py
# EXPECT: Prints: Hello, World!

# Step 15: Complete Task
run maestro task complete task-001  # TODO_CMD
# EXPECT: Task status → completed
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-09 Outcome A: Runbook→Workflow→Plan→Code complete"
echo "Runbook: ./docs/maestro/runbooks/hello-cli-tool.json"
echo "Workflow: ./docs/maestro/workflows/hello-cli-workflow.json"
echo "Task: ./docs/maestro/tasks/task-001.json (status: completed)"
echo "Code: hello.py (working)"
