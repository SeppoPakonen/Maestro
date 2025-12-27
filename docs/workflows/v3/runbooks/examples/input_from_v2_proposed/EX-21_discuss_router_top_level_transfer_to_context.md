# EX-21: Discuss Router (Top-Level) — Transfer to Context

**Scope**: `maestro discuss` as a call-center router that transfers to a specialized context
**Outcome**: Demonstrate routing decision, context transfer, and OPS output after routing

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Repo initialized and repoconf selected
- At least one task and repo context exist

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
| 1 | `maestro discuss` | Start top-level discuss | Session started, router begins intent scan | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe problem | Provide intent signal | Router classifies as task or repo | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | Router decision | Determine best context | Transfer offer or auto-switch | `ROUTER_CONFIRM` | `IPC_MAILBOX` |
| 4 | `maestro task discuss TASK-042` | Transfer to task context | Task discuss prompt loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 5 | User: `/done` | Request final JSON | JSON emitted with patch operations | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 6 | Apply OPS | Update task metadata | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Detect intent keywords ("build fails" → repo; "finish task" → task)
- Prefer specialized discuss context when confidence is high
- Refuse to apply OPS if JSON contract fails

---

## Outcomes

### Outcome A: Routed to Task Discuss

- Router identifies task context by `TASK-042`
- OPS emitted: `edit_task_fields`

### Outcome B: Routed to Repo Discuss

- Router identifies repo context
- OPS emitted: `add_task` (create a repo-resolve follow-up task)

### Outcome C: Ambiguous → Stay in General Discuss

- Router confidence low, asks for clarification
- No OPS applied until user clarifies

---

## CLI Notes

- Use `maestro discuss --context repo` to force a repo discuss session.
- Use `maestro discuss resume <session_id>` to retry after invalid JSON.

---

## Trace (YAML)

```yaml
trace:
  example: EX-21
  discuss_context: top_level
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro discuss"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
    - step: route_to_task
      command: "maestro task discuss TASK-042"
      gates: [ROUTER_CONFIRM, JSON_CONTRACT_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: edit_task_fields
      args: { task_id: "TASK-042", fields: { status: "in_progress" } }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
