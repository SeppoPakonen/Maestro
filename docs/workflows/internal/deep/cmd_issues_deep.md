# Command: `issues`

## 1. Command Surface

*   **Command:** `issues`
*   **Aliases:** None
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.issues.handle_issues_command`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.issues.handle_issues_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/issues.py`
*   **Specific Subcommand Handlers:** `_handle_list`, `_handle_show`, `_handle_state`, `_handle_rollback`, `_handle_react`, `_handle_analyze`, `_handle_decide`, `_handle_fix`.

## 3. Call Chain (ordered)

The `handle_issues_command` function acts as the central router, dispatching to various specialized `_handle_*` functions based on the `issues_subcommand`.

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.issues.handle_issues_command(args)`
    *   **Purpose:** Entry point for the `issues` command.
2.  `maestro.commands.issues._find_repo_root()`
    *   **Purpose:** Locates the repository root by searching for a `.maestro/` directory. This is crucial for determining the base path for `docs/issues/` files.
3.  **Specific subcommand handler is invoked.**

### `maestro issues list`

1.  ... → `maestro.commands.issues._handle_list(repo_root, issue_type)`
2.  `maestro.issues.issue_store.list_issues(repo_root, issue_type=issue_type)`
    *   **Purpose:** Reads all issue Markdown files from `docs/issues/` and filters them.
3.  `maestro.modules.utils.print()` for formatted output.

### `maestro issues show <id>`

1.  ... → `maestro.commands.issues._handle_show(repo_root, issue_id)`
2.  `maestro.commands.issues._find_issue_path(repo_root, issue_id)`
    *   **Purpose:** Locates the specific `docs/issues/<issue_id>.md` file.
3.  `maestro.issues.issue_store.load_issue(issue_path)`
    *   **Purpose:** Parses the Markdown file into an `IssueRecord` object.
4.  `maestro.modules.utils.print()` for formatted output.

### `maestro issues state <id> <state>`

1.  ... → `maestro.commands.issues._handle_state(repo_root, issue_id, state)`
2.  `maestro.issues.issue_store.update_issue_state(repo_root, issue_id, state)`
    *   **Purpose:** Updates the `state` metadata in the issue's Markdown file and records the change in `## History`.
    *   **Internal Call Chain:** `_find_issue_path`, `_update_metadata_line`, `_append_history` (from `issue_store.py`).
    *   **Validation:** `IssueRecord.can_transition(new_state)` (from `maestro.issues.model.py`) is used internally to validate state changes.

### `maestro issues rollback <id>`

1.  ... → `maestro.commands.issues._handle_rollback(repo_root, issue_id)`
2.  `maestro.issues.issue_store.rollback_issue_state(repo_root, issue_id)`
    *   **Purpose:** Reverts the issue state to the previous one recorded in `## History`.
    *   **Internal Call Chain:** `_find_issue_path`, `_load_history`, `_update_metadata_line`, `_append_history` (from `issue_store.py`).

### `maestro issues react <id>`

1.  ... → `maestro.commands.issues._handle_react(repo_root, issue_id, include_external)`
2.  `_find_issue_path(repo_root, issue_id)`
3.  `maestro.issues.issue_store.load_issue(issue_path)`
4.  `maestro.solutions.solution_store.match_solutions(record, repo_root, include_external=include_external)`
    *   **Purpose:** Finds relevant solutions for the issue.
5.  `maestro.issues.issue_store.update_issue_state(repo_root, record.issue_id, "reacted")`
6.  `maestro.issues.issue_store.update_issue_metadata(repo_root, record.issue_id, "solutions", ", ".join(solution_ids))`
7.  `maestro.issues.issue_store.update_issue_section(repo_root, record.issue_id, "Reaction", summary)`.

### `maestro issues analyze <id>`

1.  ... → `maestro.commands.issues._handle_analyze(repo_root, issue_id, use_ai, summary, confidence, include_external)`
2.  `_find_issue_path(repo_root, issue_id)`
3.  `maestro.issues.issue_store.load_issue(issue_path)`
4.  `maestro.solutions.solution_store.match_solutions(...)` (to provide context to AI).
5.  `(If use_ai)` `maestro.ai.client.ExternalCommandClient()` → `client.send_message(...)`
    *   **Purpose:** Sends issue details to an AI for analysis.
6.  `maestro.commands.issues._extract_confidence(analysis_text)`
    *   **Purpose:** Extracts a numerical confidence score from the AI's (or manual) analysis text.
7.  `maestro.commands.issues._first_sentence(analysis_text)` (to create a summary).
8.  `maestro.issues.issue_store.update_issue_state(...)` ("analyzing" then "analyzed").
9.  `maestro.issues.issue_store.update_issue_metadata(...)` (for analysis summary and confidence).
10. `maestro.issues.issue_store.update_issue_section(...)` (for adding the "Analysis" section).

### `maestro issues decide <id>`

1.  ... → `maestro.commands.issues._handle_decide(repo_root, issue_id, decision, auto, priority)`
2.  `_find_issue_path(repo_root, issue_id)`
3.  `maestro.issues.issue_store.load_issue(issue_path)`
4.  Decision logic (auto-approve if `auto` and high confidence, else prompt user).
5.  `maestro.issues.issue_store.update_issue_metadata(...)` (for decision).
6.  `maestro.issues.issue_store.update_issue_section(...)` (for "Decision" section).
7.  `maestro.issues.issue_store.update_issue_state(...)` ("decided" or "cancelled").
8.  `maestro.issues.issue_store.update_issue_priority(...)` (if defer decision).

### `maestro issues fix <id>`

1.  ... → `maestro.commands.issues._handle_fix(repo_root, issue_id, complete, include_external)`
2.  `_find_issue_path(repo_root, issue_id)`
3.  `maestro.issues.issue_store.load_issue(issue_path)`
4.  `maestro.solutions.solution_store.match_solutions(...)` (to include solutions in the fix plan).
5.  `maestro.commands.issues._create_fix_session(repo_root, record, matches)`
    *   **Purpose:** Generates a new Markdown file (`docs/sessions/issue-<id>-fix-<timestamp>.md`) containing a plan to fix the issue.
6.  `maestro.issues.issue_store.update_issue_metadata(...)` (for `fix_session` path).
7.  `maestro.issues.issue_store.update_issue_state(...)` ("fixing" then optionally "fixed").
8.  `maestro.issues.issue_store.update_issue_section(...)` (for "Fix" section).

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/issues/*.md`: Individual Markdown files storing issue records.
    *   `docs/solutions/*.md`: Individual Markdown files storing solution records (for `match_solutions`).
*   **Writes:**
    *   `docs/issues/*.md`: Updated for state changes, metadata updates, and new sections (`Reaction`, `Analysis`, `Decision`, `Fix`).
    *   `docs/sessions/*.md`: New Markdown files are created for fix sessions.
*   **Schema:** Issues are stored in a custom Markdown format enforced by `maestro.issues.issue_store` with metadata at the top and structured sections (`## Description`, `## Location`, `## History`, etc.).

## 5. Configuration & Globals

*   `maestro.issues.model.ISSUE_TYPES`: Defines valid issue categories.
*   `maestro.issues.model.ISSUE_STATES`: Defines valid issue lifecycle states.
*   `maestro.issues.model.STATE_TRANSITIONS`: Defines valid transitions between issue states.
*   `docs/issues/`: Canonical directory for issue files.
*   `docs/sessions/`: Canonical directory for fix session files.

## 6. Validation & Assertion Gates

*   **Issue Type Validation:** `_handle_list` and internal logic check against `ISSUE_TYPES`.
*   **Issue State Validation:** `_handle_state` checks against `ISSUE_STATES` and `IssueRecord.can_transition`.
*   **Issue ID Existence:** `_find_issue_path` ensures the issue exists.
*   **AI Confidence Threshold:** `_handle_decide` uses `record.analysis_confidence >= 80` for auto-approval.
*   **Input Validation:** `argparse` validates subcommand arguments; `_handle_decide` validates user input for decision.

## 7. Side Effects

*   Modifies existing Markdown files (`docs/issues/*.md`).
*   Creates new Markdown files (`docs/sessions/*.md`).
*   May invoke external AI service (`ExternalCommandClient`).
*   Prints formatted output to console.

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., issue not found, invalid state).
*   `ValueError` for invalid state transitions.
*   Graceful fallback for AI analysis failure.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_issues.py` should cover all `_handle_*` functions.
    *   Tests for state transitions (valid/invalid).
    *   Tests for `_create_fix_session` to verify correct Markdown generation.
    *   Integration tests with `ExternalCommandClient` (mocked).
    *   Tests for solution matching.
    *   Tests for `_extract_confidence` logic.
*   **Coverage Gaps:**
    *   Testing with issues having very long descriptions, titles, or numerous solutions.
    *   Edge cases for `_extract_confidence` (e.g., text without a number).
    *   Robustness against malformed `docs/issues/*.md` files.
    *   Comprehensive testing of AI analysis fallback when `use_ai` is false or AI fails.
