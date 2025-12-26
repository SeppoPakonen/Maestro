# Command: `tu`

## 1. Command Surface

*   **Command:** `tu`
*   **Aliases:** None
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.tu.handle_tu_command`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.tu.handle_tu_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/tu.py`
*   **Specific Subcommand Handlers:** `handle_tu_build_command`, `handle_tu_info_command`, `handle_tu_query_command`, `handle_tu_complete_command`, `handle_tu_references_command`, `handle_tu_lsp_command`, `handle_tu_cache_clear_command`, `handle_tu_cache_stats_command`, `handle_tu_transform_command`, `handle_tu_print_ast_command`, `handle_tu_draft_command`.

## 3. Call Chain (ordered)

The `handle_tu_command` function acts as the central router, dispatching to various specialized `handle_tu_*_command` functions based on the `tu_subcommand`.

### Common Flow for most `tu` subcommands involving parsing

1.  `maestro.main.main()` → `maestro.commands.tu.handle_tu_command(args)`
    *   **Purpose:** Entry point for the `tu` command.
2.  `maestro.commands.tu.detect_language_from_path(file_path)`
    *   **Purpose:** Determines the programming language of a file based on its extension.
3.  `maestro.commands.tu.get_parser_by_language(lang)`
    *   **Purpose:** Returns the appropriate language parser (`ClangParser`, `JavaParser`, `KotlinParser`, `PythonParser`) implementing `TranslationUnitParser`.

### `maestro tu build`

1.  ... → `maestro.commands.tu.handle_tu_build_command(args)`
2.  `detect_language_from_path(...)`, `get_parser_by_language(...)`.
3.  `maestro.commands.tu.get_files_by_language(args.path, lang)`
    *   **Purpose:** Collects all source files for the detected language.
4.  `maestro.tu.TUBuilder(parser, cache_dir=args.output)`
    *   **Purpose:** Initializes the Translation Unit builder.
5.  `(If args.force)` `shutil.rmtree(cache_dir)`, `cache_dir.mkdir(...)`.
    *   **Purpose:** Clears and recreates the cache directory.
6.  `builder.build(files=files, compile_flags=args.compile_flags)`.
    *   **Purpose:** Parses and builds TUs for all specified files, caching results.

### `maestro tu query`

1.  ... → `maestro.commands.tu.handle_tu_query_command(args)`
2.  `maestro.tu.SymbolIndex(index_path)`
    *   **Purpose:** Initializes the symbol index for querying.
3.  `index.query(name=args.symbol, file_path=args.file, kind=args.kind)`.
    *   **Purpose:** Searches for symbols matching criteria.
4.  `json.dumps(...)` (if `--json`).

### `maestro tu complete`

1.  ... → `maestro.commands.tu.handle_tu_complete_command(args)`
2.  `maestro.tu.CompletionProvider()`.
3.  `provider.get_completions(file_path, line, column)`.
4.  `json.dumps(...)` (if `--json`).

### `maestro tu references`

1.  ... → `maestro.commands.tu.handle_tu_references_command(args)`
2.  `maestro.tu.SymbolIndex(index_path)`.
3.  `index.find_references(symbol_name, file_path, line)`.
4.  `json.dumps(...)` (if `--json`).

### `maestro tu lsp`

1.  ... → `maestro.commands.tu.handle_tu_lsp_command(args)`
2.  `maestro.tu.lsp_server.MaestroLSPServer()`.
3.  `server.start_tcp(args.port)` or `server.start_io()`.

### `maestro tu cache clear`

1.  ... → `maestro.commands.tu.handle_tu_cache_clear_command(args)`
2.  `shutil.rmtree(cache_dir)`.

### `maestro tu cache stats`

1.  ... → `maestro.commands.tu.handle_tu_cache_stats_command(args)`
2.  `Path('.maestro/tu/cache').rglob('*.ast')`.
3.  Calculates and prints total size and count.

### `maestro tu transform`

1.  ... → `maestro.commands.tu.handle_tu_transform_command(args)`
2.  `detect_language_from_path(...)`, `get_parser_by_language(...)`, `get_files_by_language(...)`.
3.  `maestro.tu.transformers.UppConventionTransformer(package_name)`.
4.  **Phase 1: Header Generation:** Parses files (via `parser.parse_file`), builds dependency graph (`transformer._build_dependency_graph`), computes declaration order, generates primary header (`transformer.generate_primary_header`).
5.  Writes generated header to file.
6.  **Phase 2: Source Transformation:** Transforms each document (`transformer.transform_document`), updates includes (`transformer.update_cpp_includes`).
7.  Writes updated source files back.

### `maestro tu print-ast`

1.  ... → `maestro.commands.tu.handle_tu_print_ast_command(args)`
2.  `detect_language_from_path(...)`, `get_parser_by_language(...)`.
3.  `parser.parse_file(file_path, compile_flags)`.
4.  `maestro.tu.ASTPrinter(...)`.
5.  `printer.print_document(document)`.
6.  Writes output to file or stdout.

### `maestro tu draft`

1.  ... → `maestro.commands.tu.handle_tu_draft_command(args)`
2.  `detect_language_from_path(...)`, `get_parser_by_language(...)`, `get_files_by_language(...)`.
3.  `maestro.tu.code_generator.CodeGenerator(lang=lang)`.
4.  `generator.generate_class(class_name, prompt)` or `generator.generate_function(func_name, prompt)`.
5.  Writes generated code to files in `args.output`.
6.  Conditionally links to phase/task by appending to `docs/todo-classes.md`.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   Source code files (`.cpp`, `.java`, `.py`, etc.).
    *   TU cache files (`.maestro/tu/cache/*.ast`).
    *   Symbol index database (`.maestro/tu/analysis/symbols.db`).
*   **Writes:**
    *   Generated TU cache files (`.maestro/tu/cache/*.ast`).
    *   Symbol index database (`.maestro/tu/analysis/symbols.db`).
    *   Output files for `print-ast` and `transform` commands.
    *   Generated draft files (`.maestro/tu/draft/`).
    *   `docs/todo-classes.md` (for draft linking).
*   **Schema:** The internal representation of parsed code is an Abstract Syntax Tree (AST), serialized as `.ast` files. Symbol index is a database.

## 5. Configuration & Globals

*   `compile_flags` for C/C++ parsing.
*   `.maestro/tu/cache/`: Default directory for TU cache.
*   `.maestro/tu/analysis/symbols.db`: Default path for symbol index.
*   `lang_ext_map` in `get_file_extension` helper.

## 6. Validation & Assertion Gates

*   **Language Support:** `get_parser_by_language` checks for supported languages.
*   **File Existence:** Checks for source files and cache directories.
*   **Compile Flags:** Passed to parsers for accurate analysis.
*   Symbol index existence for `query` and `references`.
*   JSON output validation (`json.dumps`).

## 7. Side Effects

*   Reads and parses source code files, potentially intensive CPU/memory usage.
*   Creates/updates cached Translation Units and symbol indices.
*   Modifies source code files (in `transform` command).
*   Generates new source code files (in `draft` command).
*   Launches long-running LSP server process.
*   Prints extensive, formatted code details to console or files.

## 8. Error Semantics

*   `print()` messages for errors, `sys.exit(1)` for critical failures (e.g., unsupported language, file not found, parsing error).
*   `ValueError` for invalid language or other input.
*   `EngineError` for underlying parsing issues.
*   `KeyboardInterrupt` is handled for LSP server.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/tu/` directory should contain unit/integration tests for each parser, `TUBuilder`, `SymbolIndex`, `CompletionProvider`, `ASTPrinter`, `UppConventionTransformer`, `CodeGenerator`, and `MaestroLSPServer`.
    *   Tests for all `handle_tu_*_command` functions covering successful execution, error conditions, and various options (e.g., `--json`, `--verbose`, `--force`).
    *   Cross-language testing for `build`, `query`, `complete`, `references`, `print-ast`, `draft`.
    *   Tests for cache clear and stats.
    *   Tests for `transform`'s two-phase process, including header generation and source file modification.
*   **Coverage Gaps:**
    *   Thorough testing of `transform` for various C++ code styles and complex dependency scenarios.
    *   Performance testing on large codebases.
    *   Robustness testing against malformed source code, ensuring graceful error handling by parsers.
    *   Full integration tests for LSP server functionality with external clients.
    *   Comprehensive testing of all `ASTPrinter` options and their output.
    *   Testing `draft` with AI prompts.
