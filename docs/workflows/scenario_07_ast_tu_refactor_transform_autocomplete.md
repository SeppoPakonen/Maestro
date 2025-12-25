# AST/TU workflows — rename, C++→JS transform, autocomplete

## Metadata

- **ID**: WF-07
- **Title**: AST/TU workflows — rename, C++→JS transform, autocomplete
- **Tags**: [ast, tu, translation-unit, repo-resolve, repo-conf, build, refactor, transform, autocomplete]
- **Entry Conditions**: 
  - Repo Resolve (WF-05) has completed successfully
  - RepoConf has identified buildable targets/configs
  - Build succeeds (compile-to-app) for the target package
- **Exit Conditions**: AST generated; operation applied or halted safely
- **Artifacts Created**: AST index/cache, reports, modified sources; grounded in code
- **Failure Semantics**: 
  - Hard stops: TU build failure; ambiguity; verification failure
  - Partial operations are prevented to avoid corruption
- **Related Commands**: `maestro tu`, `maestro repo conf`, `maestro repo resolve`
- **Links To**: WF-05 (Repo Resolve), WF-04 (build loop), RepoConf workflow

## Prerequisites

    This scenario requires a working build environment established by prior workflows:

    1. **Repo Resolve (WF-05)** must have produced packages/targets/configs
    2. **RepoConf** must identify sane output targets/executables
    3. **Build** must succeed (compile-to-app) before TU/AST can run

    If repo-conf is not yet documented, see `docs/workflows/command_repo_conf.md` for the command details.

    ## Branch Boundaries Note

    **Important**: Maestro operates strictly on the current Git branch. AST/TU operations are highly sensitive to the exact state of the source code. Switching branches during an active AST/TU generation or manipulation process (e.g., refactoring, transformation) is **unsupported** and risks corrupting the AST index or applying changes inconsistently. This is an **operational rule**. Users must ensure they are on the desired branch before initiating AST/TU workflows.
## TU/AST Generation Flow

The `maestro tu build` command generates translation unit ASTs with the following contract:

- Selects a package/target/config (from RepoConf)
- For each translation unit:
  - Invokes compiler in "emit AST" mode (specifically uses ClangParser for C++ or other language parsers)
  - Captures AST output and caches it
- Merges per-TU AST into a unified symbol namespace/index
- Stores index/cache/report in `docs/maestro/tu/` directory structure

**Hard stops**:
- TU generation failure treated like compile error (block continuation)

### Command Contract: `maestro tu build`

- **Inputs**: Path to source files, optional language specification, compile flags
- **Outputs**: Cached AST files, symbol index database
- **Exit codes**: 0 for success, 1 for failure
- **Hard stops**: TU generation failure

## Operation 1: Rename Symbol (Safe, AST-Guided)

The rename operation follows these safety-gated steps:

1. **Pre-check**: Symbol exists uniquely (by name + scope + location)
2. **Query references**: Find all occurrences across files (line, column)
3. **Apply edits**: Update all occurrences atomically
4. **Verification gate**:
   - Old symbol no longer resolves unexpectedly
   - New symbol resolves to the intended entity
   - Ambiguity detection triggers **HARD STOP** (no partial corruption)
5. **Optional**: Re-run TU or compile to confirm stability

### Command Contract: `maestro tu references`

- **Inputs**: Symbol name, definition file, definition line
- **Outputs**: List of reference locations (file, line, column)
- **Exit codes**: 0 for success, 1 for failure
- **Hard stops**: Symbol not found

## Operation 2: Transform C++ → JavaScript (Mechanical)

The transformation pipeline follows this sequence:

1. **Pre-step**: Normalize memory model in C++ using SmartPointer (exact name/approach from code)
2. **AST-driven mechanical translation**:
   - Class → JS class/module structure
   - Methods/fields mapping
   - Includes/namespaces handling
3. **Post-step**: Emit JS files, update project structure accordingly
4. **Optional**: Pass result to AI for review *only after* mechanical transform

**Important framing**: AI is used to improve the mechanical transformer, not to "freehand translate".

### Command Contract: `maestro tu transform`

- **Inputs**: Package path, target convention (e.g., 'upp'), language specification, compile flags
- **Outputs**: Transformed source files, updated project structure
- **Exit codes**: 0 for success, 1 for failure
- **Hard stops**: Transformation ambiguity, file write failures

## Operation 3: Autocomplete via AST

The autocomplete operation follows these steps:

1. Locate cursor position in file
2. Map cursor to AST node and scope
3. Enumerate visible symbols and legal completions
4. Return ranked suggestions (ranking method prioritizes same-file symbols)
5. Hard stop / fallback if AST missing/outdated

### Command Contract: `maestro tu complete`

- **Inputs**: File path, line number, column number
- **Outputs**: List of completion suggestions with details
- **Exit codes**: 0 for success, 1 for failure
- **Hard stops**: File not found, AST unavailable

## Additional TU Commands

### `maestro tu query`
- **Purpose**: Query symbols in translation unit
- **Inputs**: Symbol name, file filter, kind filter
- **Outputs**: Symbol information (name, kind, location)

### `maestro tu print-ast`
- **Purpose**: Print AST for a source file
- **Inputs**: File path, output options (types, locations, values, modifiers)
- **Outputs**: Formatted AST representation

### `maestro tu lsp`
- **Purpose**: Start Language Server Protocol server
- **Inputs**: Optional TCP port
- **Outputs**: LSP server connection

### `maestro tu cache`
- **Purpose**: Manage TU cache (clear, stats)
- **Subcommands**: `clear`, `stats`

## Tests Implied by This Scenario

### Unit Tests
- TU invocation command construction
- AST merge/index correctness
- Rename reference enumeration
- Rename verification gate (ambiguity → stop)
- Transform pipeline deterministic mapping for fixtures
- Autocomplete scope resolution

### Integration Fixtures
- Minimal compilable C++ project
- Rename fixture with multiple refs
- Rename ambiguity fixture (should stop)
- Transform fixture (golden JS output)
- Autocomplete fixture (known cursor → suggestions)