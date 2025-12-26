# Settings Audit (v3)

This audit proposes a minimal, stable settings surface. Favor few knobs over many.

## AI role selection

- `planner_engine`: used for planning, decomposition, and high-level synthesis.
- `worker_engine`: used for execution, patching, and code manipulation.

Heuristics:

- Use `planner_engine` for `track|phase|task discuss`, `runbook discuss`, and workflow authoring.
- Use `worker_engine` for `work`, `wsession`, and task execution flows.

## Verbosity defaults

- Default: normal (neither quiet nor verbose).
- `--quiet`: only essential outputs and errors.
- `--verbose`: includes debug info, guard outcomes, and store writes.

## Cookie vs context

- `wsession` cookie is the primary coupling mechanism.
- Avoid a separate persistent "context set" unless required for engine resume.
- Recommend explicit flags: `--cookie <id>` only where necessary (breadcrumb and resume). 

## Safety knobs

- `dangerously_skip_permissions`: scope to commands that mutate repo truth or external files.
- UX: require explicit confirmation in interactive mode, allow flag in automation.

## Git context guard

- Setting: `git_guard` with values `strict|lenient`.
- `strict` blocks mutations on dirty tree or wrong branch; `lenient` warns.

## Feature flags

- Use minimal flags for legacy command compatibility (e.g., `legacy_build_alias=true`).
- Avoid per-subcommand flags unless a deprecation window is active.
