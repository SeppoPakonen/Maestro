# Command: `session/s`

## 1. Command Surface

*   **Command:** `session`
*   **Aliases:** `s`
*   **Handler Binding:** `maestro.main.main` dispatches directly to `maestro.modules.command_handlers.handle_session_*` functions for session management and to `maestro.commands.work_session.handle_wsession_*` for breadcrumbs, timeline, and stats.

## 2. Entrypoint(s)

*   **Primary Dispatchers:** `maestro.modules.command_handlers.handle_session_new`, `handle_session_list`, `handle_session_set`, `handle_session_get`, `handle_session_remove`, `handle_session_details`.
*   **Delegated Dispatchers:** `maestro.commands.work_session.handle_wsession_breadcrumbs`, `handle_wsession_timeline`, `handle_wsession_stats`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/modules/command_handlers.py` (for direct session management) and `/home/sblo/Dev/Maestro/maestro/commands/work_session.py` (for delegated commands).

## 3. Call Chain (ordered)

The `session` command functions are directly integrated into `maestro.main.main`'s dispatch logic for "Legacy session management".

### `maestro session new <name>`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_new(args.name, args.verbose, args.root_task)`
2.  `maestro.modules.command_handlers.get_session_path_by_name(session_name)`
    *   **Purpose:** Determines the expected path for the session file.
3.  `(If session exists)` User confirmation (`input()`).
4.  `maestro.modules.command_handlers.edit_root_task_in_editor()` or file read.
    *   **Purpose:** Gets the root task description.
5.  `maestro.modules.command_handlers.create_session(session_name, root_task, overwrite=True)`
    *   **Purpose:** Creates the `Session` object and saves it to `docs/sessions/<session_name>/session.json`.
6.  `maestro.modules.command_handlers.set_active_session_name(session_name)`
    *   **Purpose:** Updates the user-specific configuration (`~/.maestro/config.json`) to mark this session as active.

### `maestro session list`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_list(args.verbose)`
2.  `maestro.modules.command_handlers.list_sessions()`
    *   **Purpose:** Retrieves a list of all session names.
3.  `maestro.modules.command_handlers.get_active_session_name()`
    *   **Purpose:** Determines the currently active session.
4.  `maestro.modules.command_handlers.get_session_details(session_name)` (if `verbose`).
    *   **Purpose:** Loads specific session details for display.
5.  `maestro.modules.utils.styled_print()` for formatted output.

### `maestro session set <name|number>`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_set(args.name, args.number, args.verbose)`
2.  `maestro.modules.command_handlers.list_sessions()` (if name/number not provided, or for number resolution).
3.  User input for selection (if no name/number provided).
4.  `maestro.modules.command_handlers.get_session_path_by_name(session_name)` (to verify existence).
5.  `maestro.modules.command_handlers.set_active_session_name(session_name)`.

### `maestro session get`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_get(args.verbose)`
2.  `maestro.modules.command_handlers.get_active_session_name()`.
3.  `maestro.modules.command_handlers.get_session_details(active_session)` (if `verbose`).
4.  `print()` for the active session name.

### `maestro session remove <name>`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_remove(args.name, args.skip_confirmation, args.verbose)`
2.  `maestro.modules.command_handlers.get_session_path_by_name(session_name)` (to verify existence).
3.  User confirmation (`input()`) unless `skip_confirmation`.
4.  `maestro.modules.command_handlers.remove_session(session_name)`.
    *   **Purpose:** Deletes the session directory and its contents.
5.  Logic to clear active session and optionally prompt user to set a new one.

### `maestro session details <name|number>`

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_session_details(args.name, args.list_number, args.verbose)`
2.  `maestro.modules.command_handlers.list_sessions()` (for number resolution or if no name provided).
3.  `maestro.modules.command_handlers.get_session_details(session_name)`
    *   **Purpose:** Loads basic session metadata.
4.  `maestro.session_model.load_session(details['path'])`
    *   **Purpose:** Loads the full `Session` object for detailed display.
5.  `maestro.modules.command_handlers.list_build_targets(details['path'])` (to show build targets count).

### Delegated `wsession` commands (`breadcrumbs`, `timeline`, `stats`)

These commands are directly passed through to `maestro.commands.work_session` handlers.

1.  `maestro.main.main()` → `maestro.commands.work_session.handle_wsession_breadcrumbs(args)` (or `handle_wsession_timeline`, `handle_wsession_stats`).
    *   **Purpose:** Uses the more modern `wsession` commands for these functionalities.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/sessions/<session-name>/session.json`: Main storage for `Session` objects.
    *   `~/.maestro/config.json`: User-specific configuration for active session.
*   **Writes:**
    *   `docs/sessions/<session-name>/session.json`: Created, modified, or deleted.
    *   `~/.maestro/config.json`: Updated for active session management.
*   **Schema:** `Session` objects adhere to the schema defined in `maestro.session_model.py`.

## 5. Configuration & Globals

*   `docs/sessions/`: Canonical directory for all session data.
*   User-specific active session configured in `~/.maestro/config.json`.
*   `EDITOR` environment variable for `edit_root_task_in_editor()` (called by `handle_session_new`).

## 6. Validation & Assertion Gates

*   **Session Existence:** Checks if sessions exist before operating on them.
*   **Confirmation Prompts:** For overwriting new sessions or removing existing ones.
*   **Input Validation:** For session names/numbers.
*   `Session.root_task` cannot be empty for new sessions.

## 7. Side Effects

*   Creates, modifies, or deletes session directories and files (`docs/sessions/`).
*   Updates user-specific configuration files (`~/.maestro/config.json`).
*   Prompts the user for input (`input()`) for selections or confirmations.
*   Opens external editor (`subprocess`) for root task editing.
*   Prints formatted output to console.

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical failures (e.g., session not found, invalid input).
*   `print_warning` for non-critical issues (e.g., session already exists).
*   `FileNotFoundError` for session files.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Unit/integration tests for each `handle_session_*` command.
    *   Tests for active session management (`set`, `get`).
    *   Tests for confirmation prompts and their effects.
    *   Tests for root task creation (file, editor, stdin).
    *   Tests for session details display.
*   **Coverage Gaps:**
    *   Testing the edge cases of session name resolution (numeric vs. string).
    *   Ensuring robustness during file system operations.
    *   Comprehensive testing of active session management, especially after removals.
    *   Testing integration with `edit_root_task_in_editor`.
