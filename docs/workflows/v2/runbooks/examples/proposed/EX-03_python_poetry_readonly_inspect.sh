#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-03: Python Poetry Read-Only Inspection — No Repo Writes

# Step 1: Resolve repo in read-only mode
run maestro repo resolve --readonly  # TODO_CMD: confirm --readonly flag
# EXPECT: Detects Poetry, Python 3.11, FastAPI deps
# STORES_WRITE: HOME_HUB_REPO (NOT repo truth)
# STORES_READ: (none)
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 2: Show detected packages
run maestro repo show packages  # TODO_CMD: exact command uncertain
# EXPECT: Lists fastapi, uvicorn, python=^3.11
# STORES_READ: HOME_HUB_REPO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 3: Show entry points
run maestro repo show entry-points  # TODO_CMD: may be 'entrypoints' or 'targets'
# EXPECT: Shows FastAPI app at src/api/main.py:app
# STORES_READ: HOME_HUB_REPO
# GATES: (none)
# INTERNAL: UNKNOWN

echo ""
echo "EX-03 Outcome A: Metadata cached to HOME_HUB_REPO, no repo writes"
echo "Cache: \$HOME/.maestro/hub/repo/<repo-id>/metadata.json"
echo "Repo truth: ./docs/maestro/ (NOT modified)"
