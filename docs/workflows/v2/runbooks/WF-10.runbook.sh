#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-10: Repo resolve levels and convention policy
# This runbook demonstrates lite vs deep resolve and convention acceptance/waiver flow.

# Step 1: Lite resolve
run maestro repo resolve --level lite
# EXPECT: Fast scan to detect build drivers and targets
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 2: Deep resolve
run maestro repo resolve --level deep
# EXPECT: Deep scan to infer conventions and violations
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_DEEP
# INTERNAL: UNKNOWN
# TODO: Confirm the deep resolve flag

# Step 3: List inferred convention packs
run maestro conventions list
# EXPECT: Lists proposed convention packs
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm conventions command namespace

# Step 4: Review proposed conventions
run maestro conventions review
# EXPECT: Presents conventions for acceptance
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Accept a convention pack
run maestro conventions accept --pack "default"
# EXPECT: Stores accepted convention pack
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm how conventions are accepted

# Step 6: Check violations
run maestro conventions check
# EXPECT: Detects violations against accepted conventions
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Create issues for violations
run maestro issue create --title "Convention violations" --description "Violations detected during deep resolve"
# EXPECT: Creates issues for detected violations
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 8: Waive a violation (policy override)
run maestro conventions waive --id "VIOL-001" --reason "Legacy layout"
# EXPECT: Records a waiver for a blocking violation
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the correct waiver command
