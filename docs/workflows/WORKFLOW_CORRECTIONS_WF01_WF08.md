# Workflow Corrections Report: WF-01 to WF-08

This report summarizes the corrections and normalizations applied to the Maestro workflow documentation (WF-01 through WF-08) and their corresponding PlantUML diagrams, as per the established canonical rules.

## Summary of Changes per Workflow

### WF-01: Existing Repo Bootstrap (Single Main, Compiled Language)
- **Markdown (`scenario_01_existing_repo_single_main.md`)**
    - Corrected repo-local config path: Replaced `.maestro/config.json` with `docs/maestro/config.json`.
    - Removed legacy `docs/todo.md` and `docs/done.md` references, replacing with a note on structured task state management.
    - Updated `# TODO` and `# DONE` markdown examples to reflect JSON task management.
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during active sessions.
- **PlantUML (`scenario_01_existing_repo_single_main.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Updated `# TODO` note in Phase 4 to reflect JSON task management.

### WF-02: New Project from Empty Directory (Manual Track/Phase/Task Planning)
- **Markdown (`scenario_02_new_project_manual_plan.md`)**
    - Removed legacy `docs/todo.md` and `docs/done.md` references, replacing with a note on structured task state management.
    - Updated references to `todo.md` and `done.md` in task completion descriptions and command summaries to reflect JSON-based status updates.
    - Updated unit test names (`test_task_add_updates_todo_md`, `test_task_complete_moves_to_done_md`) to reflect JSON-based status updates.
    - Updated "Decision Gates" to refer to `active tasks in JSON` instead of `todo.md`.
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching.
- **PlantUML (`scenario_02_new_project_manual_plan.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.

### WF-03: Read-only repo inspection + build
- **Markdown (`scenario_03_readonly_repo_inspect_build.md`)**
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during repo or build operations.
- **PlantUML (`scenario_03_readonly_repo_inspect_build.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Replaced generic "Check for build driver detection" node with an explicit call to `CALL_WF_05_REPO_RESOLVE()`.

### WF-04: Reactive compile error → Solutions match → immediate solution-task
- **Markdown (`scenario_04_reactive_compile_error_solution.md`)**
    - Added a note in Phase 1 clarifying that `maestro make build` implicitly leverages Repo Resolve (WF-05).
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during build processes.
- **PlantUML (`scenario_04_reactive_compile_error_solution.puml`)**
    - Included `_shared.puml` at the top.
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Inserted `CALL_WF_05_REPO_RESOLVE()` before the 'Execute build command' step to explicitly show dependency on Repo Resolve.

### WF-05: Repo Resolve — packages, conventions, build targets, and derived issues/tasks
- **Markdown (`scenario_05_repo_resolve_packages_conventions_targets.md`)**
    - Corrected repo-local data paths: Replaced all 16 occurrences of `.maestro/repo/` with `docs/maestro/repo/`.
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during repository resolution.
- **PlantUML (`scenario_05_repo_resolve_packages_conventions_targets.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Corrected repo-local data paths: Replaced `.maestro/repo/` with `docs/maestro/repo/` for writing scan results.

### WF-06: AI-driven task execution with Work Sessions and multi-session resume
- **Markdown (`scenario_06_ai_task_work_sessions.md`)**
    - Updated "AI Engine Session Initiation" to explicitly mention `wsession cookie/run-id` in the AI prompt context.
    - Removed "Shared memory" from "Communication Mechanism" and added `(keyed by wsession cookie/run-id)` to "File-based coordination".
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during active work sessions.
- **PlantUML (`scenario_06_ai_task_work_sessions.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Added a note to "Work Session Store" (WSS) describing file-based polling IPC, `wsession cookie/run-id`, and multi-process allowance.

### WF-07: AST/TU workflows — rename, C++→JS transform, autocomplete
- **Markdown (`scenario_07_ast_tu_refactor_transform_autocomplete.md`)**
    - Corrected repo-local data path: Replaced `.maestro/tu/` with `docs/maestro/tu/`.
    - Added "Branch Boundaries Note" to clarify operational rule against branch switching during AST/TU operations.
- **PlantUML (`scenario_07_ast_tu_refactor_transform_autocomplete.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.

### WF-08: Convert — cross-repo pipeline (New/Plan/Run)
- **Markdown (`scenario_08_convert_cross_repo_pipeline.md`)**
    - Corrected repo-local data paths: Replaced `.maestro/convert` with `docs/maestro/convert` and `.maestro/convert/plan/plan.json` with `docs/maestro/convert/plan/plan.json`.
    - Added "Branch Boundaries Note (Cross-Repo Context)" to clarify operational rule against branch switching on either source or target repositories during conversion pipelines.
    - Added clarification about file-based polling, `wsession cookie/run-id`, and multi-process operations in "Work Sessions & Transcripts".
- **PlantUML (`scenario_08_convert_cross_repo_pipeline.puml`)**
    - Added `BRANCH_GUARD("operational rule")` at the beginning of the diagram.
    - Corrected repo-local data paths: Replaced `.maestro/convert/` with `docs/maestro/convert/` in two places.
    - Added explicit `CALL_WF_05_REPO_RESOLVE()` before `ENSURE_AST_AVAILABLE()` to clarify prerequisites.
    - Added a note clarifying `wsession` file-based polling and `cookie/run-id` in the task execution section.

## Ambiguities and Further Confirmation

- **Macro Usage in PlantUML:** While `CALL_WF_05_REPO_RESOLVE()` and `BRANCH_GUARD("operational rule")` macros were used to standardize and convey information, their visual representation in the rendered PlantUML diagrams should be verified to ensure clarity and consistency. The instruction to use "note-only macro if not implemented" for `BRANCH_GUARD()` suggests the current implementation is an operational rule rather than a code-enforced guardrail.
- **`RepoConf` Workflow Details:** The Markdown for WF-07 and WF-08 mentions `RepoConf` as a prerequisite, but the specific workflow `RepoConf` itself (how it's run, its outputs, etc.) is not detailed within these WF documents. It points to `docs/workflows/command_repo_conf.md`, which was not part of this correction pass. A comprehensive understanding of `RepoConf` would require examining that separate document and potentially integrating its key concepts into these workflows more directly.
- **`$HOME/.maestro/**/repo` vs. `docs/maestro/`:** The distinction between repo-local "truth" in `docs/maestro/` and a user-global hub/index in `$HOME/.maestro/**/repo` was maintained. However, the exact interaction and potential for data overlap or conflict between these two locations, especially for generated artifacts like scan results, might warrant further explicit detailing in a dedicated "Maestro Data Model" document if it doesn't already exist.

## Grep-style Summary of Banned Strings

The following banned strings should now be absent from the corrected Markdown and PlantUML files:

*   `./.maestro` (replaced with `docs/maestro/` where applicable)
*   `docs/todo.md` (references removed or updated to structured task management)
*   `docs/done.md` (references removed or updated to structured task management)
*   `Shared memory` (removed from IPC descriptions)