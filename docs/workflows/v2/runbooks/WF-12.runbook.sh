#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-12: RepoConf gate for build, TU, and convert
# This runbook ensures RepoConf exists and is valid before operations.

# Step 1: Resolve repository to generate RepoConf candidates
run maestro repo resolve --level lite
# EXPECT: Generates RepoConf candidates from repository scan
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 2: Add a RepoConf target
run maestro repo conf target add "app" --type exe --package "core"
# EXPECT: Creates a target entry in RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm repo conf target add syntax

# Step 3: Set the default target
run maestro repo conf set-default-target "app"
# EXPECT: Stores default target selection in RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Show RepoConf to confirm validity
run maestro repo conf show
# EXPECT: Displays RepoConf content for validation
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the correct command for RepoConf inspection

# Step 5: Build using RepoConf
run maestro build --target "app"
# EXPECT: Builds the selected target with RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6: Generate TU/AST
run maestro tu --package "core"
# EXPECT: Generates TU/AST using RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Run conversion pipeline
run maestro convert run --pipeline "example"
# EXPECT: Runs conversion using RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the convert run command syntax
