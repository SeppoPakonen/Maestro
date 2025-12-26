# EX-27: Runbook + Workflow Discuss — Authoring

**Scope**: Discuss for authoring runbooks and workflow graphs
**Outcome**: Create runbook steps and workflow nodes/edges

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Workflow files stored in `./docs/maestro/workflows/*.json`

---

## Contract (Shared Discuss)

- Discuss interaction uses the shared editor/TTY mechanism
- User inputs:
  - `/done` requests final JSON
  - `/quit` exits immediately
- System behavior:
  - Stream events recorded
  - On `/done`, assistant must return a **single JSON object** matching a schema
  - If JSON invalid → **hard fail** → no OPS applied → user must retry/resume

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `TODO_CMD: maestro runbook discuss` | Enter runbook discuss | Runbook context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe workflow | Capture steps + nodes | AI proposes runbook/workflow ops | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Runbook + workflow updated | Repo truth updated | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Use runbook steps for narrative flow
- Use workflow nodes/edges for graph structure
- Export/render only when graph is valid

---

## Outcomes

### Outcome A: Runbook + Workflow Created

- OPS emitted: `runbook.create`, `runbook.step.add`, `workflow.node.add`, `workflow.edge.add`

### Outcome B: Export + Render Added

- OPS emitted: `workflow.export.puml`, `workflow.render.svg`

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro runbook discuss`
- `TODO_CMD: maestro runbook create <name>`
- `TODO_CMD: maestro workflow export --format puml <name>`
- `TODO_CMD: maestro workflow render --format svg <name>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-27
  discuss_context: runbook_workflow
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro runbook discuss"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: runbook.create
      args: { name: "onboard_service" }
    - op: runbook.step.add
      args: { runbook: "onboard_service", step: "Generate repo skeleton" }
    - op: workflow.node.add
      args: { workflow: "onboard_service", node_id: "node-1", layer: "interface" }
    - op: workflow.edge.add
      args: { workflow: "onboard_service", from: "node-1", to: "node-2" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro runbook discuss"
  - "maestro runbook create <name>"
  - "maestro workflow export --format puml <name>"
  - "maestro workflow render --format svg <name>"
```
