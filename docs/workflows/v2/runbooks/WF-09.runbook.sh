#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-09: Storage contract - repo truth vs home hub
# This runbook highlights storage selection and the ./.maestro hard stop.

# Step 1: Enter read-only mode (home hub storage)
run maestro init --readonly
# EXPECT: Initializes maestro in read-only mode and targets home hub storage
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN
# TODO: Confirm the correct read-only initialization command

# Step 2: Resolve repo structure in read-only mode
run maestro repo resolve --level lite --readonly
# EXPECT: Writes resolve results to home hub storage
# STORES_WRITE: HOME_HUB_REPO
# GATES: REPO_RESOLVE_LITE, READONLY_GUARD, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN

# Step 3: Read issues from home hub
run maestro issue list --readonly
# EXPECT: Reads issue data from home hub storage
# STORES_READ: HOME_HUB_REPO
# GATES: READONLY_GUARD, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN
# TODO: Confirm the correct issue listing command in read-only mode

# Step 4: Adopt the repository (repo truth storage)
run maestro init
# EXPECT: Initializes repo truth storage under ./docs/maestro/
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN

# Step 5: Resolve repo structure for repo truth
run maestro repo resolve --level lite
# EXPECT: Writes resolve results to repo truth storage
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN

# Step 6: Read tasks from repo truth
run maestro task list
# EXPECT: Reads task data from repo truth storage
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE, FORBID_DOT_MAESTRO
# INTERNAL: UNKNOWN
# TODO: Confirm the correct task listing command
