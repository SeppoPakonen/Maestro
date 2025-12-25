# Command: `repo`

## 1. Command Surface

*   **Command:** `repo`
*   **Aliases:** `rp` (from `maestro.modules.cli_parser.normalize_command_aliases`)
*   **Handler Binding:** `maestro.commands.repo.handle_repo_command`

## 2. Entrypoint(s)

*   **Exact Python Function(s) Invoked First:** `maestro.commands.repo.handle_repo_command(args: argparse.Namespace)`
*   **File Path(s):** `/home/sblo/Dev/Maestro/maestro/commands/repo.py`

## 3. Call Chain (ordered)

The `repo` command dispatches to numerous subcommands, each with its own specific call chain. The `handle_repo_command` acts as the central router.

### `maestro repo resolve` (and `maestro repo refresh all` which calls resolve)

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
    *   **Purpose:** Entry point for the `repo` command.
2.  `maestro.commands.repo.find_repo_root(start_path)` (if `args.find_root` or `scan_path` is not provided)
    *   **Purpose:** Locates the repository root by searching for a `.maestro/` directory.
3.  `maestro.repo.scanner.scan_upp_repo_v2(scan_path, verbose, include_user_config)`
    *   **Purpose:** Performs the comprehensive repository scan (discovering packages, assemblies, unknown paths across all build systems).
    *   **Internal Call Chain (from `subsystem_repo_resolve`):** `os.walk` → `upp_parser.parse_upp_file` → `build_systems.scan_all_build_systems` → `uplusplus_var_reader.read_user_assemblies` → `assembly.detect_assemblies` → `scanner.infer_internal_packages` (which uses `grouping.AutoGrouper`).
4.  `maestro.commands.repo.write_repo_artifacts(repo_root, repo_result, verbose)`
    *   **Purpose:** Persists the scan results to JSON and summary files in `.maestro/repo/`.
5.  `maestro.modules.utils.print_header(...)`, `print_info(...)`, `print_success(...)`
    *   **Purpose:** Provides formatted output to the user.
6.  `maestro.global_index.update_global_repo_index(repo_root, verbose)` (called by `handle_repo_refresh_all`)
    *   **Purpose:** Updates a global index of repositories managed by Maestro.

### `maestro repo show`

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
2.  `maestro.commands.repo.load_repo_index(repo_root)`
    *   **Purpose:** Loads the `index.json` file from `.maestro/repo/`.
3.  `maestro.commands.repo.find_repo_root()` (implicitly called by `load_repo_index` if `repo_root` is None)
4.  `maestro.modules.utils.print_header(...)`, `print_info(...)`
    *   **Purpose:** Displays human-readable summary of scan results.

### `maestro repo pkg <action>` (e.g., `maestro repo pkg info <pkg_name>`)

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
2.  `maestro.commands.repo.load_repo_index(repo_root)`
3.  `maestro.commands.repo.find_repo_root()` (implicitly called by `load_repo_index`)
4.  (Conditional) Package matching logic (e.g., `pkg_name.lower() in p.get('name', '').lower()`).
5.  Dispatch to specific package handler:
    *   `maestro.commands.repo.handle_repo_pkg_list(packages, json_output, repo_root)`
    *   `maestro.commands.repo.handle_repo_pkg_info(pkg, json_output)`
    *   `maestro.commands.repo.handle_repo_pkg_files(pkg, json_output)`
    *   `maestro.commands.repo.handle_repo_pkg_groups(pkg, json_output, show_groups, group_filter)`
    *   `maestro.commands.repo.handle_repo_pkg_search(pkg, query, json_output)`
    *   `maestro.commands.repo.handle_repo_pkg_tree(pkg, all_packages, json_output, deep, config_flags)`
        *   **Internal Call Chain:** `maestro.commands.repo.build_tree()` (recursive) → `maestro.repo.upp_conditions.match_when()` (for conditional dependencies).
    *   `maestro.commands.repo.handle_repo_pkg_conf(pkg, json_output)`
        *   **Internal Call Chain:** `maestro.repo.build_config.get_package_config(package_info)`

### `maestro repo hier`

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
2.  `maestro.commands.repo.load_hierarchy(repo_root)` (if not `rebuild`)
3.  `maestro.commands.repo.load_repo_index(repo_root)` (if `rebuild` or no hierarchy found)
4.  `maestro.commands.repo.build_repo_hierarchy(repo_scan, repo_root)`
    *   **Purpose:** Constructs the hierarchical representation from `RepoScanResult`.
5.  `maestro.commands.repo.save_hierarchy(hierarchy, repo_root, verbose)` (if newly built)
6.  `maestro.commands.repo.load_hierarchy_overrides(repo_root)`
7.  `maestro.commands.repo.merge_hierarchy_overrides(hierarchy, overrides)`
    *   **Purpose:** Applies user-defined overrides to the generated hierarchy.
8.  `maestro.commands.repo.print_hierarchy_tree(hierarchy, show_files)`
    *   **Purpose:** Renders the hierarchy to console using `maestro.modules.utils.Colors`.

### `maestro repo hier edit`

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
2.  `maestro.commands.repo.handle_repo_hier_edit(repo_root)`
3.  `builtins.open(overrides_file, 'w', ...)` (to create template if needed).
4.  `subprocess.run([editor, overrides_file], check=True)`
    *   **Purpose:** Invokes the user's `$EDITOR`.

### `maestro repo rules <action>` (e.g., `maestro repo rules edit`)

1.  `maestro.main.main()` → `maestro.commands.repo.handle_repo_command(args)`
2.  `maestro.commands.repo.handle_repo_rules_show(repo_root)` or `handle_repo_rules_edit(repo_root)` or `handle_repo_rules_inject(repo_root, context)`
3.  `builtins.open(rules_file, 'r'/'w', ...)`
4.  `subprocess.run([editor, rules_file])` (for `edit`).

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   Repository structure: Filesystem (`os.walk`, `pathlib.Path`).
    *   Scan results: `.maestro/repo/index.json`, `.maestro/repo/assemblies.json`, `.maestro/repo/state.json`.
    *   User-defined assembly overrides: `~/.config/u++/ide/*.var`.
    *   Hierarchy overrides: `.maestro/repo/hierarchy_overrides.json`.
    *   Repository rules/conventions: `docs/RepoRules.md`.
*   **Writes:**
    *   Scan results and summary: `.maestro/repo/index.json`, `.maestro/repo/index.summary.txt`, `.maestro/repo/assemblies.json`, `.maestro/repo/state.json`.
    *   Repository hierarchy: `.maestro/repo/hierarchy.json`.
    *   Hierarchy overrides template: `.maestro/repo/hierarchy_overrides.json`.
*   **Schema:** The JSON files (`index.json`, `assemblies.json`, `state.json`, `hierarchy.json`, `hierarchy_overrides.json`) have specific JSON schemas corresponding to the `RepoScanResult`, `AssemblyInfo`, `PackageInfo`, `InternalPackage`, and hierarchical structures. `docs/RepoRules.md` has an implicit Markdown structure.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vi')`: Uses the user's preferred text editor.
*   `.maestro/`: Marker directory for repository root.
*   `docs/RepoRules.md`: Default file for repository rules.
*   `maestro.global_index`: Updated during `repo refresh all`.

## 6. Validation & Assertion Gates

*   **Repository Root:** `find_repo_root` ensures operations are performed within a valid Maestro repository.
*   **File Existence:** Checks for presence of `index.json`, `docs/RepoRules.md` before attempting to load/edit.
*   **Path Validity:** Validates `scan_path` exists and is a directory.
*   **Package Matching:** For `repo pkg` commands, it handles no match, single match, and multiple matches.
*   **Dependency Tree:** `handle_repo_pkg_tree` includes cycle detection and duplicate suppression.
*   **U++ Conditions:** `maestro.repo.upp_conditions.match_when` applies conditional logic based on build flags for dependency trees.
*   **JSON Schema:** Implicitly relies on the correctness of JSON files loaded.

## 7. Side Effects

*   Extensive file system I/O (reads and writes to `.maestro/repo/` and `docs/`).
*   Spawns external editor processes.
*   Generates highly structured and formatted console output.
*   Updates a global Maestro repository index.

## 8. Error Semantics

*   `SystemExit` (via `sys.exit(1)`) is used for critical errors (e.g., repo root not found, index not found, invalid package name).
*   `print_error`, `print_warning`, `print_info` are used for user feedback.
*   `FileNotFoundError`, `subprocess.CalledProcessError` are handled during editor invocation.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_repo.py` should cover all subcommands.
    *   Integration tests that run `maestro repo resolve`, then `maestro repo show`, `maestro repo pkg`, etc., and verify the output and file contents.
    *   Tests for `find_repo_root` under various directory structures.
    *   Tests for `write_repo_artifacts` ensuring atomic writes.
    *   Tests for `handle_repo_pkg_tree` with different dependency scenarios (including cycles and conditional dependencies).
    *   Tests for hierarchy override merging.
*   **Coverage Gaps:**
    *   Comprehensive testing of all possible combinations of flags and subcommands.
    *   Performance testing on large repositories.
    *   Testing with corrupted or incomplete `.maestro/repo` files.
    *   Testing the interaction of `repo refresh all` with the (currently placeholder) convention and rules analysis steps once implemented.
