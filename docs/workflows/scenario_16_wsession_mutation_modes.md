---
id: WF-16
title: wsession modes — log-only vs mutation API (opt-in)
tags: [wsession, mutation, breadcrumbs, audit, policy, work, ipc]
entry_conditions: |
  A Maestro work-run is active, and the `wsession` utility is invoked, either directly by a user or programmatically by an AI agent.
exit_conditions: |
  The `wsession` operation completes, either by successfully logging an event or mutating state (if permitted), or by failing due to policy violation or error.
artifacts_created: |
  - If log-only: new entries appended to the active Work Session log.
  - If mutation: new entries appended to the active Work Session log, and modifications to `docs/maestro/**` (e.g., task files, issue files).
failure_semantics: |
  - Unknown cookie: Operation rejected.
  - Mutation mode disabled (for a mutation attempt): Operation rejected, breadcrumbs still accepted.
  - Invalid operation schema: Specific operation rejected, error recorded, other operations may proceed.
  - Referential integrity failure: Specific operation rejected, error recorded.
  - Repo truth parse errors (during mutation): Hard stop of the `wsession` utility.
links_to: [WF-09, WF-14, WF-15]
related_commands: |
  - `maestro wsession <subcommand>` (existing read-only commands)
  - Proposed: `maestro wsession mutate <operation> [args...]`
---

# WF-16: wsession modes — log-only vs mutation API (opt-in)

This workflow formalizes the operational modes for `maestro wsession`, distinguishing between a default log-only behavior and an opt-in mutation mode. This distinction is crucial for managing the integrity of project state while enabling AI agents to interact dynamically during long-running work.

## Two modes of wsession

### Mode A — Log-only (default)

In its default mode, `maestro wsession` functions purely as a "breadcrumb bus." It is designed to append progress updates, notes, and observational data to a Work Session without altering the fundamental project state stored in the repository.

*   **Allowed message types:** `breadcrumb`, `progress`, `note`, and other informational messages that contribute to an audit trail or context for the current work session.
*   **Disallowed actions:** Direct creation or update of tasks, issues, phase states, or track states. No writes to the repository truth beyond appending to the session log itself (if the session log is part of the repository truth).
*   **Purpose:** To provide a structured, chronological record of activity within a work session, supporting review, debugging, and understanding of AI agent behavior without the risk of unintended state changes.

### Mode B — Mutation mode (opt-in)

When explicitly enabled, `maestro wsession` transforms into a state mutation API. This mode allows AI agents to perform controlled, state-changing operations against the project's repository truth during long-running tasks. This addresses scenarios where waiting for a "final JSON summary + restart session" is inefficient, enabling direct and immediate updates to tasks, issues, and project metadata.

*   **Allowed actions:** A controlled set of state-changing operations defined below.
*   **Purpose:** To facilitate dynamic adjustments and updates by AI agents, allowing them to mark progress, create follow-up tasks, or resolve issues directly as they occur, aligning with an iterative development process.
*   **Safety mechanism:** While allowing mutations, this mode acknowledges `git rollback` as a practical safety mechanism for reverting unintended changes.

## How mutation is enabled

Enabling mutation mode requires explicit authorization through a layered gating mechanism to prevent accidental or unauthorized state changes.

*   **Config setting (project-level):** A `maestro` configuration setting (e.g., in `maestro.yaml` or a similar project config file) must explicitly enable `wsession` mutation for the current project. This provides a clear, project-wide intent.
*   **CLI flag on work-run:** The `maestro work-run` command must include a specific CLI flag (e.g., `--enable-wsession-mutation`) to activate mutation capabilities for that particular execution. This acts as an immediate override or activation for a specific run.
*   **Cookie capability token (WF-15):** The `wsession cookie` (as defined in WF-15) must contain a capability token explicitly granting permission for mutation operations. This ensures multi-process and IPC safety by embedding authorization directly into the communication mechanism.

**Policy / Proposed Gating Mechanism:** The preferred mechanism will involve a combination of these. A project-level config *must* allow mutation, and a `work-run` CLI flag *must* activate it. The WF-15 cookie will then carry this activated capability. If any of these gates are not met, mutation operations will be rejected.

## Allowed mutations (operation list)

The following is a minimal initial set of proposed operations for `wsession` mutation mode. Each operation is carefully considered for its inputs, side effects, validation, and failure behavior.

**`issue.create`**
*   **Inputs:** `title` (string), `description` (string, optional), `type` (enum: `bug`, `feature`, `chore`), `priority` (enum: `low`, `medium`, `high`), `assigned_to` (string, optional).
*   **Side effects:** Creates a new issue file (e.g., `docs/maestro/issues/<id>.md`).
*   **Validation gates:** Schema validation for inputs.
*   **Failure behavior:** Reject operation, record error in session log.

**`issue.link`**
*   **Inputs:** `issue_id` (string), `target_type` (enum: `task`, `phase`), `target_id` (string).
*   **Side effects:** Updates the specified issue file and/or the target task/phase file to establish a link.
*   **Validation gates:** `issue_id` and `target_id` must refer to existing entities. Schema validation.
*   **Failure behavior:** Reject operation, record error.

**`task.create`**
*   **Inputs:** `title` (string), `description` (string, optional), `assigned_to` (string, optional), `priority` (enum: `low`, `medium`, `high`), `status` (enum: `pending`, `in_progress`).
*   **Side effects:** Creates a new task file (e.g., `docs/maestro/tasks/<id>.md`).
*   **Validation gates:** Schema validation for inputs.
*   **Failure behavior:** Reject operation, record error.

**`task.update`**
*   **Inputs:** `task_id` (string), `field` (enum: `priority`, `description`, `title`, `assigned_to`, `status`), `value` (string for description/title/assigned_to, enum for priority/status).
*   **Side effects:** Modifies the specified task file.
*   **Validation gates:** `task_id` must exist. `field` and `value` must match schema.
*   **Failure behavior:** Reject operation, record error.

**`task.mark_done`**
*   **Inputs:** `task_id` (string).
*   **Side effects:** Updates the specified task file, setting its status to `completed` and potentially adding a completion timestamp.
*   **Validation gates:** `task_id` must exist. Task must not already be `completed` or `cancelled`.
*   **Failure behavior:** Reject operation, record error.

**`phase.update` (optional)**
*   **Inputs:** `phase_id` (string), `field` (enum: `status`, `notes`), `value` (enum for status, string for notes).
*   **Side effects:** Modifies the specified phase metadata file.
*   **Validation gates:** `phase_id` must exist. Schema validation.
*   **Failure behavior:** Reject operation, record error.

**`track.update` (optional)**
*   **Inputs:** `track_id` (string), `field` (enum: `status`, `notes`), `value` (enum for status, string for notes).
*   **Side effects:** Modifies the specified track metadata file.
*   **Validation gates:** `track_id` must exist. Schema validation.
*   **Failure behavior:** Reject operation, record error.

## Audit & provenance

Every mutation executed through `wsession` will generate an audit event appended to the active Work Session log. This is critical for operational traceability, debugging, and understanding the sequence of changes made by an AI agent. This is distinct from security logging; it focuses on providing a clear history of actions within a work-run.

Each audit event will include:
*   **`timestamp`:** UTC timestamp of the mutation.
*   **`cookie_id` / `run_id`:** Identifier of the `wsession` instance or `work-run` that initiated the mutation.
*   **`originating_ai_session_id`:** (If available) An identifier for the specific AI reasoning session or agent that requested the mutation.
*   **`operation_type`:** e.g., `task.create`, `issue.update`.
*   **`payload`:** The full input parameters provided to the mutation operation.
*   **`before_ref` / `after_ref`:** (If cheap to generate) Hashing or content snippets of the relevant file(s) before and after the mutation. This could be a Git object hash or a SHA256 of the file content.
*   **`status`:** `success` or `failure`.
*   **`error_details`:** (If `status` is `failure`) Details about why the operation failed.

## Branch guardrails

To maintain repository integrity and prevent mutations on an unexpected branch, `wsession` in mutation mode must integrate with WF-14 (Branch Guardrails).

*   **Hard-stop on branch change:** If the Git branch identity of the project changes since the `work-run` began (as detected by WF-14 mechanisms), any mutation attempt via `wsession` must trigger a hard stop. This prevents an AI from accidentally modifying the wrong branch.
*   **Operational rule:** If WF-14 checks for branch identity changes are not yet fully implemented in the core system, this remains a critical operational rule that must be enforced externally until code support is available.

## Failure semantics

Robust failure handling is crucial for a mutation API.

*   **Unknown cookie:** If the `wsession` cookie is invalid or unknown, the operation is immediately rejected.
*   **Mutation mode disabled:** If a mutation operation is attempted while mutation mode is not explicitly enabled, the mutation message is rejected. Log-only breadcrumbs, however, will still be accepted.
*   **Invalid operation schema:** If the payload for a mutation operation does not conform to the expected schema (e.g., missing required fields, incorrect types), that specific operation is rejected. An error is recorded in the session log, but the `wsession` utility may continue processing other valid operations.
*   **Referential integrity failure:** If an operation refers to a non-existent entity (e.g., `task.update` for a `task_id` that doesn't exist), the operation is rejected, and an error is recorded.
*   **Repository truth parse errors:** Since mutation implies writing to the repository truth (e.g., Markdown files in `docs/maestro`), any internal errors encountered when parsing or writing these files (e.g., malformed YAML front matter in an existing task file) should result in a hard stop of the `wsession` utility, as the integrity of the project state cannot be guaranteed.

## Tests implied by WF-16

### Unit Tests
*   **Mutation gate (disabled):**
    *   Test that when mutation mode is disabled, attempts to perform mutation operations are rejected, but log-only breadcrumbs are still accepted.
*   **Mutation gate (enabled):**
    *   Test that when mutation mode is enabled and all other gates are met, mutation operations are accepted and processed.
*   **Audit log entry:**
    *   Verify that a correctly structured audit log entry is created and appended to the Work Session for every mutation operation (success or failure).
*   **Referential integrity checks:**
    *   Test cases for `issue.link`, `task.update`, `task.mark_done` where the referenced ID does not exist, ensuring the operation is rejected.
*   **Schema validation:**
    *   Test cases for all mutation operations with invalid input schemas, ensuring rejection.

### Integration Tests
*   **Run work with mutation enabled:**
    *   Simulate a `work-run` with mutation mode enabled.
    *   Have the simulated AI agent send `task.create` and `issue.create` commands via `wsession`.
    *   Verify that the repository truth (`docs/maestro/tasks` and `docs/maestro/issues`) is updated correctly with the new files.
    *   Verify that the Work Session log contains the corresponding audit events for these mutations.
*   **Run work with mutation disabled:**
    *   Simulate a `work-run` with mutation mode disabled.
    *   Have the simulated AI agent send a breadcrumb and an attempted mutation command.
    *   Verify that the breadcrumb is recorded, but the mutation command is rejected, and no changes are made to the repository truth.
    *   Verify that an appropriate error is logged for the rejected mutation.
*   **Branch mismatch (WF-14 integration):**
    *   Simulate a branch change during a `work-run` with mutation enabled.
    *   Verify that subsequent mutation attempts trigger a hard stop.
