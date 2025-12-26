#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-06: AI task work sessions + wsession breadcrumb
# This runbook demonstrates AI-assisted work sessions with session tracking and breadcrumbs.

# Step 1: Start working on a task that creates a cookie/run ID
run maestro work task --id "TASK-001"
# EXPECT: Begins working on the specified task, creating a work session with cookie/run ID
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for starting AI-assisted work on a task

# Step 2: The AI prompt includes the cookie
run maestro ai prompt --with-cookie "TASK-001_COOKIE"
# EXPECT: Sends AI prompt that includes the work session cookie
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN
# TODO: Determine the exact command for AI prompting with cookies

# Step 3: AI calls wsession breadcrumb to track progress
run maestro wsession breadcrumb --cookie "TASK-001_COOKIE" --message "Started investigating the issue"
# EXPECT: Records a breadcrumb in the work session to track progress
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN

# Step 4: AI continues work and adds more breadcrumbs
run maestro wsession breadcrumb --cookie "TASK-001_COOKIE" --message "Identified the root cause"
# EXPECT: Records another breadcrumb in the work session
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN

# Step 5: AI completes the task
run maestro wsession complete --cookie "TASK-001_COOKIE"
# EXPECT: Marks the work session as complete
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for completing a work session

# Step 6: Multi-session resume (placeholder)
run maestro wsession resume --id "SESSION-001"
# EXPECT: Resumes a previous work session if needed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: WSESSION_COOKIE_GATE
# INTERNAL: UNKNOWN
# TODO: Determine the exact command for resuming work sessions

# Note: IPC communication assumed to be file-based
# STORES_WRITE: IPC_MAILBOX