#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-21: Discuss Router (Top-Level) — Transfer to Context

echo "=== Step 1: Start top-level discuss ==="
run "$MAESTRO_BIN" discuss
# EXPECT: Session started, router begins intent scan
# STORES_WRITE: IPC_MAILBOX
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "User: The build keeps failing, can you help?"
# EXPECT: Router classifies as repo context
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "=== Step 2: Router decision ==="
echo "Router: This looks like repo resolve. Transfer? (y/n)"
# EXPECT: Router offers transfer to repo discuss
# STORES_WRITE: IPC_MAILBOX
# GATES: ROUTER_CONFIRM

echo ""
echo "User: y"
run "$MAESTRO_BIN" discuss --context repo
# EXPECT: Repo discuss prompt loaded
# STORES_WRITE: IPC_MAILBOX
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

echo ""
echo "=== Step 3: Alternate routing ==="
echo "User: I'm blocked on TASK-042"
# EXPECT: Router classifies as task context
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

run "$MAESTRO_BIN" task discuss TASK-042
# EXPECT: Task discuss prompt loaded
# STORES_WRITE: IPC_MAILBOX
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

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
echo "=== Outcome C: Ambiguous ==="
echo "User: It is weird and kind of broken"
# EXPECT: Router asks clarifying question, no transfer
# STORES_WRITE: IPC_MAILBOX
# GATES: ROUTER_CONFIRM
