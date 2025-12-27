# CLI Gaps (v3)

This index aligns v3 gaps to the hard invariants and runbook evidence. Each P0 entry maps to a specific invariant.

## P0 — Blocks Invariants

- Gap ID: SAT-0001
  - Invariant ref: Data stores — Repo truth lives under `./docs/maestro/**` (JSON only).
  - Missing capability: None (guarded by storage validation).
  - Proposed v3 command: internal-only
  - Evidence: N/A
  - Status: noted

- Gap ID: SAT-0002
  - Invariant ref: Data stores — Hub/host truth lives under `$HOME/.maestro/**`.
  - Missing capability: None (hub detection paths are defined).
  - Proposed v3 command: `maestro select toolchain detect`, `maestro platform caps detect`
  - Evidence: EX-29, EX-30, EX-31
  - Status: noted

- Gap ID: SAT-0003
  - Invariant ref: Data stores — Never use `./.maestro` for project state.
  - Missing capability: None (storage layer guard).
  - Proposed v3 command: internal-only
  - Evidence: N/A
  - Status: noted

- Gap ID: GAP-0005
  - Invariant ref: Build/make gates — `maestro make` must not run unless repo context and target are valid.
  - Missing capability: Canonical build verb with consistent gating and error messaging.
  - Proposed v3 command: `maestro make` (alias `build`)
  - Evidence: EX-01, EX-13, EX-31
  - Status: implemented

- Gap ID: GAP-0028
  - Invariant ref: Build/make gates — repoconf and target must be present.
  - Missing capability: Explicit target selection subverb for repoconf.
  - Proposed v3 command: `maestro repo conf select-default target <TARGET>`
  - Evidence: EX-31
  - Status: implemented

- Gap ID: GAP-0029
  - Invariant ref: TU/AST gates — `maestro tu` must not run unless build context is valid.
  - Missing capability: TU gate enforcement with clear remediation path.
  - Proposed v3 command: `maestro tu build`
  - Evidence: EX-31
  - Status: proposed

- Gap ID: GAP-0019
  - Invariant ref: Identity discipline — Breadcrumbs require a cookie.
  - Missing capability: Cookie-required breadcrumb subcommands.
  - Proposed v3 command: `maestro wsession breadcrumb add|list --cookie <COOKIE>`
  - Evidence: EX-07, EX-19
  - Status: implemented

- Gap ID: GAP-0018
  - Invariant ref: Identity discipline — Work session must have explicit open/closed state.
  - Missing capability: Work session lifecycle verbs and state visibility.
  - Proposed v3 command: `maestro work start|resume|pause|stop` + `maestro work status`
  - Evidence: EX-19, EX-20
  - Status: proposed

- Gap ID: SAT-0004
  - Invariant ref: Identity discipline — AI resume tokens are valid only until session close.
  - Missing capability: None (session store validation).
  - Proposed v3 command: internal-only
  - Evidence: EX-21
  - Status: noted

- Gap ID: SAT-0005
  - Invariant ref: Discuss contract — `/done` must return a single valid JSON object.
  - Missing capability: None (discuss handler validation).
  - Proposed v3 command: internal-only
  - Evidence: EX-21..EX-28
  - Status: noted

- Gap ID: SAT-0006
  - Invariant ref: Git guard — Branch switching during active work sessions is forbidden.
  - Missing capability: None (work session guard).
  - Proposed v3 command: internal-only
  - Evidence: EX-20
  - Status: noted

## P1 — Improves UX / Completeness

- Gap ID: GAP-0001
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Read-only repo resolve for fingerprinting.
  - Proposed v3 command: `maestro repo resolve --no-write` (+ hub cache write)
  - Evidence: EX-03, EX-18
  - Status: proposed
  - Priority: P1
  - Type: needs_setting
  - Notes: Flag semantics must prevent writes to `./docs/maestro/**`.

- Gap ID: GAP-0004
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Show repo conf (targets, compiler).
  - Proposed v3 command: `maestro repo conf show`
  - Evidence: EX-01
  - Status: implemented
  - Priority: P1
  - Type: naming_conflict
  - Notes: Avoid `repo conf --show` flag form.

- Gap ID: GAP-0006
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Match solutions from build logs.
  - Proposed v3 command: `maestro solutions match --from-build-log <path>`
  - Evidence: EX-01
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Decide path vs auto-detect last build.

- Gap ID: GAP-0007
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Create issue from solution.
  - Proposed v3 command: `maestro issues add --from-solution <id>`
  - Evidence: EX-01
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Needs consistent solution-id linkage.

- Gap ID: GAP-0008
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Create task from issue with action.
  - Proposed v3 command: `maestro task add --issue <id> --action <action>`
  - Evidence: EX-01
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Action vocabulary must be defined.

- Gap ID: GAP-0010
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Discuss router transfer.
  - Proposed v3 command: `maestro discuss --transfer <context>`
  - Evidence: EX-21, EX-05
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Needs clear routing and session transfer rules.

- Gap ID: GAP-0011
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Discuss resume/context selection.
  - Proposed v3 command: `maestro discuss --resume <id>` / `maestro discuss --context task <id>`
  - Evidence: EX-05
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Align with `work resume` and `ai resume`.

- Gap ID: GAP-0013
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Workflow export/render.
  - Proposed v3 command: `maestro workflow export puml <id>` / `maestro workflow render svg <id>`
  - Evidence: EX-02, EX-11, EX-27
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Export then render via PlantUML.

- Gap ID: GAP-0014
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Workflow validate.
  - Proposed v3 command: `maestro workflow validate <id>`
  - Evidence: EX-11, EX-12
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Gate for graph invariants.

- Gap ID: GAP-0015
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Runbook discuss and create.
  - Proposed v3 command: `maestro runbook discuss` / `maestro runbook add <name>`
  - Evidence: EX-27
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: `add` is preferred over `create`.

- Gap ID: GAP-0016
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Issues discuss/ignore/link.
  - Proposed v3 command: `maestro issues discuss` / `issues ignore <id> --reason <text>` / `issues link solution <issue> <solution>`
  - Evidence: EX-26
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Consolidate under `issues link`.

- Gap ID: GAP-0017
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Task completion status.
  - Proposed v3 command: `maestro task set status <id> done`
  - Evidence: EX-12
  - Status: proposed
  - Priority: P1
  - Type: inconsistent_verb
  - Notes: Prefer `set status` over `complete`.

- Gap ID: GAP-0020
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Repo hub queries and list.
  - Proposed v3 command: `maestro repo hub find package <name>` / `repo hub list`
  - Evidence: EX-18
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Hub store should be `HOME_HUB_REPO`.

- Gap ID: GAP-0023
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Convert pipeline creation.
  - Proposed v3 command: `maestro convert add <name>`
  - Evidence: EX-15, EX-17
  - Status: proposed
  - Priority: P1
  - Type: inconsistent_verb
  - Notes: Prefer `add` over `new`.

- Gap ID: GAP-0024
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Repo discuss.
  - Proposed v3 command: `maestro repo discuss`
  - Evidence: EX-21, EX-25
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Discuss endpoints per namespace.

- Gap ID: GAP-0030
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Entry point listing from repo model.
  - Proposed v3 command: `maestro repo show entry-points`
  - Evidence: EX-03
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Requires entry point extraction for Python projects.

- Gap ID: GAP-0031
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Work mutation mode flag.
  - Proposed v3 command: `maestro work task <id> --allow-mutations`
  - Evidence: EX-07
  - Status: proposed
  - Priority: P1
  - Type: needs_setting
  - Notes: Must be opt-in and auditable.

- Gap ID: GAP-0032
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Commit message suggestion from task metadata.
  - Proposed v3 command: `maestro ops commit suggest --task <task-id>`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Should read task/phase/track metadata and git status.

- Gap ID: GAP-0033
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Commit creation using suggested template.
  - Proposed v3 command: `maestro ops commit create --task <task-id>`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Should stage files from session and record commit hash.

- Gap ID: GAP-0034
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Git guard status query.
  - Proposed v3 command: `maestro ops git status-guard`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Exposes guard readiness for scripts.

- Gap ID: GAP-0035
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Work session pause semantics.
  - Proposed v3 command: `maestro work pause <wsession-id>`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Distinct from close; must preserve resume token.

- Gap ID: GAP-0036
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Toolchain profile selection.
  - Proposed v3 command: `maestro select toolchain set <profile> --scope project`
  - Evidence: EX-29, EX-31
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Requires hub profile store.

- Gap ID: GAP-0037
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Platform caps detection.
  - Proposed v3 command: `maestro platform caps detect`
  - Evidence: EX-30, EX-31
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Cache results in hub.

- Gap ID: GAP-0038
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Platform caps prefer policy.
  - Proposed v3 command: `maestro platform caps prefer <cap> --scope project`
  - Evidence: EX-30, EX-31
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Prefer is non-blocking.

- Gap ID: GAP-0039
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Platform caps require policy.
  - Proposed v3 command: `maestro platform caps require <cap> --scope project`
  - Evidence: EX-30, EX-31
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Require is a hard gate.

- Gap ID: GAP-0040
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Make/TU caps gating + issue creation.
  - Proposed v3 command: `maestro make` (caps-aware gate)
  - Evidence: EX-31
  - Status: proposed
  - Priority: P1
  - Type: missing_command
  - Notes: Missing caps should block and create an issue with detection evidence.

## P2 — Nice to have

- Gap ID: GAP-0002
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Show detected packages.
  - Proposed v3 command: `maestro repo show packages`
  - Evidence: EX-03
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Read-only report of detected deps.

- Gap ID: GAP-0003
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Show entry points / targets.
  - Proposed v3 command: `maestro repo show entrypoints`
  - Evidence: EX-03
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Normalize spelling to `entrypoints`.

- Gap ID: GAP-0012
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Workflow graph init and node add.
  - Proposed v3 command: `maestro workflow init <name>` / `workflow node add <id> --layer <layer> --label <text>`
  - Evidence: EX-02, EX-11, EX-12
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Must write `./docs/maestro/workflows/*.json`.

- Gap ID: GAP-0021
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Make with hub deps.
  - Proposed v3 command: `maestro make --with-hub-deps`
  - Evidence: EX-18
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Alternative: `repo conf set use-hub-deps true`.

- Gap ID: GAP-0022
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: TU build with hub resolve.
  - Proposed v3 command: `maestro tu build --target <t> --resolve-from-hub`
  - Evidence: EX-18
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Clarify TU store inputs.

- Gap ID: GAP-0025
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Settings for stacking mode.
  - Proposed v3 command: `maestro settings set ai_stacking_mode managed`
  - Evidence: EX-19
  - Status: proposed
  - Priority: P2
  - Type: needs_setting
  - Notes: Standardize with `ai.stacking_mode`.

- Gap ID: GAP-0026
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Ops commit helper.
  - Proposed v3 command: `maestro ops commit suggest|create --task <id>`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Needs guard integration (dirty tree).

- Gap ID: GAP-0027
  - Invariant ref: N/A (not tied to a hard invariant)
  - Missing capability: Ops git guard status.
  - Proposed v3 command: `maestro ops git status-guard`
  - Evidence: EX-20
  - Status: proposed
  - Priority: P2
  - Type: missing_command
  - Notes: Optional command under ops/doctor.

## Notes

- Evidence references are to v2/v3 runbook examples (see `docs/workflows/v3/reports/example_index.md`).
- Several gaps are naming conflicts (`build` vs `make`, `complete` vs `set status`). These are normalization tasks rather than new features.
