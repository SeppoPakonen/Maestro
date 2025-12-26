#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-02: Greenfield new project with manual plan
# This runbook demonstrates creating a new project from scratch with a manually authored plan.

# Step 1: Initialize the maestro environment for a new project
run maestro init
# EXPECT: Initializes the maestro environment in the current directory
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create a new track manually
run maestro track add --name "initial-development" --description "Initial development track for new project"
# EXPECT: Creates a new track to organize related work
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3: Create a phase within the track
run maestro phase add --track "initial-development" --name "setup" --description "Project setup phase"
# EXPECT: Creates a new phase within the specified track
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Add tasks to the phase
run maestro task add --phase "setup" --title "Create project structure" --description "Set up basic directory structure and initial files"
# EXPECT: Creates a new task within the specified phase
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Add another task
run maestro task add --phase "setup" --title "Configure build system" --description "Set up build configuration files"
# EXPECT: Creates another task in the phase
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6: Work on a specific task (placeholder for current equivalent)
run maestro work task --id "TASK-001"
# EXPECT: Begins working on the specified task, potentially starting an AI session
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN
# TODO: Determine the exact command for working on a task

# Step 7: Resolve repository structure (to establish build system)
run maestro repo resolve --level lite
# EXPECT: Discovers and sets up build system for the new project
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 8: Build the project
run maestro build
# EXPECT: Builds the project based on the configured build system
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if 'maestro build' is the correct command