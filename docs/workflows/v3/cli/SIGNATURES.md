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

## Canonical verbs

All subcommands should use these canonical verbs:

- **list** (alias: `ls`) — List all items
- **show** (alias: `sh`) — Show details of a single item
- **add** — Add a new item
- **edit** — Edit an existing item
- **remove** (alias: `rm`) — Remove an item

Additional verbs for specific contexts:

- **set** — Set a value or state
- **start**, **stop**, **pause**, **resume** — Lifecycle operations (work sessions)
- **validate**, **preview**, **apply** — Operation sequences (ops, plan ops)
- **export**, **render** — Output transformations (workflows, runbooks)

**Deprecated verb forms:**

- `new` → use `add` (with deprecation warning)
- `create` → use `add` (exception: `workflow create` is canonical; see TREE.md)
- `delete` → use `remove` or `rm`

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
- `maestro discuss replay <PATH> [--dry-run] [--allow-cross-context]` (replay transcript)
- `maestro task discuss <TASK_ID>` (direct context-specific entry)
- `maestro phase discuss <PHASE_ID>`
- `maestro track discuss <TRACK_ID>`
- `maestro discuss --context {repo|issues|runbook|workflow|solutions}` (preferred for non-track contexts)
- `maestro runbook discuss <RUNBOOK_ID>` (placeholder; use `maestro discuss --context runbook`)

Router behavior:
- Priority 1: Explicit flags (--task, --phase, --track, --context)
- Priority 2: Active work session (most recent running/paused)
- Priority 3: Fall back to global context

Context metadata stored in session:
- `context.kind` (e.g., "task", "phase", "track")
- `context.ref` (entity ID if applicable)
- `router_reason` (why this context was chosen)

Discuss returns JSON->OPS; invalid JSON hard-stops apply.

Locking:
- Discuss acquires a repo lock at `docs/maestro/locks/repo.lock`.
- Concurrent sessions fail with `Error: Repository is locked by session <id> (PID <pid>, started <timestamp>).`
- Lock is released when sessions close or `/done` completes.

Replay accepts:
- `.json` with `final_json` or `patch_operations`
- `.jsonl` with a `final_json` entry

## Runbook authoring primitives

- `maestro runbook add --title <TITLE> --scope <SCOPE>`
- `maestro runbook step-add <ID> --actor <ACTOR> --action <ACTION> --expected <EXPECTED>`
- `maestro runbook export <ID> --format {md|puml} [--out <PATH>]`
- `maestro runbook render <ID> [--out <PATH>]`

## Workflow authoring primitives

- `maestro workflow list`
- `maestro workflow show <NAME>`
- `maestro workflow create <NAME>`
- `maestro workflow edit <NAME>`
- `maestro workflow delete <NAME>`
- `maestro workflow visualize <NAME> --format {plantuml|mermaid|graphviz}`

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
