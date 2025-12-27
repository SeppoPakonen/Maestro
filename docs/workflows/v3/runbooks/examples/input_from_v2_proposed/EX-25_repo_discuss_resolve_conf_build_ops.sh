#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-25: Repo Discuss — Resolve, Conf, Build

echo "=== Step 1: Lite resolve ==="
run "$MAESTRO_BIN" repo resolve
# EXPECT: Repo model refreshed
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE

echo ""
echo "=== Step 2: Enter repo discuss ==="
run "$MAESTRO_BIN" discuss --context repo
# EXPECT: Repo context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: Resolve deeper and prep a build"
# EXPECT: AI proposes follow-up tasks
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "patch_operations": [
#     {"op_type": "add_task", "data": {"task_name": "Investigate build failure", "task_id": "TASK-BUILD", "phase_id": "PH-CORE"}}
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
echo "=== Step 3: Deep refresh ==="
run "$MAESTRO_BIN" repo refresh all
# EXPECT: Full refresh complete
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_REFRESH_DEEP

echo ""
echo "=== Step 4: Select default target ==="
run "$MAESTRO_BIN" repo conf select-default target build
# EXPECT: Default target stored
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 5: Build ==="
run "$MAESTRO_BIN" make build
# EXPECT: Build runs with selected target
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
