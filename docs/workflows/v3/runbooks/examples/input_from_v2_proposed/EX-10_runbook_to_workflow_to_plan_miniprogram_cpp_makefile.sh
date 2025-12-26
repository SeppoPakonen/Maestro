#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-10: Tiny C++ Single-File Program + Makefile — Runbook→Workflow→Plan→Build→Run

# Step 1: Initialize Maestro
run maestro init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create Runbook
run maestro runbook add --title "C++ Hello Program" --scope product --tag greenfield --tag cpp
# EXPECT: Runbook c-hello-program.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3: Add Runbook Steps (Build & Execute Flow)
run maestro runbook step-add c-hello-program --actor manager --action "Define goal: minimal C++ program that prints greeting" --expected "Goal documented"
# EXPECT: Step 1 added (manager intent)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add c-hello-program --actor user --action "Run: make" --expected "Compiles successfully, creates ./hello binary"
# EXPECT: Step 2 added (user intent - build)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add c-hello-program --actor user --action "Run: ./hello" --expected "Prints: Hello from C++!"
# EXPECT: Step 3 added (user intent - execute)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add c-hello-program --actor system --action "Detect Makefile, invoke g++ with -std=c++17" --expected "Compilation successful"
# EXPECT: Step 4 added (interface layer - build)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add c-hello-program --actor ai --action "Write main.cpp with iostream, string" --expected "Code compiles cleanly"
# EXPECT: Step 5 added (code layer)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Export Runbook
run maestro runbook export c-hello-program --format md
# EXPECT: Markdown printed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 5: Create Workflow from Runbook
run maestro workflow init hello-cpp-workflow --from-runbook c-hello-program  # TODO_CMD
# EXPECT: Workflow JSON created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6: Add Workflow Nodes (Layered)
run maestro workflow node add hello-cpp-workflow --layer manager_intent --label "Goal: minimal C++ greeting"  # TODO_CMD
run maestro workflow node add hello-cpp-workflow --layer user_intent --label "User runs make; then ./hello"  # TODO_CMD
run maestro workflow node add hello-cpp-workflow --layer interface --label "Build: Makefile + g++"  # TODO_CMD
run maestro workflow node add hello-cpp-workflow --layer code --label "main.cpp: iostream + cout"  # TODO_CMD
# EXPECT: Nodes added to workflow graph
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Validate Workflow
run maestro workflow validate hello-cpp-workflow  # TODO_CMD
# EXPECT: Validation passes
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 8: Create Track
run maestro track add "Sprint 1: C++ Hello" --start 2025-01-01
# EXPECT: Track track-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 9: Create Phase
run maestro phase add track-001 "P1: Implement and Build"
# EXPECT: Phase phase-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 10: Create Task
run maestro task add phase-001 "Write main.cpp and Makefile"
# EXPECT: Task task-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 11: Resolve Repository (Detect Build System)
run maestro repo resolve --level lite  # TODO_CMD
# EXPECT: Build system: Make, Language: C++
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 12: Start Work Session
run maestro work task task-001
# EXPECT: Work session created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 13: AI Implements Code (simulated - creates main.cpp and Makefile)
echo ""
echo "# AI would generate main.cpp (possibly with intentional error - missing #include <string>)"

# Step 14: Build (First Attempt)
run maestro build
# EXPECT: Compilation may fail if error present
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

# Step 15: Match Solution (Error Recovery)
run maestro solutions match --from-build-log  # TODO_CMD
# EXPECT: Suggests "Add #include <string>"
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: SOLUTIONS_GATE
# INTERNAL: UNKNOWN

# Step 16: Create Issue
run maestro issues add --type build --desc "Missing include: <string>"  # TODO_CMD
# EXPECT: Issue issue-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 17: Apply Fix (AI or user adds #include <string>)
echo ""
echo "# Fix applied: add #include <string> to main.cpp"

# Step 18: Build (Retry)
run maestro build
# EXPECT: Compilation succeeds, ./hello created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

# Step 19: Test
run ./hello
# EXPECT: Prints: "Hello from C++!"

# Step 20: Complete Task
run maestro task complete task-001  # TODO_CMD
# EXPECT: Task status → completed
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-10 Outcome B: Compile error detected, solution matched, fix applied, build succeeds"
echo "Runbook: ./docs/maestro/runbooks/c-hello-program.json"
echo "Workflow: ./docs/maestro/workflows/hello-cpp-workflow.json"
echo "Issue: ./docs/maestro/issues/issue-001.json (status: resolved)"
echo "Binary: ./hello (working)"
