---
id: WF-14
title: Branch safety guardrails — branch-bound state, no branch switching during work
tags: [git, branch, safety, guardrails, work, sessions, corruption-prevention]
entry_conditions: A `maestro work` or stateful session is initiated in a Git repository.
exit_conditions: The work session completes successfully, or is hard-stopped due to a branch mismatch.
artifacts_created:
  - Git identity snapshot stored with work session metadata.
failure_semantics:
  - If a branch mismatch is detected, Maestro performs a hard stop, logs a clear error message, and provides recovery instructions. No state is corrupted.
links_to: [WF-09, WF-06]
related_commands: [work, wsession, init, repo, convert]
---

# WF-14: Branch Safety Guardrails

This workflow documents the operational guardrails for Git branch management to ensure state integrity during Maestro operations. Maestro's state is strictly bound to the Git branch it was initiated on, and switching branches during active work is an unsupported operation that will trigger a hard stop.

## 1. Core Rules (Operational Contract)

These rules define the non-negotiable contract for branch management:

*   **MUST**: Repository-local truth (all files under `./docs/maestro/`) is considered part of the branch's state and is therefore branch-bound.
*   **MUST**: Maestro must not perform `git checkout` or any other branch-switching operations as part of a work session.
*   **MUST**: The operator must not switch Git branches while a `maestro work` session or any stateful operation is in progress.
*   **MUST**: If a change in branch identity is detected between the start of a work run and a subsequent step, or between work session resume events, Maestro must perform a **hard stop** to prevent state corruption or a "split-brain" scenario.

## 2. Branch Identity Model

"Branch identity" is defined by a snapshot taken at the beginning of a work session. This snapshot serves as the ground truth for all subsequent checks within that session.

*   **Identity Snapshot Tuple**: `(<git_repo_root>, <HEAD_commit_hash>, <branch_name>)`
*   **Storage**: This identity snapshot is stored as part of the work session's metadata.
    *   *Expected behavior; implementation pending.*

The `git_repo_root` ensures that the check is valid even if the working directory changes. The `HEAD_commit_hash` and `branch_name` together provide a strong guarantee of the branch's state at the point of origin.

## 3. Guard Points: Where Checks Happen

To enforce the guardrails, branch identity checks should be implemented at the following critical points:

*   When initiating a new work session with `maestro work`.
*   When resuming a work session (`maestro work --resume <id>` or equivalent).
*   When applying any state mutations via `wsession` commands (if state-mutating modes are introduced).

## 4. Recovery Playbook

If Maestro detects a branch mismatch and performs a hard stop, the operator should follow these steps:

1.  **Read the Error Message**: Maestro will report the detected mismatch, showing the original branch identity and the current one.
2.  **Return to the Original Branch**: Use `git checkout <original_branch_name>` to return to the branch where the work session was started.
3.  **Resume Work**: Re-run the resume command (e.g., `maestro work --resume <id>`). The session should now proceed correctly.

**Intentional Branch Changes**: If you intended to switch branches, the correct approach is to treat it as a separate line of work. The recommended practice is to use a separate clone of the repository or a different subdirectory to avoid state conflicts.

## 5. Tests Implied by WF-14

This workflow implies the need for the following tests:

### Unit Tests

*   A function that correctly reads the current Git identity snapshot (`(root, hash, name)`).
*   A function that compares a stored identity snapshot against the current identity and correctly identifies matches and mismatches.

### Integration Tests

*   **Test Case**: Successful resume on same branch.
    1.  Start a work run and record its Git identity.
    2.  Perform some work.
    3.  Resume the work run without changing branches.
    4.  **Expected**: The run resumes successfully.
*   **Test Case**: Hard stop on branch switch.
    1.  Start a work run and record its Git identity.
    2.  Manually switch branches using `git checkout new-branch`.
    3.  Attempt to resume the work run.
    4.  **Expected**: Maestro performs a hard stop and prints a clear error message detailing the branch mismatch.
