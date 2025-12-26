#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-14: Branch safety guardrails
# This runbook demonstrates the branch-bound work session constraint.

# Step 1: Start a work session
run maestro work
# EXPECT: Starts a work session and stores branch identity snapshot
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: GIT_REPO_GATE
# INTERNAL: UNKNOWN

# Step 2: Switch branches (unsupported during active work)
run git checkout feature/other-branch
# EXPECT: Branch identity changes while work session is active
# GATES: BRANCH_SWITCH_FORBIDDEN
# INTERNAL: UNKNOWN

# Step 3: Attempt to resume work session
run maestro work --resume "<session_id>"
# EXPECT: Hard stop due to branch mismatch
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: BRANCH_IDENTITY_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the correct resume flag
