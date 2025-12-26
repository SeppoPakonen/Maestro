# Maestro Workflow Catalog — v2 Canonical Specification

## Overview

This index catalogs all Maestro workflows in the v2 canonical specification format. Each workflow is defined by YAML IR files that serve as the single source of truth for diagram generation and implementation.

For an explanation of the v2 structure and philosophy, see [README.md](README.md).

---

## Workflow Table

| ID | Title | Status | IR Files | Evidence (v1) |
|----|-------|--------|----------|---------------|
| **WF-01** | Existing Repo Bootstrap (Single Main, Compiled) | Pending | — | [v1 MD](../v1/scenario_01_existing_repo_single_main.md) |
| **WF-02** | New Project from Empty Directory (Manual Planning) | Pending | — | [v1 MD](../v1/scenario_02_new_project_manual_plan.md) |
| **WF-03** | Read-only Repo Inspection + Build | Pending | — | [v1 MD](../v1/scenario_03_readonly_repo_inspect_build.md) |
| **WF-04** | Reactive Compile Error → Solutions Match → Task | Pending | — | [v1 MD](../v1/scenario_04_reactive_compile_error_solution.md) |
| **WF-05** | Repo Resolve — Packages, Conventions, Build Targets | Pending | — | [v1 MD](../v1/scenario_05_repo_resolve_packages_conventions_targets.md) |
| **WF-06** | AI-driven Task Execution with Work Sessions | Pending | — | [v1 MD](../v1/scenario_06_ai_task_work_sessions.md) |
| **WF-07** | AST/TU Workflows — Rename, Transform, Autocomplete | Pending | — | [v1 MD](../v1/scenario_07_ast_tu_refactor_transform_autocomplete.md) |
| **WF-08** | Convert — Cross-repo Pipeline (New/Plan/Run) | Pending | — | [v1 MD](../v1/scenario_08_convert_cross_repo_pipeline.md) |
| **WF-09** | Storage Contract: Repo Truth vs. Home Hub | **Seeded** | [intent](ir/wf/WF-09.intent.yaml) | [v1 MD](../v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md) |
| **WF-10** | Repo Resolve Levels — Lite vs Deep, Convention Acceptance | Pending | — | [v1 MD](../v1/scenario_10_repo_resolve_levels_lite_deep.md) |
| **WF-11** | Manual Repo Model + Manual RepoConf (Resolve Optional) | Pending | — | [v1 MD](../v1/scenario_11_manual_repo_model_and_conf.md) |
| **WF-12** | RepoConf Gate — Required Targets/Configs for Build/TU/Convert | Pending | — | [v1 MD](../v1/scenario_12_repo_conf_gate_for_build_tu_convert.md) |
| **WF-13** | Read-only → Adopt Bridge (Home Hub to Repo Truth) | Pending | — | [v1 MD](../v1/scenario_13_readonly_to_adopt_bridge.md) |
| **WF-14** | Branch Safety Guardrails — No Branch Switching During Work | Pending | — | [v1 MD](../v1/scenario_14_branch_safety_guardrails.md) |
| **WF-15** | Work ↔ wsession Cookie Protocol (File-based Polling) | Pending | — | [v1 MD](../v1/scenario_15_work_wsession_cookie_protocol.md) |
| **WF-16** | wsession Modes — Log-only vs Mutation API (Opt-in) | Pending | — | [v1 MD](../v1/scenario_16_wsession_mutation_modes.md) |
| **WF-17** | TBD (Reserved for Future Workflow) | Pending | — | — |

---

## MEGA Workflows

MEGA workflows are composite workflows that combine multiple atomic workflows into end-to-end scenarios.

| ID | Title | Status | Combines | IR Files |
|----|-------|--------|----------|----------|
| **MEGA-01** | Full Adoption Flow (Readonly → Adopt → Resolve → Conf → Build) | Pending | WF-03, WF-13, WF-05, WF-10, WF-12 | — |
| **MEGA-02** | Greenfield Project Creation (Init → Plan → Work → Test → Deploy) | Pending | WF-02, WF-06, WF-15, WF-16 | — |
| **MEGA-03** | Cross-repo Convert Pipeline (Resolve → AST → Export → Convert) | Pending | WF-05, WF-07, WF-08 | — |
| **MEGA-04** | Error-driven Development (Build → Error → Solutions → Work → Verify) | Pending | WF-01, WF-04, WF-06, WF-15 | — |

---

## Status Definitions

- **Seeded**: IR files exist with minimal but complete example
- **Pending**: IR files not yet created; v1 evidence available
- **In Progress**: IR files partially completed
- **Complete**: All IR layers (intent, CLI, code) exist and are verified
- **Verified**: IR matches implementation and tests pass

---

## Workflow Breakdown by Layer

Each workflow can be specified at multiple levels of detail (LOD):

### LOD0: Intent Layer
User-facing conceptual flow. Files: `WF-XX.intent.yaml`

### LOD1: CLI Layer
CLI command structure, argparse, handlers, validation gates. Files: `WF-XX.cli.yaml`

### LOD2: Code Layer
Code implementation topology (functions, classes, modules, data stores). Files: `WF-XX.code.yaml`

### Observed Layer
Extracted from v1 internal/deep (current code behavior). Files: `WF-XX.observed.yaml`

---

## Priority Workflows (Implementation Order)

Based on architectural invariants and dependencies, the following workflows should be prioritized:

1. **WF-09** (Storage Contract) — Foundation for all persistence ✅ Seeded
2. **WF-05** (Repo Resolve) — Detection spine
3. **WF-10** (Repo Resolve Levels) — Extends WF-05 with Lite/Deep modes
4. **WF-12** (RepoConf Gate) — Required for build/TU/convert
5. **WF-13** (Read-only → Adopt) — Adoption bridge
6. **WF-14** (Branch Safety) — Work session safety
7. **WF-15** (wsession Cookie) — Work session protocol
8. **WF-16** (wsession Mutation) — Work session mutation safety

Then:

9. **WF-01** (Existing Repo Bootstrap)
10. **WF-02** (New Project)
11. **WF-06** (AI Work Sessions)
12. **WF-07** (AST/TU)
13. **WF-08** (Convert)

Finally:

14. **WF-03** (Read-only Inspection)
15. **WF-04** (Reactive Compile Error)
16. **WF-11** (Manual Repo Model)
17. **WF-17** (Reserved)

---

## Architectural Invariants

All workflows enforce these invariants (see [README.md](README.md#invariants-enforced)):

1. `FORBID_REPO_DOT_MAESTRO`
2. `REPO_TRUTH_IS_DOCS_MAESTRO`
3. `REPO_TRUTH_FORMAT_IS_JSON`
4. `HOME_HUB_ALLOWED_IN_READONLY`
5. `REPO_RESOLVE_IS_DETECTION_SPINE`
6. `REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT`
7. `BRANCH_SWITCH_FORBIDDEN_DURING_WORK`
8. `WSESSION_COOKIE_REQUIRED`
9. `WSESSION_IPC_FILE_BASED`
10. `CONVENTION_ACCEPTANCE_GATE`
11. `WSESSION_MUTATION_MODE_OPTIN`

---

## Contributing

To add or update a workflow:

1. **Create/edit IR files** in `ir/wf/WF-XX.*.yaml`
2. **Update Implementation Ledger** (`IMPLEMENTATION_LEDGER.md`) with spec→code deltas
3. **Generate diagrams** from IR (manual for now; automated future)
4. **Update this index** to reflect new status
5. **Commit** all changes together

---

## Related Documentation

- [v2 README](README.md) — Overview of v2 philosophy and structure
- [YAML IR Schema](ir/schema/workflow_ir.md) — Detailed IR format specification
- [Implementation Ledger](IMPLEMENTATION_LEDGER.md) — Spec→code delta tracking
- [v1 Archive](../v1/) — Legacy diagrams and documentation

---

**Last Updated**: 2025-12-26
**Version**: 2.0.0-alpha
