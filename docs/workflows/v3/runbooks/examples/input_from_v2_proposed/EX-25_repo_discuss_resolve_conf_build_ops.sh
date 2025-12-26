#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-25: Repo Discuss — Resolve, Conf, Build

echo "=== Step 1: Enter repo discuss ==="
run TODO_CMD: maestro repo discuss
# EXPECT: Repo context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: Resolve the repo and run the build"
# EXPECT: AI proposes resolve + repoconf + build ops
# STORES_WRITE: IPC_MAILBOX
# GATES: REPO_RESOLVE_LITE

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "repo.resolve.lite", "args": {"path": "."}},
#     {"op": "repo.conf.select_default_target", "args": {"target": "build"}},
#     {"op": "build.run", "args": {"target": "build"}}
#   ],
#   "summary": "Resolve repo, pick target, run build"
# }

echo ""
echo "=== Optional: Build failure ==="
run TODO_CMD: maestro issues add "Build failed" --label build
# EXPECT: Issue created with build log summary
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
