#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; }

# Preconditions:
# - Repo truth is JSON under ./docs/maestro/**
# - Repo initialized
# - Sample runbooks and workflows exist

run maestro init
# EXPECT: repo truth created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Step 1: List active runbooks (both types)
run maestro runbook list
# EXPECT: shows only active runbooks (JSON and markdown)
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 2: Archive a JSON runbook by ID
run maestro runbook archive RB-001 --reason "Superseded by v2"
# EXPECT: runbook moved to archived/<YYYYMMDD>/
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_IDEMPOTENCY

# Step 3: Archive a markdown runbook example by path
run maestro runbook archive docs/workflows/v3/runbooks/examples/EX-01_old_example.sh --reason "Outdated approach"
# EXPECT: example moved to archived/<YYYYMMDD>/
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_IDEMPOTENCY

# Step 4: List active runbooks - verify archived items excluded
run maestro runbook list
# EXPECT: RB-001 and EX-01 not shown in default list
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_DEFAULT_LISTING

# Step 5: List archived runbooks
run maestro runbook list --archived
# EXPECT: shows RB-001 and EX-01 with archive IDs
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 6: Filter archived runbooks by type
run maestro runbook list --archived --type json
# EXPECT: shows only JSON runbook (RB-001)
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 7: Show archived runbook
run maestro runbook show RB-001 --archived
# EXPECT: displays archived runbook content and metadata
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 8: Attempt to archive same item twice (should fail)
run maestro runbook archive RB-001 --reason "Testing idempotency"
# EXPECT: error - already archived
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_IDEMPOTENCY

# Step 9: Restore archived runbook
run maestro runbook restore <ARCHIVE_ID>
# EXPECT: runbook moved back to original location
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: RESTORE_PATH_OCCUPIED

# Step 10: List workflows
run maestro workflow list
# EXPECT: shows only active workflows
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_DEFAULT_LISTING

# Step 11: Archive a workflow file
run maestro workflow archive docs/workflows/v3/workflows/WF-OLD.md --reason "Legacy workflow"
# EXPECT: workflow moved to archived/<YYYYMMDD>/
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: ARCHIVE_IDEMPOTENCY

# Step 12: List archived workflows
run maestro workflow list --archived
# EXPECT: shows WF-OLD.md with archive ID
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 13: Show archived workflow
run maestro workflow show docs/workflows/v3/workflows/WF-OLD.md --archived
# EXPECT: displays archived workflow content and metadata
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Step 14: Restore workflow
run maestro workflow restore <WORKFLOW_ARCHIVE_ID>
# EXPECT: workflow moved back to original location
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: RESTORE_PATH_OCCUPIED

# Step 15: Verify restore - list active workflows
run maestro workflow list
# EXPECT: WF-OLD.md appears in active list
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# /done would return JSON OPS in discuss mode
