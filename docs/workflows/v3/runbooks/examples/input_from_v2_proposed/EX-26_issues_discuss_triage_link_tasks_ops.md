# EX-26: Issues Discuss — Triage and Link Tasks

**Scope**: Issues discuss for triage, dedup, and linking
**Outcome**: Create/update issues and link to tasks

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Existing issue backlog or logs

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
| 1 | `maestro discuss --context issues` | Enter issues discuss | Issues context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe logs | Cluster duplicates | AI proposes triage tasks | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Tasks created for triage | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- De-duplicate by signature and stack trace
- Link new issues to existing tasks when possible
- Use issue CLI to cancel duplicates after triage

---

## Outcomes

### Outcome A: Triage Tasks Created

- OPS emitted: `add_task` (triage or fix tasks)

### Outcome B: Duplicate Closed or Cancelled

- CLI actions: `maestro issues state <issue_id> cancelled`

---

## CLI Notes

- Use `maestro issues list` and `maestro issues show <id>` for triage visibility.

---

## Trace (YAML)

```yaml
trace:
  example: EX-26
  discuss_context: issues
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro discuss --context issues"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_task
      args: { task_name: "Triage parser crash", task_id: "TASK-TRIAGE", phase_id: "PH-CORE" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
