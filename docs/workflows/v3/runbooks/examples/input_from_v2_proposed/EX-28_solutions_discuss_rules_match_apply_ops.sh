#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-28: Solutions Discuss — Rules Match and Apply

echo "=== Step 1: Enter solutions discuss ==="
run TODO_CMD: maestro solutions discuss
# EXPECT: Solutions context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: The linker error says undefined reference to vtable"
# EXPECT: AI matches known solution signatures
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "solutions.match", "args": {"signature": "undefined reference to vtable"}},
#     {"op": "task.create", "args": {"title": "Try solution SOL-9", "phase_id": "PH-CORE"}},
#     {"op": "issue.link_solution", "args": {"issue_id": "ISS-9", "solution_id": "SOL-9"}}
#   ],
#   "summary": "Match solution and create task"
# }

echo ""
echo "=== Optional: Link solution directly ==="
run TODO_CMD: maestro issues link-solution ISS-9 SOL-9
# EXPECT: Issue linked to solution
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
