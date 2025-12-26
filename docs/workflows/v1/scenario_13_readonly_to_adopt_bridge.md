---
id: WF-13
title: Read-only → Adopt bridge (home hub to repo truth)
tags: [readonly, adopt, init, home-hub, repo-truth, import, resolve, repo-conf]
entry_conditions: |
  - Operator is in an existing repository with no Maestro adoption yet
  - Repository contains buildable code
  - Maestro is installed and accessible
  - Read-only mode is supported (commands that write to $HOME/.maestro/ only)
exit_conditions: |
  - If adopt decision is "No": Nothing repo-local is written, only hub outputs created
  - If adopt decision is "Yes": `./docs/maestro/**` structure created and populated
  - RepoConf exists (WF-12) and build can proceed
artifacts_created: |
  - `$HOME/.maestro/repo/` outputs during read-only inspection (if performed)
  - Optionally: `./docs/maestro/tracks/`, `./docs/maestro/phases/`, `./docs/maestro/tasks/`, `./docs/maestro/repo/`
failure_semantics: |
  - Hard stop if read-only mode attempts to write to repo truth paths
  - Hard stop if init validation fails (malformed repo truth structure)
  - Hard stop if RepoConf is missing after adoption and no candidates can be generated
links_to: [WF-03, WF-01, WF-09, WF-10, WF-12]
related_commands: ["maestro repo resolve", "maestro init", "Proposed: maestro import-from-hub"]
---

# WF-13: Read-only → Adopt bridge (home hub to repo truth)

This workflow formalizes the bridge from read-only inspection (WF-03 style) to stateful adoption (WF-01 style). It defines the explicit "Adopt" decision point and the process of creating repo-local truth from home hub data.

## Phase 0 — Read-only inspection

The Operator is in an existing repository with no Maestro adoption yet. They perform read-only inspection to understand the repository structure without creating any repo-local state.

### Actions:
- Operator runs read-only commands:
  - `maestro repo resolve --level lite` (producing hub outputs only)
  - Optional: `maestro make build` (report diagnostics only; no issues/tasks in repo truth)
- All write outputs go to `$HOME/.maestro/repo/` (per WF-09 storage contract)

### Verification:
- Confirm no files were created in `./docs/maestro/` or other repo-local truth paths
- Confirm outputs exist in `$HOME/.maestro/repo/` as expected

## Phase 1 — Decision gate: Adopt?

The Operator reviews the scan results and decides whether to adopt the repository with full Maestro state management.

### Decision Options:
- **Yes**: Proceed to Phase 2 (Adopt via init)
- **No**: Stop; nothing repo-local is written

## Phase 2 — Adopt via init

If the Operator decides to adopt, they run `maestro init` to create the repo-local truth structure.

### Actions:
- `maestro init` creates `./docs/maestro/**` structure:
  - `./docs/maestro/tracks/`
  - `./docs/maestro/phases/`
  - `./docs/maestro/tasks/`
  - `./docs/maestro/repo/` (for repo-specific truth, separate from hub)
- Structural validation confirms the layout is parseable and correct
- No usage of `./.maestro` or legacy `docs/todo.md`/`docs/done.md`

### Verification:
- Confirm `./docs/maestro/` directory exists with correct subdirectories
- Confirm no legacy paths (`./.maestro`, `docs/todo.md`, `docs/done.md`) are created or referenced

## Phase 3 — Import / re-materialize from Home Hub (optional)

This is the core "bridge" value of WF-13, allowing the Operator to bring previously generated scan outputs from the Home Hub into repo truth.

### Strategy A: Re-run resolve into repo truth
- After init, run `maestro repo resolve --level lite` again, but now writing to `./docs/maestro/**`
- Most deterministic approach as it re-analyzes the current repository state
- Recommended as the current practice if import functionality is not implemented

### Strategy B: Import from hub (Planned feature)
- Import the previously generated read-only scan outputs from `$HOME/.maestro/**/repo` into repo truth
- Requires a stable identity mapping from repo path to hub record
- **Status**: Planned but not yet implemented in current codebase

### Verification:
- If using Strategy A: Confirm resolve outputs are written to `./docs/maestro/repo/`
- If using Strategy B (when implemented): Confirm hub data is correctly mapped to repo truth

## Phase 4 — RepoConf gate

After adoption and import/re-run, ensure RepoConf exists (WF-12) before proceeding to build/TU workflows.

### Actions:
- Verify `maestro repo conf` can successfully extract build configuration
- If RepoConf is missing:
  - Generate candidates from resolve results, or
  - Author manually (WF-11)

### Verification:
- Confirm RepoConf exists and can provide necessary build information
- Confirm build operations can proceed successfully

## Ownership rules

### Pre-adopt (Phase 0):
- Hub-only, read-only outputs
- All scan/build results stored in `$HOME/.maestro/repo/`
- No repo-local truth files created

### Post-adopt (Phases 2-4):
- Repo truth under version control in `./docs/maestro/`
- Hub remains as cross-repo index/cache
- Repo truth becomes the canonical source for this repository's Maestro state

## Tests implied by WF-13

### Unit Tests:
- Read-only mode does not touch repo truth paths (verifies Phase 0)
- Adopt/init creates `./docs/maestro/**` layout correctly (verifies Phase 2)
- (When import exists) hub import maps correctly to repo truth (verifies Phase 3 Strategy B)

### Integration Tests:
- Start with no `./docs/maestro/**`
- Run read-only scan → verify hub writes only to `$HOME/.maestro/repo/`
- Adopt → verify repo truth created in `./docs/maestro/`
- Re-run resolve → verify repo truth populated and build can proceed