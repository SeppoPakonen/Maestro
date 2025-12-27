#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# EX-03: Python Poetry Read-Only Inspection — No Repo Writes

# Step 1: Resolve repo in read-only mode
run "$MAESTRO_BIN" repo resolve --no-write
# EXPECT: Detects Poetry, Python 3.11, FastAPI deps
# EXPECT: NOT IMPLEMENTED (hub cache write) (CLI_GAPS: GAP-0001)
# STORES_WRITE: HOME_HUB_REPO (NOT repo truth)
# STORES_READ: (none)
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 2: Show detected packages
run "$MAESTRO_BIN" repo pkg list
# EXPECT: Lists fastapi, uvicorn, python=^3.11
# STORES_READ: HOME_HUB_REPO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 3: Show entry points
run "$MAESTRO_BIN" repo show --json
# EXPECT: NOT IMPLEMENTED (entry-point query) (CLI_GAPS: GAP-0030)
# STORES_READ: HOME_HUB_REPO
# GATES: (none)
# INTERNAL: UNKNOWN

echo ""
echo "EX-03 Outcome A: Metadata cached to HOME_HUB_REPO, no repo writes"
echo "Cache: \$HOME/.maestro/hub/repo/<repo-id>/metadata.json"
echo "Repo truth: ./docs/maestro/ (NOT modified)"
