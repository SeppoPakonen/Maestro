#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-22: Track Discuss — Plan and Decompose

echo "=== Step 1: Enter track discuss ==="
run "$MAESTRO_BIN" track discuss TRK-ALPHA
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
#   "patch_operations": [
#     {"op_type": "add_phase", "data": {"track_id": "TRK-ALPHA", "phase_name": "Phase 1: Core", "phase_id": "PH-CORE"}},
#     {"op_type": "add_phase", "data": {"track_id": "TRK-ALPHA", "phase_name": "Phase 2: Hardening", "phase_id": "PH-HARD"}}
#   ]
# }

SESSION_DIR=$(ls -dt docs/maestro/sessions/discuss/* | head -1)
SESSION_ID=$(python - <<'PY' "$SESSION_DIR/meta.json"
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    print(json.load(f)["session_id"])
PY
)

run "$MAESTRO_BIN" discuss replay "$SESSION_ID" --dry-run
# EXPECT: REPLAY_OK (dry-run)
