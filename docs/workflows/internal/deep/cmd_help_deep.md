# Command: `help`

## 1. Command Surface

*   **Command:** `help`
*   **Aliases:** `h`
*   **Handler Binding:** The `help` command is directly handled within `maestro.main.main` by checking `args.command == 'help'` or `args.help`, leading to `parser.print_help()`.

## 2. Entrypoint(s)

*   **Exact Python Function(s) Invoked First:** `maestro.main.main`
*   **File Path(s):** `/home/sblo/Dev/Maestro/maestro/main.py`

## 3. Call Chain (ordered)

1.  `maestro.main.main()`
    *   **Purpose:** Main entry point; orchestrates command parsing and dispatch.
2.  `maestro.modules.cli_parser.create_main_parser()`
    *   **Purpose:** Initializes and configures the `argparse.ArgumentParser` instance with all commands and arguments.
3.  `argparse.ArgumentParser.parse_args()` (implicitly called within `main`)
    *   **Purpose:** Parses command-line arguments into an `args` namespace object.
4.  `maestro.main.main()` (conditional branch)
    *   **Purpose:** Detects if the `help` command was requested based on `args.command` or `args.help`.
5.  `maestro.modules.cli_parser.StyledArgumentParser.print_help(file=None)`
    *   **Purpose:** Overrides the default `argparse` help printing to apply custom styling and display a banner.
6.  `maestro.modules.cli_parser.StyledArgumentParser.format_help()` (called by `print_help`)
    *   **Purpose:** Retrieves the raw help text from `argparse` and applies syntax highlighting and other styling.
7.  `argparse.ArgumentParser.format_help()` (super call within `StyledArgumentParser.format_help()`)
    *   **Purpose:** Generates the raw, unstyled help message from the parser's definition.
8.  `maestro.modules.cli_parser._filter_suppressed_help(...)`
    *   **Purpose:** Removes suppressed help messages before styling.
9.  `maestro.modules.utils.styled_print(...)`, `maestro.modules.utils.print_subheader(...)`, `maestro.modules.utils.Colors`
    *   **Purpose:** Utility functions and constants used for printing colored and formatted output to the console.
10. `pyfiglet.figlet_format("MAESTRO", font="letters")` (conditional import/call)
    *   **Purpose:** Generates ASCII art for the "MAESTRO" banner if `pyfiglet` is installed.

## 4. Core Data Model Touchpoints

*   None. The `help` command is purely informational and does not interact with persistent data stores.

## 5. Configuration & Globals

*   **Config Files Read:** None.
*   **Env Vars Used:** None.
*   **Global Singletons / Module-Level Variables:**
    *   `maestro.__version__`: Set in `/home/sblo/Dev/Maestro/maestro/__init__.py`. Consumed in `maestro.modules.cli_parser.create_main_parser()` for `--version` and `StyledArgumentParser.print_help()` for the footer.
    *   `maestro.modules.utils.Colors`: Defined in `/home/sblo/Dev/Maestro/maestro/modules/utils.py`. Consumed by `StyledArgumentParser` for coloring output.
    *   `maestro.modules.utils.styled_print`: Defined in `/home/sblo/Dev/Maestro/maestro/modules/utils.py`. Consumed by `StyledArgumentParser` for printing styled text.
    *   `maestro.modules.utils.print_subheader`: Defined in `/home/sblo/Dev/Maestro/maestro/modules/utils.py`. Consumed by `StyledArgumentParser` for printing styled subheaders.

## 6. Validation & Assertion Gates

*   None directly within the `help` command's logic. Argument parsing is handled by `argparse`, which implicitly validates the command structure.

## 7. Side Effects

*   Prints formatted text (CLI usage, options, banner, version) to standard output (stdout).

## 8. Error Semantics

*   **Exceptions Caught vs Propagated:** The `help` command itself does not typically raise specific exceptions beyond those handled by `argparse` during initial parsing. If `argparse` cannot parse the arguments, it will `exit()` or raise `SystemExit`.
*   **User-facing Messaging Path:** Output is directly printed to stdout by `StyledArgumentParser.print_help()`.
*   **Exit Code Policy:** Typically exits with `0` for successful help display, or `2` (default `argparse` error) if invalid arguments prevent help from being shown.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Likely covered by integration tests that invoke `maestro --help` or `maestro help`.
    *   Unit tests for `StyledArgumentParser` in `maestro/tests/test_cli_parser.py` (or similar) should verify styling and banner generation.
*   **Coverage Gaps:**
    *   Ensure `pyfiglet` import failure (and graceful fallback) is explicitly tested.
    *   Test output correctness with various terminal configurations (e.g., no color support if that's a factor, though not explicitly handled here).
