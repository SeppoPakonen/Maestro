# v3 CLI Signatures (Canonical)

This sheet locks the canonical command shapes used in v3 docs and runbooks.

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

- `maestro discuss`
- `maestro task discuss <TASK_ID>`
- `maestro phase discuss <PHASE_ID>`
- `maestro track discuss <TRACK_ID>`
- `maestro repo discuss`
- `maestro issues discuss`
- `maestro runbook discuss`
- `maestro workflow discuss`
- `maestro solutions discuss`

Discuss returns JSON->OPS; invalid JSON hard-stops apply.

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

- `maestro repo resolve {lite|deep}`
- `maestro repo conf show`
- `maestro repo conf select-default target <TARGET>`
- `maestro make ...` (v3 canonical)
- `maestro build ...` (legacy alias)

## Select toolchain vs platform caps

- `maestro select toolchain {list|show|set|unset|detect|export}`
- `maestro platform caps {detect|list|show|prefer|require|unprefer|unrequire|export}`

See `docs/workflows/v3/cli/SELECT_TOOLCHAIN.md` and `docs/workflows/v3/cli/PLATFORM_CAPS.md` for semantics.
