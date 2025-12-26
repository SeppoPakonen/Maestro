#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-21: Discuss Router (Top-Level) — Transfer to Context

echo "=== Step 1: Start top-level discuss ==="
run maestro discuss
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
run TODO_CMD: maestro repo discuss
# EXPECT: Repo discuss prompt loaded
# STORES_WRITE: IPC_MAILBOX
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "repo.resolve.lite", "args": {"path": "."}},
#     {"op": "repo.conf.select_default_target", "args": {"target": "build"}}
#   ],
#   "summary": "Resolve repo and select default target"
# }

echo ""
echo "=== Step 3: Alternate routing ==="
echo "User: I'm blocked on TASK-042"
# EXPECT: Router classifies as task context
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

run TODO_CMD: maestro task discuss TASK-042
# EXPECT: Task discuss prompt loaded
# STORES_WRITE: IPC_MAILBOX
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "task.update", "args": {"task_id": "TASK-042", "status": "in_progress"}}
#   ],
#   "summary": "Move task to in_progress"
# }

echo ""
echo "=== Outcome C: Ambiguous ==="
echo "User: It is weird and kind of broken"
# EXPECT: Router asks clarifying question, no transfer
# STORES_WRITE: IPC_MAILBOX
# GATES: ROUTER_CONFIRM
