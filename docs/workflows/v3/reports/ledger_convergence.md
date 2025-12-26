# Ledger Convergence (v2  v3)

This report reconciles the v3 implementation ledger with the older v2 spectocode delta ledger and yields a single P0 implementation sprint map.

## v3  v2 mapping (overlaps only)

| v3 LED | v2 LEDGER | Overlap summary | Notes |
| --- | --- | --- | --- |
| LED-0005 | LEDGER-0004 | Repo conf gate before execution | v3 uses `make` canonical; v2 uses `build/tu/convert`. |
| LED-0024 | LEDGER-0004 | Enforce repoconf/target gate | Strengthens to target selection requirement. |
| LED-0025 | LEDGER-0004 | TU gate enforcement | Same intent; v3 clarifies toolchain requirement. |
| LED-0026 | LEDGER-0006 | Wsession cookie required | v3 adds breadcrumb semantics. |

## v2 ledger items without v3 ledger entries (still active)

- LEDGER-0001: JSON-only repo truth (covered by `docs/workflows/v3/cli/INVARIANTS.md`).
- LEDGER-0002: forbid `./.maestro` (covered by `docs/workflows/v3/cli/INVARIANTS.md`).
- LEDGER-0003: repo resolve is detection spine (covered by `docs/workflows/v3/cli/INVARIANTS.md`).
- LEDGER-0005: branch switch forbidden during work (covered by `docs/workflows/v3/cli/INVARIANTS.md`).

## Decision log (resolved contradictions)

- DEC-0001  Build vs make
  - Decision: `maestro make` is canonical; `maestro build` is a deprecated alias.
  - Reason: v3 CLI principles prefer short verbs and runbook usage already favors `make`.
  - Impacts: LED-0004, LED-0005, LED-0024, LED-0025.

- DEC-0002  Mutation opt-in vs rules/assert
  - Decision: explicit rules/assert commands only; no implicit mutation opt-in flags.
  - Reason: discuss JSONOPS should emit explicit commands (`rules apply`, `solutions apply`) to mutate.
  - Impacts: CLI gaps in governance namespace; avoid hidden side effects.

- DEC-0003  Repo resolve spine
  - Decision: `maestro repo resolve` remains the detection spine; build/TU/convert must consume its outputs.
  - Reason: avoids per-command re-detection and keeps repo model consistent.
  - Impacts: LED-0005, LED-0024, LED-0025; v2 LEDGER-0003 remains P0.

## Unified P0 sprint (10 items max)

1. JSON-only repo truth enforcement
   - Acceptance tests: creating/editing repo truth always emits JSON under `./docs/maestro/**`; no Markdown persistence.
   - Evidence: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0001`, `docs/workflows/v3/cli/INVARIANTS.md`.

2. Forbid `./.maestro` repository state
   - Acceptance tests: any attempt to read/write `./.maestro` hard-fails with migration guidance.
   - Evidence: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0002`, `docs/workflows/v3/cli/INVARIANTS.md`.

3. Repo resolve as detection spine
   - Acceptance tests: `make/tu/convert` require `repo_model.json`; no per-command detection allowed.
   - Evidence: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0003`.

4. Repoconf + target gate before `make`
   - Acceptance tests: `maestro make` fails if no target selected; error references `repo conf select-default target <TARGET>`.
   - Evidence: `docs/workflows/v3/IMPLEMENTATION_LEDGER.md#led-0024`, `docs/workflows/v3/cli/INVARIANTS.md`.

5. TU readiness gate
   - Acceptance tests: `maestro tu build` fails if repoconf or toolchain missing; error points to `repo conf` and `select toolchain`.
   - Evidence: `docs/workflows/v3/IMPLEMENTATION_LEDGER.md#led-0025`.

6. Wsession cookie required for breadcrumbs
   - Acceptance tests: `wsession breadcrumb add` rejects missing cookie with clear guidance; `wsession show` reveals cookie.
   - Evidence: `docs/workflows/v3/IMPLEMENTATION_LEDGER.md#led-0026`, `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0006`.

7. Work session open/close lifecycle enforcement
   - Acceptance tests: operations on closed sessions are blocked; resume tokens expire on close.
   - Evidence: `docs/workflows/v3/IMPLEMENTATION_LEDGER.md#led-0027`.

8. Discuss JSON hard gate
   - Acceptance tests: invalid `/done` JSON blocks OPS and logs failure event.
   - Evidence: `docs/workflows/v3/IMPLEMENTATION_LEDGER.md#led-0028`, `docs/workflows/v3/cli/INVARIANTS.md`.

9. Branch switch guard during active work
   - Acceptance tests: branch switch denied while work session open; closing session re-enables.
   - Evidence: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0005`.

10. Repo conf gate for convert
    - Acceptance tests: `maestro convert` fails without repoconf; message points to `repo conf`.
    - Evidence: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md#ledger-0004`.

## Invariant coverage (P0)

- Repo truth JSON only: mapped to LEDGER-0001.
- Hub/host truth under `$HOME/.maestro`: satisfied by storage conventions; no CLI delta identified.
- Forbid `./.maestro`: mapped to LEDGER-0002.
- Make gate requires repoconf/target: mapped to LED-0024.
- TU gate requires build context: mapped to LED-0025.
- Breadcrumb cookie required: mapped to LED-0026.
- Work session open/close state: mapped to LED-0027.
- AI resume token lifecycle: internal session store enforcement; no CLI delta identified.
- Discuss JSON hard gate: mapped to LED-0028.
- Branch switch forbidden during work: mapped to LEDGER-0005.
