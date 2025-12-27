#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-23: Phase Discuss — Scope Tasks and Gates

echo "=== Step 1: Enter phase discuss ==="
run "$MAESTRO_BIN" phase discuss PH-CORE
# EXPECT: Phase context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: We need API design, implementation, then tests"
# EXPECT: AI proposes tasks + dependency order
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "patch_operations": [
#     {"op_type": "add_task", "data": {"task_name": "Define API", "task_id": "TASK-API", "phase_id": "PH-CORE"}},
#     {"op_type": "add_task", "data": {"task_name": "Implement handlers", "task_id": "TASK-IMPL", "phase_id": "PH-CORE"}},
#     {"op_type": "edit_task_fields", "data": {"task_id": "TASK-IMPL", "fields": {"depends_on": ["TASK-API"]}}}
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
