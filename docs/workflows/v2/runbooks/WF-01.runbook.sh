#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-01: Existing repo, adopt + analyze + build/run
# This runbook demonstrates the workflow for adopting an existing repository,
# analyzing it, building it, and running it.

# Step 1: Initialize the maestro environment
run maestro init
# EXPECT: Initializes the maestro environment in the current directory
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Check if init is needed or if resolve automatically initializes

# Step 2: Resolve the repository structure (lite version)
run maestro repo resolve --level lite
# EXPECT: Discovers repository structure, build system, and dependencies
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 3: Handle repository configuration (validate/show/select default target)
run maestro repo config --show
# EXPECT: Shows current repository configuration
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Determine the exact command for repository configuration

# Step 4: Build the project
run maestro build
# EXPECT: Builds the project using detected build system
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if 'maestro build' is the correct command or if it's 'maestro make'

# Step 5: Run the binary and check for errors
run maestro run --grep-errors
# EXPECT: Runs the built binary and optionally checks for errors
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Determine the correct command for running the built binary

# Step 6: Create issues/tasks if needed
run maestro issue create --title "Initial analysis completed" --description "Repository analysis and initial build completed"
# EXPECT: Creates an issue to track the initial adoption
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Issue creation command may vary