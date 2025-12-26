# EX-22: Track Discuss — Plan and Decompose

**Scope**: Track-level discuss for goals, phases, and high-level rules
**Outcome**: Create phases and update track summary

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Track exists (e.g., `TRK-ALPHA`)

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
| 1 | `TODO_CMD: maestro track discuss TRK-ALPHA` | Enter track discuss | Track context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: provide goals | Describe milestones | AI proposes phases | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Create phases, update track | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Capture goals at track level, avoid task detail
- Prefer phase creation with clear names and estimates
- Emit OPS that align with CLI commands

---

## Outcomes

### Outcome A: Phase Plan Created

- OPS emitted: `phase.create`, `track.update`

### Outcome B: Rules Applied

- OPS emitted: `rules.apply` to attach track rules

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro track discuss <track_id>`
- `TODO_CMD: maestro rules apply --track <track_id>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-22
  discuss_context: track
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "TODO_CMD: maestro track discuss TRK-ALPHA"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: phase.create
      args: { track_id: "TRK-ALPHA", title: "Phase 1: Core" }
    - op: phase.create
      args: { track_id: "TRK-ALPHA", title: "Phase 2: Hardening" }
    - op: track.update
      args: { track_id: "TRK-ALPHA", summary: "Two-phase plan" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
cli_gaps:
  - "maestro track discuss <track_id>"
  - "maestro rules apply --track <track_id>"
```
