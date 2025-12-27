# v3 Implementation Ledger

Entries derived from the v2 runbook audit. Status is `proposed` until implemented.

See also: `docs/workflows/v3/cli/CLI_GAPS.md` for the P0 gap list mapped to invariants.

- ID: LED-0001
  Title: Normalize workflow node/edge CLI signature
  Rationale: Conflicting usage in `docs/workflows/v2/runbooks/examples/proposed/EX-02_rust_cargo_greenfield_workflow_first.sh` and `docs/workflows/v2/runbooks/examples/proposed/EX-09_runbook_to_workflow_to_plan_miniprogram_hello_cli.sh`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro workflow node add <workflow> --layer <layer> --label <label>` works; alternate legacy forms are rejected with guidance.
  Notes: Add `workflow show` to list nodes/edges.

- ID: LED-0002
  Title: Unify wsession breadcrumb API
  Rationale: `docs/workflows/v2/runbooks/examples/proposed/EX-07_work_wsession_cookie_breadcrumb_ipc.sh` vs `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.sh`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro wsession breadcrumb add --cookie <cookie> --status <msg>` records breadcrumb; `wsession show` returns breadcrumbs.
  Notes: Keep `--message` as alias if needed.

- ID: LED-0003
  Title: Canonical work resume/close lifecycle
  Rationale: Resume syntax differs across examples.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro work resume <wsession>` and `maestro work close <wsession>` are supported; deprecated forms emit warnings.
  Notes: Add `work list` for active sessions.

- ID: LED-0004
  Title: Make command standardization (build alias)
  Rationale: `maestro build` vs `maestro make --with-hub-deps` in examples.
  Status: proposed
  Priority: P1
  Blocked_by: DEC-0001
  Acceptance criteria: `maestro make` supports `--with-hub-deps`; `maestro build` is a deprecated alias with warnings.
  Notes: Provide `make --help` and `make status` for last build info.

- ID: LED-0005
  Title: Repo conf gate enforcement
  Rationale: Build invoked before repo conf in `docs/workflows/v2/runbooks/examples/proposed/EX-01_cpp_cmake_adopt_build_fix.sh`.
  Status: implemented
  Priority: P0
  Blocked_by: DEC-0003
  Acceptance criteria: `maestro make` fails with actionable message if no repo conf target selected; `repo conf select-default target <TARGET>` resolves it.
  Notes: `repo conf list` added; tests in `tests/test_repo_conf_cli.py`.

- ID: LED-0006
  Title: Discuss resume/replay and session logs
  Rationale: `maestro discuss --resume` and `maestro session log` are implied but undefined.
  Status: partial
  Priority: P1
  Acceptance criteria: sessions are listed, resume works, log shows streamed events for a session.
  Notes: `maestro discuss replay <path>` stub added; resume/log still pending.

- ID: LED-0007
  Title: OPS-aligned discuss subcommands
  Rationale: `repo discuss`, `task discuss`, `phase discuss`, `runbook discuss` are TODO in examples.
  Status: proposed
  Priority: P1
  Acceptance criteria: each discuss command triggers a context-specific OPS schema and produces valid JSON output.
  Notes: See EX-21..EX-28 runbooks.

- ID: LED-0008
  Title: Repo hub query primitives
  Rationale: `maestro repo hub find package Core` requires explicit hub state.
  Status: proposed
  Priority: P2
  Acceptance criteria: hub queries return package hits with repo references; `--with-hub-deps` uses this data.
  Notes: Store in `HOME_HUB_REPO` and reference by repo resolve.

- ID: LED-0009
  Title: Convert plan approval workflow
  Rationale: `convert plan` exists but no approval gate is defined.
  Status: proposed
  Priority: P2
  Acceptance criteria: `convert plan approve` and `convert plan reject` update plan state and ledger.
  Notes: Connect to `convert run` gating.

- ID: LED-0010
  Title: Issue lifecycle normalization
  Rationale: Issues are added/accepted/ignored but no update/close operations.
  Status: proposed
  Priority: P1
  Acceptance criteria: `issues update`, `issues close`, `issues link-task` are supported; list reflects state.
  Notes: Keep `issues add` as create alias.

- ID: LED-0011
  Title: Toolchain profile store in hub
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: profiles can be created, listed, and retrieved from `$HOME/.maestro/select/toolchain/profiles/*.json`.
  Notes: Default selection stored in `$HOME/.maestro/select/toolchain/default.json`.

- ID: LED-0012
  Title: Select toolchain CLI (list/show/set/unset/export)
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro select toolchain list|show|set|unset|export` works with `--scope session|project|host`.
  Notes: Keep `maestro select tc` as alias.

- ID: LED-0013
  Title: Repoconf references toolchain profile with precedence rules
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: repoconf stores toolchain name; selection precedence is session > project > host.
  Notes: Store reference in `./docs/maestro/repoconf.json` or `./docs/maestro/select.json`.

- ID: LED-0014
  Title: Make/TU consumes selected toolchain environment
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro make` and `maestro tu` use exported env vars (include/lib paths, sysroot) from selected toolchain.
  Notes: Ensure build alias behavior remains consistent.

- ID: LED-0015
  Title: Platform caps detect stored in hub with confidence
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro platform caps detect` writes `present`, `version`, `provider`, `confidence` into `$HOME/.maestro/platform/caps/detected.json`.
  Notes: Support optional `--toolchain` preview cache.

- ID: LED-0016
  Title: Prefer/require policy stored in repo truth
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro platform caps prefer/require` updates `./docs/maestro/platform_caps.json` with policy arrays.
  Notes: Keep policy separate from detection data.

- ID: LED-0017
  Title: Make/build consumes caps policy for optional features
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro make` enables optional flags only when caps are present and preferred.
  Notes: Provide a cap-report flag or log to trace applied caps.

- ID: LED-0018
  Title: Require missing triggers gate and issue creation
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: missing required cap blocks build and creates an issue/task stub with actionable guidance.
  Notes: Gate should reference `CAP_REQUIRE`.

- ID: LED-0019
  Title: Integration gate evaluation plumbing
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `GATE_TOOLCHAIN_SELECTED`, `GATE_CAPS_DETECTED`, `GATE_REPOCONF_PRESENT`, `GATE_REQUIRE_CAPS_SATISFIED`, `GATE_BUILD_OK`, and `GATE_TU_READY` are evaluated consistently across make and TU flows.
  Notes: Gate outcomes should be reported with next-step guidance.

- ID: LED-0020
  Title: Export artifacts for toolchain and caps
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: `maestro select toolchain export` and `maestro platform caps export` emit env/json (and cmake for toolchain) with deterministic ordering.
  Notes: Make/TU should consume exported artifacts.

- ID: LED-0021
  Title: Make/TU consumes toolchain + caps exports deterministically
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: build invocation uses toolchain export first, then caps export, then repoconf target overrides.
  Notes: Record applied env for troubleshooting.

- ID: LED-0022
  Title: Require-caps missing creates issue with evidence
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P1
  Acceptance criteria: missing required caps create an issue with detect evidence (provider/version/confidence) and suggested fixes.
  Notes: Provide links to toolchain profiles and re-run detect.

- ID: LED-0023
  Title: Suggest alternate toolchain profiles when caps missing
  Rationale: Required by `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P2
  Acceptance criteria: when a required cap is missing, list candidate toolchain profiles that could provide it.
  Notes: Use hub profile metadata as the source.

- ID: LED-0024
  Title: Enforce repoconf/target gate before make
  Rationale: Required by `docs/workflows/v3/cli/INVARIANTS.md` and `docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md`.
  Status: proposed
  Priority: P0
  Blocked_by: DEC-0003
  Acceptance criteria: `maestro make` refuses to run without a resolved repo and selected target, and prints next-step guidance.
  Notes: Gate should be consistent with `repo conf select-default target`.

- ID: LED-0025
  Title: Enforce TU readiness gate
  Rationale: Required by `docs/workflows/v3/cli/INVARIANTS.md` and `docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md`.
  Status: proposed
  Priority: P0
  Blocked_by: DEC-0003
  Acceptance criteria: `maestro tu build` fails if repoconf or toolchain selection is missing; error points to the required commands.
  Notes: Gate aligns with `GATE_TU_READY`.

- ID: LED-0026
  Title: Require wsession cookie for breadcrumb ops
  Rationale: Required by `docs/workflows/v3/cli/SIGNATURES.md` and `docs/workflows/v3/cli/INVARIANTS.md`.
  Status: proposed
  Priority: P0
  Acceptance criteria: `maestro wsession breadcrumb add` rejects missing cookie with a clear message; `wsession show` reveals the cookie.
  Notes: Keep cookie semantics explicit in help output.

- ID: LED-0027
  Title: Work session open/close lifecycle enforcement
  Rationale: Required by `docs/workflows/v3/cli/INVARIANTS.md` and `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.md`.
  Status: proposed
  Priority: P0
  Acceptance criteria: operations on closed sessions are blocked; `work start` and `work close` update state deterministically.
  Notes: Resume tokens expire on close.

- ID: LED-0028
  Title: Discuss JSON hard gate
  Rationale: Required by `docs/workflows/v3/cli/INVARIANTS.md` and EX-21..EX-28 discuss runbooks.
  Status: proposed
  Priority: P0
  Acceptance criteria: invalid JSON on `/done` hard-stops OPS application and records a failure event.
  Notes: Provide a retry prompt with schema hint.
