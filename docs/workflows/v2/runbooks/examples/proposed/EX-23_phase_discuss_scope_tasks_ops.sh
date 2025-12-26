#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-23: Phase Discuss — Scope Tasks and Gates

echo "=== Step 1: Enter phase discuss ==="
run TODO_CMD: maestro phase discuss PH-CORE
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
#   "ops": [
#     {"op": "task.create", "args": {"title": "Define API", "phase_id": "PH-CORE"}},
#     {"op": "task.create", "args": {"title": "Implement handlers", "phase_id": "PH-CORE"}},
#     {"op": "task.set_dependency", "args": {"task_id": "TASK-IMPL", "depends_on": "TASK-API"}}
#   ],
#   "summary": "Create tasks and dependency"
# }

echo ""
echo "=== Optional: Issue creation ==="
run TODO_CMD: maestro issues add "Missing API spec" --phase PH-CORE
# EXPECT: Issue created for missing requirements
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
