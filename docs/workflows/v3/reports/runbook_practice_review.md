# Runbook Practice Review (v2 → v3)

This review highlights contradictions, grey-zone practices, dead paths, and
pressure points visible in the v2 example scripts.

## Hard Contradictions

- Workflow node add signature mismatch
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-02_rust_cargo_greenfield_workflow_first.sh` vs `docs/workflows/v2/runbooks/examples/proposed/EX-09_runbook_to_workflow_to_plan_miniprogram_hello_cli.sh`
  Risk: the CLI cannot satisfy both call styles; tooling and JSON→OPS mapping will diverge.
  Fix category: CLI addition (normalize to one signature).

- Wsession breadcrumb syntax mismatch
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-07_work_wsession_cookie_breadcrumb_ipc.sh` vs `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.sh`
  Risk: clients and OPS cannot know whether to use `breadcrumb <session> --status` or `breadcrumb add --message`.
  Fix category: CLI addition (single canonical subcommand + aliases).

- Work resume syntax mismatch
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-07_work_wsession_cookie_breadcrumb_ipc.sh` vs `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.sh`
  Risk: resume tokens and cookies become unportable; scripts diverge.
  Fix category: runbook rewrite (choose `work resume <id>` and update examples).

## Grey-Zone Practices (likely to break)

- Build invoked without repo conf gate
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-01_cpp_cmake_adopt_build_fix.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-14_tu_ast_refactor_autocomplete.sh`
  Risk: targets are ambiguous; build may run against the wrong config or fail silently.
  Fix category: new invariant (build requires repo conf or target).

- Discuss router decision lacks rule source
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-21_discuss_router_top_level_transfer_to_context.sh`
  Risk: routing is inconsistent and cannot be tested without a routing policy store.
  Fix category: internal implementation change (persist routing hints or rules).

- Cookie lifecycle inconsistent
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-07_work_wsession_cookie_breadcrumb_ipc.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-19_managed_mode_resume_stacking_subwork_sessions.sh`
  Risk: breadcrumbs can be rejected or attributed to closed sessions.
  Fix category: new invariant (cookie must include wsession state + TTL).

## Dead-Path Suspects

- `maestro build` vs `maestro make`
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-01_cpp_cmake_adopt_build_fix.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-18_upp_two_repo_hub_link_core_dependency.sh`
  Risk: users cannot predict the correct command; automation tools cannot infer intent.
  Fix category: CLI addition (single build command with aliases).

- `maestro repo conf --show` vs `maestro repo conf show`
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-01_cpp_cmake_adopt_build_fix.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-13_repo_resolve_levels_and_repoconf_targets.sh`
  Risk: mixed patterns lead to brittle docs and script failures.
  Fix category: runbook rewrite (pick one canonical form).

- `maestro session log` and `maestro ai <engine>`
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-08_json_contract_hard_fail_reprompt_recover.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-06_ai_engine_manager_noninteractive_resume_stream.sh`
  Risk: these commands may not exist or be wired; discuss sessions cannot be audited.
  Fix category: internal implementation change (create minimal logging + engine wrapper).

## Design Pressure Points

- JSON→OPS needs command parity
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-24_task_discuss_execute_patch_test_ops.sh`, `docs/workflows/v2/runbooks/examples/proposed/EX-27_runbook_workflow_discuss_authoring_ops.sh`
  Risk: OPS cannot be applied if no CLI command exists for the op (workflow export/render, wsession breadcrumbs, repo discuss).
  Fix category: CLI addition (OPS-aligned subcommands).

- Ops boundary: shell vs Maestro
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-24_task_discuss_execute_patch_test_ops.sh`
  Risk: audit logs do not show which actions are external vs internal; repeatability suffers.
  Fix category: new invariant (explicit ops namespace for shell runs).

- Repo hub linking is underdefined
  Evidence: `docs/workflows/v2/runbooks/examples/proposed/EX-18_upp_two_repo_hub_link_core_dependency.sh`
  Risk: dependency discovery depends on implicit hub state.
  Fix category: internal implementation change (hub query primitives + store schema).

## Decision Board

- Workflow node/edge CLI signature
  Options: correct / incorrect / partially_correct / drop
  Default recommendation: partially_correct (keep intent, fix signature to require workflow id + layer/label).

- Build vs make naming
  Options: correct / incorrect / partially_correct / drop
  Default recommendation: correct (standardize on `maestro build` with `--engine` or `--profile` flags; provide `maestro make` alias if needed).

- Work/wsession resume and breadcrumb interface
  Options: correct / incorrect / partially_correct / drop
  Default recommendation: partially_correct (merge into `maestro work resume <wsession>` and `maestro wsession breadcrumb add --status`).

- Repo conf gating before build
  Options: correct / incorrect / partially_correct / drop
  Default recommendation: correct (enforce gate, emit actionable error if missing).
