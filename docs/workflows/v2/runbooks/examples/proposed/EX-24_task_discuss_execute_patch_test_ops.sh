#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-24: Task Discuss — Execute, Patch, Test

echo "=== Step 1: Enter task discuss ==="
run TODO_CMD: maestro task discuss TASK-123
# EXPECT: Task context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: Fix the failing unit tests and run the suite"
# EXPECT: AI proposes patch + test ops
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "wsession.breadcrumb.append", "args": {"session_id": "ws-555", "status": "Applying patch"}},
#     {"op": "ops.run_command", "args": {"command": "make test"}},
#     {"op": "task.mark_done", "args": {"task_id": "TASK-123"}}
#   ],
#   "summary": "Apply patch, run tests, mark done"
# }

echo ""
echo "=== Optional: If tests fail ==="
run TODO_CMD: maestro issues add "Tests failed" --task TASK-123
# EXPECT: Issue created, task stays in progress
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
