# EX-22: Track Discuss — Plan and Decompose

**Scope**: Track-level discuss for goals, phases, and high-level rules
**Outcome**: Create phases and seed initial tasks

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
| 1 | `maestro track discuss TRK-ALPHA` | Enter track discuss | Track context loaded | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `IPC_MAILBOX` |
| 2 | User: provide goals | Describe milestones | AI proposes phases | `INTENT_CLASSIFY` | `IPC_MAILBOX` |
| 3 | User: `/done` | Request JSON | JSON OPS emitted | `JSON_CONTRACT_GATE` | `IPC_MAILBOX` |
| 4 | Apply OPS | Phases created | Repo truth updated | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## Expected Outputs

- `Discussion session ID: <id>` is printed and `docs/maestro/sessions/discuss/<id>/meta.json` exists.
- `maestro discuss replay <id> --dry-run` prints `REPLAY_OK`; failures print `[Replay] ERROR ...` (treat as REPLAY_FAIL).
- Starting a second discuss while a session is open prints `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`

---

## AI Perspective (Heuristic)

- Capture goals at track level, avoid task detail
- Prefer phase creation with clear names and estimates
- Emit OPS that align with the patch operation contract

---

## Outcomes

### Outcome A: Phase Plan Created

- OPS emitted: `add_phase`

### Outcome B: Initial Tasks Seeded

- OPS emitted: `add_task` (per phase)

---

## CLI Notes

- Track rules live in `docs/RepoRules.md`; update via `maestro repo rules edit` when needed.

---

## Trace (YAML)

```yaml
trace:
  example: EX-22
  discuss_context: track
  contract: discuss_ops_contract
  steps:
    - step: start_discuss
      command: "maestro track discuss TRK-ALPHA"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX]
  ops:
    - op: add_phase
      args: { track_id: "TRK-ALPHA", phase_name: "Phase 1: Core", phase_id: "PH-CORE" }
    - op: add_phase
      args: { track_id: "TRK-ALPHA", phase_name: "Phase 2: Hardening", phase_id: "PH-HARD" }
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
    - IPC_MAILBOX
```
