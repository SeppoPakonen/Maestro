# Command: `init`

## 1. Command Surface

*   **Command:** `init`
*   **Aliases:** None explicitly defined in `add_init_parser` (though `index.md` may suggest otherwise based on `maestro.py --help` output, the code in `add_init_parser` does not list aliases).
*   **Handler Binding:** `maestro.commands.init.handle_init_command` is bound as the function to handle this command.

## 2. Entrypoint(s)

*   **Exact Python Function(s) Invoked First:** `maestro.commands.init.handle_init_command(args: argparse.Namespace)`
*   **File Path(s):** `/home/sblo/Dev/Maestro/maestro/commands/init.py`

## 3. Call Chain (ordered)

1.  `maestro.main.main()`
    *   **Purpose:** Main CLI entry point.
2.  `maestro.modules.cli_parser.create_main_parser()`
    *   **Purpose:** Initializes `argparse` and registers `add_init_parser`.
3.  `maestro.commands.init.add_init_parser(subparsers)`
    *   **Purpose:** Adds the `init` command and its arguments (`--force`) to the main parser.
4.  `argparse.ArgumentParser.parse_args()` (implicitly called within `main`)
    *   **Purpose:** Parses command-line arguments.
5.  `maestro.main.main()` (dispatches based on `args.command == 'init'`)
    *   **Purpose:** Calls the handler function.
6.  `maestro.commands.init.handle_init_command(args)`
    *   **Purpose:** Executes the initialization logic.
7.  `pathlib.Path.mkdir(parents=True, exist_ok=True)`
    *   **Purpose:** Creates required directories (`docs`, `docs/tracks`, `docs/phases`, `docs/tasks`, `docs/sessions`).
8.  `pathlib.Path.exists()`
    *   **Purpose:** Checks if `docs/Settings.md` or `docs/RepoRules.md` already exist to determine if overwriting is needed.
9.  `builtins.open(path, 'w', encoding='utf-8')`
    *   **Purpose:** Opens `docs/Settings.md` and `docs/RepoRules.md` for writing their default content.
10. `file.write(content)`
    *   **Purpose:** Writes the boilerplate content to the configuration files.

## 4. Core Data Model Touchpoints

*   **Writes:**
    *   Creates directories: `docs`, `docs/tracks`, `docs/phases`, `docs/tasks`, `docs/sessions`.
    *   Creates files: `docs/Settings.md`, `docs/RepoRules.md`.
*   **Reads:**
    *   Checks for the existence of `docs/Settings.md` and `docs/RepoRules.md` using `Path.exists()`.
*   **Schema:** The files `docs/Settings.md` and `docs/RepoRules.md` are created with a predefined Markdown structure and boilerplate text. This structure acts as an implicit schema for how these documents should be formatted for later parsing by other Maestro components (e.g., `maestro/data/markdown_parser.py`, `maestro/config/settings.py`).

## 5. Configuration & Globals

*   **Config Files Written:** This command *creates* the initial `docs/Settings.md` and `docs/RepoRules.md` files. These files are later consumed by other Maestro components to configure behavior and rules.
*   **Env Vars Used:** None directly by `handle_init_command`.
*   **Global Singletons / Module-Level Variables:** None directly.

## 6. Validation & Assertion Gates

*   **File Existence Check:** `Path.exists()` is used to prevent accidental overwrites of `Settings.md` and `RepoRules.md`.
*   **`--force` Argument:** Acts as an override for the file existence check, allowing explicit overwriting.
*   No other complex data validation or assertions are performed by this command. It assumes the file system operations will succeed.

## 7. Side Effects

*   Modifies the local filesystem by creating new directories and files relative to the current working directory (or repository root, depending on where `maestro init` is run).
*   Prints informational messages to `stdout`.

## 8. Error Semantics

*   **Exceptions Caught vs Propagated:** File system errors (e.g., permission denied) from `Path.mkdir` or `open` would propagate as `OSError` or `IOError` if not handled higher up the stack (which is not shown within `handle_init_command`).
*   **User-facing Messaging Path:** Uses `print()` to display status and instructions.
*   **Exit Code Policy:** Implicitly relies on Python's default exit code (0 for success, non-zero for unhandled exceptions).

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Unit/integration tests should exist in `maestro/tests/commands/test_init.py` (or similar).
    *   Tests should verify:
        *   Correct creation of all specified directories.
        *   Correct creation and content of `docs/Settings.md` and `docs/RepoRules.md`.
        *   Behavior when `--force` is used (overwriting existing files).
        *   Behavior when files already exist and `--force` is *not* used (no overwrite, prints message).
        *   Handling of non-existent parent directories (ensuring `parents=True` works).
*   **Coverage Gaps:**
    *   Testing of permission denied scenarios for directory/file creation (e.g., running `init` in a read-only location).
    *   Ensure boilerplate content is consistently updated if command logic changes.
