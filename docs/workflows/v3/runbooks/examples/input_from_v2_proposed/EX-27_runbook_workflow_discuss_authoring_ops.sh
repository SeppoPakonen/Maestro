#!/usr/bin/env bash
set -euo pipefail

# Configurable binary path
MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

run() { echo "+ $*"; }

# EX-27: Runbook + Workflow Discuss — Authoring

echo "=== Step 1: Enter runbook discuss ==="
run "$MAESTRO_BIN" discuss --context runbook
# EXPECT: Runbook context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: I need a workflow for onboarding a service"
# EXPECT: AI proposes authoring tasks
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "patch_operations": [
#     {"op_type": "add_task", "data": {"task_name": "Author runbook and workflow", "task_id": "TASK-RB", "phase_id": "PH-CORE"}}
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
echo "=== Step 2: Create runbook ==="
run "$MAESTRO_BIN" runbook add --title "Onboard Service" --scope product
# EXPECT: Runbook ID created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 3: Add runbook step ==="
run "$MAESTRO_BIN" runbook step-add rb-001 --actor user --action "Bootstrap repo" --expected "Repo scaffold created"
# EXPECT: Step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 4: Create workflow stub ==="
run "$MAESTRO_BIN" workflow create onboard_service
# EXPECT: Workflow stub created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 5: Visualize workflow ==="
run "$MAESTRO_BIN" workflow visualize onboard_service --format plantuml
# EXPECT: PlantUML output generated
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO
