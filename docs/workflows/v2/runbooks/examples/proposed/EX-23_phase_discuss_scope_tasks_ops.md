# EX-23: Phase Discuss — Scope Tasks and Gates

**Scope**: Phase-level discuss for task scoping and ordering
**Outcome**: Create tasks, link to phase, set dependencies

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Phase exists (e.g., `PH-CORE`)

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
| 1 | `TODO_CMD: maestro phase discuss PH-CORE` | Enter phase discuss | Phase context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe scope | Capture tasks and gates | AI proposes tasks + dependencies | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Tasks created and linked | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Break phase into small, testable tasks
- Ensure dependencies are explicit before ordering
- Add gate tasks when build must pass first

---

## Outcomes

### Outcome A: Tasks + Dependencies Created

- OPS emitted: `task.create`, `task.link_phase`, `task.set_dependency`

### Outcome B: Issue Raised During Scoping

- OPS emitted: `issue.create` for missing requirements

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro phase discuss <phase_id>`
- `TODO_CMD: maestro task set-dependency <task_id> <depends_on>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-23
  discuss_context: phase
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro phase discuss PH-CORE"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: task.create
      args: { title: "Define API", phase_id: "PH-CORE" }
    - op: task.create
      args: { title: "Implement handlers", phase_id: "PH-CORE" }
    - op: task.set_dependency
      args: { task_id: "TASK-IMPL", depends_on: "TASK-API" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro phase discuss <phase_id>"
  - "maestro task set-dependency <task_id> <depends_on>"
```
