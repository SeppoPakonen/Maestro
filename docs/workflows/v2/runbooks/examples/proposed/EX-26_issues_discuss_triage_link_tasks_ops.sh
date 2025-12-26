#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-26: Issues Discuss — Triage and Link Tasks

echo "=== Step 1: Enter issues discuss ==="
run TODO_CMD: maestro issues discuss
# EXPECT: Issues context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: These two stack traces look the same, and one is noise"
# EXPECT: AI clusters duplicates and suggests ignore
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "issue.create", "args": {"title": "Null pointer in parser", "label": "bug"}},
#     {"op": "issue.link_task", "args": {"issue_id": "ISS-7", "task_id": "TASK-321"}},
#     {"op": "issue.ignore", "args": {"issue_id": "ISS-3", "reason": "duplicate"}}
#   ],
#   "summary": "Create issue, link to task, ignore duplicate"
# }

echo ""
echo "=== Optional: Ignore noisy issue ==="
run TODO_CMD: maestro issues ignore ISS-3 --reason "duplicate of ISS-7"
# EXPECT: Issue marked ignored
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
