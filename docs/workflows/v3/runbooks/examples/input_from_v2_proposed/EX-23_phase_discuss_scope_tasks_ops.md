# EX-23: Phase Discuss — Scope Tasks and Gates

**Scope**: Phase-level discuss for task scoping and ordering
**Outcome**: Create tasks, link to phase, record dependencies

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
| 1 | `maestro phase discuss PH-CORE` | Enter phase discuss | Phase context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe scope | Capture tasks and gates | AI proposes tasks + dependencies | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Tasks created and linked | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Break phase into small, testable tasks
- Ensure dependencies are explicit before ordering
- Add gate tasks when build must pass first

---

## Outcomes

### Outcome A: Tasks + Dependencies Recorded

- OPS emitted: `add_task`, `edit_task_fields` (store `depends_on` metadata)

### Outcome B: Issue Raised During Scoping

- OPS emitted: `add_task` (investigation task)

---

## CLI Notes

- Dependency metadata is stored in task fields and managed via discuss ops.

---

## Trace (YAML)

```yaml
trace:
  example: EX-23
  discuss_context: phase
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro phase discuss PH-CORE"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_task
      args: { task_name: "Define API", task_id: "TASK-API", phase_id: "PH-CORE" }
    - op: add_task
      args: { task_name: "Implement handlers", task_id: "TASK-IMPL", phase_id: "PH-CORE" }
    - op: edit_task_fields
      args: { task_id: "TASK-IMPL", fields: { depends_on: ["TASK-API"] } }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
