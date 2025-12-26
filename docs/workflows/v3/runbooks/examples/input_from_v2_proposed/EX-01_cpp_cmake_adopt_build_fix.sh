#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# EX-01: C++ CMake Existing Repo — Adopt, Build, Reactive Error, Solution Trial
# This example demonstrates adopting an existing C++ CMake project, encountering
# a compile error (missing #include <iostream>), matching it to a solution,
# and applying the fix.

# Step 1: Initialize Maestro in the existing repo
run maestro init
# EXPECT: Creates ./docs/maestro/** structure, detects existing project
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Resolve repository structure (lite mode - detect build system)
run maestro repo resolve --level lite
# EXPECT: Detects CMakeLists.txt, identifies C++ source files, finds include paths
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 3: Show detected repository configuration
run maestro repo conf --show  # TODO_CMD: exact syntax uncertain
# EXPECT: Displays detected build system (CMake), targets (my_app), compiler
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO_CMD: May be 'repo config show' or 'repo show-config'

# Step 4: Attempt to build (will fail due to missing include)
run maestro build  # TODO_CMD: confirm if 'build' vs 'make'
# EXPECT: Build fails with compile error: src/main.cpp:4 - 'std::cout' not declared
# STORES_WRITE: (none - build fails before completion)
# GATES: READONLY_GUARD (fails)
# INTERNAL: UNKNOWN
# TODO_CMD: Command name uncertain, may be 'maestro make' or 'maestro compile'

# Step 5: Match error against solution database
run maestro solutions match --from-build-log  # TODO_CMD: syntax uncertain
# EXPECT: Suggests "Missing include directive: #include <iostream>"
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (creates issue entry)
# GATES: SOLUTIONS_GATE
# INTERNAL: UNKNOWN
# TODO_CMD: May need build log file path, or auto-detects last build

# Step 6: Create issue from matched solution
run maestro issues add --from-solution solution-12345  # TODO_CMD: syntax uncertain
# EXPECT: Issue created: "Fix missing <iostream> include in src/main.cpp"
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO_CMD: Link between solution ID and issue creation unclear

# Step 7: Create task to apply the solution
run maestro task add --issue issue-001 --action apply-solution  # TODO_CMD: syntax uncertain
# EXPECT: Task created with action: "Add #include <iostream> to src/main.cpp:1"
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO_CMD: Task-issue-solution linkage not finalized

# Step 8: Execute task (apply solution - add include directive)
run maestro work task task-001  # TODO_CMD: confirm work task syntax
# EXPECT: File src/main.cpp modified, #include <iostream> added at line 1
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD (write)
# INTERNAL: UNKNOWN
# TODO: May need user confirmation before file edit

# Step 9: Retry build (should succeed now)
run maestro build  # TODO_CMD: confirm if 'build' vs 'make'
# EXPECT: Build succeeds, binary created at build/my_app
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

echo ""
echo "EX-01 Outcome A: Build succeeded after auto-solution applied"
echo "Binary: build/my_app"
echo "Issue: ./docs/maestro/issues/issue-001.json (status: resolved)"
echo "Task: ./docs/maestro/tasks/task-001.json (status: completed)"
