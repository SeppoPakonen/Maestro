# Command: `wsession/ws`

## 1. Command Surface

*   **Command:** `wsession`
*   **Aliases:** `ws`
*   **Handler Binding:** `maestro.main.main` dispatches to various `handle_wsession_*` functions within `maestro/commands/work_session.py`.

## 2. Entrypoint(s)

*   **Primary Dispatchers:** `maestro.commands.work_session.handle_wsession_list`, `handle_wsession_show`, `handle_wsession_tree`, `handle_wsession_breadcrumbs`, `handle_wsession_timeline`, `handle_wsession_stats`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/work_session.py`

## 3. Call Chain (ordered)

The `handle_wsession_*` functions serve as entry points for each subcommand, providing different views and tools for inspecting AI work sessions.

### Common Flow for most `wsession` subcommands

1.  `maestro.main.main()` → `maestro.commands.work_session.handle_wsession_* (args)`
    *   **Purpose:** Entry point for various `wsession` subcommands.
2.  `maestro.commands.work_session._resolve_session_id(args.session_id)` (for commands that take a `session_id`).
    *   **Purpose:** Resolves "latest" to the actual ID of the most recently modified session, or returns the provided ID.
    *   **Internal Call Chain:** `maestro.work_session.list_sessions()`.
3.  `maestro.work_session.list_sessions()` (for listing all sessions or finding "latest").
4.  `maestro.work_session.load_session(session_file)` (for commands that operate on a single session).
    *   **Purpose:** Loads a `WorkSession` object from its `session.json` file.

### `maestro wsession list`

1.  ... → `maestro.commands.work_session.handle_wsession_list(args)`
2.  `maestro.work_session.list_sessions(session_type=args.type, status=args.status)`
    *   **Purpose:** Retrieves sessions, applying type and status filters.
3.  Further filtering by `since` timestamp and `entity`.
4.  Sorting logic based on `sort_by` and `reverse` arguments.
5.  `maestro.visualization.table.SessionTableFormatter().format_table(sessions)`
    *   **Purpose:** Renders the list of sessions into a formatted table.

### `maestro wsession show <id>`

1.  ... → `maestro.commands.work_session.handle_wsession_show(args)`
2.  `_resolve_session_id(args.session_id)`.
3.  Locates the `docs/sessions/<session_id>/session.json` file (or in nested directories).
4.  `maestro.work_session.load_session(session_file)`.
5.  `maestro.visualization.detail.SessionDetailFormatter().format_details(session, show_all_breadcrumbs=args.show_all_breadcrumbs)`.
    *   **Purpose:** Renders comprehensive details of the session.
6.  `maestro.commands.work_session.export_session_json(session, args.export_json)` (if `--export-json`).
7.  `maestro.commands.work_session.export_session_markdown(session, args.export_md)` (if `--export-md`).

### `maestro wsession tree`

1.  ... → `maestro.commands.work_session.handle_wsession_tree(args)`
2.  `maestro.work_session.get_session_hierarchy()`
    *   **Purpose:** Constructs a parent-child hierarchy of all sessions.
3.  `maestro.commands.work_session._filter_hierarchy_by_status(hierarchy, args.filter_status)` (if `--status` filter).
4.  `maestro.visualization.tree.SessionTreeRenderer().render(hierarchy, max_depth=args.depth)`.
    *   **Purpose:** Renders the session hierarchy as an ASCII tree.
5.  `maestro.commands.work_session._print_breadcrumb_counts(hierarchy["root"])` (if `--show-breadcrumbs`).

### `maestro wsession breadcrumbs <id>`

1.  ... → `maestro.commands.work_session.handle_wsession_breadcrumbs(args)`
2.  `_resolve_session_id(args.session_id)`.
3.  Locates the session directory.
4.  `(If args.summary)` `maestro.breadcrumb.get_breadcrumb_summary(session_id)`.
5.  `(Else)` `maestro.breadcrumb.list_breadcrumbs(session_id, depth=args.depth, limit=args.limit)`.
    *   **Purpose:** Retrieves and displays breadcrumb records for the session.

### `maestro wsession timeline <id>`

1.  ... → `maestro.commands.work_session.handle_wsession_timeline(args)`
2.  `_resolve_session_id(args.session_id)`.
3.  Locates the session directory.
4.  `maestro.breadcrumb.reconstruct_session_timeline(session_id)`.
    *   **Purpose:** Reconstructs a chronological sequence of all AI events within the session.
5.  `print()` for formatted output.

### `maestro wsession stats [id]`

1.  ... → `maestro.commands.work_session.handle_wsession_stats(args)`
2.  `(If session_id provided)` Loads specific session.
3.  `maestro.stats.session_stats.calculate_session_stats(session)` (for single session).
4.  `maestro.stats.session_stats.calculate_tree_stats(session)` (if `--tree`).
5.  `maestro.visualization.detail.SessionDetailFormatter().format_statistics(session)`.
6.  `(If no session_id)` Aggregates statistics across all sessions (using `maestro.work_session.list_sessions()` and `calculate_session_stats()`).

### Export Helpers (`export_session_json`, `export_session_markdown`)

These functions are called by `handle_wsession_show` when export flags are used. They gather session data, breadcrumbs, statistics, and child sessions, then format and write them to the specified output file.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/sessions/<session_id>/session.json`: Main storage for `WorkSession` metadata.
    *   `docs/sessions/<session_id>/breadcrumbs.jsonl`: Stores individual breadcrumb records.
*   **Writes:**
    *   User-specified output paths for `export-json` and `export-md` (`handle_wsession_show`).
*   **Schema:** `WorkSession` and `Breadcrumb` objects are serialized to JSON.

## 5. Configuration & Globals

*   `docs/sessions/`: Canonical base directory for all work session data.
*   `logging` module for internal debug messages.

## 6. Validation & Assertion Gates

*   **Session ID Resolution:** `_resolve_session_id` handles "latest" and validates session ID existence.
*   **Session File Existence:** Checks if `session.json` exists for a given ID.
*   Filter and sort argument validation (`argparse`).
*   `datetime.fromisoformat` for date parsing.

## 7. Side Effects

*   Reads extensively from `docs/sessions/` directory to gather session metadata and breadcrumbs.
*   Writes exported session data to user-specified files.
*   Prints highly formatted, sometimes graphical (tree), output to console.
*   Uses `logging` for internal debug messages.

## 8. Error Semantics

*   `print()` and `logging.error` for errors.
*   `FileNotFoundError` if a session or session file cannot be found.
*   `JSONDecodeError` if session files are corrupted.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_work_session.py` should cover all subcommands.
    *   Tests for filtering, sorting, and display of session lists.
    *   Tests for accurate display of session details, hierarchy, breadcrumbs, and timeline.
    *   Tests for correct calculation of session statistics (single and tree).
    *   Tests for JSON and Markdown export functionality.
    *   Tests for `_resolve_session_id` logic (e.g., "latest" resolution, partial ID matching).
    *   Tests for session file location logic (`handle_wsession_show`) under nested directory structures.
*   **Coverage Gaps:**
    *   Comprehensive testing of hierarchical filtering for `wsession tree --status`.
    *   Robustness testing against corrupted session or breadcrumb JSON files.
    *   Performance testing for sessions with a very large number of breadcrumbs or deeply nested hierarchies.
    *   Ensuring consistency of output across various terminal sizes and `unicode_symbols` settings.
    *   Testing with various `related_entity` types during filtering.