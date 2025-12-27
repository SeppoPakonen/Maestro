#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-26: Issues Discuss — Triage and Link Tasks

echo "=== Step 1: Enter issues discuss ==="
run "$MAESTRO_BIN" discuss --context issues
# EXPECT: Issues context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: These two stack traces look the same, and one is noise"
# EXPECT: AI clusters duplicates and suggests triage tasks
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "patch_operations": [
#     {"op_type": "add_task", "data": {"task_name": "Triage parser crash", "task_id": "TASK-TRIAGE", "phase_id": "PH-CORE"}}
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

echo ""
echo "=== Optional: Cancel duplicate issue ==="
run "$MAESTRO_BIN" issues state ISS-3 cancelled
# EXPECT: Issue state updated
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
