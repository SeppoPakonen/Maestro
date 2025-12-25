# Command: `phase`

## 1. Command Surface

*   **Command:** `phase`
*   **Aliases:** `ph`, `p`
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.phase.handle_phase_command` which then routes to specific `list_phases`, `add_phase`, `remove_phase`, `show_phase`, etc.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.phase.handle_phase_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/phase.py`
*   **Specific Subcommand Handlers:** `list_phases`, `show_phase`, `add_phase`, `remove_phase`, `edit_phase`, `set_phase_status`, `set_phase_context`, `maestro.commands.discuss.handle_phase_discuss`.

## 3. Call Chain (ordered)

The `handle_phase_command` function acts as the central router, dispatching to various specialized functions based on the `phase_subcommand`.

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.phase.handle_phase_command(args)`
    *   **Purpose:** Entry point for the `phase` command.
2.  `maestro.commands.phase._parse_todo_safe(Path('docs/todo.md'))` (often implicitly called by helpers like `get_all_tracks_with_phases_and_tasks`).
    *   **Purpose:** Safely parses the main `todo.md` file for phase information.
3.  **Specific subcommand handler is invoked.**

### `maestro phase list`

1.  ... → `maestro.commands.phase.list_phases(args)`
2.  `maestro.data.common_utils.get_all_tracks_with_phases_and_tasks(verbose)`
    *   **Purpose:** Retrieves a comprehensive view of tracks and their phases from the underlying storage (JSON store).
3.  `maestro.config.settings.get_settings()` (to get `current_track` for filtering).
4.  `maestro.display.table_renderer.render_phase_table(formatted_phases, track_filter)`
    *   **Purpose:** Formats the phase data for console output.

### `maestro phase show <id>`

1.  ... → `maestro.commands.phase.show_phase(phase_id, args)`
2.  `pathlib.Path(f'docs/phases/{phase_id}.md').exists()`
    *   **Purpose:** Checks for a dedicated Markdown file for the phase.
3.  `maestro.data.parse_phase_md(str(phase_file))` (if dedicated file exists).
    *   **Purpose:** Parses the phase's dedicated Markdown file.
4.  `maestro.commands.phase._parse_todo_safe(Path('docs/todo.md'))` (if no dedicated file, searches in `docs/todo.md`).
5.  `maestro.modules.utils.print_header(...)` and `print()` for detailed, formatted output.

### `maestro phase add <name>`

1.  ... → `maestro.commands.phase.add_phase(name, args)`
2.  `maestro.config.settings.get_settings()` (to get `current_track` if not explicitly provided).
3.  `maestro.tracks.json_store.JsonStore()`
4.  `JsonStore.load_track(track_id, ...)` (to ensure parent track exists).
5.  `maestro.commands.phase._looks_like_phase_id(phase_id)` (to validate ID).
6.  `JsonStore.load_phase(phase_id, ...)` (to check for duplicates).
7.  `maestro.tracks.models.Phase(...)` (to create a new Phase object).
8.  `JsonStore.save_phase(phase)`.
9.  `JsonStore.save_track(track)` (to update the parent track's list of phases).
10. `maestro.modules.utils.print_success(...)`.

### `maestro phase remove <id>`

1.  ... → `maestro.commands.phase.remove_phase(phase_id, args)`
2.  `maestro.tracks.json_store.JsonStore()`
3.  `JsonStore.load_phase(phase_id, ...)` (to get `track_id` and verify existence).
4.  `JsonStore.load_track(track_id, ...)` (to update parent track).
5.  `JsonStore.save_track(track)`.
6.  `pathlib.Path(f'{json_store.phases_dir}/{phase_id}.json').unlink()` (to delete the phase's JSON file).
7.  `maestro.modules.utils.print_success(...)`.

### `maestro phase edit <id>`

1.  ... → `maestro.commands.phase.edit_phase(phase_id, args)`
2.  `pathlib.Path(f'docs/phases/{phase_id}.md').exists()` (checks for dedicated Markdown file).
3.  `subprocess.run([editor, str(phase_file)])` (if dedicated file exists, opens directly).
4.  `maestro.data.markdown_writer.extract_phase_block(todo_path, phase_id)` (if no dedicated file, extracts from `docs/todo.md`).
5.  `tempfile.NamedTemporaryFile()` → `subprocess.run([editor, tmp_path])`
    *   **Purpose:** Opens content in a temporary file in `$EDITOR`.
6.  `maestro.data.markdown_writer.replace_phase_block(todo_path, phase_id, new_block)`.

### `maestro phase status <id> <status>`

1.  ... → `maestro.commands.phase.set_phase_status(phase_id, args)`
2.  `maestro.commands.phase.normalize_status(status_value)` (from `maestro.commands.status_utils`).
3.  `maestro.tracks.json_store.JsonStore()`
4.  `JsonStore.load_phase(phase_id, ...)` (loads phase object).
5.  `phase.status = status_value`.
6.  `JsonStore.save_phase(phase)`.
7.  `maestro.modules.utils.print_success(...)`.

### `maestro phase set <id>`

1.  ... → `maestro.commands.phase.set_phase_context(phase_id, args)`
2.  `_parse_todo_safe(...)` (to find phase and its parent track from `docs/todo.md`).
3.  `maestro.data.parse_phase_md(str(phase_file))` (if found in dedicated phase file).
4.  `maestro.config.settings.get_settings()`
5.  `settings.current_phase = phase_id`, `settings.current_track = parent_track`, `settings.current_task = None`.
6.  `settings.save()`.

### `maestro phase discuss <id>`

1.  ... → `maestro.commands.discuss.handle_phase_discuss(phase_id, args)`
    *   **Purpose:** Delegates to the dedicated AI discussion handler.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/todo.md`: Main Markdown for active tracks/phases.
    *   `docs/done.md`: Markdown for completed tracks/phases (for `list_phases` indirectly).
    *   `docs/phases/<phase_id>.md`: Dedicated Markdown files for phases.
    *   `.maestro/tracks/*.json` (e.g., `<track_id>.json`, `<phase_id>.json`): JSON files for `Track` and `Phase` objects (via `JsonStore`).
    *   `settings.json`: For current context.
*   **Writes:**
    *   `docs/todo.md`: Modified during `edit_phase` (if no dedicated file).
    *   `docs/phases/<phase_id>.md`: Modified directly during `edit_phase` if file exists.
    *   `.maestro/tracks/*.json`: Created/deleted/updated during `add_phase`, `remove_phase`, `set_phase_status` (for JSON representation).
    *   `settings.json`: Updated during `set_phase_context`.
*   **Schema:**
    *   Markdown files (`docs/todo.md`, `docs/phases/*.md`) adhere to the implicit schema enforced by `maestro.data.markdown_parser` and `maestro.data.markdown_writer`.
    *   JSON files (`.maestro/tracks/*.json`) adhere to the schema defined by `maestro.tracks.models.Phase`.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vim')`: User's preferred editor.
*   `maestro.config.settings`: Provides access to global settings (`current_track`, `current_phase`, `current_task`).
*   `docs/todo.md`, `docs/phases/`: Canonical file paths.

## 6. Validation & Assertion Gates

*   **Phase ID Format:** `_looks_like_phase_id` and regex checks for phase IDs.
*   **Duplicate Phase ID Check:** `add_phase` prevents adding phases with existing IDs.
*   **Phase Status Validation:** `normalize_status` and `allowed_statuses` ensure valid status values.
*   **File Existence:** Checks for `docs/todo.md` and dedicated phase Markdown files.
*   **Track Existence:** `add_phase` ensures the parent track exists.
*   **Editor Invocation:** Error handling for editor not found.

## 7. Side Effects

*   Modifies files on the local filesystem (`docs/todo.md`, `docs/phases/*.md`, `.maestro/tracks/*.json`, `settings.json`).
*   Creates temporary files.
*   Spawns external editor processes.
*   Prints formatted output to console.
*   Changes global application context (`settings.current_phase`, `settings.current_track`).

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., phase not found, invalid input, file system issues).
*   `print_warning` for non-critical issues.
*   `ValueError` can be raised by internal parsing/validation logic.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_phase.py` should cover all subcommands.
    *   Tests for Markdown interaction (extract, replace, update blocks).
    *   Tests for JSON store interaction (add, remove phases).
    *   Tests for identifier resolution.
    *   Tests for status updates and context setting.
    *   Integration tests with `handle_phase_discuss`.
    *   Tests for editor integration.
*   **Coverage Gaps:**
    *   Thorough testing of the hybrid Markdown/JSON persistence model to ensure consistency when phases are moved or status changes.
    *   Testing of edge cases in `add_phase` (e.g., track not found).
    *   Robustness testing for malformed Markdown or JSON phase files.
    *   Testing scenarios where `current_track` is used for filtering.
