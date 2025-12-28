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
