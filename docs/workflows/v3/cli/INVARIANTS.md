# v3 CLI Invariants (Hard Gates)

These are the rules the system must enforce. If any invariant fails, the CLI must refuse to proceed and explain the next step.

See also:
- `docs/workflows/v3/cli/GATES.md`
- `docs/workflows/v3/cli/SIGNATURES.md`
- `docs/workflows/v3/cli/CLI_GAPS.md`
- `docs/workflows/v3/reports/ledger_convergence.md`

## Help contract

- Bare keywords show extended help and exit 0.
  - Failure: N/A (informational command).
  - Examples: `maestro workflow`, `maestro task`, `maestro repo`
  - Implemented in: CLI parser help behavior.
- `--help/-h` flags remain supported but are non-canonical in docs.
  - Canonical form: `maestro <keyword>` or `maestro <keyword> help`
  - Implemented in: argparse standard behavior.

## Data stores

- Repo truth lives under `./docs/maestro/**` (JSON only).
  - Failure: repo truth missing or non-JSON.
  - Next: run `maestro init` or repair repo truth.
  - Implemented in: CLI validation + schema gate.
- Hub/host truth lives under `$HOME/.maestro/**`.
  - Failure: missing hub profiles or detection cache.
  - Next: run `maestro select toolchain detect` or `maestro platform caps detect`.
  - Implemented in: CLI validation + hub access layer.
- Never use `./.maestro` for project state.
  - Failure: any write under repo root `./.maestro`.
  - Next: migrate to `./docs/maestro/**`.
  - Implemented in: CLI validation and storage layer.

## Build/make gates

- `maestro make` must not run unless repo context and target are valid.
  - Failure: repoconf missing or no target selected.
  - Next: `maestro repo resolve {lite|deep}` then `maestro repo conf select-default target <TARGET>`.
  - Implemented in: CLI validation + repoconf gate.

## TU/AST gates

- `maestro tu` must not run unless build context is valid.
  - Failure: repoconf missing or toolchain not selected.
  - Next: select toolchain, resolve repo, set target, then re-run.
  - Implemented in: CLI validation + tu gate.

## Identity discipline

- Breadcrumbs require a cookie.
  - Failure: missing cookie for `wsession breadcrumb add`.
  - Next: resume or show session to obtain cookie.
  - Implemented in: CLI validation.
- Work session must have explicit open/closed state.
  - Failure: operations on a closed session.
  - Next: `maestro work start` or `maestro work resume`.
  - Implemented in: session store + CLI.
- AI resume tokens are valid only until session close.
  - Failure: resume token expired.
  - Next: start a new discuss/work session.
  - Implemented in: session store.

## Work session stacking (managed mode)

- Parent cannot be closed while any child is running or paused.
  - Failure: attempted to close parent with open subwork.
  - Next: `maestro work subwork list <PARENT_WSESSION_ID>` then close children.
  - Implemented in: `maestro wsession close`.
- Child sessions must include `parent_wsession_id`.
  - Failure: orphan child session detected.
  - Next: recreate via `maestro work subwork start` or close orphan.
  - Implemented in: session store + ops doctor.
- Closing a child emits a `result` breadcrumb into the parent (unless parent missing).
  - Failure: missing parent breadcrumb for subwork completion.
  - Next: re-run `maestro work subwork close` or add breadcrumb manually.
  - Implemented in: `maestro work subwork close`.
- Session operations are idempotent where reasonable.
  - Failure: duplicate result breadcrumbs or state flips on re-run.
  - Next: ensure handlers are safe to re-invoke with same IDs.

## Discuss contract

- `/done` must return a single valid JSON object.
  - Failure: invalid JSON.
  - Next: re-run or resume discuss; no OPS applied.
  - Implemented in: discuss handler.

## Git guard

- Branch switching during active work sessions is forbidden (strict guard).
  - Failure: repo branch changed while work session open.
  - Next: close work session or set guard mode to lenient.
  - Implemented in: work session guard + CLI.

## Verb standardization

- All commands must use canonical verbs: `list`, `show`, `add`, `edit`, `remove` (or `rm` alias).
  - Failure: non-canonical verb used in implementation.
  - Next: use approved aliases (`ls` for `list`, `sh` for `show`, `rm` for `remove`).
  - Canonical: `list`, `show`, `add`, `edit`, `remove`
  - Approved aliases: `ls`, `sh`, `rm`
  - Implemented in: CLI parser and documentation.
- Legacy verb forms must emit deprecation warnings.
  - Example: `convert new` should warn and suggest `convert add`.
  - Implemented in: command handlers.

## Legacy command deprecation

- Legacy keywords must not appear in default help or must show deprecation notice.
  - Legacy commands: `session`, `resume`, `rules`, `root`, `understand`
  - Replacement paths:
    - `session` → `wsession` (for work sessions) or `discuss` (for AI sessions)
    - `resume` → `work resume` or `discuss resume`
    - `rules` → `solutions` (for policy rules)
    - `root` → deprecated (use `track`/`phase`/`task` hierarchy)
    - `understand` → deprecated (fold into `repo resolve` or `runbook`)
  - Implemented in: CLI parser help filtering and command handlers.

## Log scan determinism

- Log scans produce stable, deterministic results for the same input.
  - Failure: same log file scanned twice produces different scan IDs or findings.
  - Next: verify scan normalization rules and fingerprint algorithm.
  - Implemented in: log scan storage and fingerprint generation.
- Scan storage is append-only; scans are never modified after creation.
  - Failure: attempt to modify existing scan results.
  - Next: create new scan instead of modifying existing.
  - Implemented in: log scan storage layer.
- Scan results stored under `docs/maestro/log_scans/<SCAN_ID>/` with:
  - `meta.json` — scan metadata (timestamp, source, command context)
  - `raw.txt` — raw log snapshot
  - `findings.json` — extracted findings with fingerprints
  - Failure: missing or malformed scan files.
  - Next: re-run scan or repair scan storage.
  - Implemented in: log scan command and storage layer.

## Issue fingerprints and deduplication

- Issues have stable fingerprints; same error → same issue across scans.
  - Fingerprint = hash of normalized message + optional tool + file basename.
  - Normalization: remove absolute paths, collapse line-specific numbers if too noisy.
  - Failure: duplicate issues created for same error.
  - Next: verify fingerprint normalization and deduplication logic.
  - Implemented in: issues ingestion and fingerprint generation.
- Issue ingestion from logs is idempotent.
  - Existing issue by fingerprint → update occurrences list and last_seen.
  - New fingerprint → create new issue.
  - Failure: same log ingested twice creates duplicate issues.
  - Next: verify deduplication by fingerprint.
  - Implemented in: `maestro issues add --from-log` command.
- Issues storage lives under `docs/maestro/issues/` (JSON).
  - Failure: issues stored in markdown or old format.
  - Next: migrate to JSON truth under `docs/maestro/`.
  - Implemented in: issues storage layer.

## AI Cache determinism and validation

- AI cache entries have stable prompt hashes; same prompt + context → same hash.
  - Hash = SHA256(prompt + engine + model + context_kind + inputs_signature).
  - Failure: same prompt produces different hashes across runs.
  - Next: verify prompt hash normalization (whitespace, canonicalization).
  - Implemented in: `maestro.ai.cache.AiCacheStore.compute_prompt_hash()`.
- Cache lookup validates workspace fingerprint.
  - Fingerprint = git HEAD + dirty flag + watched file hashes.
  - Failure: workspace changed since cache entry created → cache miss.
  - Next: commit changes or use `lenient_git` mode for testing.
  - Implemented in: `maestro.ai.cache.AiCacheStore.validate_entry()`.
- Cache entries are rejected if workspace fingerprint doesn't match.
  - Stale entries are marked `validity=stale` but not deleted.
  - Failure: stale cache applied to changed workspace.
  - Next: run AI again to create fresh cache entry, or verify workspace state.
  - Implemented in: cache validation layer in discuss command.
- Cache storage is dual-scope: user ($HOME/.maestro/cache/ai/) and repo (docs/maestro/cache/ai/).
  - Repo cache has priority for lookup (useful for deterministic tests).
  - Failure: cache stored in wrong location or mixed scopes.
  - Next: verify `MAESTRO_AI_CACHE_SCOPE` environment variable.
  - Implemented in: `maestro.ai.cache.AiCacheStore` with env var configuration.
- Cache entries are immutable once created; updates create new entries.
  - Failure: attempt to modify existing cache entry.
  - Next: create new cache entry with different prompt hash.
  - Implemented in: cache storage layer (no update methods).

## Archive lifecycle (runbooks and workflows)

- Archive operations move items (not copy); item is active OR archived, never both.
  - Failure: item exists in both active and archived locations.
  - Next: verify archive implementation uses move/rename, not copy.
  - Implemented in: `maestro.archive.runbook_archive` and `maestro.archive.workflow_archive` using `shutil.move()`.
- Archive uses timestamped folders (YYYYMMDD) to mirror original path structure.
  - Format: `archived/YYYYMMDD/<original_relative_path>`
  - Failure: archived items not in timestamped folders.
  - Next: verify archive path generation logic.
  - Implemented in: `maestro.archive.storage.get_timestamp_folder()`.
- Archiving is idempotent: archiving the same item twice fails with clear error.
  - Failure: attempt to archive already-archived item.
  - Next: check archive index to verify item not already archived.
  - Implemented in: archive functions check index before archiving.
- Archive metadata is stored in separate index files (archive_index.json).
  - Runbook archive index: `docs/maestro/runbooks/archive_index.json`
  - Workflow archive index: `docs/maestro/workflows/archive_index.json`
  - Failure: index file missing or corrupted.
  - Next: index automatically created on first archive operation.
  - Implemented in: `maestro.archive.storage.load_archive_index()` and `save_archive_index()`.
- Default listings exclude archived items; `--archived` flag required to view archive.
  - Failure: archived items appear in default list output.
  - Next: verify list implementation filters out archived directories.
  - Implemented in: list handlers check `args.archived` flag and use separate functions.
- Restore operations check original path is unoccupied before restoring.
  - Failure: attempt to restore when original path exists.
  - Next: move or rename existing file at original path first.
  - Implemented in: restore functions validate original path before moving file back.
- Archive IDs are globally unique (UUID4); no collision risk.
  - Failure: archive ID collision.
  - Next: verify UUID generation is random (not sequential).
  - Implemented in: `maestro.archive.storage.generate_archive_id()` using `uuid.uuid4()`.

## Work gates and blockers

- Blocker issues (build errors, critical failures) gate work start.
  - Gate name: `BLOCKED_BY_BUILD_ERRORS`
  - Trigger: blocker severity issues with no linked in-progress task.
  - Failure: work start attempted with active blocker gate.
  - Next: fix blocker issue, link to task, or use `--ignore-gates` / `--override gate:BLOCKED_BY_BUILD_ERRORS`.
  - Implemented in: work command gate validation.
- Work prioritizes blocker-linked tasks first.
  - Failure: non-blocker tasks started before blocker tasks.
  - Next: use `maestro work gate status` to see blockers; start blocker-linked tasks first.
  - Implemented in: work command task prioritization.
- Gate overrides require explicit flags; no silent bypass.
  - `--ignore-gates` bypasses all gates.
  - `--override gate:<NAME>` bypasses specific named gate.
  - Failure: gate bypassed without explicit flag.
  - Next: add explicit override flag to work start command.
  - Implemented in: work command flag parsing and gate validation.

## WorkGraph decomposition (plan decompose)

- All WorkGraphs must have verifiable Definitions-of-Done (DoD).
  - Failure: task missing `definition_of_done` or DoD is empty.
  - Next: AI auto-repairs once; if still invalid, manual fix required.
  - Implemented in: WorkGraph schema validation (`maestro/data/workgraph_schema.py`).
- No "meta-runbook tasks" - all tasks must be machine-checkable.
  - Failure: DoD has no `kind="command"` or `kind="file"` entry.
  - Next: add explicit command to run or file to check.
  - Implemented in: `DefinitionOfDone.__post_init__` validation.
- Repo discovery must respect budgets (no unbounded resource use).
  - Max 40 files processed
  - Max 200KB total bytes collected
  - Max 5 seconds per binary execution
  - Failure: N/A (budgets enforced internally)
  - Next: N/A (warnings logged if budget exceeded)
  - Implemented in: `maestro/repo/discovery.py::discover_repo()`.
- WorkGraph storage must be atomic (no partial writes).
  - Failure: WorkGraph file corrupted or incomplete.
  - Next: re-run `maestro plan decompose` to regenerate.
  - Implemented in: `maestro/archive/workgraph_storage.py::save_workgraph()` using atomic write pattern.
- WorkGraph IDs must be deterministic and collision-resistant.
  - Format: `wg-YYYYMMDD-<shortsha>` (date + SHA256 hash of goal)
  - Failure: duplicate ID generated (extremely rare).
  - Next: change goal text slightly and regenerate.
  - Implemented in: `WorkGraph.__post_init__` ID generation.

## Plan enact (WorkGraph materialization)

- WorkGraph materialization is idempotent.
  - Failure: running enact twice creates duplicate tracks/phases/tasks.
  - Next: verify JsonStore checks for existing items before creating.
  - Implemented in: `WorkGraphMaterializer.materialize()` checks for existing items and updates instead of creating.
- Track/Phase/Task IDs must be stable and deterministic.
  - Failure: same WorkGraph produces different IDs on re-enact.
  - Next: use WorkGraph-provided IDs (TRK-001, PH-001, TASK-001).
  - Implemented in: `WorkGraphMaterializer` uses WorkGraph IDs directly.
- Enact only writes to docs/ (or MAESTRO_DOCS_ROOT equivalent).
  - Failure: enact writes to repo code or other locations.
  - Next: verify JsonStore base_path is under docs/.
  - Implemented in: `JsonStore` validation and `handle_plan_enact()` path handling.

## Plan run (WorkGraph execution)

- Run records are append-only and deterministic.
  - Failure: modifying existing events or run meta after creation.
  - Next: verify append_event() only appends, never modifies.
  - Implemented in: `maestro.plan_run.storage.append_event()` appends to JSONL file.
- Run IDs must be deterministic and collision-resistant.
  - Format: `wr-YYYYMMDD-HHMMSS-<shortsha>` (date + time + SHA256 hash)
  - Failure: duplicate run ID generated.
  - Next: verify generate_run_id() uses workgraph_id + timestamp hash.
  - Implemented in: `maestro.plan_run.models.generate_run_id()`.
- Resume must detect WorkGraph changes and refuse to continue.
  - Failure: resume continues with stale/changed WorkGraph.
  - Next: compute workgraph hash on start and compare on resume.
  - Implemented in: `WorkGraphRunner._resume_run()` checks workgraph_hash.
- Topological ordering must be deterministic.
  - Failure: same WorkGraph produces different task execution order.
  - Next: sort runnable tasks by task_id for stable ordering.
  - Implemented in: `WorkGraphRunner._get_runnable_tasks()` with sorted().
- Dry-run mode must never execute subprocesses.
  - Failure: commands executed in dry-run mode.
  - Next: verify _dry_run_task() never calls subprocess.
  - Implemented in: `WorkGraphRunner._dry_run_task()` only emits events.
- Command execution must use timeout to prevent hangs.
  - Default: 60s (configurable via MAESTRO_PLAN_RUN_CMD_TIMEOUT).
  - Failure: commands run indefinitely.
  - Next: verify subprocess.run() uses timeout parameter.
  - Implemented in: `WorkGraphRunner._execute_command()` with timeout.
- Run records must only write to docs/maestro/plans/workgraphs/.
  - Failure: run records written to repo code or other locations.
  - Next: verify get_run_dir() returns path under workgraph_dir.
  - Implemented in: `maestro.plan_run.storage.get_run_dir()`.

## Runbook actionability (runbook resolve --actionable)

- All runbook steps must be executable when --actionable flag is set.
  - Each step requires `command` (string) or `commands` (list of strings).
  - Failure: step missing both `command` and `commands` fields.
  - Next: AI re-generates or falls back to WorkGraph; user runs `maestro plan enact <WG_ID>`.
  - Implemented in: `maestro.commands.runbook.validate_runbook_actionability()`.
- Meta-steps (documentation/organization without executable commands) are rejected under --actionable.
  - Examples of rejected meta-steps: "parse docs and organize", "create outline", "review code structure"
  - Failure: step has `action` like "Review documentation" but no command field.
  - Next: AI adds executable command (e.g., `grep`, `sed`, `ls`) or falls back to WorkGraph.
  - Implemented in: `validate_runbook_actionability()` checks each step for command presence.
- Placeholders are allowed in commands (e.g., <REPO_ROOT>, <BSS_BIN>, <DOCS_DIR>).
  - Failure: N/A (placeholders are valid; user replaces them at execution time).
  - Next: N/A (guidance provided in step `expected` or documentation).
  - Implemented in: no validation against placeholders; they're string literals.
- --actionable flag enforcement falls back to WorkGraph on validation failure.
  - Failure: runbook validation fails (schema or actionability).
  - Next: WorkGraph generated and saved; user runs `maestro plan enact <WG_ID>`.
  - Implemented in: `handle_runbook_resolve()` catches actionability errors and calls WorkGraphGenerator.
- Evidence-pack driven variable hints are included in AI prompt when available.
  - Hints format: `<VARIABLE>: candidate_path` (e.g., `<BSS_BIN>: ./build_maestro/bss`).
  - Failure: N/A (best-effort hint; AI may or may not use them).
  - Next: N/A (informational only).
  - Implemented in: `_create_runbook_generation_prompt()` appends hints section from evidence pack CLI candidates.
- Without --actionable flag, meta-steps are allowed (backward compatible).
  - Failure: N/A (default mode permits meta-steps).
  - Next: N/A (no validation enforced unless --actionable is set).
  - Implemented in: `handle_runbook_resolve()` skips actionability validation unless `args.actionable` is True.

## WorkGraph scoring (plan score / plan recommend)

- WorkGraph scoring is deterministic (no AI, no network calls).
  - Failure: same WorkGraph + same profile produces different scores.
  - Next: verify scoring formulas are pure functions with no randomness.
  - Implemented in: `maestro.builders.workgraph_scoring.score_task()` and `rank_workgraph()`.
- Scoring is bounded and fast (<100ms for 100+ tasks).
  - Failure: scoring takes >1 second or unbounded time.
  - Next: profile scoring engine and optimize hot paths.
  - Implemented in: deterministic heuristics with no file I/O loops.
- JSON output has stable, sorted keys for scripting.
  - Failure: JSON output order changes between runs.
  - Next: verify `json.dumps(..., sort_keys=True)` is used.
  - Implemented in: `handle_plan_score()` uses `sort_keys=True`.
- Top N output prevents information overload (default: top 10 tasks, top 3 recommendations).
  - Failure: output prints all tasks without limit.
  - Next: verify slicing `[:10]` and `[:3]` is applied.
  - Implemented in: `handle_plan_score()` slices to top 10; `handle_plan_recommend()` uses `--top` parameter (default 3).
- Scoring profiles (investor, purpose, default) produce meaningfully different orderings.
  - Failure: all profiles produce same ranking.
  - Next: verify formulas differ (investor: ROI-first; purpose: mission-first; default: balanced).
  - Implemented in: `score_task()` has distinct formulas per profile.
- Ops doctor shows top 3 WorkGraph recommendations when -v flag is used.
  - Failure: doctor doesn't show recommendations even with -v.
  - Next: verify `check_workgraph_recommendations()` is called when `verbose=True`.
  - Implemented in: `run_doctor()` adds WORKGRAPH_RECOMMENDATIONS finding when verbose=True.
- Ops doctor recommendations are bounded (latest WorkGraph only, top 3 tasks).
  - Failure: doctor scans all WorkGraphs or shows too many tasks.
  - Next: verify only latest WG by mtime is loaded; top 3 slicing applied.
  - Implemented in: `check_workgraph_recommendations()` sorts by mtime, takes first file, returns top 3.
