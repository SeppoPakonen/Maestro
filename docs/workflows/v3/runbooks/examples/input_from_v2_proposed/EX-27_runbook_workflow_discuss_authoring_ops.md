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
| 1 | `maestro discuss --context runbook` | Enter runbook discuss | Runbook context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: describe workflow | Capture steps + nodes | AI proposes authoring tasks | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Tasks created for authoring | Repo truth updated | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro runbook add --title "Onboard Service" --scope product` | Create runbook | Runbook ID created | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro runbook step-add <id> --actor user --action "Bootstrap repo" --expected "Repo scaffold created"` | Add steps | Step added | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 7 | `maestro workflow create onboard_service` | Create workflow stub | Workflow created (stub) | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 8 | `maestro workflow visualize onboard_service --format plantuml` | Visualize workflow | PlantUML output generated | `REPO_TRUTH_IS_DOCS_MAESTRO` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Use runbook steps for narrative flow
- Use workflow visualization for high-level structure
- Export/render only when graph is valid

---

## Outcomes

### Outcome A: Runbook Authored

- OPS emitted: `add_task` (authoring task)

### Outcome B: Workflow Stub Created

- CLI actions: `maestro workflow create`, `maestro workflow visualize`

---

## CLI Notes

- `maestro runbook discuss` is a placeholder; use `maestro discuss --context runbook` for now.

---

## Trace (YAML)

```yaml
trace:
  example: EX-27
  discuss_context: runbook
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro discuss --context runbook"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_task
      args: { task_name: "Author runbook and workflow", task_id: "TASK-RB", phase_id: "PH-CORE" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
