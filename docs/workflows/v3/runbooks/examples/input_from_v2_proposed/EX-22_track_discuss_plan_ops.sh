#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-22: Track Discuss — Plan and Decompose

echo "=== Step 1: Enter track discuss ==="
run TODO_CMD: maestro track discuss TRK-ALPHA
# EXPECT: Track context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: Our goal is a two-phase launch with core features and hardening"
# EXPECT: AI proposes phases and milestones
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "phase.create", "args": {"track_id": "TRK-ALPHA", "title": "Phase 1: Core"}},
#     {"op": "phase.create", "args": {"track_id": "TRK-ALPHA", "title": "Phase 2: Hardening"}},
#     {"op": "track.update", "args": {"track_id": "TRK-ALPHA", "summary": "Two-phase plan"}}
#   ],
#   "summary": "Create phases and update track summary"
# }

echo ""
echo "=== Optional: Apply track rules ==="
run TODO_CMD: maestro rules apply --track TRK-ALPHA
# EXPECT: Track rules attached
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
