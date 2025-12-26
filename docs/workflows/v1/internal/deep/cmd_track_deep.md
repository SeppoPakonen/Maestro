# Command: `track`

## 1. Command Surface

*   **Command:** `track`
*   **Aliases:** `tr`, `t`
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.track.handle_track_command` which then routes to specific `list_tracks`, `add_track`, `remove_track`, `show_track`, etc.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.track.handle_track_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/track.py`
*   **Specific Subcommand Handlers:** `list_tracks`, `show_track`, `show_track_details`, `add_track`, `remove_track`, `edit_track`, `set_track_status`, `set_track_context`, `maestro.commands.discuss.handle_track_discuss`.

## 3. Call Chain (ordered)

The `handle_track_command` function acts as the central router, dispatching to various specialized functions based on the `track_subcommand`.

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.track.handle_track_command(args)`
2.  `maestro.commands.track.resolve_track_identifier(identifier, verbose)` (for commands needing a `track_id`)
    *   **Purpose:** Converts a numerical index or partial ID to a canonical track ID.
    *   **Internal Call Chain:** `maestro.data.common_utils.resolve_identifier_by_type`.
3.  **Specific subcommand handler is invoked.**

### `maestro track list`

1.  ... → `maestro.commands.track.list_tracks(args)`
2.  `maestro.data.common_utils.get_all_tracks_with_phases_and_tasks(verbose)`
    *   **Purpose:** Retrieves a comprehensive view of tracks from the underlying storage.
3.  `maestro.display.table_renderer.render_track_table(formatted_tracks)`
    *   **Purpose:** Formats the track data for console output.

### `maestro track show <id>` and `maestro track details <id>`

1.  ... → `maestro.commands.track.show_track(track_identifier, args)` or `show_track_details(...)`
2.  `maestro.commands.track.resolve_track_identifier(...)`
3.  `_ensure_todo_file(...)` and `_parse_todo_safe(...)`
    *   **Purpose:** Ensures `docs/todo.md` exists and safely parses its content (also `docs/done.md`).
4.  `maestro.config.settings.get_settings()` (for `show_track` to get unicode symbols).
5.  `maestro.modules.utils.Colors` and styling functions for formatted output (`show_track`).
6.  `maestro.display.table_renderer.render_phase_table()` (for `show_track` to list phases).

### `maestro track add <name>`

1.  ... → `maestro.commands.track.add_track(name, args)`
2.  `maestro.tracks.json_store.JsonStore()`
3.  `maestro.commands.track._slugify_track_id(name)` (to generate a track ID if not provided).
4.  `JsonStore.load_track(track_id, ...)` (to check for duplicates).
5.  `maestro.tracks.models.Track(...)` (to create a new Track object).
6.  `JsonStore.save_track(track)`.
7.  `maestro.modules.utils.print_success(...)`.

### `maestro track remove <id>`

1.  ... → `maestro.commands.track.remove_track(track_identifier, args)`
2.  `maestro.tracks.json_store.JsonStore()`
3.  `maestro.commands.track.resolve_track_identifier(...)`
4.  `JsonStore.load_track(...)` (to verify existence).
5.  `Path.unlink()` (to delete the track's JSON file).
6.  `JsonStore.load_index()`, modify, `JsonStore.save_index(index)` (to remove from track index).
7.  `maestro.modules.utils.print_success(...)`.

### `maestro track edit <id>`

1.  ... → `maestro.commands.track.edit_track(track_identifier, args)`
2.  `maestro.commands.track.resolve_track_identifier(...)`
3.  `maestro.data.markdown_writer.extract_track_block(todo_path, track_id)`
    *   **Purpose:** Extracts the Markdown block corresponding to the track.
4.  `tempfile.NamedTemporaryFile()` → `subprocess.run([editor, tmp_path])`
    *   **Purpose:** Opens the track's content in a temporary file in the user's `$EDITOR`.
5.  `maestro.data.markdown_writer.replace_track_block(todo_path, track_id, new_block)`
    *   **Purpose:** Replaces the original Markdown block with the edited content.

### `maestro track status <id> <status>`

1.  ... → `maestro.commands.track.set_track_status(track_identifier, args)`
2.  `maestro.commands.track.resolve_track_identifier(...)`
3.  `maestro.commands.track.normalize_status(status_value)` (from `maestro.commands.status_utils`).
4.  `maestro.data.markdown_writer.update_track_metadata(...)`
5.  `maestro.data.markdown_writer.update_track_heading_status(...)`
6.  `maestro.modules.utils.print_success(...)`.

### `maestro track set <id>`

1.  ... → `maestro.commands.track.set_track_context(track_identifier, args)`
2.  `maestro.commands.track.resolve_track_identifier(...)`
3.  `_parse_todo_safe(...)`
4.  `maestro.config.settings.get_settings()`
5.  `settings.current_track = track_id`, `settings.current_phase = None`, `settings.current_task = None`.
6.  `settings.save()`.
7.  `maestro.modules.utils.print_info(...)`.

### `maestro track discuss [id]`

1.  ... → `maestro.commands.discuss.handle_track_discuss(track_id, args)`
    *   **Purpose:** Delegates to the dedicated AI discussion handler.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/todo.md`: Main Markdown file for active tracks, phases, tasks.
    *   `docs/done.md`: Markdown file for completed tracks, phases, tasks (for `show_track`).
    *   `.maestro/tracks/*.json`: JSON files for individual `Track` objects (via `JsonStore`).
    *   `.maestro/tracks/index.json`: Index for JSON-stored tracks (via `JsonStore`).
    *   `settings.json` (via `get_settings`) for current context.
*   **Writes:**
    *   `docs/todo.md`: Modified during `add_track`, `remove_track`, `edit_track`, `set_track_status` (for Markdown representation).
    *   `.maestro/tracks/*.json`: Created/deleted/updated during `add_track`, `remove_track` (for JSON representation).
    *   `.maestro/tracks/index.json`: Updated by `JsonStore`.
    *   `settings.json`: Updated during `set_track_context`.
*   **Schema:**
    *   Markdown files (`docs/todo.md`, `docs/done.md`) adhere to the implicit schema enforced by `maestro.data.markdown_parser` and `maestro.data.markdown_writer`.
    *   JSON files (`.maestro/tracks/*.json`) adhere to the schema defined by `maestro.tracks.models.Track`.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vim')`: Used to open the user's preferred editor.
*   `maestro.config.settings`: Provides access to global settings, including `current_track`, `current_phase`, `current_task`, and `unicode_symbols`.
*   `docs/todo.md`, `docs/done.md`: Canonical file paths.

## 6. Validation & Assertion Gates

*   **Track ID Resolution:** Ensures a valid track ID is found for operations.
*   **Track ID Format:** `_slugify_track_id` and `_looks_like_track_id` for generating and validating track IDs.
*   **Duplicate Track ID Check:** `add_track` prevents adding tracks with existing IDs.
*   **Track Status Validation:** `normalize_status` and `allowed_statuses` ensure valid status values.
*   **File Existence:** Checks for `docs/todo.md` existence.
*   **Editor Invocation:** Error handling for `FileNotFoundError` if the editor is not found.

## 7. Side Effects

*   Modifies files on the local filesystem (`docs/todo.md`, `.maestro/tracks/*.json`, `settings.json`).
*   Creates temporary files (`tempfile`).
*   Spawns external editor processes (`subprocess`).
*   Prints highly formatted and colored output to console.
*   Changes global application context (`settings.current_track`).

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., track not found, invalid input, file system issues).
*   `print_warning` for non-critical issues (e.g., `docs/todo.md` not found initially).
*   `ValueError` can be raised by internal parsing/validation logic.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_track.py` should cover all subcommands.
    *   Tests for Markdown interaction (extract, replace, update blocks).
    *   Tests for JSON store interaction (add, remove tracks).
    *   Tests for identifier resolution (`resolve_track_identifier`).
    *   Tests for `set_track_context` behavior.
    *   Integration tests for `handle_track_discuss`.
*   **Coverage Gaps:**
    *   Comprehensive testing of status update scenarios, including edge cases for status changes and summary logging.
    *   Robustness testing for malformed `docs/todo.md` files (though `_parse_todo_safe` handles exceptions, detailed recovery might need testing).
    *   Testing of concurrent access if multiple Maestro instances could modify the same files (though this is a CLI, less likely to be an issue).
    *   Testing interaction with phase and task commands to ensure data consistency across Markdown and JSON stores.
