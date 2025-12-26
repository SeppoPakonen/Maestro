# v3 CLI Normalization Summary

## P0 gaps (blocking invariants)

See `docs/workflows/v3/cli/CLI_GAPS.md` for the P0 list mapped to `docs/workflows/v3/cli/INVARIANTS.md`.

## What v3 fixes

- Normalized verbs (`list/show/add/edit/rm`), keyword-first growth, and consistent help behavior.
- Consolidated naming conflicts (`make` canonical, `build` alias).
- Clear ownership of discussion flows per namespace plus a router entrypoint.
- Explicit gaps and deprecation paths for legacy/problem commands.

## What v3 breaks

- Long or flag-based commands (`repo conf --show`, `repo resolve --level deep`) are replaced by keyword forms.
- Legacy commands (`understand`, `session`, `root`, `rules`) are folded or deprecated.
- `task complete` is replaced by `task set status`.

## Top 10 recommended changes

1. Make `maestro make` the canonical build entrypoint, keep `build` alias.
2. Enforce keyword-help behavior on bare keywords.
3. Implement `repo conf show` and standardize repo conf access.
4. Add workflow graph CRUD (`workflow init`, `node add`, `edge add`, `validate`, `export`, `render`).
5. Add `repo hub` query/list commands with `HOME_HUB_REPO` store.
6. Normalize work session lifecycle (`work start|resume|pause|stop`, `wsession breadcrumb add|list`).
7. Make `discuss` router explicit and enforce JSON contract gating.
8. Define issue/solution linkage commands under `issues link`.
9. Provide `convert add` and `convert run` to replace ad-hoc `convert new`.
10. Add `ops commit` helpers with guard integration.

## Top 10 aliases to keep temporarily

1. `build` -> `make`
2. `repo config show` -> `repo conf show`
3. `repo show-config` -> `repo conf show`
4. `repo resolve --level deep` -> `repo resolve deep`
5. `task complete` -> `task set status <id> done`
6. `issues link-solution` -> `issues link solution`
7. `workflow create` -> `workflow add`
8. `runbook create` -> `runbook add`
9. `work --resume` -> `work resume`
10. `session` -> `wsession` / `ai resume` (dual alias during transition)
