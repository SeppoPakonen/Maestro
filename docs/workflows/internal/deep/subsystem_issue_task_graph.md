# Subsystem Deep Dive: Issue/Task Graph

This subsystem manages the creation, linking, and lifecycle of issues and tasks within Maestro. It integrates structured data from Markdown files (for issues and their human-readable representations) and JSON files (for detailed task/phase/track management).

## 1. How Issues/Tasks are Created and Linked

### Issue Creation and Persistence

*   **Source:**
    *   Issues can be automatically generated from build logs (`maestro/issues/parsers.py:_parse_build_line`) and static analyzer outputs (`maestro/issues/parsers.py:_parse_analyzer_line`).
    *   The `maestro make` command can trigger issue generation from its output.
    *   Implicitly, issues can be "written" via `maestro.issues.issue_store.write_issue` which could be called by other commands or internal logic not directly exposed as a top-level `issues add` command.
*   **Structure:** Defined by `maestro.issues.model.IssueRecord` and `maestro.issues.issue_store.IssueDetails`.
*   **Storage:** Each issue is stored as a Markdown file in `docs/issues/<issue_id>.md`.
    *   Metadata is extracted using key-value pairs at the beginning of the file (e.g., `"issue_id": "value"`).
    *   Detailed description, location, and history are stored in Markdown sections (`## Description`, `## Location`, `## History`).
*   **Linking:**
    *   **To Solutions:** The `maestro issues react` command (handled by `maestro.commands.issues._handle_react`) attempts to match known solutions (`maestro.solutions.solution_store.match_solutions`) and updates the issue's `solutions` metadata field and adds a `## Reaction` section.
    *   **To Fix Sessions/Tasks:** The `maestro issues fix` command (handled by `maestro.commands.issues._handle_fix`) creates a dedicated Markdown "fix session" file (`docs/sessions/issue-<id>-fix-<timestamp>.md`). This file details the issue and includes a `## Plan` section with a list of checkboxes (`- [ ] step`), acting as a set of actionable tasks directly linked to resolving the issue. This creates a conceptual link between an issue and a task list.

### Task Creation and Management

*   **Source:**
    *   Tasks are primarily created via the `maestro task add` command (`maestro.commands.task.add_task`).
    *   The `_create_fix_session` function for issues also generates a list of task-like steps, though these are initially free-form Markdown rather than structured `Task` objects.
*   **Structure:** Defined by `maestro.tracks.models.Task` (from `maestro/tracks/json_store.py` contextually). A `Task` object includes `task_id`, `name`, `status`, `priority`, `estimated_hours`, `description`, `phase_id`, `completed`, `tags`, `owner`, `dependencies`, `subtasks`.
*   **Storage:** Tasks are primarily managed as structured JSON files via `maestro.tracks.json_store.JsonStore` (e.g., `.maestro/tracks/tasks/<task_id>.json`).
    *   However, tasks are also represented within Markdown files (`docs/todo.md`, `docs/phases/<phase_id>.md`) using Markdown headings, lists, and checkboxes. `maestro.data.markdown_parser.py` and `maestro.data.markdown_writer.py` are used to read and update these Markdown representations. This indicates a hybrid storage or migration from Markdown-centric to JSON-centric task management.
*   **Hierarchy and Linking:**
    *   Tasks are linked to `Phase` objects via their `phase_id` field.
    *   Phases are linked to `Track` objects (as seen in `Docs Truth` discussion and `maestro.tracks.models`).
    *   This creates a hierarchical graph: `Track -> Phase -> Task`.
    *   Tasks can contain `subtasks` (a list of subtask objects/IDs), creating a nested hierarchy within tasks.
    *   The `_collect_task_entries` function in `maestro.commands.task.py` collects tasks by traversing tracks and phases from the JSON store.

## 2. Dependency Ordering Logic

*   **Task-to-Task Dependencies:** The `maestro.tracks.models.Task` object includes a `dependencies: List[str]` field. This field is intended to store `task_id`s that the current task depends on.
*   **Current Implementation:** While the field exists, the explicit logic for building a dependency graph, performing topological sorting, or enforcing dependency order (e.g., preventing a task from being marked `done` if its dependencies are not met) is not directly evident in the `maestro.commands.task.py` or `maestro.issues.issue_store.py` files. This logic would likely reside in a higher-level planning or execution component that processes the task graph.

## 3. Priority Computation

*   **Issues:**
    *   The `maestro.issues.issue_store.IssueDetails` and `maestro.issues.model.IssueRecord` dataclasses include a `priority: int` field (defaulting to 50 for new issues).
    *   Priority can be explicitly set or updated via `maestro.issues.issue_store.update_issue_priority` and the `maestro issues decide --priority` command.
    *   There is no explicit "computation" of issue priority; it's a value set by the user or an automated decision (e.g., during AI analysis).
*   **Tasks:**
    *   The `maestro.tracks.models.Task` object includes a `priority` field (e.g., defaulting to 'P2' when a task is added).
    *   Similar to issues, task priority is directly assigned rather than computed algorithmically based on dependencies or other factors within the currently reviewed files.

## 4. Configuration & Globals

*   `maestro.issues.model.ISSUE_TYPES` (set of strings): Valid issue categories.
*   `maestro.issues.model.ISSUE_STATES` (list of strings): Valid states for issues.
*   `maestro.issues.model.STATE_TRANSITIONS` (dict): Defines valid state transitions for issues.
*   File system paths for `docs/issues/` and `docs/sessions/` are used as persistent storage locations.
*   `maestro.config.settings.get_settings().current_task`: Global state for the currently active task context.

## 5. Validation & Assertion Gates

*   **Issue State Transitions:** `maestro.issues.model.IssueRecord.can_transition(next_state)` enforces valid state changes for issues based on `STATE_TRANSITIONS`. `maestro.issues.issue_store.update_issue_state` checks this before updating.
*   **Issue Type Validation:** `maestro.issues.model.IssueRecord.is_valid_type()` validates against `ISSUE_TYPES`.
*   **Task Status Validation:** `maestro.commands.task.set_task_status` uses `status_utils.normalize_status` and `status_utils.allowed_statuses` to validate task status inputs.
*   **Data Integrity:** Both issue and task management rely on the integrity of their respective Markdown and JSON files. Errors in parsing or writing can lead to data inconsistencies.

## 6. Side Effects

*   Creation/modification of Markdown files in `docs/issues/` (for issues) and `docs/sessions/` (for fix sessions).
*   Creation/modification of JSON files in `.maestro/tracks/tasks/` (for tasks).
*   Updates to `docs/todo.md` and `docs/phases/*.md` Markdown files reflecting task changes.
*   Updates to global configuration (e.g., `current_task` in `settings.json`).
*   Potential invocation of AI for issue analysis (`ExternalCommandClient`).

## 7. Error Semantics

*   `ValueError` raised for invalid issue state transitions.
*   `KeyError` or `FileNotFoundError` can occur during parsing/loading if files are malformed or missing.
*   Command-line errors are reported to `stderr` with exit code `1`.

## 8. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/test_issues.py` (likely for `issue_store.py` and `model.py`).
    *   `maestro/tests/test_commands_issues.py` and `maestro/tests/test_commands_task.py` (for CLI command logic).
    *   Tests for `maestro.issues.parsers.py` should exist to cover different log/analyzer formats.
*   **Coverage Gaps:**
    *   Explicit tests for complex dependency scenarios (e.g., circular dependencies, long chains).
    *   Integration tests for the hybrid Markdown/JSON task management system to ensure consistency.
    *   Tests covering the graceful handling of corrupted Markdown/JSON files.
