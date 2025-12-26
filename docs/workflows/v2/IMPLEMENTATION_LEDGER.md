# Implementation Ledger

## Purpose

This ledger tracks **spec→code deltas** between the v2 canonical workflow specification and the actual codebase implementation. It serves as:

1. A **record of contradictions** between what workflows specify and what the code does
2. A **task list** for alignment work required to bring code into conformance with spec
3. An **audit trail** showing when and why implementation decisions diverge from spec
4. A **living contract** ensuring v2 is not just aspirational documentation

## Status Definitions

Each ledger entry has one of these statuses:

- **proposed** — Delta identified, not yet reviewed
- **accepted** — Delta confirmed, implementation work approved
- **implemented** — Code changes completed
- **verified** — Implementation tested and confirmed to match spec
- **dropped** — Delta rejected; spec or observation was incorrect

## Entry Template

```markdown
### LEDGER-NNNN: [Brief description]

**Workflow**: WF-XX
**Layer**: intent|cli|code|observed
**Status**: proposed|accepted|implemented|verified|dropped

**Spec change**: What the v2 workflow specification defines SHOULD happen.

**Observed (v1 internal/deep)**: What the current code (as documented in v1 internal/deep) DOES happen.

**Required code changes**:
- Specific module/function/class modifications needed
- File paths and line numbers if applicable
- Breaking changes or migration steps

**Tests**:
- Test cases required to verify conformance
- Acceptance criteria

**Evidence**:
- Links to v1 diagrams: `v1/internal/deep/...`
- Links to IR files: `ir/wf/WF-XX.*.yaml`
- Links to source code: `maestro/...`

**Notes**: (Optional) Additional context, rationale, or discussion.
```

---

## Ledger Entries

### LEDGER-0001: Storage backend is JSON, not Markdown

**Workflow**: WF-09
**Layer**: code
**Status**: accepted

**Spec change**: Repository truth is stored in `./docs/maestro/**/*.json` (repo_model.json, repo_conf.json, packages.json, tasks.json, issues.json). No Markdown files should be used for persistent data.

**Observed (v1 internal/deep)**: Some v1 documentation suggests sessions or metadata might be stored in `.md` files. The actual code may already conform to JSON-only storage, but this needs verification.

**Required code changes**:
- Audit all file I/O in `maestro/` codebase
- Ensure no `*.md` files are written as persistent data (except human-readable exports)
- Confirm `session_model.py`, `repo_model.py`, and related modules use JSON exclusively
- Add validation to reject or warn on Markdown-based persistence

**Tests**:
- Unit tests for session load/save verifying JSON format
- Integration tests creating/modifying sessions and checking file format
- Regression tests ensuring no `.md` files appear in `./docs/maestro/`

**Evidence**:
- IR: `ir/wf/WF-09.intent.yaml` (storage_backend: json)
- v1: `v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md`
- Code: `maestro/session_model.py`, `maestro/modules/repo_model.py`

**Notes**: This is a critical invariant (`REPO_TRUTH_FORMAT_IS_JSON`) that must be enforced project-wide.

---

### LEDGER-0002: ./.maestro directory must not exist

**Workflow**: WF-09, WF-11, WF-12
**Layer**: code
**Status**: accepted

**Spec change**: Repository truth must reside in `./docs/maestro/`, never in `./.maestro`. Any code attempting to create or read from `./.maestro` should fail with a hard stop error.

**Observed (v1 internal/deep)**: Some legacy or experimental code paths may reference `.maestro` directory. This needs to be completely removed.

**Required code changes**:
- Grep codebase for `.maestro` references
- Replace all with `docs/maestro/` paths
- Add validation gate in `maestro/modules/utils.py` or similar to raise error if `./.maestro` is detected
- Update documentation and examples

**Tests**:
- Unit test verifying `get_repo_truth_dir()` returns `./docs/maestro/`
- Integration test attempting to create `./.maestro` and expecting failure
- Test that existing `./.maestro` directory triggers hard stop

**Evidence**:
- IR: `ir/wf/WF-09.intent.yaml`, `ir/wf/WF-11.intent.yaml`
- v1: `v1/scenario_11_manual_repo_model_and_conf.md`
- Code: `maestro/modules/utils.py`, `maestro/session_model.py`

**Notes**: Invariant `FORBID_REPO_DOT_MAESTRO`. This is non-negotiable for clarity and consistency.

---

### LEDGER-0003: Repo resolve is the detection spine

**Workflow**: WF-05, WF-10
**Layer**: cli, code
**Status**: accepted

**Spec change**: The `maestro repo resolve` command is the central detection mechanism that identifies packages, conventions, targets, and repo structure. All downstream commands (build, tu, convert) depend on `repo_resolve` having been run and `repo_model.json` being populated.

**Observed (v1 internal/deep)**: The v1 diagrams may show ad-hoc detection in individual command handlers. The spec requires a centralized detection spine.

**Required code changes**:
- Ensure `maestro/modules/repo_resolve.py` is the single source of truth for detection
- Other commands (`maestro build`, `maestro tu`, `maestro convert`) should read from `repo_model.json` and NOT re-detect
- Add validation gate in affected commands: "repo_model.json not found or incomplete → prompt user to run `maestro repo resolve`"

**Tests**:
- Test `maestro build` without prior `repo resolve` → expect error/prompt
- Test `maestro repo resolve` → verify `repo_model.json` created
- Test `maestro build` after `repo resolve` → expect success

**Evidence**:
- IR: `ir/wf/WF-05.intent.yaml`, `ir/wf/WF-10.intent.yaml`
- v1: `v1/scenario_05_repo_resolve_packages_conventions_targets.md`
- Code: `maestro/modules/repo_resolve.py`, `maestro/modules/command_handlers.py`

**Notes**: Invariant `REPO_RESOLVE_IS_DETECTION_SPINE`.

---

### LEDGER-0004: RepoConf gate for build/TU/convert

**Workflow**: WF-12
**Layer**: cli, code
**Status**: accepted

**Spec change**: Commands `maestro build`, `maestro tu`, and `maestro convert` require `repo_conf.json` to exist and be valid. If missing, these commands should fail with a hard stop directing the user to run `maestro repo conf`.

**Observed (v1 internal/deep)**: May not be enforced consistently; some commands may attempt to run without conf.

**Required code changes**:
- Add `require_repo_conf()` validation function in `maestro/modules/utils.py`
- Inject this gate into handlers for `build`, `tu`, `convert` commands
- Error message: "repo_conf.json not found. Run `maestro repo conf` to configure this repository."

**Tests**:
- Test `maestro build` without `repo_conf.json` → expect error
- Test `maestro tu` without `repo_conf.json` → expect error
- Test `maestro convert` without `repo_conf.json` → expect error
- Test after `maestro repo conf` → expect success

**Evidence**:
- IR: `ir/wf/WF-12.intent.yaml`
- v1: `v1/scenario_12_repo_conf_gate_for_build_tu_convert.md`
- Code: `maestro/modules/command_handlers.py`

**Notes**: Invariant `REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT`.

---

### LEDGER-0005: Branch switch forbidden during work session

**Workflow**: WF-14
**Layer**: code
**Status**: accepted

**Spec change**: While a `maestro work` session is active (wsession cookie exists), attempting to switch git branches should be blocked with a hard stop. User must end the work session first.

**Observed (v1 internal/deep)**: May not be enforced; git branch operations are external to Maestro.

**Required code changes**:
- Add `.git/hooks/pre-checkout` hook template to detect active wsession
- Alternatively, add `maestro worksession check` command to be called before branch operations
- Error message: "Cannot switch branches while work session is active. Run `maestro work end` first."
- Provide `maestro worksession install-hooks` command to set up git hooks

**Tests**:
- Start `maestro work` → attempt `git checkout <branch>` → expect error
- End work session → `git checkout <branch>` → expect success

**Evidence**:
- IR: `ir/wf/WF-14.intent.yaml`
- v1: `v1/scenario_14_branch_safety_guardrails.md`
- Code: `maestro/modules/work_session.py`

**Notes**: Invariant `BRANCH_SWITCH_FORBIDDEN_DURING_WORK`. Requires coordination with git hooks or pre-command checks.

---

### LEDGER-0006: Work session cookie/token required

**Workflow**: WF-15
**Layer**: code
**Status**: accepted

**Spec change**: Active work sessions are tracked via a wsession cookie (file-based token in `./docs/maestro/wsession/cookie`). Commands that mutate state must check for this cookie.

**Observed (v1 internal/deep)**: Cookie mechanism may exist but not enforced in all mutation paths.

**Required code changes**:
- Implement `wsession_cookie_exists()` in `maestro/modules/work_session.py`
- Add cookie check to mutation commands: `maestro task create`, `maestro issues create`, etc.
- Cookie format: JSON with `session_id`, `started_at`, `branch`, `pid`

**Tests**:
- Test `maestro work start` → verify cookie created
- Test `maestro task create` without active session → expect error or prompt
- Test `maestro work end` → verify cookie removed

**Evidence**:
- IR: `ir/wf/WF-15.intent.yaml`
- v1: `v1/scenario_15_work_wsession_cookie_protocol.md`
- Code: `maestro/modules/work_session.py`

**Notes**: Invariant `WSESSION_COOKIE_REQUIRED`. Essential for session isolation.

---

### LEDGER-0007: Work session mutation modes (opt-in)

**Workflow**: WF-16
**Layer**: cli, code
**Status**: accepted

**Spec change**: Work session mutations (create/update/delete on tasks/issues) require explicit opt-in via `--mutate` flag or `mutation_mode: enabled` in session config. Default mode is read-only.

**Observed (v1 internal/deep)**: Mutation mode may not be implemented; all commands may mutate by default.

**Required code changes**:
- Add `mutation_mode` field to session config (default: `readonly`)
- Add `--mutate` flag to `maestro work start`
- Check `mutation_mode` before allowing task/issue creation/updates
- Error message: "Mutation disabled. Restart work session with `--mutate` to enable."

**Tests**:
- Test `maestro work start` → `maestro task create` → expect error (readonly)
- Test `maestro work start --mutate` → `maestro task create` → expect success

**Evidence**:
- IR: `ir/wf/WF-16.intent.yaml`
- v1: `v1/scenario_16_wsession_mutation_modes.md`
- Code: `maestro/modules/work_session.py`, `maestro/modules/command_handlers.py`

**Notes**: Invariant `WSESSION_MUTATION_MODE_OPTIN`. Safety feature to prevent accidental state changes.

---

### LEDGER-0008: Home hub allowed in readonly repos

**Workflow**: WF-13
**Layer**: code
**Status**: accepted

**Spec change**: Read-only repositories (no `./docs/maestro/`) can still use Maestro for inspection/build/TU by falling back to home hub (`~/.maestro/registry/`). Session state is stored in home hub, not repo.

**Observed (v1 internal/deep)**: May not be fully supported; some commands may require repo truth to exist.

**Required code changes**:
- Implement `get_storage_backend()` in `maestro/modules/utils.py` returning "repo_truth" or "home_hub"
- Allow commands like `maestro build`, `maestro tu` to run using home hub state
- Forbid commands like `maestro repo conf`, `maestro work` in readonly mode
- Add `maestro repo adopt` command to transition readonly → adopted (creates `./docs/maestro/`)

**Tests**:
- Test `maestro build` in repo without `./docs/maestro/` → expect success using home hub
- Test `maestro repo conf` in readonly repo → expect error
- Test `maestro repo adopt` → verify `./docs/maestro/` created and transition to repo truth mode

**Evidence**:
- IR: `ir/wf/WF-13.intent.yaml`
- v1: `v1/scenario_13_readonly_to_adopt_bridge.md`
- Code: `maestro/modules/utils.py`, `maestro/modules/command_handlers.py`

**Notes**: Invariant `HOME_HUB_ALLOWED_IN_READONLY`. Enables lightweight Maestro usage without repo adoption.

---

## Adding New Entries

When adding ledger entries:

1. Use sequential `LEDGER-NNNN` numbering
2. Fill in all required fields (Workflow, Layer, Status, Spec change, Observed, Required code changes, Tests, Evidence)
3. Cross-reference IR files, v1 diagrams, and source code paths
4. Update status as work progresses
5. Commit ledger updates with related IR/code changes

## Review Process

- **Weekly review**: Scan ledger for `proposed` entries → triage to `accepted` or `dropped`
- **Implementation tracking**: Move `accepted` → `implemented` as PRs merge
- **Verification**: Move `implemented` → `verified` after tests pass and behavior confirmed
- **Cleanup**: Archive `verified` and `dropped` entries periodically (move to `LEDGER_ARCHIVE.md`)
