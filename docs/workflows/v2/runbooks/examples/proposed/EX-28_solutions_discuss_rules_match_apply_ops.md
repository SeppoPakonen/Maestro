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
| 1 | `TODO_CMD: maestro solutions discuss` | Enter solutions discuss | Solutions context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: provide error signature | Match solutions | AI proposes matches + tasks | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Link solution + create task | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Match on error signatures and context
- Propose lowest-risk solution first
- Create a task to apply and verify

---

## Outcomes

### Outcome A: Solution Matched and Task Created

- OPS emitted: `solutions.match`, `task.create`, `issue.link_solution`

### Outcome B: No Match → Create Investigation Task

- OPS emitted: `task.create` only

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro solutions discuss`
- `TODO_CMD: maestro issues link-solution <issue_id> <solution_id>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-28
  discuss_context: solutions
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro solutions discuss"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: solutions.match
      args: { signature: "undefined reference to vtable" }
    - op: task.create
      args: { title: "Try solution SOL-9", phase_id: "PH-CORE" }
    - op: issue.link_solution
      args: { issue_id: "ISS-9", solution_id: "SOL-9" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro solutions discuss"
  - "maestro issues link-solution <issue_id> <solution_id>"
```
