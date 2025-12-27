# EX-24: Task Discuss — Execute, Patch, Test

**Scope**: Task-level discuss for actionable execution
**Outcome**: Produce OPS for patch planning, testing, and task status

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
| 1 | `maestro task discuss TASK-123` | Enter task discuss | Task context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe fix | Determine patch + tests | AI proposes ops | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Task metadata updated | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Prefer explicit patch plan and test commands in task notes
- Mark task done only after tests pass
- Emit minimal patch operations

---

## Outcomes

### Outcome A: Patch + Tests Planned

- OPS emitted: `edit_task_fields` (add patch/test notes)

### Outcome B: Follow-up Task Added

- OPS emitted: `add_task` (for additional verification)

---

## CLI Notes

- Run tests directly via `maestro make build` or your CI scripts; discuss only stores intent.

---

## Trace (YAML)

```yaml
trace:
  example: EX-24
  discuss_context: task
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro task discuss TASK-123"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: edit_task_fields
      args: { task_id: "TASK-123", fields: { patch_plan: "Fix tests", test_command: "pytest -q" } }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
