#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-13: Read-only to adopt bridge
# This runbook shows read-only inspection followed by adoption.

# Step 1: Start in read-only mode
run maestro init --readonly
# EXPECT: Initializes read-only mode and uses home hub storage
# STORES_WRITE: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm read-only initialization command

# Step 2: Resolve in read-only mode
run maestro repo resolve --level lite --readonly
# EXPECT: Writes resolve results to home hub storage
# STORES_WRITE: HOME_HUB_REPO
# GATES: REPO_RESOLVE_LITE, READONLY_GUARD
# INTERNAL: UNKNOWN

# Step 3: Optional diagnostic build
run maestro make build --dry-run
# EXPECT: Performs a dry-run build without repo writes
# STORES_READ: HOME_HUB_REPO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm build command and dry-run flag

# Step 4: Adopt the repository
run maestro init
# EXPECT: Creates repo truth structure under ./docs/maestro/
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Re-run resolve into repo truth
run maestro repo resolve --level lite
# EXPECT: Writes resolve results to repo truth
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 6: Verify RepoConf presence
run maestro repo conf show
# EXPECT: Shows RepoConf after adoption
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm RepoConf inspection command

# Step 7: Proceed with build
run maestro make build
# EXPECT: Builds using repo truth configuration
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
