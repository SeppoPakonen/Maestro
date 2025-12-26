# `command_wsession_mutation.md` - Analysis of `maestro wsession` Implementation

## Overview

This document analyzes the current implementation of `maestro wsession` to understand its existing capabilities, specifically in relation to the proposed "log-only" and "mutation API" modes described in WF-16. The inspection focuses on identifying existing subcommands, their operational effects (read vs. write), any configuration toggles, and relevant file paths and functions.

## Current `maestro wsession` Implementation

Based on the inspection of `maestro/commands/work_session.py` and `maestro/main.py`, the `maestro wsession` command currently provides the following subcommands:

| Subcommand    | Aliases   | Description                           | Operational Effect (Read/Write) |
| :------------ | :-------- | :------------------------------------ | :------------------------------ |
| `list`        | `ls`, `l` | List work sessions.                   | Read-only                       |
| `show`        | `sh`      | Show work session details.            | Read-only                       |
| `tree`        | `tr`      | Show session hierarchy tree.          | Read-only                       |
| `breadcrumbs` | -         | Show breadcrumbs for a session.       | Read-only                       |
| `timeline`    | -         | Show timeline for a session.          | Read-only                       |
| `stats`       | -         | Show work session statistics.         | Read-only                       |

**Key observation:** All existing `wsession` subcommands are designed for **read-only** operations. They retrieve and display information about past or current work sessions and their associated data (like breadcrumbs, timelines, and statistics). There are no subcommands or functionalities that directly allow for the creation, update, or deletion of project artifacts such as tasks, issues, or modifications to phase/track states within the `Repo Truth Store` (e.g., files in `docs/maestro/**`).

## Existing Message Types

The `wsession` commands primarily interact with and display structured log data, which implicitly includes "breadcrumb" and "timeline" events. While the specific internal representation of these messages isn't fully detailed in the CLI parsing, the functionality strongly suggests that these are informational, append-only records of activity within a session.

There are no explicit "mutation" message types or commands that would correspond to `issue.create`, `task.update`, etc., as proposed in WF-16.

## Configuration Toggles

No explicit configuration toggles were identified within the `wsession` command structure or its handlers that would enable or disable a "mutation mode." The current implementation operates solely in what WF-16 terms "Log-only mode."

## Relevant File Paths and Functions

The core logic for `wsession` commands resides in:

*   **`maestro/commands/work_session.py`**:
    *   `add_wsession_parser(subparsers)`: Defines the `wsession` command and its subcommands using `argparse`.
    *   `handle_wsession_list(args)`: Handler for `wsession list`.
    *   `handle_wsession_show(args)`: Handler for `wsession show`.
    *   `handle_wsession_tree(args)`: Handler for `wsession tree`.
    *   `handle_wsession_breadcrumbs(args)`: Handler for `wsession breadcrumbs`.
    *   `handle_wsession_timeline(args)`: Handler for `wsession timeline`.
    *   `handle_wsession_stats(args)`: Handler for `wsession stats`.
*   **`maestro/main.py`**:
    *   Contains the main command dispatch logic that calls the `handle_wsession_*` functions based on parsed CLI arguments.
*   **`maestro/modules/cli_parser.py`**:
    *   Integrates `add_wsession_parser` into the overall CLI structure.

## Gap Analysis: Mutation Mode Implementation

Currently, a "mutation mode" for `maestro wsession` **does not exist** in the codebase. The existing `wsession` utility is exclusively a diagnostic and reporting tool for work session data.

### Minimal Code Entry Points for Future Mutation Gating

Implementing mutation mode would require adding new subcommands or an alternative command structure to `maestro wsession`. The gating mechanisms (config, CLI flag, cookie capability) would need to be checked at the earliest possible entry point for any mutation-related subcommand.

Potential entry points for integrating mutation gating:

1.  **Within `maestro/commands/work_session.py`:**
    *   A new function, e.g., `add_wsession_mutation_parser(subparsers)`, would be introduced to define mutation-specific subcommands (e.g., `wsession mutate task.create`).
    *   The handlers for these new mutation commands (e.g., `handle_wsession_mutate_task_create`) would be the primary place to enforce the WF-16 gating policies.
    *   Checks for the CLI flag (`--enable-wsession-mutation`) would be performed here.
2.  **Within the main dispatch in `maestro/main.py`:**
    *   Before calling any `handle_wsession_mutate_*` function, a check would occur to ensure that the global configuration allows mutation and that the `work-run` was invoked with the appropriate CLI flag.
    *   The `wsession cookie` validation (WF-15) would also be performed at this stage or delegated to a shared utility function.
3.  **A new `maestro/modules/wsession_mutator.py` (Proposed):**
    *   To keep `work_session.py` focused on read-only operations, a new module could be created to encapsulate all mutation logic and its associated gating. This would contain functions like `perform_task_create`, `perform_issue_update`, etc., each beginning with the necessary checks for mutation mode enablement, cookie validation, and branch guardrails.

This approach ensures that the "log-only" default remains, and "mutation mode" is strictly opt-in and controlled through clearly defined code paths.
