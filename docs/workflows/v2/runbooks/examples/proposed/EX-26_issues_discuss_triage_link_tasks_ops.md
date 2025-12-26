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
| 1 | `TODO_CMD: maestro issues discuss` | Enter issues discuss | Issues context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe logs | Cluster duplicates | AI proposes issue ops | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Issues updated + linked | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- De-duplicate by signature and stack trace
- Link new issues to existing tasks when possible
- Ignore noisy issues with explicit reason

---

## Outcomes

### Outcome A: New Issues Created and Linked

- OPS emitted: `issue.create`, `issue.link_task`

### Outcome B: Duplicate Closed or Ignored

- OPS emitted: `issue.update` or `issue.ignore`

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro issues discuss`
- `TODO_CMD: maestro issues ignore <issue_id> --reason <text>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-26
  discuss_context: issues
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro issues discuss"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: issue.create
      args: { title: "Null pointer in parser", label: "bug" }
    - op: issue.link_task
      args: { issue_id: "ISS-7", task_id: "TASK-321" }
    - op: issue.ignore
      args: { issue_id: "ISS-3", reason: "duplicate of ISS-7" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro issues discuss"
  - "maestro issues ignore <issue_id> --reason <text>"
```
