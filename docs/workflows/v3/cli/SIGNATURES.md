# v3 CLI Signatures (Canonical)

This sheet locks the canonical command shapes used in v3 docs and runbooks.

See also:
- `docs/workflows/v3/cli/INVARIANTS.md`
- `docs/workflows/v3/cli/GATES.md`

## Help behavior

- Bare keyword prints extended help and exits 0.
  - `maestro workflow`
  - `maestro task`
- `--help/-h` remain supported but are non-canonical in docs.

## Work / wsession / resume identities

- `maestro work start task <TASK_ID>`
- `maestro work resume <WORK_ID>`
- `maestro wsession list`
- `maestro wsession show <WSESSION_ID>`
- `maestro wsession breadcrumb add --cookie <COOKIE> --json <FILE|STDIN>`
- `maestro wsession close <WSESSION_ID>`

Rule: breadcrumb ops require a cookie; missing cookie is a hard error.

## Discuss (router + context discuss)

- `maestro discuss` (router auto-detects context from active work session or flags)
- `maestro discuss --context {task|phase|track|repo|issues|runbook|workflow|solutions|global}`
- `maestro discuss --task <TASK_ID>` (explicit task context)
- `maestro discuss --phase <PHASE_ID>` (explicit phase context)
- `maestro discuss --track <TRACK_ID>` (explicit track context)
- `maestro discuss resume <SESSION_ID>` (resume previous discussion)
- `maestro discuss replay <PATH> [--dry-run]` (replay transcript)
- `maestro task discuss <TASK_ID>` (direct context-specific entry)
- `maestro phase discuss <PHASE_ID>`
- `maestro track discuss <TRACK_ID>`
- `maestro repo discuss` (planned)
- `maestro issues discuss` (planned)
- `maestro runbook discuss` (planned)
- `maestro workflow discuss` (planned)
- `maestro solutions discuss` (planned)

Router behavior:
- Priority 1: Explicit flags (--task, --phase, --track, --context)
- Priority 2: Active work session (most recent running/paused)
- Priority 3: Fall back to global context

Context metadata stored in session:
- `context.kind` (e.g., "task", "phase", "track")
- `context.ref` (entity ID if applicable)
- `router_reason` (why this context was chosen)

Discuss returns JSON->OPS; invalid JSON hard-stops apply.

Replay accepts:
- `.json` with `final_json` or `patch_operations`
- `.jsonl` with a `final_json` entry

## Workflow authoring primitives

- `maestro workflow list`
- `maestro workflow show <WF_ID>`
- `maestro workflow add <NAME>`
- `maestro workflow node add <WF_ID> <NODE_ID> --label "..."`
- `maestro workflow edge add <WF_ID> <FROM> <TO> [--label "..."]`
- `maestro workflow validate <WF_ID>`
- `maestro workflow export puml <WF_ID> --out <PATH>`
- `maestro workflow render svg <WF_ID> --out <PATH>`

## Repo resolve/conf + make/build naming

- `maestro repo resolve` (lite default)
- `maestro repo refresh all` (deep resolve)
- `maestro repo conf show`
- `maestro repo conf select-default target <TARGET>`
- `maestro make ...` (v3 canonical)
- `maestro build ...` (legacy alias)

## Select toolchain vs platform caps

- `maestro select toolchain {list|show|set|unset|detect|export}`
- `maestro platform caps {detect|list|show|prefer|require|unprefer|unrequire|export}`

See `docs/workflows/v3/cli/SELECT_TOOLCHAIN.md` and `docs/workflows/v3/cli/PLATFORM_CAPS.md` for semantics.
