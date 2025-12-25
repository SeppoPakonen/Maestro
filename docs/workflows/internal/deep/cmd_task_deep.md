# Command: `task`

## 1. Command Surface

*   **Command:** `task`
*   **Aliases:** `ta`
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.task.handle_task_command` which then routes to specific `list_tasks`, `add_task`, `remove_task`, `show_task`, etc.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.task.handle_task_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/task.py`
*   **Specific Subcommand Handlers:** `list_tasks`, `show_task`, `add_task`, `remove_task`, `edit_task`, `set_task_status`, `set_task_context`, `maestro.commands.discuss.handle_task_discuss`.

## 3. Call Chain (ordered)

The `handle_task_command` function acts as the central router, dispatching to various specialized functions based on the `task_subcommand`. It also includes complex argument parsing logic for `maestro task <id> <action>` syntax.

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.task.handle_task_command(args)`
    *   **Purpose:** Entry point for the `task` command.
2.  `maestro.commands.task._collect_task_entries(verbose)` (often implicitly called by helpers or for data collection).
    *   **Purpose:** Gathers all task data from JSON storage.
    *   **Internal Call Chain:** `maestro.tracks.json_store.JsonStore` methods (`list_all_tracks`, `load_track`, `list_all_phases`, `load_phase`, `load_task`).
3.  **Specific subcommand handler is invoked.**

### `maestro task list`

1.  ... → `maestro.commands.task.list_tasks(args)`
2.  `maestro.commands.task._parse_task_list_filters(tokens)`
    *   **Purpose:** Extracts status, track, and phase filters from CLI arguments.
3.  `maestro.commands.task._collect_task_entries(verbose)`
    *   **Purpose:** Loads all tasks.
4.  `maestro.display.table_renderer.render_task_table(formatted_tasks)`
    *   **Purpose:** Formats the task data for console output.

### `maestro task show <id>`

1.  ... → `maestro.commands.task.show_task(task_id, args)`
2.  `maestro.commands.task._resolve_task_identifier(task_id, verbose)`
    *   **Purpose:** Resolves the provided `task_id` (which can be an ID or list number) to a full task entry.
3.  `maestro.config.settings.get_settings()` (for Unicode symbol display).
4.  `maestro.modules.utils.print_header(...)` and `print()` for detailed, formatted output.

### `maestro task add <name>`

1.  ... → `maestro.commands.task.add_task(name, args)`
2.  `maestro.config.settings.get_settings()` (to get `current_phase` if not explicitly provided).
3.  `maestro.tracks.json_store.JsonStore()`
4.  `JsonStore.load_phase(phase_id, ...)` (to ensure parent phase exists and get its tasks).
5.  Logic to auto-generate `task_id` (e.g., `<phase_id>.<number>`).
6.  `JsonStore.load_task(task_id)` (to check for duplicates).
7.  `maestro.tracks.models.Task(...)` (to create a new Task object).
8.  `JsonStore.save_task(task)`.
9.  `JsonStore.save_phase(phase)` (to update the parent phase's list of tasks).
10. `maestro.modules.utils.print_success(...)`.

### `maestro task remove <id>`

1.  ... → `maestro.commands.task.remove_task(task_id, args)`
2.  `maestro.tracks.json_store.JsonStore()`
3.  `JsonStore.load_task(task_id)` (to get `phase_id` and verify existence).
4.  `JsonStore.load_phase(phase_id, ...)` (to update parent phase).
5.  `JsonStore.save_phase(phase)`.
6.  `pathlib.Path(f'{json_store.tasks_dir}/{task_id}.json').unlink()` (to delete the task's JSON file).
7.  `maestro.modules.utils.print_success(...)`.

### `maestro task edit <id>`

1.  ... → `maestro.commands.task.edit_task(task_id, args)`
2.  `maestro.commands.task._find_task_file(task_id)`
    *   **Purpose:** Finds the `docs/phases/<phase_id>.md` file containing the task.
3.  `maestro.data.markdown_writer.extract_task_block(phase_file, task_id)`
    *   **Purpose:** Extracts the Markdown block corresponding to the task.
4.  `tempfile.NamedTemporaryFile()` → `subprocess.run([editor, tmp_path])`
    *   **Purpose:** Opens the task's content in a temporary file in the user's `$EDITOR`.
5.  `maestro.data.markdown_writer.replace_task_block(phase_file, task_id, new_block)`.

### `maestro task status <id> <status>`

1.  ... → `maestro.commands.task.set_task_status(task_id, args)`
2.  `maestro.commands.task.normalize_status(status_value)` (from `maestro.commands.status_utils`).
3.  `maestro.tracks.json_store.JsonStore()`
4.  `JsonStore.load_task(task_id)` (loads task object).
5.  `task.status = status_value`, `task.completed = (status_value == 'done')`.
6.  `JsonStore.save_task(task)`.
7.  `maestro.modules.utils.print_success(...)`.

### `maestro task complete <id>`

1.  ... → `maestro.commands.task.complete_task(task_id, args)`
2.  Sets `args.status = 'done'` and calls `set_task_status`.

### `maestro task set <id>`

1.  ... → `maestro.commands.task.set_task_context(task_id, args)`
2.  `maestro.config.settings.get_settings()`
3.  `settings.current_task = task_id`.
4.  `settings.save()`.

### `maestro task discuss <id>`

1.  ... → `maestro.commands.discuss.handle_task_discuss(task_id, args)`
    *   **Purpose:** Delegates to the dedicated AI discussion handler.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/todo.md`, `docs/done.md`, `docs/phases/<phase_id>.md`: Markdown files related to tasks.
    *   `.maestro/tracks/*.json` (e.g., `<track_id>.json`, `<phase_id>.json`, `tasks/<task_id>.json`): JSON files for `Track`, `Phase`, and `Task` objects (via `JsonStore`).
    *   `settings.json`: For current context.
*   **Writes:**
    *   `docs/phases/<phase_id>.md`: Modified during `edit_task` and `set-text`.
    *   `.maestro/tracks/tasks/*.json`: Created/deleted/updated for `Task` objects.
    *   `.maestro/tracks/phases/*.json`: Updated for parent `Phase` objects.
    *   `settings.json`: Updated during `set_task_context`.
*   **Schema:**
    *   Markdown files (`docs/phases/*.md`) adhere to the implicit schema enforced by `maestro.data.markdown_parser` and `maestro.data.markdown_writer` for tasks.
    *   JSON files (`.maestro/tracks/tasks/*.json`) adhere to the schema defined by `maestro.tracks.models.Task`.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vim')`: User's preferred editor.
*   `maestro.config.settings`: Provides access to global settings (`current_track`, `current_phase`, `current_task`, `unicode_symbols`).
*   `docs/phases/`: Directory for dedicated phase Markdown files.

## 6. Validation & Assertion Gates

*   **Task ID Resolution:** `_resolve_task_identifier` ensures a valid task is targeted.
*   **Task ID Generation:** `add_task` auto-generates IDs and checks for uniqueness.
*   **Task Status Validation:** `normalize_status` and `allowed_statuses` ensure valid status values.
*   **File Existence:** Checks for Markdown files.
*   **Phase Existence:** `add_task` ensures the parent phase exists.
*   **Editor Invocation:** Error handling for editor not found.
*   **Filter Parsing:** `_parse_task_list_filters` robustly handles list filters.

## 7. Side Effects

*   Modifies files on the local filesystem (`docs/phases/*.md`, `.maestro/tracks/tasks/*.json`, `settings.json`).
*   Creates temporary files.
*   Spawns external editor processes.
*   Prints formatted output to console.
*   Changes global application context (`settings.current_task`).

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., task not found, invalid input, file system issues).
*   `print_warning` for non-critical issues.
*   `ValueError` can be raised by internal parsing/validation logic.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_task.py` should cover all subcommands.
    *   Tests for Markdown interaction (extract, replace, update blocks).
    *   Tests for JSON store interaction (add, remove tasks).
    *   Tests for identifier resolution (`_resolve_task_identifier`).
    *   Tests for status updates and context setting.
    *   Integration tests with `handle_task_discuss`.
    *   Tests for editor integration.
    *   Comprehensive testing of filter parsing (`_parse_task_list_filters`).
    *   Testing of the hybrid Markdown/JSON persistence model to ensure consistency.
*   **Coverage Gaps:**
    *   Thorough testing of complex task dependencies and subtasks in the `Task` model.
    *   Robustness testing for malformed Markdown or JSON task files.
    *   Testing scenarios where `current_phase` is used for filtering tasks.
    *   Integration with AI-driven task modification workflows (e.g., from `maestro plan explore`).
