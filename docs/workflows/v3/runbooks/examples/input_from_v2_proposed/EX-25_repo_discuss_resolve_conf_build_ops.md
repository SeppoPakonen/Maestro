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
| 1 | `TODO_CMD: maestro repo discuss` | Enter repo discuss | Repo context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: request resolve | Choose lite vs deep | AI proposes resolve ops | `REPO_RESOLVE_LITE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Resolve + repoconf + build | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Start with lite resolve unless deep needed
- Require repoconf target selection before build
- Create an issue on build failure

---

## Outcomes

### Outcome A: Resolve + Build Succeeds

- OPS emitted: `repo.resolve.lite`, `repo.conf.select_default_target`, `build.run`

### Outcome B: Build Fails

- OPS emitted: `issue.create` with build log summary

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro repo discuss`

---

## Trace (YAML)

```yaml
trace:
  example: EX-25
  discuss_context: repo
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro repo discuss"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: repo.resolve.lite
      args: { path: "." }
    - op: repo.conf.select_default_target
      args: { target: "build" }
    - op: build.run
      args: { target: "build" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro repo discuss"
```
