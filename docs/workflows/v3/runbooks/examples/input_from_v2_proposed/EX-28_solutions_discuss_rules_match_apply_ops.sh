#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-28: Solutions Discuss — Rules Match and Apply

echo "=== Step 1: Enter solutions discuss ==="
run "$MAESTRO_BIN" discuss --context solutions
# EXPECT: Solutions context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: The linker error says undefined reference to vtable"
# EXPECT: AI proposes candidate solution tasks
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "patch_operations": [
#     {"op_type": "add_task", "data": {"task_name": "Try solution SOL-9", "task_id": "TASK-SOL", "phase_id": "PH-CORE"}}
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

run "$MAESTRO_BIN" discuss replay "$SESSION_ID" --dry-run --allow-cross-context
# EXPECT: REPLAY_OK (dry-run)

echo ""
echo "=== Step 2: List solutions ==="
run "$MAESTRO_BIN" solutions list
# EXPECT: Solutions listed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 3: Match solutions for issue ==="
run "$MAESTRO_BIN" issues react ISS-9 --external
# EXPECT: Solution matches suggested
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
