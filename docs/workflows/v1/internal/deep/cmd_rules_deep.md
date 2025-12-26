# Command: `rules/r`

## 1. Command Surface

*   **Command:** `rules`
*   **Aliases:** `r`
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.modules.command_handlers.handle_rules_list` or `maestro.modules.command_handlers.handle_rules_file`.

## 2. Entrypoint(s)

*   **Primary Dispatchers:** `maestro.modules.command_handlers.handle_rules_list(session_path, verbose)`, `maestro.modules.command_handlers.handle_rules_file(session_path, verbose)`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/modules/command_handlers.py`

## 3. Call Chain (ordered)

The `rules` command functions operate on a session-specific `rules.txt` file, which contains instructions for AI task orchestration.

### Common Flow for `rules` commands

1.  `maestro.main.main()` → (dispatches to `handle_rules_list` or `handle_rules_file`)
    *   **Purpose:** Entry point for the `rules` command.
2.  `maestro.session_model.load_session(session_path)`
    *   **Purpose:** Loads the `Session` object to determine the rules file path.
    *   **Error Handling:** Catches `FileNotFoundError` or other exceptions if the session file is missing or corrupted.
3.  Determines `rules_filename`:
    *   If `session.rules_path` is set, uses that.
    *   Otherwise, defaults to `session_dir/rules.txt` and updates `session.rules_path` in the `Session` object, then `save_session()`.

### `maestro rules list`

1.  ... → `maestro.modules.command_handlers.handle_rules_list(session_path, verbose)`
2.  Reads the content of `rules_filename`.
3.  `print_header("CURRENT RULES")` and prints rules content line by line, prepending line numbers.

### `maestro rules edit`

1.  ... → `maestro.modules.command_handlers.handle_rules_file(session_path, verbose)`
2.  Ensures `rules_filename` exists (creates with boilerplate if not).
3.  `os.environ.get('EDITOR', 'vi')` to get the editor.
4.  `subprocess.run([editor, rules_filename])`
    *   **Purpose:** Invokes the user's `$EDITOR` to modify the rules file.
    *   **Error Handling:** Catches `FileNotFoundError` if editor is not found, or other exceptions during subprocess execution. If an error occurs, it tries to mark the session status as "failed".

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/sessions/<session-name>/session.json`: To get or update `session.rules_path`.
    *   `docs/sessions/<session-name>/rules.txt`: The rules file itself.
*   **Writes:**
    *   `docs/sessions/<session-name>/session.json`: If `session.rules_path` is updated or `session.status` is set to "failed" due to editor error.
    *   `docs/sessions/<session-name>/rules.txt`: Created with boilerplate if it doesn't exist, or modified by the external editor.
*   **Schema:** `rules.txt` is a plain text file, typically Markdown or similar, without a strict programmatic schema enforced by this module, though it's intended to contain human-readable rules.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vi')`: User's preferred text editor.
*   `session_path`: Derived from the `session` command's `--session` argument or inferred.

## 6. Validation & Assertion Gates

*   **Session Existence:** Checks if the session file exists.
*   **Rules File Existence:** If `rules.txt` doesn't exist, it's created.
*   **Editor Existence:** `FileNotFoundError` for `subprocess.run` if the editor is not found.

## 7. Side Effects

*   Loads and saves `Session` objects.
*   Creates or modifies `rules.txt` files within a session's directory.
*   Invokes an external editor process.
*   Prints rules content or status messages to console.

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., session not found, editor error).
*   `Session` status is updated to "failed" if an editor error prevents rule file handling.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Unit/integration tests for `handle_rules_list` and `handle_rules_file`.
    *   Tests for rules file creation with boilerplate.
    *   Tests for editor invocation (mocking `subprocess.run`).
    *   Tests for `session.rules_path` update logic.
    *   Tests for error handling scenarios (missing session, editor not found).
*   **Coverage Gaps:**
    *   Testing with various forms of `rules.txt` content (e.g., very large files, special characters).
    *   Robustness testing for editor failures during editing.
    *   Integration with AI prompts that consume these rules.
