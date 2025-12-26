#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-16: wsession modes (log-only vs mutation)
# This runbook shows opt-in mutation and default log-only behavior.

# Step 1: Start a work session with mutation enabled
run maestro work-run --enable-mutation
# EXPECT: Creates a work session with mutation capability
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_MUTATION_MODE_OPTIN
# INTERNAL: UNKNOWN
# TODO: Confirm the mutation enable flag

# Step 2: Send a log-only breadcrumb
run maestro wsession log --cookie "<session_id>" --message "status only"
# EXPECT: Writes a log-only breadcrumb
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_REQUIRED
# INTERNAL: UNKNOWN

# Step 3: Apply a mutation operation
run maestro wsession mutate --cookie "<session_id>" --operation "task.add" --payload '{"title":"Bootstrap"}'
# EXPECT: Applies a state mutation with audit logging
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_MUTATION_MODE_OPTIN, BRANCH_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm mutation command and payload schema

# Step 4: Demonstrate schema rejection
run maestro wsession mutate --cookie "<session_id>" --operation "task.add" --payload '{}'
# EXPECT: Rejects invalid mutation schema
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_MUTATION_MODE_OPTIN, OP_SCHEMA_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm schema validation gate name
