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
- `maestro work subwork start <PARENT_WSESSION_ID> --purpose "<text>" [--context <kind:ref>] [--no-pause-parent]`
- `maestro work subwork list <PARENT_WSESSION_ID>`
- `maestro work subwork show <CHILD_WSESSION_ID>`
- `maestro work subwork close <CHILD_WSESSION_ID> --summary "<text>" [--status {ok|failed|partial}] [--no-resume-parent]`
- `maestro work subwork resume-parent <CHILD_WSESSION_ID>`
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
- `maestro discuss --wsession <WSESSION_ID>` (attach discuss metadata to a work session)
- `maestro discuss resume <SESSION_ID>` (resume previous discussion)
- `maestro discuss replay <PATH> [--dry-run] [--allow-cross-context]` (replay transcript)
- `maestro task discuss <TASK_ID>` (direct context-specific entry)
- `maestro phase discuss <PHASE_ID>`
- `maestro track discuss <TRACK_ID>`
- `maestro discuss --context {repo|issues|runbook|workflow|solutions}` (preferred for non-track contexts)
- `maestro runbook discuss <RUNBOOK_ID>` (placeholder; use `maestro discuss --context runbook`)

Router behavior:
- Priority 1: Explicit flags (--task, --phase, --track, --context)
- Priority 2: Explicit --wsession (inherit context when no explicit context)
- Priority 3: Active work session (most recent running/paused)
- Priority 4: Fall back to global context

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
- `maestro runbook resolve [-v|--verbose] [-vv|--very-verbose] [--eval|-e] <freeform string>` (Freeform → JSON Runbook)

## Runbook lifecycle (archive/restore)

- `maestro runbook list [--archived] [--type {markdown|json|all}]`
- `maestro runbook show <ID_OR_PATH> [--archived]`
- `maestro runbook archive <ID_OR_PATH> [--reason <TEXT>]`
- `maestro runbook restore <ARCHIVE_ID>`

Archive operations support both JSON runbooks (CLI-managed) and markdown example files.
Archived items are moved (not copied) to timestamped folders and excluded from default listings.

## Workflow authoring primitives

- `maestro workflow list`
- `maestro workflow show <NAME>`
- `maestro workflow create <NAME>`
- `maestro workflow edit <NAME>`
- `maestro workflow delete <NAME>`
- `maestro workflow visualize <NAME> --format {plantuml|mermaid|graphviz}`

## Workflow lifecycle (archive/restore)

- `maestro workflow list [--archived]`
- `maestro workflow show <PATH> [--archived]`
- `maestro workflow archive <PATH> [--reason <TEXT>]`
- `maestro workflow restore <ARCHIVE_ID>`

Archived workflows are moved to timestamped folders and excluded from default listings.

## Repo resolve/conf + make/build naming

- `maestro repo resolve` (lite default)
- `maestro repo refresh all` (deep resolve)
- `maestro repo conf show`
- `maestro repo conf select-default target <TARGET>`
- `maestro make ...` (v3 canonical)
- `maestro build ...` (legacy alias)

## Repo assemblies

- `maestro repo asm list [--json]` (aliases: `assembly`)
- `maestro repo asm show <ASSEMBLY_ID|NAME> [--json]` (aliases: `assembly`)

## Repo hub (cross-repo package discovery and linking)

### maestro repo hub scan

Scan a repository and add to hub index.

```
maestro repo hub scan [PATH]
  [--verbose]
```

Arguments:
- `PATH`: Repository path to scan (default: current directory)
- `--verbose`: Show detailed scan progress

### maestro repo hub list

List all repositories in hub index.

```
maestro repo hub list
  [--json]
```

Arguments:
- `--json`: Output in JSON format

### maestro repo hub show

Show details about a specific repository.

```
maestro repo hub show <REPO_ID>
  [--json]
```

Arguments:
- `REPO_ID`: Repository ID (from `hub list`)
- `--json`: Output in JSON format

### maestro repo hub find package

Find package across all repos in hub index.

```
maestro repo hub find package <NAME>
  [--json]
```

Arguments:
- `NAME`: Package name to search for
- `--json`: Output in JSON format

Returns:
- `NOT_FOUND`: Package not found in any repo
- `SINGLE_MATCH`: Exactly one package matches
- `AMBIGUOUS`: Multiple packages match (requires explicit `--to <PKG_ID>`)

### maestro repo hub link package

Create explicit link from local package to external package.

```
maestro repo hub link package <NAME>
  --to <PKG_ID>
  [--reason <TEXT>]
```

Arguments:
- `NAME`: Local package name that depends on external package
- `--to <PKG_ID>`: Target package ID (from `hub find`)
- `--reason <TEXT>`: Optional reason for link (default: "explicit")

Behavior:
- Validates target package ID exists in hub index
- Creates link entry in `./docs/maestro/repo/hub_links.json`
- Computes deterministic link ID
- Updates existing link if already present

### maestro repo hub link show

Show all hub links for current repository.

```
maestro repo hub link show
  [--json]
```

Arguments:
- `--json`: Output in JSON format

### maestro repo hub link remove

Remove a hub link.

```
maestro repo hub link remove <LINK_ID>
```

Arguments:
- `LINK_ID`: Link ID to remove (from `hub link show`)

### Hub determinism rules

**Repo ID:**
```
repo_id = sha256(canonical_path + ":" + git_head + ":" + mtime_summary)
```

**Package ID:**
```
pkg_id = sha256(build_system + ":" + name + ":" + normalized_root)
```

**Link ID:**
```
link_id = sha256(from_package + ":" + to_package_id)
```

**Stable sorting:**
- Package search results: by name, then by repo path
- Link lists: by from_package, then by to_package_id

See `docs/workflows/v3/cli/REPO_HUB.md` for complete hub system documentation.

## Select toolchain vs platform caps

- `maestro select toolchain {list|show|set|unset|detect|export}`
- `maestro platform caps {detect|list|show|prefer|require|unprefer|unrequire|export}`

See `docs/workflows/v3/cli/SELECT_TOOLCHAIN.md` and `docs/workflows/v3/cli/PLATFORM_CAPS.md` for semantics.

## Log scanning and observability

- `maestro log scan [--source <PATH>] [--last-run] [--kind {build|run|any}]`
  - Scans build/run output or log files for errors/warnings
  - Produces stable fingerprints for findings
  - Stores results in `docs/maestro/log_scans/<SCAN_ID>/`
- `maestro log list` — List all log scans
- `maestro log show <SCAN_ID>` — Show scan details and findings

## Issues management and triage

- `maestro issues list [--severity {blocker|critical|warning|info}] [--status {open|resolved|ignored}]`
- `maestro issues show <ISSUE_ID>` — Show issue details including occurrences
- `maestro issues add --from-log <SCAN_ID|PATH>` — Ingest findings from log scan into issues
- `maestro issues add --manual --message <MSG> [--severity <LEVEL>]` — Manually create issue
- `maestro issues triage [--auto] [--severity-first]` — Triage issues (assign severity, propose tasks)
- `maestro issues link-task <ISSUE_ID> <TASK_ID>` — Link issue to task (bidirectional)
- `maestro issues resolve <ISSUE_ID> [--reason <REASON>]` — Mark issue as resolved
- `maestro issues ignore <ISSUE_ID> [--reason <REASON>]` — Ignore issue (won't block work)

Issue fingerprints:
- Stable hash of normalized message + optional tool/file
- Same error → same issue across scans (deduplication)

## AI Cache management

- `maestro cache stats` — Show cache statistics (user + repo cache)
- `maestro cache show <PROMPT_HASH>` — Show cache entry details
- `maestro cache prune [--scope {user|repo}] [--older-than N]` — Prune old cache entries

Configuration via environment variables:
- `MAESTRO_AI_CACHE={on|off}` — Enable/disable cache (default: on)
- `MAESTRO_AI_CACHE_SCOPE={auto|user|repo}` — Cache scope preference (default: auto)
- `MAESTRO_AI_CACHE_WATCH=<glob;glob;...>` — Watch patterns for workspace fingerprinting

Cache behavior:
- Reuses prior AI results for identical prompts (stable SHA256 hash)
- Validates workspace fingerprint (git HEAD + watched file hashes)
- Supports both user-level ($HOME/.maestro/cache/ai/) and repo-level (docs/maestro/cache/ai/) caching
- Repo cache has priority for lookup; useful for deterministic test runs

## Ops automation (doctor + run)

### maestro ops doctor

Run health checks and report gates/blockers with recommended commands.

```
maestro ops doctor
  [--format {text|json}]
  [--strict]
  [--ignore-gates]
```

Arguments:
- `--format {text|json}`: Output format (default: text)
- `--strict`: Treat warnings as errors (non-zero exit code)
- `--ignore-gates`: Report gates but do not enforce them

Exit codes:
- `0`: No fatal findings
- `2`: Fatal findings present (blockers, locked repo)
- `3`: Internal error

### maestro ops run

Execute a deterministic ops plan (YAML runbook).

```
maestro ops run <PLAN>
  [--dry-run]
  [--format {text|json}]
  [--continue-on-error]
```

Arguments:
- `PLAN`: Path to ops plan YAML file
- `--dry-run`: Show what would be executed without running
- `--format {text|json}`: Output format (default: text)
- `--continue-on-error`: Continue executing steps even if one fails

Behavior:
- Only `maestro:` command steps allowed (no arbitrary shell)
- Creates run record under `docs/maestro/ops/runs/<RUN_ID>/`
- Run ID is deterministic (timestamp + kind)
- Dry-run creates run record but skips execution

### maestro ops list

List ops run records.

```
maestro ops list
```

Aliases: `ls`

### maestro ops show

Show ops run details.

```
maestro ops show <RUN_ID>
```

Aliases: `sh`

Arguments:
- `RUN_ID`: Run ID from `ops list`

See also:
- `docs/workflows/v3/cli/OPS_RUN_FORMAT.md` - Ops plan YAML format specification

## Plan decompose

### maestro plan decompose

Decompose freeform request into structured WorkGraph plan with verifiable DoD.

```bash
maestro plan decompose [OPTIONS] <freeform>
maestro plan decompose -e [OPTIONS]
```

Aliases: `dec`

Arguments:
- `<freeform>`: Freeform request text (optional if using `-e`)

Options:
- `-e, --eval` - Read freeform input from stdin
- `--engine ENGINE` - AI engine to use (default: planner role engine)
- `--profile PROFILE` - Planning profile: default, investor, purpose (default: default)
- `--domain DOMAIN` - Domain: runbook, issues, workflow, convert, repo, general (default: general)
- `--json` - Output full WorkGraph JSON to stdout
- `--out PATH` - Write WorkGraph JSON to custom path
- `-v, --verbose` - Show evidence summary, engine, validation summary
- `-vv, --very-verbose` - Also print AI prompt and response

Behavior:
- Performs repo-agnostic discovery (max 40 files, 200KB)
- Uses AI to generate WorkGraph JSON with tracks/phases/tasks
- Validates all tasks have executable definition_of_done (hard gate)
- Auto-repairs once if validation fails
- Saves to `docs/maestro/plans/workgraphs/{id}.json` by default

See also:
- `docs/workflows/v3/cli/PLAN_DECOMPOSE.md` - Full decompose documentation

## Convert plan approval

- `maestro convert plan <PIPELINE_ID>`
- `maestro convert plan <PIPELINE_ID> {show|approve|reject|status|history}`
- `maestro convert plan {show|approve|reject|status|history} <PIPELINE_ID>`
- `maestro convert plan show <PIPELINE_ID>`
- `maestro convert plan approve <PIPELINE_ID> [--reason <TEXT>]`
- `maestro convert plan reject <PIPELINE_ID> [--reason <TEXT>]`
- `maestro convert run <PIPELINE_ID> [--ignore-gates]`

Behavior:
- `convert run` requires an approved plan unless `--ignore-gates` is set.
- Approve/reject are idempotent; repeats are no-ops with a logged message.

## Work gates and blockers

- `maestro work gate status` — Show current gate status (blockers, warnings)
- `maestro work start task <TASK_ID> [--ignore-gates] [--override gate:<NAME>]`
  - Gates block work start if blocker issues exist with no linked in-progress tasks
  - Use `--ignore-gates` to bypass all gates
  - Use `--override gate:BLOCKED_BY_BUILD_ERRORS` to bypass specific gate

Gate semantics:
- Blocker issues (e.g., build failures) create `BLOCKED_BY_BUILD_ERRORS` gate
- Gates are surfaced before work starts
- Override requires explicit flag; no silent bypass

## Legacy Command Kill Switch

### MAESTRO_ENABLE_LEGACY

**Purpose:** Control visibility and availability of deprecated legacy commands.

**Default:** unset (legacy commands disabled)

**Accepted values:**
- `0`, `false`, `no`, unset → Legacy commands disabled (default)
- `1`, `true`, `yes` → Legacy commands enabled

### Behavior

**Default Mode (unset or MAESTRO_ENABLE_LEGACY=0):**
- Legacy commands **NOT** registered in parser
- `maestro session --help` fails with argparse error (command not found)
- `maestro --help` does NOT list legacy commands
- Helpful error message suggests canonical replacement

**Legacy Mode (MAESTRO_ENABLE_LEGACY=1):**
- Legacy commands registered with `[DEPRECATED]` markers
- All 5 legacy commands functional (session, understand, resume, rules, root)
- `maestro --help` lists legacy commands marked as deprecated
- Deprecation warning banner displayed when command invoked

### Legacy Commands and Replacements

- `maestro session` → `maestro wsession`
- `maestro understand` → `maestro repo resolve` + `maestro runbook export`
- `maestro resume` → `maestro discuss resume` / `maestro work resume`
- `maestro rules` → `maestro repo conventions` / `maestro solutions`
- `maestro root` → `maestro track` / `maestro phase` / `maestro task`

### Usage Examples

```bash
# Enable legacy commands (temporary)
export MAESTRO_ENABLE_LEGACY=1
maestro session list  # Works with deprecation warning

# Disable legacy commands (default)
unset MAESTRO_ENABLE_LEGACY
maestro session list  # Error: command not available

# Explicit disable
export MAESTRO_ENABLE_LEGACY=0
maestro session list  # Error: command not available
```

### Error Message Example

When legacy disabled and user tries to invoke:

```
Error: 'session' command is not available.
Use: maestro wsession instead.

To enable legacy commands (for backward compatibility):
  export MAESTRO_ENABLE_LEGACY=1

See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md
```

### See Also

- [CLI Surface Contract](./CLI_SURFACE_CONTRACT.md) - Complete contract and migration playbook
- [Deprecation Policy](./DEPRECATION.md) - Timeline and rationale
- [Test Contract](../../tests/test_cli_surface_contract.py) - Behavioral tests
