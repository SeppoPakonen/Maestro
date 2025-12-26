#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-15: Work <-> wsession cookie protocol
# This runbook shows cookie-based messaging between work and wsession.

# Step 1: Start a work session
run maestro work
# EXPECT: Creates a session cookie and inbox
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_REQUIRED
# INTERNAL: UNKNOWN

# Step 2: Send a breadcrumb into the session inbox
run maestro wsession log --cookie "<session_id>" --message "status ping"
# EXPECT: Writes a breadcrumb message for the session
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_REQUIRED
# INTERNAL: UNKNOWN
# TODO: Confirm the correct wsession log command

# Step 3: Poll the inbox for breadcrumbs
run maestro wsession list --cookie "<session_id>"
# EXPECT: Lists breadcrumbs waiting to be processed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_REQUIRED
# INTERNAL: UNKNOWN
# TODO: Confirm the correct wsession list command

# Step 4: Acknowledge a processed breadcrumb
run maestro wsession ack --cookie "<session_id>" --breadcrumb "<id>"
# EXPECT: Marks a breadcrumb as processed
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_REQUIRED
# INTERNAL: UNKNOWN
# TODO: Confirm the correct ack command
