# EX-28: Solutions Discuss — Rules Match and Apply

**Scope**: Solutions discuss for matching known patterns and proposing fixes
**Outcome**: Match solution, create task to apply, link to issue

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Solutions catalog exists in repo truth

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
| 1 | `maestro discuss --context solutions` | Enter solutions discuss | Solutions context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: provide error signature | Match solutions | AI proposes candidate solution tasks | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Task created for solution trial | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro solutions list` | Review catalog | Candidate solutions listed | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro issues react <issue_id> --external` | Match solutions | Solution matches suggested | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Match on error signatures and context
- Propose lowest-risk solution first
- Create a task to apply and verify

---

## Outcomes

### Outcome A: Solution Candidate Identified

- OPS emitted: `add_task` (trial task)

### Outcome B: No Match → Create Investigation Task

- OPS emitted: `add_task` only

---

## CLI Notes

- Use `maestro issues react` to match solutions from the catalog.

---

## Trace (YAML)

```yaml
trace:
  example: EX-28
  discuss_context: solutions
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro discuss --context solutions"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_task
      args: { task_name: "Try solution SOL-9", task_id: "TASK-SOL", phase_id: "PH-CORE" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
