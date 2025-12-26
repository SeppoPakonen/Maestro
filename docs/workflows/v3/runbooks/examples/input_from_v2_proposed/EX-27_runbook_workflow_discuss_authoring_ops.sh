#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-27: Runbook + Workflow Discuss — Authoring

echo "=== Step 1: Enter runbook discuss ==="
run TODO_CMD: maestro runbook discuss
# EXPECT: Runbook context loaded
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# STORES_WRITE: IPC_MAILBOX
# GATES: REPOCONF_GATE

echo ""
echo "User: I need a workflow for onboarding a service"
# EXPECT: AI proposes runbook steps and workflow nodes
# STORES_WRITE: IPC_MAILBOX
# GATES: INTENT_CLASSIFY

echo ""
echo "User: /done"
# EXPECT: Assistant returns single JSON object
# GATES: JSON_CONTRACT_GATE

# JSON response (example):
# {
#   "ops": [
#     {"op": "runbook.create", "args": {"name": "onboard_service"}},
#     {"op": "runbook.step.add", "args": {"runbook": "onboard_service", "step": "Generate repo skeleton"}},
#     {"op": "workflow.node.add", "args": {"workflow": "onboard_service", "node_id": "node-1", "layer": "interface"}},
#     {"op": "workflow.edge.add", "args": {"workflow": "onboard_service", "from": "node-1", "to": "node-2"}}
#   ],
#   "summary": "Create runbook and workflow graph"
# }

echo ""
echo "=== Optional: Export and render ==="
run TODO_CMD: maestro workflow export --format puml onboard_service
# EXPECT: PlantUML export created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

run TODO_CMD: maestro workflow render --format svg onboard_service
# EXPECT: SVG rendered via /usr/bin/plantuml
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO
