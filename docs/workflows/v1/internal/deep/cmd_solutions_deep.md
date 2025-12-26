# Command: `solutions`

## 1. Command Surface

*   **Command:** `solutions`
*   **Aliases:** None
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.solutions.handle_solutions_command`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.solutions.handle_solutions_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/solutions.py`
*   **Specific Subcommand Handlers:** `_handle_list`, `_handle_show`, `_handle_add`, `_handle_remove`, `_handle_edit`.

## 3. Call Chain (ordered)

The `handle_solutions_command` function acts as the central router, dispatching to various specialized `_handle_*` functions based on the `solutions_subcommand`.

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.solutions.handle_solutions_command(args)`
    *   **Purpose:** Entry point for the `solutions` command.
2.  `maestro.commands.solutions._find_repo_root()`
    *   **Purpose:** Locates the repository root by searching for a `.maestro/` directory.

### `maestro solutions list`

1.  ... → `maestro.commands.solutions._handle_list(repo_root, include_external)`
2.  `maestro.solutions.solution_store.list_solutions(repo_root)`
    *   **Purpose:** Reads local solution Markdown files from `docs/solutions/`.
3.  `maestro.solutions.solution_store.list_external_solutions()` (if `include_external`).
    *   **Purpose:** Retrieves solutions from external sources (e.g., global registry).
4.  `print()` for formatted output.

### `maestro solutions show <id>`

1.  ... → `maestro.commands.solutions._handle_show(repo_root, solution_id)`
2.  `maestro.commands.solutions._find_solution_path(repo_root, solution_id)`
    *   **Purpose:** Locates the specific `docs/solutions/<solution_id>.md` file.
3.  `maestro.solutions.solution_store.load_solution(solution_path)`
    *   **Purpose:** Parses the Markdown file into a `SolutionRecord` object.
4.  `print()` for formatted output.

### `maestro solutions add [...]`

1.  ... → `maestro.commands.solutions._handle_add(repo_root, args)`
2.  `maestro.solutions.solution_store.SolutionDetails(...)`
    *   **Purpose:** Creates an object to hold the new solution's data.
3.  `maestro.solutions.solution_store.write_solution(details, repo_root, solution_id=args.solution_id)`
    *   **Purpose:** Persists the new solution to `docs/solutions/<solution_id>.md`.
4.  `maestro.commands.solutions._open_editor(solution_path)` (if `--edit` or default fields used).
    *   **Purpose:** Opens the newly created solution in `$EDITOR`.

### `maestro solutions remove <id>`

1.  ... → `maestro.commands.solutions._handle_remove(repo_root, solution_id)`
2.  `maestro.solutions.solution_store.delete_solution(repo_root, solution_id)`
    *   **Purpose:** Deletes the solution's Markdown file from `docs/solutions/`.

### `maestro solutions edit <id>`

1.  ... → `maestro.commands.solutions._handle_edit(repo_root, solution_id)`
2.  `maestro.commands.solutions._find_solution_path(repo_root, solution_id)`
3.  `maestro.commands.solutions._open_editor(solution_path)`.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/solutions/*.md`: Individual Markdown files storing solution records.
    *   External sources (conceptual, via `list_external_solutions`).
*   **Writes:**
    *   `docs/solutions/*.md`: Created by `_handle_add`, deleted by `_handle_remove`, modified by `_handle_edit` (via editor).
*   **Schema:** Solutions are stored in a custom Markdown format enforced by `maestro.solutions.solution_store` with metadata at the top and structured sections.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vim')`: User's preferred editor.
*   `docs/solutions/`: Canonical directory for solution files.

## 6. Validation & Assertion Gates

*   Solution ID uniqueness (handled by `solution_store.write_solution` implicitly via file naming).
*   File existence checks for solution Markdown files.
*   Editor invocation error handling.
*   Argument validation (`argparse`).

## 7. Side Effects

*   Modifies existing Markdown files (`docs/solutions/*.md`).
*   Creates new Markdown files (`docs/solutions/*.md`).
*   Invokes external editor (`subprocess`).
*   Prints formatted output to console.

## 8. Error Semantics

*   `print()` messages for errors, `sys.exit(1)` for critical failures.
*   `OSError` for editor issues.
*   "Solution not found" messages for non-existent IDs.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_solutions.py` should cover all `_handle_*` functions.
    *   Tests for solution CRUD operations.
    *   Tests for `_find_solution_path` and `_open_editor`.
    *   Tests for `list_external_solutions` (mocking external integration).
    *   Tests for default values during solution creation.
*   **Coverage Gaps:**
    *   Robustness testing for malformed `docs/solutions/*.md` files.
    *   Comprehensive testing of search functionality (keywords, regex, context).
    *   Testing editor integration across various editors.
