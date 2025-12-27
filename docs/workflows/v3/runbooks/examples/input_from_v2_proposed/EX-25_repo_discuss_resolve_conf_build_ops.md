# EX-25: Repo Discuss — Resolve, Conf, Build

**Scope**: Repo discuss for resolve and repoconf gating
**Outcome**: Resolve repo, select target, run build

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Repo directory exists and is accessible

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
| 1 | `maestro repo resolve` | Lite scan | Repo model refreshed | `REPO_RESOLVE_LITE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 2 | `maestro discuss --context repo` | Enter repo discuss | Repo context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Task created for deep scan or build prep | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro repo refresh all` | Deep scan | Full refresh complete | `REPO_REFRESH_DEEP` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro repo conf select-default target build` | Select target | Default target stored | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 7 | `maestro make build` | Build repo | Build runs with selected target | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Start with lite resolve unless deep refresh is required
- Require repoconf target selection before build
- Create a follow-up task when deeper analysis or build fixes are needed

---

## Outcomes

### Outcome A: Resolve + Build Succeeds

- CLI actions: `repo resolve`, `repo refresh all`, `repo conf select-default`, `make build`

### Outcome B: Build Fails

- OPS emitted: `add_task` (create a build-fix follow-up task)

---

## CLI Notes

- Deep scans use `maestro repo refresh all` (not `repo resolve --level deep`).

---

## Trace (YAML)

```yaml
trace:
  example: EX-25
  discuss_context: repo
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro discuss --context repo"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_task
      args: { task_name: "Investigate build failure", task_id: "TASK-BUILD", phase_id: "PH-CORE" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
