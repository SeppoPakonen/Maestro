#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# EX-01: C++ CMake Existing Repo — Adopt, Build, Reactive Error, Solution Trial
# This example demonstrates adopting an existing C++ CMake project, encountering
# a compile error (missing #include <iostream>), matching it to a solution,
# and applying the fix.

# Step 1: Initialize Maestro in the existing repo
run "$MAESTRO_BIN" init
# EXPECT: Creates ./docs/maestro/** structure, detects existing project
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Resolve repository structure (lite mode - detect build system)
run "$MAESTRO_BIN" repo resolve
# EXPECT: Detects CMakeLists.txt, identifies C++ source files, finds include paths
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 3: Show detected repository configuration
run "$MAESTRO_BIN" repo conf show
# EXPECT: Displays detected build system (CMake), targets (my_app), compiler
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# Step 4: Attempt to build (will fail due to missing include)
run "$MAESTRO_BIN" make
# EXPECT: Build fails with compile error: src/main.cpp:4 - 'std::cout' not declared
# STORES_WRITE: (none - build fails before completion)
# GATES: READONLY_GUARD (fails)
# INTERNAL: UNKNOWN
# Step 5: Match error against solution database
run "$MAESTRO_BIN" solutions match --from-build-log build.log
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0006)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (creates issue entry)
# GATES: SOLUTIONS_GATE
# INTERNAL: UNKNOWN

# Step 6: Create issue from matched solution
run "$MAESTRO_BIN" issues add --from-solution solution-12345
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0007)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Create task to apply the solution
run "$MAESTRO_BIN" task add --issue issue-001 --action apply-solution
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0008)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 8: Execute task (apply solution - add include directive)
run "$MAESTRO_BIN" work task task-001
# EXPECT: File src/main.cpp modified, #include <iostream> added at line 1
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD (write)
# INTERNAL: UNKNOWN
# TODO: May need user confirmation before file edit

# Step 9: Retry build (should succeed now)
run "$MAESTRO_BIN" make
# EXPECT: Build succeeds, binary created at build/my_app
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

echo ""
echo "EX-01 Outcome A: Build succeeded after auto-solution applied"
echo "Binary: build/my_app"
echo "Issue: ./docs/maestro/issues/issue-001.json (status: resolved)"
echo "Task: ./docs/maestro/tasks/task-001.json (status: completed)"
