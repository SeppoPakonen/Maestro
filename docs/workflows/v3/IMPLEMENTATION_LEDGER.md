# v3 Implementation Ledger

Entries derived from the v2 runbook audit. Status is `proposed` until implemented.

- ID: LED-0001
  Title: Normalize workflow node/edge CLI signature
  Rationale: Conflicting usage in `docs/workflows/v2/runbooks/examples/proposed/EX-02_rust_cargo_greenfield_workflow_first.sh` and `docs/workflows/v2/runbooks/examples/proposed/EX-09_runbook_to_workflow_to_plan_miniprogram_hello_cli.sh`.
  Status: proposed
  Acceptance criteria: `maestro workflow node add <workflow> --layer <layer> --label <label>` works; alternate legacy forms are rejected with guidance.
  Notes: Add `workflow show` to list nodes/edges.

- ID: LED-0002
  Title: Unify wsession breadcrumb API
  Rationale: `docs/workflows/v2/runbooks/examples/proposed/EX-07_work_wsession_cookie_breadcrumb_ipc.sh` vs `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.sh`.
  Status: proposed
  Acceptance criteria: `maestro wsession breadcrumb add --cookie <cookie> --status <msg>` records breadcrumb; `wsession show` returns breadcrumbs.
  Notes: Keep `--message` as alias if needed.

- ID: LED-0003
  Title: Canonical work resume/close lifecycle
  Rationale: Resume syntax differs across examples.
  Status: proposed
  Acceptance criteria: `maestro work resume <wsession>` and `maestro work close <wsession>` are supported; deprecated forms emit warnings.
  Notes: Add `work list` for active sessions.

- ID: LED-0004
  Title: Build command standardization
  Rationale: `maestro build` vs `maestro make --with-hub-deps` in examples.
  Status: proposed
  Acceptance criteria: `maestro build` supports `--with-hub-deps`; `maestro make` becomes alias or removed.
  Notes: Provide `build --help` and `build status` for last build info.

- ID: LED-0005
  Title: Repo conf gate enforcement
  Rationale: Build invoked before repo conf in `docs/workflows/v2/runbooks/examples/proposed/EX-01_cpp_cmake_adopt_build_fix.sh`.
  Status: proposed
  Acceptance criteria: `maestro build` fails with actionable message if no repo conf target selected; `repo conf select-default-target` resolves it.
  Notes: Add `repo conf list`.

- ID: LED-0006
  Title: Discuss resume/replay and session logs
  Rationale: `maestro discuss --resume` and `maestro session log` are implied but undefined.
  Status: proposed
  Acceptance criteria: sessions are listed, resume works, log shows streamed events for a session.
  Notes: Align with JSON contract enforcement.

- ID: LED-0007
  Title: OPS-aligned discuss subcommands
  Rationale: `repo discuss`, `task discuss`, `phase discuss`, `runbook discuss` are TODO in examples.
  Status: proposed
  Acceptance criteria: each discuss command triggers a context-specific OPS schema and produces valid JSON output.
  Notes: See EX-21..EX-28 runbooks.

- ID: LED-0008
  Title: Repo hub query primitives
  Rationale: `maestro repo hub find package Core` requires explicit hub state.
  Status: proposed
  Acceptance criteria: hub queries return package hits with repo references; `--with-hub-deps` uses this data.
  Notes: Store in `HOME_HUB_REPO` and reference by repo resolve.

- ID: LED-0009
  Title: Convert plan approval workflow
  Rationale: `convert plan` exists but no approval gate is defined.
  Status: proposed
  Acceptance criteria: `convert plan approve` and `convert plan reject` update plan state and ledger.
  Notes: Connect to `convert run` gating.

- ID: LED-0010
  Title: Issue lifecycle normalization
  Rationale: Issues are added/accepted/ignored but no update/close operations.
  Status: proposed
  Acceptance criteria: `issues update`, `issues close`, `issues link-task` are supported; list reflects state.
  Notes: Keep `issues add` as create alias.

- ID: LED-0011
  Title: Toolchain profile store in hub
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Acceptance criteria: profiles can be created, listed, and retrieved from `$HOME/.maestro/select/toolchain/profiles/*.json`.
  Notes: Default selection stored in `$HOME/.maestro/select/toolchain/default.json`.

- ID: LED-0012
  Title: Select toolchain CLI (list/show/set/unset/export)
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Acceptance criteria: `maestro select toolchain list|show|set|unset|export` works with `--scope session|project|host`.
  Notes: Keep `maestro select tc` as alias.

- ID: LED-0013
  Title: Repoconf references toolchain profile with precedence rules
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Acceptance criteria: repoconf stores toolchain name; selection precedence is session > project > host.
  Notes: Store reference in `./docs/maestro/repoconf.json` or `./docs/maestro/select.json`.

- ID: LED-0014
  Title: Make/TU consumes selected toolchain environment
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Acceptance criteria: `maestro make` and `maestro tu` use exported env vars (include/lib paths, sysroot) from selected toolchain.
  Notes: Ensure build alias behavior remains consistent.
