# EX-24: Task Discuss — Execute, Patch, Test

**Scope**: Task-level discuss for actionable execution
**Outcome**: Produce OPS for patching, testing, and task completion

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Task exists (e.g., `TASK-123`)

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
| 1 | `TODO_CMD: maestro task discuss TASK-123` | Enter task discuss | Task context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe fix | Determine patch + tests | AI proposes ops | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Patch/tests/breadcrumbs | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |

---

## AI Perspective (Heuristic)

- Prefer pure Maestro ops when possible
- Use shell ops only if explicitly supported
- Mark task done only after tests pass

---

## Outcomes

### Outcome A: Patch + Tests + Done

- OPS emitted: `ops.run_command` (if supported), `wsession.breadcrumb.append`, `task.mark_done`

### Outcome B: Patch Applied, Tests Fail

- OPS emitted: `issue.create`, task remains in progress

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro task discuss <task_id>`
- `TODO_CMD: maestro ops run <command>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-24
  discuss_context: task
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro task discuss TASK-123"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: wsession.breadcrumb.append
      args: { session_id: "ws-555", status: "Applying patch" }
    - op: ops.run_command
      args: { command: "make test" }
    - op: task.mark_done
      args: { task_id: "TASK-123" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro task discuss <task_id>"
  - "maestro ops run <command>"
```
