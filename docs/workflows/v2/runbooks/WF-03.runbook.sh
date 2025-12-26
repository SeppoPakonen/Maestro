#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-03: Read-only repo inspection + build detection
# This runbook demonstrates inspecting a repository in read-only mode, with all writes going to HOME_HUB_REPO.

# Step 1: Initialize the maestro environment in read-only mode
run maestro init --readonly
# EXPECT: Initializes the maestro environment with read-only settings
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if --readonly flag exists or if read-only mode is set differently

# Step 2: Resolve the repository structure in read-only mode
run maestro repo resolve --level lite --readonly
# EXPECT: Discovers repository structure without modifying repo truth
# STORES_WRITE: HOME_HUB_REPO
# GATES: REPO_RESOLVE_LITE, READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if --readonly flag exists for repo resolve

# Step 3: Scan for build system in read-only mode
run maestro scan build
# EXPECT: Detects build system without modifying project files
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Determine the correct command for build system detection in read-only mode

# Step 4: Analyze dependencies without modifying repo truth
run maestro analyze deps --readonly
# EXPECT: Analyzes project dependencies without writing to repo truth
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if --readonly flag exists for dependency analysis

# Step 5: Attempt build without writing to repo truth
run maestro build --dry-run
# EXPECT: Simulates build process without making changes
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm if --dry-run flag exists or if there's another way to do read-only builds